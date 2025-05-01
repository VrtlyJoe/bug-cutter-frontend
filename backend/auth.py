"""
Handles Jira (Atlassian) OAuth for Vrtly Bug Cutter.
The env-var names now match those configured on Render.
"""

import os
import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

# ── ENV VARS ───────────────────────────────────────────
CLIENT_ID: str     = os.getenv("JIRA_CLIENT_ID", "")
CLIENT_SECRET: str = os.getenv("JIRA_CLIENT_SECRET", "")
REDIRECT_URI: str  = os.getenv("JIRA_REDIRECT_URI", "")
TOKEN_URL: str     = "https://auth.atlassian.com/oauth/token"

# ── OAUTH START ───────────────────────────────────────
@router.get("/start")
async def start_jira_auth():
    scopes = [
        "read:jira-user",
        "read:jira-work",
        "write:jira-work",
        "offline_access",
    ]
    authorize_url = (
        "https://auth.atlassian.com/authorize?"
        f"audience=api.atlassian.com&"
        f"client_id={CLIENT_ID}&"
        f"scope={'%20'.join(scopes)}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"prompt=consent"
    )
    return RedirectResponse(authorize_url)

# ── OAUTH CALLBACK ────────────────────────────────────
@router.get("/callback")
async def jira_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing auth code"}

    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        return {"error": "Failed to exchange token", "details": resp.text}

    token_data = resp.json()
    # Redirect back to Streamlit with the freshly minted token
    frontend_url = "https://bug-cutter-frontend.streamlit.app"
    return RedirectResponse(f"{frontend_url}?access_token={token_data['access_token']}")
