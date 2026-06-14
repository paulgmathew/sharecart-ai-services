# sharecart-ai-service

Production-ready FastAPI microservice for ShareCart AI image extraction.

This service is stateless and focused only on extracting grocery items and prices from:
- Receipts
- Shelf/price tags

It reuses the same JWT auth system as the existing Spring Boot backend.

## Architecture Fit

Existing ShareCart stack:
- Flutter mobile app
- Spring Boot backend
- JWT access tokens (issued by Spring Boot)

This service validates JWT locally using the shared `JWT_SECRET` and `HS256`.

No login APIs are included.
No database is used.
No persistence is performed.

## Project Structure

```
sharecart-ai-service/
app/
├── main.py
├── config/
│   └── settings.py
├── api/
│   ├── receipt_routes.py
│   └── health_routes.py
├── middleware/
│   ├── auth_middleware.py
│   ├── request_context.py
│   └── rate_limit.py
├── security/
│   └── jwt_validator.py
├── services/
│   ├── image_preprocessing_service.py
│   ├── openai_extraction_service.py
│   └── extraction_service.py
├── models/
│   ├── request_models.py
│   ├── response_models.py
│   └── auth_models.py
├── prompts/
│   └── grocery_extraction_prompt.py
├── utils/
│   └── image_utils.py
├── tests/
│   ├── test_auth.py
│   ├── test_receipt_extraction.py
│   └── test_rate_limit.py

Dockerfile
requirements.txt
.env.example
.env
.github/workflows/ci.yml
scripts/smoke_test.sh
README.md
```

## Core Endpoint

`POST /api/v1/receipt/extract`

Headers:
- `Authorization: Bearer <jwt>`

Content type:
- `multipart/form-data`

Form fields:
- `image` (required)
- `scanType` (required enum: `RECEIPT`, `PRICE_TAG`)
- `latitude` (optional)
- `longitude` (optional)

Validation:
- Max upload: 10 MB
- Allowed extensions: `jpg`, `jpeg`, `png`, `webp`

## Health Endpoints

- `GET /health`
- `GET /ready`

No auth required.

## Authentication and Authorization

- Local JWT validation with `PyJWT`
- Signature validation (`HS256`)
- Expiration validation (`exp`)
- Malformed token rejection
- Claims extraction: `userId`, `email`, `exp`
- Invalid auth returns `401`

No RBAC is implemented in this service.

## Rate Limiting

Per authenticated user (`userId`):
- 10 scans/hour
- 50 scans/day

MVP implementation uses in-memory storage with swappable limiter design.

Rate-limited requests return `429`.

## Image Processing Pipeline

Flow:
1. Validate JWT
2. Validate image metadata and size
3. Resize large images
4. Deskew
5. Enhance contrast
6. Normalize brightness
7. Crop likely receipt region
8. Send processed image to OpenAI multimodal model
9. Return structured JSON

Images are processed in memory only.

## Logging

Uses `structlog` JSON logs.

Logged fields include:
- request id
- user id
- processing time
- image size
- scan type
- extraction confidence
- failure details

Never logs JWT token or image content.

## Environment

The repository now includes a local `.env` with production-oriented defaults.

Important:
- Replace `JWT_SECRET` in `.env` with the exact shared Spring Boot JWT secret before deployment.
- Set `OPENAI_API_KEY` in `.env`.

Required values:
- `JWT_SECRET` (must match Spring Boot secret)
- `OPENAI_API_KEY`

You can still use `.env.example` as a reference template.

## Local Run

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API:

```bash
uvicorn app.main:app --reload
```

## Docker Run

Build:

```bash
docker build -t sharecart-ai-service:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env sharecart-ai-service:latest
```

## Deploy on Render

This project now includes Render blueprint config in [render.yaml](render.yaml).

### Option A: Blueprint deploy (recommended)

1. Push this repository to GitHub.
2. In Render, click New + and select Blueprint.
3. Connect the repository.
4. Render detects [render.yaml](render.yaml) and creates the web service.
5. In Render Environment settings, set secret values:
	- JWT_SECRET (must match Spring Boot JWT secret)
	- OPENAI_API_KEY
6. Deploy.

### Option B: Manual Web Service (Docker)

1. In Render, create a new Web Service.
2. Select this repository.
3. Set runtime to Docker.
4. Keep Dockerfile path as Dockerfile.
5. Set health check path to /health.
6. Add the same required environment variables as in [render.yaml](render.yaml), plus secrets:
	- JWT_SECRET
	- OPENAI_API_KEY
7. Deploy.

### Important Render notes

- Container port: Dockerfile now binds Uvicorn to Render-provided PORT automatically.
- APP_ENV should be prod (not production).
- If your Flutter app calls this service from a different domain, set CORS_ORIGINS to your app origin(s) instead of *.
- In-memory rate limiting works for single-instance MVP; for multi-instance scaling use shared storage (for example Redis).

## Testing

```bash
pytest app/tests -q
```

## Live Smoke Test

The repository now includes `scripts/smoke_test.sh` for end-to-end API validation with a real JWT.

1. Start the API locally:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Run smoke test from another terminal using a real Spring Boot token:

```bash
API_URL=http://localhost:8000 \
JWT_TOKEN="<spring_boot_access_token>" \
IMAGE_PATH="/absolute/path/to/receipt_or_price_tag.jpg" \
SCAN_TYPE=RECEIPT \
./scripts/smoke_test.sh
```

`SCAN_TYPE` supports `RECEIPT` or `PRICE_TAG`.

## CI Pipeline

GitHub Actions workflow is included at `.github/workflows/ci.yml`.

On push and pull request it runs:
- Dependency installation (Python 3.12)
- Lint checks (critical rule set)
- Pytest suite
- Docker image build

## Error Format

All errors follow a consistent shape:

```json
{
	"success": false,
	"message": "..."
}
```

Common statuses:
- `401` invalid or missing token
- `413` file too large
- `422` validation error
- `429` rate limit exceeded
- `500` AI processing failure
