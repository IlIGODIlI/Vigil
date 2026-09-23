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

### 5. Run Tests
```powershell
pytest
```

## Vigil authentication

React
↓
Microsoft Entra ID
↓
Access token for Vigil API
↓
FastAPI
↓
JWT validation via Microsoft OIDC metadata/JWKS
↓
Issuer + audience + expiry + access_as_user scope checks
↓
Protected API

Local environment variables (placeholders only):
```env
ENTRA_TENANT_ID=your-tenant-id
ENTRA_API_CLIENT_ID=your-api-client-id
ENTRA_API_SCOPE=api://your-api-client-id/access_as_user
```
