# Afyanalytics External Platform Integration

A Python implementation of the two-step handshake authentication flow for the Afyanalytics Health Platform.

---

## Prerequisites

- Python 3.10+
- `pip` for installing dependencies

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/afyanalytics-integration.git
cd afyanalytics-integration
```

### 2. (Recommended) Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install requests
```

### 4. Update your callback URL

Open `main.py` and update the `callback_url` in the `CONFIG` block:

```python
CONFIG = {
    ...
    "callback_url": "https://your-platform.example.com/callback",  # ← update this
}
```

### 5. Run the integration

```bash
python main.py
```

---

## How the Handshake Flow Works

The authentication uses a two-step handshake:

```
Your Platform              Afyanalytics API
     |                            |
     |  POST /initiate-handshake  |
     |--------------------------->|
     |                            |
     |  handshake_token (15 min)  |
     |<---------------------------|
     |                            |
     |  POST /complete-handshake  |
     |--------------------------->|
     |                            |
     |  access_token + refresh    |
     |<---------------------------|
```

### Step 1 — Initiate Handshake

Calls `POST /api/external/initiate-handshake` with your platform credentials.

On success, the API returns a `handshake_token` that expires in **15 minutes**.

```json
{
  "success": true,
  "data": {
    "handshake_token": "xyz789abc...",
    "expires_at": "2026-01-08T10:15:00+00:00",
    "expires_in_seconds": 900
  }
}
```

### Step 2 — Complete Handshake

Calls `POST /api/external/complete-handshake` using the token from Step 1.

On success, the API returns a long-lived `access_token` and a `refresh_token`.

```json
{
  "success": true,
  "data": {
    "access_token": "abc123def456...",
    "refresh_token": "ghi789jkl012...",
    "expires_in_seconds": 21600
  }
}
```

---

## How Token Expiry Is Handled

- After Step 1, the `expires_at` timestamp is stored in `token_store`.
- Before proceeding to Step 2, `is_handshake_expired()` checks the current UTC time against the expiry.
- If the token has expired, the flow aborts with a clear error message.
- In a production system, you would re-call `initiate_handshake()` to start fresh.

---

## Error Scenarios Handled

| Scenario | Behaviour |
|---|---|
| Expired handshake token | Detected before Step 2; logs error and exits |
| Invalid credentials | HTTP 401 captured; prompts to check credentials |
| Network/connection error | `ConnectionError` caught and logged clearly |
| Request timeout | `Timeout` caught with descriptive message |
| Unexpected API error | Generic exception handler logs full details |

---

## Project Structure

```
afyanalytics-integration/
├── main.py       # Core integration script
└── README.md     # This file
```

---

## Notes

- Tokens are stored in-memory in this demo. In production, use a secure secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault, or environment variables).
- Never commit real credentials to version control. Use a `.env` file with `python-dotenv` for local development.
- The `platform_secret` in `main.py` is the one provided for this assignment only and should be treated as temporary.
