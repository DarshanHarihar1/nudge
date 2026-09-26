"""
Run once locally to get GMAIL_REFRESH_TOKEN and GMAIL_LABEL_ID.

Needs GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET (a Google Cloud OAuth client of
type "Desktop app") in .env. Opens a browser for Google sign-in, catches the
redirect on localhost, and prints the refresh token plus the ID of the Gmail
label the bank filter applies.

    python scripts/gmail_auth.py [label-name]   # default: nudge-bank
"""
import os
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

load_dotenv(".env")

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def main() -> None:
    client_id = os.environ["GMAIL_CLIENT_ID"]
    client_secret = os.environ["GMAIL_CLIENT_SECRET"]
    label_name = sys.argv[1] if len(sys.argv) > 1 else "nudge-bank"

    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            result.update({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done - you can close this tab.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 0), Handler)
    redirect_uri = f"http://localhost:{server.server_port}"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",  # always return a refresh token
        "state": state,
    })
    print(f"Opening browser to sign in. If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)
    server.handle_request()

    if result.get("state") != state or "code" not in result:
        sys.exit(f"Sign-in failed: {result.get('error', result)}")

    tokens = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).raise_for_status().json()

    labels = httpx.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).raise_for_status().json()["labels"]
    label_id = next((l["id"] for l in labels if l["name"] == label_name), None)

    print(f"GMAIL_REFRESH_TOKEN={tokens['refresh_token']}")
    if label_id:
        print(f"GMAIL_LABEL_ID={label_id}")
    else:
        print(f"No Gmail label named '{label_name}' — create it (via the filter) and re-run.")


if __name__ == "__main__":
    main()
