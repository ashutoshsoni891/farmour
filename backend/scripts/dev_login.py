"""Dev helper: create a Keycloak user (if missing) and print an access token for the local stack.

    python -m scripts.dev_login agro1@example.test [--agronomist] [--admin]

Reads KEYCLOAK_ADMIN_USER / KEYCLOAK_ADMIN_PASSWORD from ~/.farm-local.env. Local use only: it
talks to the Keycloak admin console on 127.0.0.1:8081 and logs in through Caddy on localhost.
"""

import base64
import hashlib
import json
import re
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = "http://localhost"
KC_ADMIN = "http://127.0.0.1:8081/auth"
PASSWORD = "Farm-test-pass-2026"


def env() -> dict[str, str]:
    lines = (Path.home() / ".farm-local.env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def call(req: urllib.request.Request, opener: urllib.request.OpenerDirector | None = None):  # type: ignore[no-untyped-def]
    return (opener or urllib.request.build_opener()).open(req, timeout=20)


def admin_token(e: dict[str, str]) -> str:
    data = urllib.parse.urlencode(
        {"grant_type": "password", "client_id": "admin-cli",
         "username": e["KEYCLOAK_ADMIN_USER"], "password": e["KEYCLOAK_ADMIN_PASSWORD"]}
    ).encode()  # fmt: skip
    url = f"{KC_ADMIN}/realms/master/protocol/openid-connect/token"
    return str(json.load(call(urllib.request.Request(url, data)))["access_token"])


def ensure_user(email: str, token: str) -> None:
    hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    users = json.load(
        call(
            urllib.request.Request(
                f"{KC_ADMIN}/admin/realms/farm/users?email={email}&exact=true", headers=hdr
            )
        )
    )
    if users:
        return
    body = {
        "username": email, "email": email, "emailVerified": True, "enabled": True,
        "firstName": "Dev", "lastName": email.split("@")[0],
        "credentials": [{"type": "password", "value": PASSWORD, "temporary": False}],
    }  # fmt: skip
    req = urllib.request.Request(
        f"{KC_ADMIN}/admin/realms/farm/users", json.dumps(body).encode(), hdr, method="POST"
    )
    call(req)


def login(email: str) -> str:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    redirect = f"{BASE}/login/callback"
    params = urllib.parse.urlencode(
        {"client_id": "farm-web", "response_type": "code", "scope": "openid email profile",
         "redirect_uri": redirect, "code_challenge": challenge.decode(),
         "code_challenge_method": "S256"}
    )  # fmt: skip

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # type: ignore[no-untyped-def]
            return None

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
    page = (
        call(
            urllib.request.Request(
                f"{BASE}/auth/realms/farm/protocol/openid-connect/auth?{params}"
            ),
            opener,
        )
        .read()
        .decode()
    )
    for cookie in jar:  # browsers send Secure cookies to http://localhost; urllib does not
        cookie.secure = False
    action = re.search(r'action="([^"]+)"', page)
    assert action, "login form not found"
    form = urllib.parse.urlencode({"username": email, "password": PASSWORD}).encode()
    url = action.group(1).replace("&amp;", "&")
    try:
        call(urllib.request.Request(url, form), opener)
        raise SystemExit("expected a redirect with a code")
    except urllib.error.HTTPError as err:
        location = err.headers["Location"]
        if location is None:
            body = re.sub(r"<[^>]+>", " ", err.read().decode())
            raise SystemExit(f"login HTTP {err.code}: {' '.join(body.split())[-400:]}") from err
    query = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
    if "code" not in query:
        raise SystemExit(f"login failed: {location}")
    code = query["code"][0]
    token_req = urllib.parse.urlencode(
        {"grant_type": "authorization_code", "client_id": "farm-web", "code": code,
         "redirect_uri": redirect, "code_verifier": verifier}
    ).encode()  # fmt: skip
    tok = call(
        urllib.request.Request(f"{BASE}/auth/realms/farm/protocol/openid-connect/token", token_req)
    )
    return str(json.load(tok)["access_token"])


def set_roles(email: str, agronomist: bool, admin: bool) -> None:
    sql = (
        f"update users set is_agronomist={str(agronomist).lower()}, is_admin={str(admin).lower()} "
        f"where email='{email}'"
    )
    subprocess.run(
        ["docker", "exec", "farm-postgres-1", "psql", "-U", "farm", "-d", "farm", "-qc", sql],
        check=True,
    )


if __name__ == "__main__":
    email = sys.argv[1]
    e = env()
    ensure_user(email, admin_token(e))
    token = login(email)
    if "--agronomist" in sys.argv or "--admin" in sys.argv:
        # The profile row is created on first API call.
        req = urllib.request.Request(
            f"{BASE}/api/v1/me", headers={"Authorization": f"Bearer {token}"}
        )
        call(req)
        set_roles(email, "--agronomist" in sys.argv, "--admin" in sys.argv)
    print(token)
