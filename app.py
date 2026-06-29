from typing import Optional

import os
import httpx
from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response

APP_TITLE = "APIv3 eSIM Test UI"
BASE_URL = "https://api.cradlepointecm.com/api/v3/beta"

app = FastAPI(title=APP_TITLE)


def _normalize_auth(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.strip()
    if not token.lower().startswith("bearer "):
        token = f"Bearer {token}"

    return token


def _json_headers(authorization: Optional[str]) -> dict:
    return {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": _normalize_auth(authorization),
    }


def _upload_headers(authorization: Optional[str]) -> dict:
    return {
        "Accept": "application/vnd.api+json",
        "Authorization": _normalize_auth(authorization),
    }


def _api_response(r: httpx.Response) -> JSONResponse:
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}

    req = getattr(r, "request", None)

    upstream_request = {
        "method": req.method if req else None,
        "url": str(req.url) if req else None,
    }

    return JSONResponse(
        status_code=200,
        content={
            "ok": r.is_success,
            "upstream_status_code": r.status_code,
            "upstream_request": upstream_request,
            "response": body,
        },
    )


@app.get("/health")
async def health():
    return {"ok": True, "app": APP_TITLE}


@app.get("/api/auth/check")
async def check_auth(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "auth_ok": False,
                "message": "Missing bearer token.",
                "upstream_status_code": None,
                "upstream_request": None,
                "response": None,
            },
        )

    params = {
        "page[limit]": "1",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profiles",
            headers=_json_headers(authorization),
            params=params,
        )

    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}

    req = getattr(r, "request", None)

    if r.status_code == 200:
        message = "Authenticated. Token can access the eSIM profiles endpoint."
        auth_ok = True
    elif r.status_code == 401:
        message = "Authentication failed. Token appears to be invalid or expired."
        auth_ok = False
    elif r.status_code == 403:
        message = "Token was accepted, but access to this eSIM endpoint is forbidden."
        auth_ok = False
    else:
        message = f"Auth check reached APIv3, but returned HTTP {r.status_code}."
        auth_ok = False

    return JSONResponse(
        status_code=200,
        content={
            "ok": r.is_success,
            "auth_ok": auth_ok,
            "message": message,
            "upstream_status_code": r.status_code,
            "upstream_request": {
                "method": req.method if req else None,
                "url": str(req.url) if req else None,
            },
            "response": body,
        },
    )



SAMPLE_ACTIVATION_CSV = """eid,activation_string,nickname
89033023321180000000024642232289,LPA:1$cel.prod.ondemandconnectivity.com$activation-code,test1
89033023321180000000024642232290,LPA:1$cel.prod.ondemandconnectivity.com$activation-code,test2
"""


@app.get("/api/esim-activations/sample-csv")
async def download_sample_activation_csv():
    return Response(
        content=SAMPLE_ACTIVATION_CSV,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=esim_profile_activation_sample.csv"
        },
    )




GITHUB_REPO = os.environ.get("GITHUB_REPO", "0101-CTRL/eSIM-Utility")


@app.get("/api/feature-request/config")
async def feature_request_config():
    token_present = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    return {
        "ok": True,
        "github_repo": GITHUB_REPO,
        "github_token_configured": token_present,
        "message": "GitHub token is configured." if token_present else "GitHub token is not configured on the server.",
    }


