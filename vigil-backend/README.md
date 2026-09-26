# VIGIL Backend

FastAPI backend skeleton and API structure for VIGIL (AI-powered security and code-review platform).

## Core Philosophy
"AI proposes. Evidence verifies. Humans approve."

## Getting Started

### 1. Setup Virtual Environment & Install Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Locally
```powershell
uvicorn app.main:app --reload
```

### 3. API Documentation & OpenAPI Swagger
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 4. Health & Root Checks
- **Root Check**: `GET http://127.0.0.1:8000/`
- **Health Check**: `GET http://127.0.0.1:8000/api/v1/health`

### 5. GitHub App & Webhook Configuration
Configure the following environment variables in `.env` (see `.env.example`):
* `GITHUB_APP_ID`: Your GitHub App ID.
* `GITHUB_PRIVATE_KEY` / `GITHUB_PRIVATE_KEY_PATH`: Path to or string content of the GitHub App RSA private key.
* `GITHUB_WEBHOOK_SECRET`: Secret key configured on GitHub App Webhook settings.
* `GITHUB_API_BASE_URL`: Defaults to `https://api.github.com`.

**GitHub App Subscription Requirements:**
1. In your GitHub App configuration settings, set **Webhook URL** to `https://<your-domain>/api/v1/webhooks/github`.
2. Enter your `GITHUB_WEBHOOK_SECRET` under **Webhook secret**.
3. Under **Event Subscriptions**, subscribe to:
   * **Push** (`push`)
   * **Pull request** (`pull_request`)

### 6. Run Tests
```powershell
python -m pytest tests/test_github_webhooks.py tests/test_github_integration.py tests/test_models.py
```
