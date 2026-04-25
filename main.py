"""
Afyanalytics Platform - External Integration Script
Implements the two-step handshake authentication flow.
"""

import requests
import json
import logging
from datetime import datetime, timezone

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
CONFIG = {
    "base_url": "https://staging.collabmed.net/api/external",
    "platform_name": "Test Platform v2",
    "platform_key": "afya_2d00d74512953c933172ab924f5073fa",
    "platform_secret": "e0502a5c052842cf19d0305455437b791d201761c88e2ad641680b2d5d356ba8",
    "callback_url": "https://your-platform.example.com/callback",  # Update this
}

# ─── Token Storage (in-memory; replace with secure storage in production) ─────
token_store = {
    "handshake_token": None,
    "handshake_expires_at": None,
    "access_token": None,
    "refresh_token": None,
    "access_expires_at": None,
}


# ─── Step 1: Initiate Handshake ───────────────────────────────────────────────
def initiate_handshake() -> dict | None:
    """
    Calls /initiate-handshake and retrieves a handshake token.
    Returns the response data dict on success, None on failure.
    """
    url = f"{CONFIG['base_url']}/initiate-handshake"
    payload = {
        "platform_name": CONFIG["platform_name"],
        "platform_key": CONFIG["platform_key"],
        "platform_secret": CONFIG["platform_secret"],
        "callback_url": CONFIG["callback_url"],
    }

    logger.info("Step 1: Initiating handshake...")
    logger.info(f"  POST {url}")
    logger.info(f"  Payload: {json.dumps({**payload, 'platform_secret': '***REDACTED***'}, indent=2)}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            logger.error(f"  Handshake initiation failed: {data.get('message', 'Unknown error')}")
            return None

        token_data = data["data"]
        token_store["handshake_token"] = token_data["handshake_token"]
        token_store["handshake_expires_at"] = token_data["expires_at"]

        logger.info("  ✅ Handshake initiated successfully!")
        logger.info(f"  Handshake Token : {token_data['handshake_token']}")
        logger.info(f"  Expires At      : {token_data['expires_at']}")
        logger.info(f"  Expires In      : {token_data['expires_in_seconds']} seconds")
        logger.info(f"  Next Step       : {token_data['next_step']}")

        return token_data

    except requests.exceptions.Timeout:
        logger.error("  ❌ Request timed out during handshake initiation.")
    except requests.exceptions.ConnectionError:
        logger.error("  ❌ Could not connect to the API. Check your network or base URL.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"  ❌ HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"  ❌ Unexpected error: {e}")

    return None


# ─── Step 2: Complete Handshake ───────────────────────────────────────────────
def complete_handshake(handshake_token: str) -> dict | None:
    """
    Calls /complete-handshake using the token from step 1.
    Returns the response data dict on success, None on failure.
    """
    url = f"{CONFIG['base_url']}/complete-handshake"
    payload = {
        "handshake_token": handshake_token,
        "platform_key": CONFIG["platform_key"],
    }

    logger.info("\nStep 2: Completing handshake...")
    logger.info(f"  POST {url}")
    logger.info(f"  Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            logger.error(f"  Handshake completion failed: {data.get('message', 'Unknown error')}")
            return None

        token_data = data["data"]
        token_store["access_token"] = token_data["access_token"]
        token_store["refresh_token"] = token_data["refresh_token"]
        token_store["access_expires_at"] = token_data["expires_at"]

        logger.info("  ✅ Handshake completed successfully!")
        logger.info(f"  Access Token    : {token_data['access_token']}")
        logger.info(f"  Refresh Token   : {token_data['refresh_token']}")
        logger.info(f"  Token Type      : {token_data['token_type']}")
        logger.info(f"  Expires At      : {token_data['expires_at']}")
        logger.info(f"  Expires In      : {token_data['expires_in_seconds']} seconds")
        logger.info(f"  Platform        : {token_data['platform_name']}")

        return token_data

    except requests.exceptions.Timeout:
        logger.error("  ❌ Request timed out during handshake completion.")
    except requests.exceptions.ConnectionError:
        logger.error("  ❌ Could not connect to the API.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"  ❌ HTTP error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            logger.error("     → Token may have expired. Re-initiate the handshake.")
    except Exception as e:
        logger.error(f"  ❌ Unexpected error: {e}")

    return None


# ─── Expiry Check ─────────────────────────────────────────────────────────────
def is_handshake_expired() -> bool:
    """Check whether the stored handshake token has expired."""
    expires_at = token_store.get("handshake_expires_at")
    if not expires_at:
        return True
    expiry = datetime.fromisoformat(expires_at)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expiry


# ─── Full Authentication Flow ─────────────────────────────────────────────────
def authenticate() -> bool:
    """
    Runs the full two-step handshake and stores tokens.
    Returns True on success, False on failure.
    """
    logger.info("=" * 55)
    logger.info("  Afyanalytics Platform - Authentication Flow")
    logger.info("=" * 55)

    # Step 1
    handshake_data = initiate_handshake()
    if not handshake_data:
        logger.error("\n❌ Authentication failed at Step 1.")
        return False

    # Guard: ensure we haven't already timed out (edge case)
    if is_handshake_expired():
        logger.error("\n❌ Handshake token expired before Step 2 could run.")
        return False

    # Step 2
    access_data = complete_handshake(handshake_data["handshake_token"])
    if not access_data:
        logger.error("\n❌ Authentication failed at Step 2.")
        return False

    logger.info("\n" + "=" * 55)
    logger.info("  🎉 Authentication successful!")
    logger.info("=" * 55)
    return True


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    success = authenticate()
    if not success:
        logger.error("Integration failed. Review the logs above.")
        exit(1)