@app.post("/api/feature-request")
async def create_feature_request(payload: dict):
    request_type = str(payload.get("request_type") or "feature").strip().lower()
    title = str(payload.get("title") or "").strip()
    details = str(payload.get("details") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    page_url = str(payload.get("page_url") or "").strip()

    type_map = {
        "feature": "Feature Request",
        "bug": "Bug Report",
        "feedback": "General Feedback",
    }

    type_label = type_map.get(request_type, "General Feedback")

    if not title:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "message": "Feedback title is required.",
            },
        )

    if not details:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "message": "Feedback details are required.",
            },
        )

    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    if not github_token:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "message": "GitHub token is not configured on the server. Add GITHUB_TOKEN to /etc/api-v3-esim-ui.env and restart the service.",
                "github_repo": GITHUB_REPO,
            },
        )

    issue_title = f"[{type_label}] {title}"

    issue_body = f"""## Type

{type_label}

## Details

{details}

## Submitted From

- App: eSIM Utility
- Page URL: {page_url or "Not provided"}

## Contact

{contact or "Not provided"}
"""

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "eSIM-Utility",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers,
            json={
                "title": issue_title,
                "body": issue_body,
            },
        )

    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}

    return JSONResponse(
        status_code=200,
        content={
            "ok": r.is_success,
            "message": "Feedback submitted to GitHub." if r.is_success else "GitHub rejected the feedback submission.",
            "feedback_type": type_label,
            "github_repo": GITHUB_REPO,
            "upstream_status_code": r.status_code,
            "issue_url": body.get("html_url") if isinstance(body, dict) else None,
            "response": body,
        },
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
async def ui():
    return HTMLResponse(
        """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>APIv3 eSIM Test UI</title>
  <style>
    :root {
      --bg: #f4f6fb;
      --card: #ffffff;
      --card-soft: #f9fafb;
      --text: #111827;
      --muted: #6b7280;
      --border: #e5e7eb;
      --border-strong: #d1d5db;
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --dark: #111827;
      --green: #166534;
      --green-bg: #ecfdf5;
      --orange: #9a3412;
      --orange-bg: #fff7ed;
      --red: #991b1b;
      --red-bg: #fef2f2;
      --purple: #6d28d9;
      --purple-bg: #f5f3ff;
      --shadow: 0 12px 30px rgba(15, 23, 42, .08);
      --radius: 16px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(37, 99, 235, .16), transparent 34rem),
        radial-gradient(circle at top right, rgba(109, 40, 217, .12), transparent 32rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .page {
      max-width: 1500px;
      margin: 0 auto;
      padding: 28px;
    }

    .hero {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      padding: 22px;
      border: 1px solid rgba(255,255,255,.7);
      border-radius: 24px;
      background: rgba(255,255,255,.78);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
      margin-bottom: 18px;
    }

    .hero h1 {
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: -.04em;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 850px;
      line-height: 1.45;
    }

    .status-pill {
      min-width: 220px;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 10px 14px;
      background: white;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: var(--muted);
      box-shadow: 0 6px 18px rgba(15, 23, 42, .06);
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 0 5px rgba(34,197,94,.12);
      flex: 0 0 auto;
    }

    .status-pill.busy .dot {
      background: var(--primary);
      box-shadow: 0 0 0 5px rgba(37,99,235,.12);
      animation: pulse 1s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.35); opacity: .65; }
      100% { transform: scale(1); opacity: 1; }
    }

    .token-card {
      background: var(--dark);
      color: white;
      border-radius: 20px;
      padding: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 18px;
    }

    .token-card label {
      color: #e5e7eb;
    }

    .token-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: end;
    }

    .token-card input {
      background: #020617;
      color: white;
      border-color: #374151;
    }

    .token-actions {
      display: flex;
      gap: 10px;
      align-items: end;
      flex-wrap: wrap;
    }

    .token-actions button {
      min-width: 135px;
    }

    .auth-status {
      margin-top: 10px;
      border-radius: 12px;
      padding: 10px 11px;
      font-size: 13px;
      border: 1px solid #374151;
      background: #020617;
      color: #9ca3af;
      min-height: 40px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .auth-status.good {
      background: #052e16;
      border-color: #166534;
      color: #bbf7d0;
    }

    .auth-status.bad {
      background: #450a0a;
      border-color: #991b1b;
      color: #fecaca;
    }

    .auth-status.warn {
      background: #431407;
      border-color: #9a3412;
      color: #fed7aa;
    }

    .lock-icon {
      width: 28px;
      height: 28px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 17px;
      background: #111827;
      border: 1px solid #374151;
      flex: 0 0 auto;
      transition: transform .22s ease, opacity .45s ease, background .22s ease, border-color .22s ease;
    }

    .lock-icon.checking {
      animation: lockPulse .7s infinite;
    }

    .lock-icon.good {
      background: #166534;
      border-color: #22c55e;
      animation: lockCloseFade 1.15s ease forwards;
    }

    .lock-icon.bad {
      background: #991b1b;
      border-color: #fca5a5;
      animation: lockBreak .42s ease;
    }

    @keyframes lockPulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.12); }
      100% { transform: scale(1); }
    }

    @keyframes lockCloseFade {
      0% { transform: scale(1); opacity: 1; }
      45% { transform: scale(1.18); opacity: 1; }
      100% { transform: scale(.82); opacity: 0; }
    }

    @keyframes lockBreak {
      0% { transform: translateX(0) rotate(0deg); }
      20% { transform: translateX(-4px) rotate(-8deg); }
      40% { transform: translateX(4px) rotate(8deg); }
      60% { transform: translateX(-3px) rotate(-5deg); }
      100% { transform: translateX(0) rotate(0deg); }
    }

    .token-actions {
      display: flex;
      gap: 10px;
      align-items: end;
      flex-wrap: wrap;
    }

    .token-actions button {
      min-width: 150px;
    }

    .auth-status {
      margin-top: 10px;
      border-radius: 12px;
      padding: 10px 11px;
      font-size: 13px;
      border: 1px solid #374151;
      background: #020617;
      color: #9ca3af;
    }

    .auth-status.good {
      background: #052e16;
      border-color: #166534;
      color: #bbf7d0;
    }

    .auth-status.bad {
      background: #450a0a;
      border-color: #991b1b;
      color: #fecaca;
    }

    .auth-status.warn {
      background: #431407;
      border-color: #9a3412;
      color: #fed7aa;
    }

    .feature-request-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      background: rgba(255,255,255,.84);
      border: 1px solid rgba(229,231,235,.9);
      border-radius: 18px;
      padding: 14px 16px;
      box-shadow: 0 8px 20px rgba(15,23,42,.05);
      margin-bottom: 18px;
    }

    .feature-request-bar strong {
      display: block;
      margin-bottom: 3px;
    }

    .feature-request-bar button {
      width: auto;
      min-width: 170px;
      background: var(--purple);
    }

    .feedback-button {
      position: relative;
      width: auto;
      min-width: 170px;
      overflow: hidden;
      background: linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4);
      background-size: 220% 220%;
      animation: feedbackGlow 5s ease infinite;
      box-shadow: 0 12px 24px rgba(37, 99, 235, .20);
    }

    .feedback-button::before {
      content: "";
      position: absolute;
      inset: 0;
      transform: translateX(-110%);
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.28), transparent);
      animation: feedbackShimmer 2.6s ease-in-out infinite;
    }

    .feedback-button span {
      position: relative;
      z-index: 1;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .feedback-button:hover {
      box-shadow: 0 14px 28px rgba(37, 99, 235, .28);
      transform: translateY(-2px);
    }

    @keyframes feedbackGlow {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    @keyframes feedbackShimmer {
      0% { transform: translateX(-110%); }
      45% { transform: translateX(110%); }
      100% { transform: translateX(110%); }
    }

    .feature-request-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 170px;
      min-height: 40px;
      padding: 10px 14px;
      border-radius: 11px;
      background: var(--purple);
      color: white;
      font-weight: 850;
      text-decoration: none;
      transition: transform .08s ease, box-shadow .08s ease, opacity .08s ease;
    }

    .feature-request-link:hover {
      transform: translateY(-1px);
      box-shadow: 0 10px 18px rgba(109,40,217,.18);
    }

    .modal-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(2, 6, 23, .62);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 22px;
    }

    .modal-backdrop.show {
      display: flex;
    }

    .modal {
      width: min(620px, 100%);
      background: white;
      border-radius: 20px;
      border: 1px solid var(--border);
      box-shadow: 0 24px 70px rgba(15,23,42,.34);
      padding: 18px;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 12px;
    }

    .modal-header h2 {
      margin: 0 0 4px;
      font-size: 22px;
    }

    .modal textarea {
      min-height: 150px;
      resize: vertical;
    }

    .modal-close {
      width: auto;
      min-width: unset;
      background: #f3f4f6;
      color: #111827;
      border: 1px solid var(--border);
    }

    .feedback-submit-status {
      display: none;
      margin-top: 12px;
      border-radius: 12px;
      padding: 10px 11px;
      font-size: 13px;
      border: 1px solid var(--border);
      background: #f8fafc;
      color: var(--muted);
      line-height: 1.4;
    }

    .feedback-submit-status.show {
      display: block;
    }

    .feedback-submit-status.busy {
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1d4ed8;
    }

    .feedback-submit-status.good {
      background: var(--green-bg);
      border-color: #bbf7d0;
      color: var(--green);
    }

    .feedback-submit-status.bad {
      background: var(--red-bg);
      border-color: #fecaca;
      color: var(--red);
    }

    .feedback-inline-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,.35);
      border-top-color: white;
      border-radius: 999px;
      display: inline-block;
      animation: spin .8s linear infinite;
      vertical-align: -2px;
      margin-right: 8px;
    }

    .endpoint-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(240px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    .endpoint-mini {
      background: rgba(255,255,255,.84);
      border: 1px solid rgba(229,231,235,.9);
      border-radius: 18px;
      padding: 14px;
      box-shadow: 0 8px 20px rgba(15,23,42,.05);
    }

    .endpoint-mini strong {
      display: block;
      margin-bottom: 7px;
    }

    .endpoint-mini code {
      display: block;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow-x: auto;
      padding-bottom: 2px;
    }

    .endpoint-help-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(260px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    .help-card {
      background: rgba(255,255,255,.9);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 15px;
      box-shadow: 0 8px 20px rgba(15,23,42,.05);
    }

    .help-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 900;
      margin-bottom: 8px;
    }

    .help-card p {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .chip-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .help-chip {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      border: 1px solid var(--border);
      background: #f8fafc;
      color: #1f2937;
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 850;
      cursor: help;
      outline: none;
    }

    .help-chip:hover,
    .help-chip:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(37,99,235,.10);
      background: white;
    }

    .tip {
      visibility: hidden;
      opacity: 0;
      position: absolute;
      left: 0;
      bottom: calc(100% + 10px);
      width: min(360px, 78vw);
      z-index: 50;
      background: #020617;
      color: #e5e7eb;
      border: 1px solid #1f2937;
      border-radius: 13px;
      padding: 11px 12px;
      font-size: 12px;
      font-weight: 500;
      line-height: 1.42;
      box-shadow: 0 18px 34px rgba(15,23,42,.28);
      transform: translateY(4px);
      transition: opacity .12s ease, transform .12s ease, visibility .12s ease;
      pointer-events: none;
    }

    .help-chip:hover .tip,
    .help-chip:focus .tip {
      visibility: visible;
      opacity: 1;
      transform: translateY(0);
    }

    .tip strong {
      color: white;
      font-weight: 900;
    }

    .hint {
      font-size: 12px;
      color: var(--muted);
      margin-top: 10px;
    }

    .badge-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 10px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .03em;
      border: 1px solid transparent;
    }

    .badge.get {
      background: var(--green-bg);
      color: var(--green);
      border-color: #bbf7d0;
    }

    .badge.post {
      background: var(--purple-bg);
      color: var(--purple);
      border-color: #ddd6fe;
    }

    .badge.put {
      background: var(--orange-bg);
      color: var(--orange);
      border-color: #fed7aa;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(360px, 1fr));
      gap: 16px;
      align-items: start;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: 0 8px 22px rgba(15,23,42,.05);
    }

    .card.full {
      grid-column: 1 / -1;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 14px;
    }

    .card h2 {
      margin: 0 0 5px;
      font-size: 20px;
      letter-spacing: -.02em;
    }

    .muted {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 12px;
      align-items: end;
    }

    .form-grid.two {
      grid-template-columns: repeat(2, minmax(160px, 1fr));
    }

    label {
      display: block;
      font-size: 12px;
      font-weight: 800;
      color: #374151;
      margin: 0 0 6px;
    }

    input, select, button, textarea {
      width: 100%;
      border: 1px solid var(--border-strong);
      border-radius: 11px;
      padding: 10px 11px;
      font-size: 14px;
      outline: none;
    }

    input:focus, select:focus, textarea:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(37,99,235,.12);
    }

    button {
      cursor: pointer;
      font-weight: 850;
      border: 0;
      color: white;
      background: var(--primary);
      transition: transform .08s ease, box-shadow .08s ease, opacity .08s ease;
      min-height: 40px;
    }

    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 10px 18px rgba(37,99,235,.18);
    }

    button:active {
      transform: translateY(0);
      box-shadow: none;
    }

    button.secondary {
      background: #374151;
    }

    button.safe {
      background: var(--green);
    }

    button.danger {
      background: var(--red);
    }

    button.ghost {
      background: #f3f4f6;
      color: #111827;
      border: 1px solid var(--border);
    }

    button:disabled {
      opacity: .58;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    .button-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 12px;
    }

    .button-row button {
      width: auto;
      min-width: 160px;
      padding-left: 16px;
      padding-right: 16px;
    }

    .notice {
      border-radius: 13px;
      padding: 11px 12px;
      font-size: 13px;
      margin-top: 12px;
      line-height: 1.4;
    }

    .notice.warn {
      background: var(--orange-bg);
      color: var(--orange);
      border: 1px solid #fed7aa;
    }

    .notice.ok {
      background: var(--green-bg);
      color: var(--green);
      border: 1px solid #bbf7d0;
    }

    .notice.danger {
      background: var(--red-bg);
      color: var(--red);
      border: 1px solid #fecaca;
    }

    .csv-help {
      margin-top: 12px;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 13px;
    }

    .csv-help h3 {
      margin: 0 0 6px;
      font-size: 15px;
    }

    .csv-help p {
      margin: 7px 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.42;
    }

    .csv-cols {
      display: grid;
      grid-template-columns: repeat(2, minmax(160px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }

    .csv-col-box {
      background: white;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px;
      font-size: 13px;
    }

    .csv-col-box strong {
      display: block;
      margin-bottom: 6px;
    }

    .csv-col-box code {
      display: inline-block;
      background: #eef2ff;
      color: #3730a3;
      border-radius: 7px;
      padding: 3px 6px;
      margin: 2px 3px 2px 0;
      font-size: 12px;
    }

    .table-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 14px;
      padding: 10px 12px;
      background: var(--card-soft);
      border: 1px solid var(--border);
      border-radius: 12px;
    }

    .table-wrap {
      width: 100%;
      overflow: auto;
      margin-top: 12px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: white;
      max-height: 520px;
    }

    table {
      border-collapse: separate;
      border-spacing: 0;
      width: 100%;
      font-size: 13px;
      min-width: 1320px;
    }

    th, td {
      border-bottom: 1px solid var(--border);
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }

    th {
      background: #f8fafc;
      color: #374151;
      position: sticky;
      top: 0;
      z-index: 1;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }

    tr:hover td {
      background: #f9fafb;
    }

    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: nowrap;
    }

    .small-cell {
      max-width: 260px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .active-pill {
      display: inline-flex;
      padding: 4px 8px;
      border-radius: 999px;
      font-weight: 800;
      font-size: 12px;
    }

    .active-pill.yes {
      background: var(--green-bg);
      color: var(--green);
    }

    .active-pill.no {
      background: #f3f4f6;
      color: #374151;
    }

    .request-card {
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 16px;
      align-items: stretch;
    }

    .request-box {
      background: white;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      box-shadow: 0 8px 22px rgba(15,23,42,.05);
      min-width: 0;
    }

    .request-line {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px;
      overflow-x: auto;
      margin-top: 8px;
    }

    .history-list {
      display: flex;
      flex-direction: column;
      gap: 9px;
      max-height: 430px;
      overflow: auto;
      margin-top: 10px;
    }

    .history-item {
      border: 1px solid var(--border);
      border-radius: 13px;
      background: #f8fafc;
      padding: 10px;
    }

    .history-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 7px;
      font-size: 12px;
      color: var(--muted);
    }

    .method-pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 7px;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .04em;
      background: #e0f2fe;
      color: #075985;
    }

    .status-ok {
      color: var(--green);
      font-weight: 850;
    }

    .status-bad {
      color: var(--red);
      font-weight: 850;
    }

    .history-url {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: nowrap;
      overflow-x: auto;
      font-size: 12px;
      padding-bottom: 2px;
    }

    .tiny-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }

    .tiny-actions button {
      width: auto;
      min-width: unset;
      min-height: 32px;
      padding: 7px 10px;
      font-size: 12px;
    }

    pre {
      background: #020617;
      color: #dbeafe;
      padding: 16px;
      border-radius: 14px;
      overflow: auto;
      max-height: 560px;
      min-height: 180px;
      font-size: 12px;
      line-height: 1.45;
      margin: 10px 0 0;
      border: 1px solid #1f2937;
    }

    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,.35);
      border-top-color: white;
      border-radius: 999px;
      display: inline-block;
      animation: spin .8s linear infinite;
      vertical-align: -3px;
      margin-right: 8px;
    }

    .page-loader {
      display: none;
      position: fixed;
      left: 50%;
      top: 18px;
      transform: translateX(-50%);
      z-index: 999;
      background: #111827;
      color: white;
      border-radius: 999px;
      padding: 10px 16px;
      box-shadow: var(--shadow);
      font-size: 14px;
      align-items: center;
      gap: 8px;
    }

    .page-loader.show {
      display: flex;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @media (max-width: 980px) {
      .hero, .token-row, .request-card {
        grid-template-columns: 1fr;
        display: grid;
      }

      .endpoint-strip, .endpoint-help-grid, .grid, .form-grid, .form-grid.two {
        grid-template-columns: 1fr;
      }

      .status-pill {
        min-width: unset;
      }
    }
  </style>
</head>

<body>
  <div id="pageLoader" class="page-loader">
    <span class="spinner"></span>
    <span id="pageLoaderText">Running request...</span>
  </div>

  <main class="page">
    <section class="hero">
      <div>
        <h1>APIv3 eSIM Test UI</h1>
        <p>
          Standalone local console for testing the APIv3 beta eSIM endpoints. Built around the three endpoint groups:
          profile inventory, profile management tasks, and bulk profile activation workflows.
        </p>
      </div>
      <div id="statusPill" class="status-pill">
        <span class="dot"></span>
        <span id="statusText">Ready</span>
      </div>
    </section>

    <section class="token-card">
      <div class="token-row">
        <div>
          <label>Bearer token</label>
          <input id="token" type="password" placeholder="Paste token, with or without Bearer prefix" autocomplete="off" oninput="resetTokenAuth()" />
          <div class="muted" style="margin-top:8px;color:#9ca3af;">
            Lab tool only. Do not expose this port publicly. The token is sent from this browser to the local FastAPI proxy.
          </div>
          <div id="authStatus" class="auth-status">
            <span id="authLockIcon" class="lock-icon">🔓</span>
            <span id="authStatusText">Token not added yet.</span>
          </div>
        </div>
        <div class="token-actions">
          <button id="addTokenBtn" onclick="addToken()" class="ghost">Add Token</button>
          <button onclick="clearToken()" class="ghost">Clear Token</button>
        </div>
      </div>
    </section>

    <section class="feature-request-bar">
      <div>
        <strong>Feedback for this utility?</strong>
        <div class="muted">Send a feature request, bug report, or general feedback from inside the tool.</div>
      </div>
      <button onclick="openFeatureModal()" class="feedback-button"><span>💬 Feedback</span></button>
    </section>

    <section class="endpoint-strip">
      <div class="endpoint-mini">
        <strong>eSIM Profiles</strong>
        <code>/api/v3/beta/esim_profiles</code>
        <div class="badge-row"><span class="badge get">GET</span><span class="badge">Inventory</span></div>
      </div>
      <div class="endpoint-mini">
        <strong>eSIM Profiles Manage</strong>
        <code>/api/v3/beta/esim_profiles/manage</code>
        <div class="badge-row"><span class="badge get">GET</span><span class="badge post">POST</span><span class="badge">Task-based</span></div>
      </div>
      <div class="endpoint-mini">
        <strong>eSIM Profile Activations</strong>
        <code>/api/v3/beta/esim_profile_activations</code>
        <div class="badge-row"><span class="badge get">GET</span><span class="badge post">POST</span><span class="badge put">PUT</span><span class="badge">Bulk CSV</span></div>
      </div>
    </section>

    <section class="endpoint-help-grid">
      <div class="help-card">
        <div class="help-title">
          <span class="badge get">GET</span>
          <span>esim_profiles</span>
        </div>
        <p>Profile inventory. This endpoint tells you what eSIM profiles exist and how they relate to devices.</p>
        <div class="chip-row">
          <span class="help-chip" tabindex="0">Profile row
            <span class="tip"><strong>Profile row:</strong> One eSIM profile record in the account. The useful fields are profile ID, ICCID, EID, carrier, profile name, nickname, active state, and classification.</span>
          </span>
          <span class="help-chip" tabindex="0">Active
            <span class="tip"><strong>Active:</strong> Indicates whether that profile is currently active/selected on the eUICC. This is read-only from this endpoint.</span>
          </span>
          <span class="help-chip" tabindex="0">Net device relationship
            <span class="tip"><strong>Net device relationship:</strong> The profile points back to a related net_device ID. That tells you which modem/device object the profile is associated with.</span>
          </span>
          <span class="help-chip" tabindex="0">Filters / sort
            <span class="tip"><strong>Filters / sort:</strong> The UI converts your filter fields into APIv3 query params like filter[iccid], filter[eid], filter[carrier], filter[active], and sort.</span>
          </span>
        </div>
        <div class="hint">Hover or tap a chip to learn what it means.</div>
      </div>

      <div class="help-card">
        <div class="help-title">
          <span class="badge post">POST</span>
          <span>esim_profiles/manage</span>
        </div>
        <p>Task creator. This endpoint starts a profile management job, then you poll that task for state/status.</p>
        <div class="chip-row">
          <span class="help-chip" tabindex="0">Nickname task
            <span class="tip"><strong>Nickname task:</strong> Creates an esim_profiles_nickname task. It asks the device/NCM workflow to update the friendly nickname for a selected profile.</span>
          </span>
          <span class="help-chip" tabindex="0">Set active task
            <span class="tip"><strong>Set active task:</strong> Creates an esim_profiles_active task. It asks the device to make the selected eSIM profile the active one.</span>
          </span>
          <span class="help-chip" tabindex="0">Delete task
            <span class="tip"><strong>Delete task:</strong> Creates an esim_profiles_delete task. This is destructive, so the UI requires an exact typed confirmation before submission.</span>
          </span>
          <span class="help-chip" tabindex="0">Task state
            <span class="tip"><strong>Task state:</strong> The requested change may not show in the profile inventory until the management task reaches a successful state.</span>
          </span>
          <span class="help-chip" tabindex="0">Detailed status
            <span class="tip"><strong>Detailed status:</strong> The task response can include detailed_status, status_code, and status fields. These help explain router/device-side success or failure.</span>
          </span>
        </div>
        <div class="hint">Use POST to create the task, then GET by task ID to watch it.</div>
      </div>

      <div class="help-card">
        <div class="help-title">
          <span class="badge put">FLOW</span>
          <span>esim_profile_activations</span>
        </div>
        <p>Bulk activation workflow. This is a parent/child job model built around CSV upload, preview, execute, and status polling.</p>
        <div class="chip-row">
          <span class="help-chip" tabindex="0">Preview job
            <span class="tip"><strong>Preview job:</strong> POST a CSV with operation=preview. This validates the upload and creates a parent bulk activation record without executing device activation.</span>
          </span>
          <span class="help-chip" tabindex="0">Execute
            <span class="tip"><strong>Execute:</strong> PUT operation=execute against the parent bulk job ID. This starts the actual per-device activation workflow.</span>
          </span>
          <span class="help-chip" tabindex="0">Parent job
            <span class="tip"><strong>Parent job:</strong> The bulk_esim_profile_activations record. It tracks the overall batch, operation, state, and count of child jobs.</span>
          </span>
          <span class="help-chip" tabindex="0">Child jobs
            <span class="tip"><strong>Child jobs:</strong> Individual esim_profile_activations records tied to the parent job. These show per-device/per-EID activation state and errors.</span>
          </span>
          <span class="help-chip" tabindex="0">CSV errors
            <span class="tip"><strong>CSV errors:</strong> Invalid CSV entries can return errors with line numbers and details, such as EID/modem mismatches or records not existing in the account.</span>
          </span>
        </div>
        <div class="hint">The safe path is preview first, execute only after reviewing the parent job.</div>
      </div>
    </section>

    <section class="grid">
      <div class="card full">
        <div class="card-header">
          <div>
            <h2>1. eSIM Profiles</h2>
            <div class="muted">Read-only inventory lookup for profile ID, ICCID, EID, carrier, active state, and net device relationship.</div>
          </div>
          <span class="badge get">GET</span>
        </div>

        <div class="form-grid">
          <div>
            <label>ICCID filter</label>
            <input id="iccid" placeholder="optional" />
          </div>
          <div>
            <label>EID filter</label>
            <input id="eid" placeholder="optional" />
          </div>
          <div>
            <label>Carrier filter</label>
            <input id="carrier" placeholder="optional" />
          </div>
          <div>
            <label>Active</label>
            <select id="active">
              <option value="">Any</option>
              <option value="1">Active only</option>
              <option value="0">Inactive only</option>
            </select>
          </div>
          <div>
            <label>Sort</label>
            <select id="sort">
              <option value="">Default</option>
              <option value="created_at">created_at asc</option>
              <option value="-created_at">created_at desc</option>
              <option value="updated_at">updated_at asc</option>
              <option value="-updated_at">updated_at desc</option>
              <option value="carrier">carrier asc</option>
              <option value="profile_name">profile_name asc</option>
            </select>
          </div>
        </div>

        <div class="button-row">
          <button onclick="loadProfiles()">GET Profiles</button>
          <button onclick="clearProfiles()" class="secondary">Clear Results</button>
        </div>

        <div id="profilesMeta" class="table-toolbar" style="display:none;">
          <div class="muted" id="profilesCount">No rows loaded.</div>
          <button onclick="copyProfileRows()" class="ghost">Copy Rows JSON</button>
        </div>

        <div id="profilesTable"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2>2. Manage Profile</h2>
            <div class="muted">Create a management task to rename, set active, or delete a profile.</div>
          </div>
          <span class="badge post">POST</span>
        </div>

        <div class="form-grid two">
          <div>
            <label>Profile ID</label>
            <input id="manageProfileId" placeholder="example: 124" />
          </div>
          <div>
            <label>Action</label>
            <select id="manageAction" onchange="toggleManageFields()">
              <option value="nickname">Rename nickname</option>
              <option value="active">Set active profile</option>
              <option value="delete">Delete profile</option>
            </select>
          </div>
        </div>

        <div id="nicknameBox" style="margin-top:12px;">
          <label>New nickname</label>
          <input id="nickname" placeholder="new_nickname" />
        </div>

        <div id="deleteBox" style="display:none">
          <div class="notice danger">Destructive action. Type the exact confirmation phrase before submitting.</div>
          <label style="margin-top:12px;">Confirmation</label>
          <input id="deleteConfirm" placeholder="DELETE PROFILE 124" />
        </div>

        <div class="button-row">
          <button onclick="previewManagePayload()" class="secondary">Preview Payload</button>
          <button onclick="submitManageTask()">Submit Task</button>
        </div>

        <hr style="border:0;border-top:1px solid var(--border);margin:18px 0;">

        <div class="card-header" style="margin-bottom:8px;">
          <div>
            <h2 style="font-size:17px;">Management Task Status</h2>
            <div class="muted">Lookup a previously-created profile management task.</div>
          </div>
          <span class="badge get">GET</span>
        </div>

        <label>Management task ID</label>
        <input id="manageTaskId" placeholder="task id returned from submit" />
        <div class="button-row">
          <button onclick="getManageTask()" class="secondary">GET Management Task</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2>3. Bulk Activations</h2>
            <div class="muted">Upload CSV, preview, execute, inspect parent jobs, and view child activation jobs.</div>
          </div>
          <span class="badge put">FLOW</span>
        </div>

        <div class="notice ok">
          Recommended flow: upload CSV → preview → review bulk job → execute → inspect children.
        </div>

        <div class="csv-help">
          <h3>CSV Format Help</h3>
          <p>
            Bulk activation CSV files require an <strong>EID</strong> and an <strong>activation string</strong>.
            Some carriers may also require a 4-digit confirmation code. Nickname is optional but useful.
          </p>

          <div class="csv-cols">
            <div class="csv-col-box">
              <strong>Required columns</strong>
              <code>eid</code>
              <code>activation_string</code>
            </div>
            <div class="csv-col-box">
              <strong>Optional columns</strong>
              <code>confirmation_code</code>
              <code>nickname</code>
            </div>
          </div>

          <div class="button-row">
            <button onclick="downloadSampleCsv()" class="ghost">Download Sample CSV</button>
          </div>

          <p>
            The sample CSV is useful for seeing the expected structure. For a successful live preview,
            replace the sample EIDs and activation strings with real values from the target account/carrier.
          </p>

                    <p>
            Note: The KB examples show error responses with line numbers when uploaded CSV data is invalid,
            such as an EID/modem mismatch or records that do not exist in the account.
          </p>
        </div>

        <label style="margin-top:12px;">CSV file</label>
        <input id="csvFile" type="file" accept=".csv,text/csv" />

        <div class="button-row">
          <button onclick="previewActivation()" class="safe">POST Preview CSV</button>
          <button onclick="listBulkJobs()" class="secondary">GET All Bulk Jobs</button>
        </div>

        <hr style="border:0;border-top:1px solid var(--border);margin:18px 0;">

        <div class="form-grid two">
          <div>
            <label>Bulk job ID</label>
            <input id="bulkJobId" placeholder="bulk job id" />
          </div>
          <div>
            <label>Child state filter</label>
            <input id="childState" placeholder="optional: success, running, failed" />
          </div>
        </div>

        <div class="button-row">
          <button onclick="getBulkJob()" class="secondary">GET Bulk Job</button>
          <button onclick="getChildren()" class="secondary">GET Child Jobs</button>
        </div>

        <div class="notice warn">
          Execute starts the actual activation workflow. Use only after preview looks correct.
        </div>

        <label style="margin-top:12px;">Execute confirmation</label>
        <input id="executeConfirm" placeholder="EXECUTE bulk_job_id" />

        <div class="button-row">
          <button onclick="executeActivation()" class="danger">PUT Execute Bulk Job</button>
        </div>
      </div>
    </section>

    <section class="request-card">
      <div class="request-box">
        <div class="card-header">
          <div>
            <h2>APIv3 Request History</h2>
            <div class="muted">Session history of upstream APIv3 methods, URLs, and status codes generated by the UI.</div>
          </div>
        </div>

        <div class="tiny-actions">
          <button onclick="copyLastUrl()" class="ghost">Copy Last URL</button>
          <button onclick="copyAllRequestUrls()" class="ghost">Copy All URLs</button>
          <button onclick="clearRequestHistory()" class="ghost">Clear History</button>
        </div>

        <div id="lastRequest" class="request-line muted">No APIv3 requests yet.</div>
      </div>

      <div class="request-box">
        <div class="card-header">
          <div>
            <h2>Output</h2>
            <div class="muted">Raw local proxy response, upstream status code, and API response body.</div>
          </div>
          <button onclick="clearOutput()" class="ghost" style="width:auto;">Clear</button>
        </div>
        <pre id="output">Ready.</pre>
      </div>
    </section>
<button onclick="closeFeatureModal()" class="modal-close">✕</button>
        </div>

        <label>Title</label>
        <input id="featureTitle" placeholder="Short summary" />

        <label style="margin-top:12px;">Details</label>
        <textarea id="featureDetails" placeholder="Describe the request, bug, or feedback. For bugs, include what happened, what you expected, and any steps to reproduce."></textarea>

        <label style="margin-top:12px;">Contact / submitter, optional</label>
        <input id="featureContact" placeholder="Name, email, team, or leave blank" />

        <div class="button-row">
          <button onclick="submitFeatureRequest()">Open GitHub Issue</button>
          <button onclick="closeFeatureModal()" class="secondary">Cancel</button>
        </div>
      </div>
    </div>

        <div id="featureModal" class="modal-backdrop">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h2>Feedback</h2>
            <div class="muted">Prepare feedback from inside this tool, then submit it through GitHub.</div>
          </div>
          <button onclick="closeFeatureModal()" class="modal-close">✕</button>
        </div>

        <div id="featureConfigStatus" class="notice warn" style="display:none;"></div>
        <div id="feedbackSubmitStatus" class="feedback-submit-status"></div>

        <label>Feedback type</label>
        <select id="featureType">
          <option value="feature">Feature Request</option>
          <option value="bug">Bug Report</option>
          <option value="feedback">General Feedback</option>
        </select>

        <label style="margin-top:12px;">Title</label>
        <input id="featureTitle" placeholder="Short summary" />

        <label style="margin-top:12px;">Details</label>
        <textarea id="featureDetails" placeholder="Describe the request, bug, or feedback. For bugs, include what happened, what you expected, and any steps to reproduce."></textarea>

        <label style="margin-top:12px;">Contact / submitter, optional</label>
        <input id="featureContact" placeholder="Name, email, team, or leave blank" />

        <div class="button-row">
          <button id="submitFeedbackBtn" onclick="submitFeatureRequest()">Open GitHub Issue</button>
          <button onclick="closeFeatureModal()" class="secondary">Cancel</button>
        </div>
      </div>
    </div>

  </main>

<script>
let lastUpstreamUrl = "";
let requestHistory = [];
let lastProfilesRows = [];

function esc(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setBusy(isBusy, label = "Running request...") {
  const loader = document.getElementById("pageLoader");
  const loaderText = document.getElementById("pageLoaderText");
  const pill = document.getElementById("statusPill");
  const statusText = document.getElementById("statusText");

  if (isBusy) {
    loader.classList.add("show");
    loaderText.textContent = label;
    pill.classList.add("busy");
    statusText.textContent = label;
    document.querySelectorAll("button").forEach(b => b.disabled = true);
  } else {
    loader.classList.remove("show");
    pill.classList.remove("busy");
    statusText.textContent = "Ready";
    document.querySelectorAll("button").forEach(b => b.disabled = false);
  }
}

let tokenValidated = false;

function setAuthStatus(kind, message, iconText) {
  const box = document.getElementById("authStatus");
  const text = document.getElementById("authStatusText");
  const icon = document.getElementById("authLockIcon");

  if (!box || !text || !icon) return;

  box.className = "auth-status";
  icon.className = "lock-icon";

  if (kind) {
    box.classList.add(kind);
    icon.classList.add(kind);
  }

  if (iconText) {
    icon.textContent = iconText;
  }

  text.textContent = message;
}

function resetTokenAuth() {
  tokenValidated = false;
  setAuthStatus("", "Token not added yet.", "🔓");
}

function clearToken() {
  document.getElementById("token").value = "";
  tokenValidated = false;
  setAuthStatus("", "Token cleared. Token not added yet.", "🔓");
  out({ cleared: "Bearer token field cleared" });
}

async function addToken() {
  const raw = document.getElementById("token").value.trim();

  if (!raw) {
    tokenValidated = false;
    setAuthStatus("bad", "No token entered. Paste a bearer token first.", "💔");
    out({
      error: "Missing bearer token",
      help: "Paste an APIv3 bearer token, then click Add Token."
    });
    return;
  }

  const token = raw.toLowerCase().startsWith("bearer ") ? raw : "Bearer " + raw;

  try {
    tokenValidated = false;
    setAuthStatus("", "Checking token...", "🔐");
    const icon = document.getElementById("authLockIcon");
    if (icon) {
      icon.className = "lock-icon checking";
    }

    setBusy(true, "Checking token...");

    const r = await fetch("/api/auth/check", {
      method: "GET",
      headers: {
        "Accept": "application/vnd.api+json",
        "Authorization": token
      }
    });

    const body = await r.json();

    setLastRequest(body);

    if (body.auth_ok) {
      tokenValidated = true;
      setAuthStatus("good", body.message || "Token added. Access verified.", "🔒");
      out({
        local_status_code: r.status,
        result: body
      });
    } else {
      tokenValidated = false;
      if (body.upstream_status_code === 403) {
        setAuthStatus("warn", body.message || "Token accepted, but access is forbidden.", "💔");
      } else {
        setAuthStatus("bad", body.message || "Token rejected.", "💔");
      }
      out({
        local_status_code: r.status,
        result: body
      });
    }
  } catch (err) {
    tokenValidated = false;
    setAuthStatus("bad", "Token check failed before completion.", "💔");
    out({
      error: err.message || String(err),
      action: "Add Token"
    });
  } finally {
    setBusy(false);
  }
}

function authHeaders(json = true) {
  const raw = document.getElementById("token").value.trim();

  if (!raw) {
    out({
      error: "Missing bearer token",
      help: "Paste an APIv3 bearer token and click Add Token before running this request."
    });
    throw new Error("Missing bearer token");
  }

  if (!tokenValidated) {
    setAuthStatus("warn", "Token has not been added/verified yet. Click Add Token first.", "🔓");
  }

  const token = raw.toLowerCase().startsWith("bearer ") ? raw : "Bearer " + raw;

  const headers = {
    "Accept": "application/vnd.api+json",
    "Authorization": token
  };

  if (json) {
    headers["Content-Type"] = "application/vnd.api+json";
  }

  return headers;
}

function out(obj) {
  document.getElementById("output").textContent =
    typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

function clearOutput() {
  out("Ready.");
}

function setLastRequest(body) {
  const req = body?.upstream_request;

  if (!req || !req.url) {
    renderRequestHistory();
    return;
  }

  const item = {
    ts: new Date().toLocaleString(),
    method: req.method || "UNKNOWN",
    url: req.url,
    upstream_status_code: body?.upstream_status_code ?? "unknown",
    ok: Boolean(body?.ok)
  };

  lastUpstreamUrl = item.url;
  requestHistory.unshift(item);

  // Keep the browser session history useful without letting it grow forever.
  requestHistory = requestHistory.slice(0, 25);

  renderRequestHistory();
}

function renderRequestHistory() {
  const box = document.getElementById("lastRequest");

  if (!box) return;

  if (!requestHistory.length) {
    box.className = "request-line muted";
    box.innerHTML = "No APIv3 requests yet.";
    lastUpstreamUrl = "";
    return;
  }

  box.className = "history-list";

  box.innerHTML = requestHistory.map((item, idx) => `
    <div class="history-item">
      <div class="history-top">
        <div>
          <span class="method-pill">${esc(item.method)}</span>
          <span style="margin-left:6px;" class="${item.ok ? "status-ok" : "status-bad"}">
            ${esc(item.upstream_status_code)}
          </span>
          <span style="margin-left:6px;">${idx === 0 ? "Latest" : "#" + (idx + 1)}</span>
        </div>
        <div>${esc(item.ts)}</div>
      </div>
      <div class="history-url">${esc(item.url)}</div>
    </div>
  `).join("");
}

async function copyLastUrl() {
  if (!lastUpstreamUrl) {
    out({ error: "No upstream URL to copy yet." });
    return;
  }

  await navigator.clipboard.writeText(lastUpstreamUrl);
  out({ copied: lastUpstreamUrl });
}

async function copyAllRequestUrls() {
  if (!requestHistory.length) {
    out({ error: "No request history to copy yet." });
    return;
  }

  const lines = [];

  requestHistory.forEach(function(item, idx) {
    lines.push(String(idx + 1) + ". " + item.method + " " + item.upstream_status_code + " " + item.url);
  });

  await navigator.clipboard.writeText(lines.join("\\n"));
  out({ copied_request_count: requestHistory.length });
}

function clearRequestHistory() {
  requestHistory = [];
  lastUpstreamUrl = "";
  renderRequestHistory();
  out({ cleared: "APIv3 request history cleared." });
}

async function copyProfileRows() {
  if (!lastProfilesRows.length) {
    out({ error: "No profile rows to copy." });
    return;
  }

  await navigator.clipboard.writeText(JSON.stringify(lastProfilesRows, null, 2));
  out({ copied_profile_rows: lastProfilesRows.length });
}

async function apiFetch(url, options = {}, label = "Running API request...") {
  try {
    setBusy(true, label);
    out("Loading...");
    const r = await fetch(url, options);
    const text = await r.text();

    let body;
    try {
      body = JSON.parse(text);
    } catch {
      body = { raw: text };
    }

    setLastRequest(body);

    out({
      local_status_code: r.status,
      result: body
    });

    return body;
  } catch (err) {
    out({ error: err.message || String(err) });
  } finally {
    setBusy(false);
  }
}

function qs(params) {
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && String(v).trim() !== "") {
      u.append(k, v);
    }
  });
  const s = u.toString();
  return s ? `?${s}` : "";
}

async function loadProfiles() {
  const query = qs({
    iccid: document.getElementById("iccid").value,
    eid: document.getElementById("eid").value,
    carrier: document.getElementById("carrier").value,
    active: document.getElementById("active").value,
    sort: document.getElementById("sort").value
  });

  const body = await apiFetch(`/api/esim-profiles${query}`, {
    method: "GET",
    headers: authHeaders(false)
  }, "Loading eSIM profiles...");

  renderProfiles(body);
}

function clearProfiles() {
  lastProfilesRows = [];
  document.getElementById("profilesTable").innerHTML = "";
  document.getElementById("profilesMeta").style.display = "none";
  out({ cleared: "Profile results cleared" });
}

function renderProfiles(body) {
  const target = document.getElementById("profilesTable");
  const meta = document.getElementById("profilesMeta");
  const count = document.getElementById("profilesCount");
  const rows = body?.result?.response?.data || body?.response?.data || [];

  lastProfilesRows = Array.isArray(rows) ? rows : [];

  if (!Array.isArray(rows) || rows.length === 0) {
    meta.style.display = "flex";
    count.textContent = "0 profile rows returned.";
    target.innerHTML = "<div class='notice warn'>No profile rows returned.</div>";
    return;
  }

  meta.style.display = "flex";
  count.textContent = `${rows.length} profile row${rows.length === 1 ? "" : "s"} returned.`;

  const html = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Carrier</th>
            <th>Profile</th>
            <th>Nickname</th>
            <th>Active</th>
            <th>Classification</th>
            <th>ICCID</th>
            <th>EID</th>
            <th>Net Device</th>
            <th>Created</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => {
            const a = r.attributes || {};
            const nd = r.relationships?.net_device?.data?.id || "";
            const isActive = String(a.active ?? "") === "1" || String(a.active ?? "").toLowerCase() === "true";
            return `
              <tr>
                <td class="mono">${esc(r.id)}</td>
                <td>${esc(a.carrier)}</td>
                <td class="small-cell" title="${esc(a.profile_name)}">${esc(a.profile_name)}</td>
                <td class="small-cell" title="${esc(a.nickname)}">${esc(a.nickname)}</td>
                <td><span class="active-pill ${isActive ? "yes" : "no"}">${isActive ? "Active" : esc(a.active ?? "Inactive")}</span></td>
                <td>${esc(a.classification)}</td>
                <td class="mono">${esc(a.iccid)}</td>
                <td class="mono">${esc(a.eid)}</td>
                <td class="mono">${esc(nd)}</td>
                <td class="mono">${esc(a.created_at)}</td>
                <td class="mono">${esc(a.updated_at)}</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;

  target.innerHTML = html;
}

function toggleManageFields() {
  const action = document.getElementById("manageAction").value;
  document.getElementById("nicknameBox").style.display = action === "nickname" ? "block" : "none";
  document.getElementById("deleteBox").style.display = action === "delete" ? "block" : "none";
}

function buildManagePayload() {
  const profileId = document.getElementById("manageProfileId").value.trim();
  const action = document.getElementById("manageAction").value;
  const nickname = document.getElementById("nickname").value.trim();

  if (!profileId) throw new Error("Missing profile ID");

  let type;
  let attributes = {};

  if (action === "nickname") {
    if (!nickname) throw new Error("Missing nickname");
    type = "esim_profiles_nickname";
    attributes = { nickname };
  } else if (action === "active") {
    type = "esim_profiles_active";
  } else if (action === "delete") {
    type = "esim_profiles_delete";

    const expected = `DELETE PROFILE ${profileId}`;
    const actual = document.getElementById("deleteConfirm").value.trim();

    if (actual !== expected) {
      throw new Error(`Delete confirmation must exactly equal: ${expected}`);
    }
  }

  return {
    data: {
      type,
      attributes,
      relationships: {
        profile: {
          data: {
            type: "esim_profiles",
            id: profileId
          }
        }
      }
    }
  };
}

function previewManagePayload() {
  try {
    out(buildManagePayload());
  } catch (err) {
    out({ error: err.message || String(err) });
  }
}

async function submitManageTask() {
  let payload;
  try {
    payload = buildManagePayload();
  } catch (err) {
    out({ error: err.message || String(err) });
    return;
  }

  await apiFetch("/api/esim-manage", {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload)
  }, "Submitting management task...");
}

async function getManageTask() {
  const taskId = document.getElementById("manageTaskId").value.trim();
  if (!taskId) return out({ error: "Missing management task ID" });

  await apiFetch(`/api/esim-manage/${encodeURIComponent(taskId)}`, {
    method: "GET",
    headers: authHeaders(false)
  }, "Loading management task...");
}

function downloadSampleCsv() {
  window.location.href = "/api/esim-activations/sample-csv";
}

async function previewActivation() {
  const f = document.getElementById("csvFile").files[0];
  if (!f) return out({ error: "Choose a CSV file first" });

  const fd = new FormData();
  fd.append("payload", f);

  await apiFetch("/api/esim-activations/preview", {
    method: "POST",
    headers: authHeaders(false),
    body: fd
  }, "Uploading CSV preview...");
}

async function listBulkJobs() {
  await apiFetch("/api/esim-activations/bulk-jobs", {
    method: "GET",
    headers: authHeaders(false)
  }, "Loading bulk jobs...");
}

async function getBulkJob() {
  const id = document.getElementById("bulkJobId").value.trim();
  if (!id) return out({ error: "Missing bulk job ID" });

  await apiFetch(`/api/esim-activations/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: authHeaders(false)
  }, "Loading bulk job...");
}

async function getChildren() {
  const id = document.getElementById("bulkJobId").value.trim();
  if (!id) return out({ error: "Missing bulk job ID" });

  const state = document.getElementById("childState").value.trim();

  await apiFetch(`/api/esim-activations/${encodeURIComponent(id)}/children${qs({state})}`, {
    method: "GET",
    headers: authHeaders(false)
  }, "Loading child activation jobs...");
}

async function executeActivation() {
  const id = document.getElementById("bulkJobId").value.trim();
  if (!id) return out({ error: "Missing bulk job ID" });

  const expected = `EXECUTE ${id}`;
  const actual = document.getElementById("executeConfirm").value.trim();

  if (actual !== expected) {
    return out({ error: `Execute confirmation must exactly equal: ${expected}` });
  }

  await apiFetch(`/api/esim-activations/${encodeURIComponent(id)}/execute`, {
    method: "PUT",
    headers: authHeaders(true)
  }, "Executing bulk activation job...");
}





function openFeatureModal() {
  const modal = document.getElementById("featureModal");
  if (modal) {
    modal.classList.add("show");
  }
  checkFeatureRequestConfig();
}

function closeFeatureModal() {
  const modal = document.getElementById("featureModal");
  if (modal) {
    modal.classList.remove("show");
  }
}

async function checkFeatureRequestConfig() {
  const modal = getFeedbackModal ? getFeedbackModal() : document.getElementById("featureModal");
  const box = modal ? modal.querySelector("#featureConfigStatus") : document.getElementById("featureConfigStatus");
  if (!box) return;

  box.style.display = "block";
  box.className = "notice ok";
  box.textContent = "Feedback opens a prefilled GitHub Issue. No local GitHub token is required.";
}

function setFeedbackSubmitStatus(kind, message) {
  const box = document.getElementById("feedbackSubmitStatus");
  if (!box) return;

  box.className = "feedback-submit-status show";

  if (kind) {
    box.classList.add(kind);
  }

  box.textContent = message;
}

function submitFeatureRequest() {
  const modal = getFeedbackModal ? getFeedbackModal() : document.getElementById("featureModal");

  const requestType = getFeedbackValue ? getFeedbackValue("#featureType") : document.getElementById("featureType").value.trim();
  const title = getFeedbackValue ? getFeedbackValue("#featureTitle") : document.getElementById("featureTitle").value.trim();
  const details = getFeedbackValue ? getFeedbackValue("#featureDetails") : document.getElementById("featureDetails").value.trim();
  const contact = getFeedbackValue ? getFeedbackValue("#featureContact") : document.getElementById("featureContact").value.trim();

  const typeMap = {
    feature: "Feature Request",
    bug: "Bug Report",
    feedback: "General Feedback"
  };

  const typeLabel = typeMap[requestType] || "General Feedback";

  if (!title) {
    setFeedbackSubmitStatus("bad", "Title is required before feedback can be submitted.");
    out({ error: "Feedback title is required." });
    return;
  }

  if (!details) {
    setFeedbackSubmitStatus("bad", "Details are required before feedback can be submitted.");
    out({ error: "Feedback details are required." });
    return;
  }

  const issueTitle = "[" + typeLabel + "] " + title;

  const issueBody = [
    "## Type",
    "",
    typeLabel,
    "",
    "## Details",
    "",
    details,
    "",
    "## Submitted From",
    "",
    "- App: eSIM Utility",
    "- Page URL: " + window.location.href,
    "- Submitted: " + new Date().toLocaleString(),
    "",
    "## Contact",
    "",
    contact || "Not provided"
  ].join("\\n");

  const params = new URLSearchParams({
    title: issueTitle,
    body: issueBody
  });

  const url = "https://github.com/0101-CTRL/eSIM-Utility/issues/new?" + params.toString();

  setFeedbackSubmitStatus("good", "Opening GitHub with your feedback prefilled...");
  window.open(url, "_blank", "noopener,noreferrer");

  out({
    action: "Open GitHub Issue",
    message: "Opened a prefilled GitHub Issue. The user submits it from GitHub, so no local GitHub token is required.",
    issue_url: url
  });
}


/* Final feedback behavior override:
   Feedback opens a prefilled GitHub Issue.
   No local GitHub token is required for downloaded installs. */
function getFeedbackModal() {
  return document.getElementById("featureModal");
}

function getFeedbackValue(selector) {
  const modal = getFeedbackModal();
  const el = modal ? modal.querySelector(selector) : document.querySelector(selector);
  return el ? el.value.trim() : "";
}

function setFeedbackSubmitStatus(kind, message) {
  const modal = getFeedbackModal();
  const box = modal ? modal.querySelector("#feedbackSubmitStatus") : document.getElementById("feedbackSubmitStatus");

  if (!box) return;

  box.className = "feedback-submit-status show";

  if (kind) {
    box.classList.add(kind);
  }

  box.textContent = message;
}

async function checkFeatureRequestConfig() {
  const modal = getFeedbackModal();
  const box = modal ? modal.querySelector("#featureConfigStatus") : document.getElementById("featureConfigStatus");

  if (!box) return;

  box.style.display = "block";
  box.className = "notice ok";
  box.textContent = "Feedback opens a prefilled GitHub Issue. No local GitHub token is required.";
}

function submitFeatureRequest() {
  const requestType = getFeedbackValue("#featureType") || "feature";
  const title = getFeedbackValue("#featureTitle");
  const details = getFeedbackValue("#featureDetails");
  const contact = getFeedbackValue("#featureContact");

  const typeMap = {
    feature: "Feature Request",
    bug: "Bug Report",
    feedback: "General Feedback"
  };

  const typeLabel = typeMap[requestType] || "General Feedback";

  if (!title) {
    setFeedbackSubmitStatus("bad", "Title is required before feedback can be submitted.");
    out({ error: "Feedback title is required." });
    return;
  }

  if (!details) {
    setFeedbackSubmitStatus("bad", "Details are required before feedback can be submitted.");
    out({ error: "Feedback details are required." });
    return;
  }

  const issueTitle = "[" + typeLabel + "] " + title;

  const issueBody = [
    "## Type",
    "",
    typeLabel,
    "",
    "## Details",
    "",
    details,
    "",
    "## Submitted From",
    "",
    "- App: eSIM Utility",
    "- Page URL: " + window.location.href,
    "- Submitted: " + new Date().toLocaleString(),
    "",
    "## Contact",
    "",
    contact || "Not provided"
  ].join("\\n");

  const params = new URLSearchParams({
    title: issueTitle,
    body: issueBody
  });

  const url = "https://github.com/0101-CTRL/eSIM-Utility/issues/new?" + params.toString();

  setFeedbackSubmitStatus("good", "Opening GitHub with your feedback prefilled...");
  out({
    action: "Open GitHub Issue",
    message: "Opened a prefilled GitHub Issue. No local GitHub token is required.",
    issue_url: url
  });

  const opened = window.open(url, "_blank", "noopener,noreferrer");

  if (!opened) {
    setFeedbackSubmitStatus("bad", "Popup blocked. Copy the GitHub issue URL from the output panel.");
  }
}

</script>
</body>
</html>
        """
    )


@app.get("/api/esim-profiles")
async def get_esim_profiles(
    authorization: Optional[str] = Header(default=None),
    sort: Optional[str] = None,
    active: Optional[str] = None,
    iccid: Optional[str] = None,
    eid: Optional[str] = None,
    carrier: Optional[str] = None,
):
    params = {}

    if sort:
        params["sort"] = sort
    if active:
        params["filter[active]"] = active
    if iccid:
        params["filter[iccid]"] = iccid
    if eid:
        params["filter[eid]"] = eid
    if carrier:
        params["filter[carrier]"] = carrier

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profiles",
            headers=_json_headers(authorization),
            params=params,
        )

    return _api_response(r)


