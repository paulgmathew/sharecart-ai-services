# ShareCart AI JWT Authentication Guide

## 1. Purpose

This guide explains how the ShareCart AI API should authenticate JWT access tokens issued by the ShareCart Spring Boot backend.

The AI API does not issue tokens.
It only validates tokens received in the Authorization header.

## 2. Token Source and Flow

1. User signs in through Spring Boot auth endpoints.
2. Spring Boot returns a bearer token.
3. Flutter sends the same token to the AI API.
4. AI API validates the token locally and allows or rejects the request.

## 3. Required Header Format

Authorization header format:

Authorization: Bearer <token>

Rules:
- Header must be present.
- Scheme must be Bearer.
- Token must be non-empty.

If invalid, return 401 Unauthorized.

## 4. Spring Boot Token Shape (What To Expect)

From Spring Boot implementation:
- Subject claim contains user id.
- Email is present as custom email claim.
- Expiration exp claim is present.
- Token is signed with HMAC using shared secret.
- Current environment resolves to HS512 with the configured secret length.

Claim mapping for AI API:
- user_id = sub
- email = email
- expires_at = exp

## 5. Validation Rules in AI API

Validation must perform all checks:

1. Signature verification using the same shared secret.
2. Allowed algorithm check, matching Spring Boot output.
3. Expiration check.
4. Structural validation (well-formed JWT).
5. Required claim check:
   - sub must exist
   - exp must exist

If any check fails, reject with 401.

## 6. Secret Management

Use environment variables only.

Recommended env vars:
- APP_JWT_SECRET
- APP_JWT_ALGORITHM=HS512

Rules:
- Do not hardcode secrets in source code.
- Keep AI API secret exactly the same as Spring Boot secret.
- Rotate secrets with coordinated deployment.
- Use different secrets across environments (dev, staging, prod).

## 7. FastAPI + PyJWT Reference Implementation

Dependencies:
- fastapi
- pyjwt

Example auth dependency:

```python
from fastapi import Header, HTTPException, status
import jwt
import os

JWT_SECRET = os.getenv("APP_JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("APP_JWT_ALGORITHM", "HS512")

def authenticate_bearer_token(authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization scheme")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    return {
        "user_id": user_id,
        "email": email
    }
```

Usage in route:

```python
from fastapi import Depends, FastAPI

app = FastAPI()

@app.post("/api/v1/receipt/extract")
async def extract_receipt(user=Depends(authenticate_bearer_token)):
    return {"success": True, "authenticatedUserId": user["user_id"]}
```

## 8. Error Response Contract

Use consistent JSON for auth failures:

- Status: 401
- Body:
  - success: false
  - message: short auth failure reason

Example:

```json
{
  "success": false,
  "message": "Invalid token"
}
```

## 9. Testing Checklist

1. Valid token from Spring Boot is accepted.
2. Expired token is rejected.
3. Token signed with wrong secret is rejected.
4. Missing Authorization header is rejected.
5. Non-Bearer Authorization header is rejected.
6. Token with missing sub is rejected.

## 10. Security Notes

- Never trust client-sent user identifiers outside JWT claims.
- Always derive user identity from validated token claims.
- Do not log full tokens in application logs.
- Mask or hash sensitive auth artifacts in logs.
