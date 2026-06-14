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
- `image` (required): Image file to process
- `scanType` (required enum: `RECEIPT`, `PRICE_TAG`): Type of document being scanned
- `latitude` (optional): GPS latitude of scan location (for future geo-tagging)
- `longitude` (optional): GPS longitude of scan location (for future geo-tagging)

Validation:
- Max upload: 10 MB
- Allowed extensions: `jpg`, `jpeg`, `png`, `webp`

### Request Example

```bash
curl -X POST "http://localhost:8000/api/v1/receipt/extract" \
  -H "Authorization: Bearer <jwt_token>" \
  -F "image=@receipt.jpg" \
  -F "scanType=RECEIPT" \
  -F "latitude=40.7128" \
  -F "longitude=-74.0060"
```

### Response Examples

**Success (200)**:
```json
{
  "success": true,
  "storeName": "Whole Foods Market",
  "confidence": 0.95,
  "scanType": "RECEIPT",
  "items": [
    {
      "name": "Organic Milk",
      "price": 4.99,
      "quantity": "1",
      "unit": "gal",
      "confidence": 0.98
    },
    {
      "name": "Bread",
      "price": 3.49,
      "quantity": null,
      "unit": null,
      "confidence": 0.92
    }
  ]
}
```

**Failure (200, but success=false)**:
```json
{
  "success": false,
  "message": "Unable to extract items from image"
}
```

**Error Responses**:
- `401`: Missing or invalid JWT token
- `413`: File too large (> 10 MB)
- `422`: Validation error (wrong format, missing fields)
- `429`: Rate limit exceeded
- `500`: AI processing error (OpenAI API failure)

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

## Prerequisites

- **Python 3.12+** (required)
- **System dependencies** (for local development):
  - macOS: `brew install opencv` (Homebrew)
  - Ubuntu/Debian: `apt-get install libgl1 libglib2.0-0` (for OpenCV)
  - Windows: Visual C++ build tools

## Environment

The repository now includes a local `.env` with production-oriented defaults.

Important:
- Replace `JWT_SECRET` in `.env` with the exact shared Spring Boot JWT secret before deployment.
- Set `OPENAI_API_KEY` in `.env`.

Required values:
- `JWT_SECRET` (must match Spring Boot secret)
- `OPENAI_API_KEY`

You can still use `.env.example` as a reference template.

### Environment Variables Explained

| Variable | Purpose | Default |
|----------|---------|----------|
| `JWT_SECRET` | Shared secret from Spring Boot backend | `change-me` |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 Mini model | (empty, required) |
| `OPENAI_MODEL` | OpenAI model for extraction | `gpt-4.1-mini` |
| `OPENAI_TIMEOUT_SECONDS` | API call timeout | `25` |
| `RATE_LIMIT_HOURLY` | Max extractions per user per hour | `10` |
| `RATE_LIMIT_DAILY` | Max extractions per user per day | `50` |

## Local Run

Install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API:

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
- Docs: `http://localhost:8000/docs` (Swagger UI)
- ReDoc: `http://localhost:8000/redoc`

## Docker Run

Build:

```bash
docker build -t sharecart-ai-service:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env sharecart-ai-service:latest
```

**Note**: The Dockerfile uses Python 3.12 slim and copies `.env.example` as fallback (not `.env`). Ensure sensitive values are passed via `--env-file` or `-e` flags.

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

## Troubleshooting

### OpenAI API Key Missing/Invalid
```
Error: "Unable to extract items from image" (500)
```
**Solution**: Verify `OPENAI_API_KEY` is set and valid. Check OpenAI dashboard for remaining credits.

### JWT Validation Failure
```
Error: "Invalid token" (401)
```
**Solution**: Ensure `JWT_SECRET` in `.env` matches the Spring Boot backend secret exactly.

### Rate Limit Exceeded
```
Error: "Rate limit exceeded" (429)
```
**Solution**: User has exceeded hourly (10) or daily (50) scan limits. Limits reset hourly/daily based on UTC time.

### Image Processing Errors
```
Error: "Invalid image format" (422)
```
**Solution**: Ensure image is one of: `jpg`, `jpeg`, `png`, `webp`. Max size is 10 MB.

### Python Version Mismatch
```
Error: "Unsupported operand type(s)" or type annotation errors
```
**Solution**: Verify Python 3.12+ is installed. Check with `python3 --version`.

## Known Limitations

- **Single-instance rate limiting**: In-memory rate limiting works only for single-instance deployments. For multi-instance scaling on Render, implement Redis-backed rate limiting.
- **Latitude/longitude**: Currently stored but not used in extraction logic. Intended for future geo-tagging features.
- **No OCR fallback**: If OpenAI fails, service returns error. No local OCR fallback is implemented.
- **Image processing**: Deskew and contrast enhancement may reduce quality for heavily damaged/bent receipts.
- **Stateless**: No receipt history or caching. Each request is independent.

## Development & Debugging

### Enable Verbose Logging

```bash
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

### Run Tests

```bash
pytest app/tests -q          # Quick run
pytest app/tests -v          # Verbose
pytest app/tests -k auth     # Run specific test
```

### Run Smoke Test Locally

With a real JWT from Spring Boot:

```bash
API_URL=http://localhost:8000 \
JWT_TOKEN="<your_jwt_token>" \
IMAGE_PATH="/path/to/test_receipt.jpg" \
SCAN_TYPE=RECEIPT \
./scripts/smoke_test.sh
```

### Profiling

Add to `app/main.py` before `app.include_router()`:

```python
from fastapi_slowapi import Limiter
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## License

Internal/Private - ShareCart Inc.

## Support

For issues or questions, contact the development team or file an issue in the internal repository.
