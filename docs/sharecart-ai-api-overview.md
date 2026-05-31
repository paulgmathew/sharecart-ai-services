# ShareCart AI API Overview

## 1. What This API Is

ShareCart AI API is a stateless FastAPI microservice used by the ShareCart mobile application to extract grocery items and prices from images.

It is designed to work alongside existing ShareCart components:
- Flutter mobile frontend
- Spring Boot backend
- JWT-based authentication issued by Spring Boot

## 2. What This API Does

Core responsibilities:
- Receives image uploads from Flutter (receipt images or shelf price-tag images)
- Validates the JWT sent by Flutter in the Authorization header
- Validates and preprocesses images for better extraction quality
- Uses OpenAI vision capabilities to extract grocery item data
- Returns structured JSON back to Flutter for user confirmation

After user confirmation, Flutter sends final data to Spring Boot for persistence.

## 3. What This API Does Not Do

This API intentionally does not:
- Provide login or user management
- Replace Spring Boot business authorization
- Persist extracted data to any database
- Store uploaded images for long-term use

## 4. Main Endpoint

Primary endpoint:
- POST /api/v1/receipt/extract

Expected request:
- Header: Authorization: Bearer <jwt>
- Content-Type: multipart/form-data
- Fields:
  - image (required)
  - scanType (required: RECEIPT or PRICE_TAG)
  - latitude (optional)
  - longitude (optional)

Health endpoints:
- GET /health
- GET /ready

## 5. Processing Flow

Request lifecycle:
1. Receive multipart image request from Flutter
2. Validate JWT locally using shared secret
3. Enforce per-user rate limits
4. Validate image size and format
5. Preprocess image:
   - Resize large images
   - Deskew
   - Contrast enhancement
   - Brightness normalization
   - Crop likely receipt region
6. Send processed image to OpenAI model with grocery-focused prompt
7. Parse and validate structured JSON output
8. Return success or failure response to Flutter

## 6. Authentication and Authorization

Authentication model:
- JWT validation is local (no round-trip to Spring Boot)
- HS256 signature verification
- Expiration check
- Malformed token rejection
- Claims extraction: userId, email, exp

Authorization model:
- If token is valid, request is allowed
- If token is invalid, API returns 401
- No role-based access controls in this service

## 7. Rate Limiting

Per authenticated user limits:
- 10 scans per hour
- 50 scans per day

Behavior:
- Implemented in-memory for MVP
- Designed so storage can be swapped (for example, Redis)
- Returns 429 Too Many Requests when limits are exceeded

## 8. Response Shape

Successful extraction response contains:
- success
- storeName
- confidence
- scanType
- items[] (name, price, quantity, unit, confidence)

Failure response contains:
- success: false
- message

Common error statuses:
- 401 Unauthorized
- 413 File Too Large
- 422 Validation Error
- 429 Too Many Requests
- 500 Internal Server Error

## 9. Technologies Used

Language and runtime:
- Python 3.12+

Web framework and server:
- FastAPI
- Uvicorn

AI integration:
- OpenAI Python SDK (vision-capable model)

Security and validation:
- PyJWT
- Pydantic v2

Image handling and preprocessing:
- Pillow
- OpenCV (cv2)

Request handling and configuration:
- python-multipart
- python-dotenv

Observability and networking:
- structlog
- httpx

Testing:
- pytest

Containerization:
- Docker

## 10. Production-Oriented Characteristics

This API is implemented with production orientation:
- Modular project structure with separated concerns
- Dependency-based authentication and services
- Structured JSON logging
- Consistent JSON error responses
- Stateless architecture for horizontal scalability
- Test coverage for auth, extraction route behavior, and rate limiting
- CI pipeline for lint, tests, and Docker image build

## 11. Integration Summary for Flutter Team

Flutter should:
1. Continue using Spring Boot login flow for JWT issuance.
2. Send the same JWT token to this API in Authorization header.
3. Upload image with scanType using multipart/form-data.
4. Read extracted items from response and show confirmation UI.
5. Send confirmed data to Spring Boot for storage/business workflows.

This keeps AI extraction isolated while preserving existing backend ownership of persistence and business rules.