@app.post("/api/esim-manage")
async def manage_esim_profile(
    payload: dict,
    authorization: Optional[str] = Header(default=None),
):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{BASE_URL}/esim_profiles/manage",
            headers=_json_headers(authorization),
            json=payload,
        )

    return _api_response(r)


@app.get("/api/esim-manage/{task_id}")
async def get_manage_task(
    task_id: str,
    authorization: Optional[str] = Header(default=None),
):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profiles/manage/{task_id}",
            headers=_json_headers(authorization),
        )

    return _api_response(r)


@app.post("/api/esim-activations/preview")
async def preview_esim_activation(
    authorization: Optional[str] = Header(default=None),
    payload: UploadFile = File(...),
):
    files = {
        "payload": (
            payload.filename or "esim_profile_activation.csv",
            await payload.read(),
            "text/csv",
        ),
    }

    data = {
        "operation": "preview",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{BASE_URL}/esim_profile_activations",
            headers=_upload_headers(authorization),
            files=files,
            data=data,
        )

    return _api_response(r)


@app.get("/api/esim-activations/bulk-jobs")
async def get_bulk_jobs(
    authorization: Optional[str] = Header(default=None),
):
    params = {
        "filter[type]": "bulk_esim_profile_activations",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profile_activations",
            headers=_json_headers(authorization),
            params=params,
        )

    return _api_response(r)


@app.put("/api/esim-activations/{bulk_job_id}/execute")
async def execute_esim_activation(
    bulk_job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    payload = {
        "data": {
            "type": "bulk_esim_profile_activations",
            "id": bulk_job_id,
            "attributes": {
                "operation": "execute"
            },
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.put(
            f"{BASE_URL}/esim_profile_activations/{bulk_job_id}",
            headers=_json_headers(authorization),
            json=payload,
        )

    return _api_response(r)


@app.get("/api/esim-activations/{bulk_job_id}")
async def get_bulk_activation(
    bulk_job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profile_activations/{bulk_job_id}",
            headers=_json_headers(authorization),
        )

    return _api_response(r)


@app.get("/api/esim-activations/{bulk_job_id}/children")
async def get_activation_children(
    bulk_job_id: str,
    authorization: Optional[str] = Header(default=None),
    state: Optional[str] = None,
):
    params = {
        "filter[type]": "esim_profile_activations",
        "filter[parent]": bulk_job_id,
    }

    if state:
        params["filter[state]"] = state

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{BASE_URL}/esim_profile_activations",
            headers=_json_headers(authorization),
            params=params,
        )

    return _api_response(r)
