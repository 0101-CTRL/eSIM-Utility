from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse

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

    .csv-template {
      margin-top: 10px;
      background: #020617;
      color: #dbeafe;
      border-radius: 12px;
      padding: 11px;
      overflow-x: auto;
      font-size: 12px;
      line-height: 1.45;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre;
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
          <input id="token" type="password" placeholder="Paste token, with or without Bearer prefix" autocomplete="off" />
          <div class="muted" style="margin-top:8px;color:#9ca3af;">
            Lab tool only. Do not expose this port publicly. The token is sent from this browser to the local FastAPI proxy.
          </div>
        </div>
        <button onclick="clearToken()" class="ghost" style="min-width:140px;">Clear Token</button>
      </div>
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

          <p style="margin-top:10px;">
            Simple template:
          </p>

          <div class="csv-template" id="csvTemplate">eid,activation_string,nickname
89033023321180000000024642232289,LPA:1$cel.prod.ondemandconnectivity.com$activation-code,test1
89033023321180000000024642232290,LPA:1$cel.prod.ondemandconnectivity.com$activation-code,test2</div>

          <div class="button-row">
            <button onclick="copyCsvTemplate()" class="ghost">Copy CSV Template</button>
            <button onclick="downloadSampleCsv()" class="ghost">Download Sample CSV</button>
          </div>

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
            <h2>Last APIv3 Request</h2>
            <div class="muted">Exact upstream method and URL generated by the UI.</div>
          </div>
          <button onclick="copyLastUrl()" class="ghost" style="width:auto;">Copy URL</button>
        </div>
        <div id="lastRequest" class="request-line muted">No APIv3 request yet.</div>
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
  </main>

<script>
let lastUpstreamUrl = "";
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

function clearToken() {
  document.getElementById("token").value = "";
  out({ cleared: "Bearer token field cleared" });
}

function authHeaders(json = true) {
  const raw = document.getElementById("token").value.trim();
  if (!raw) throw new Error("Missing bearer token");

  const token = raw.toLowerCase().startsWith("bearer ") ? raw : `Bearer ${raw}`;

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
  const box = document.getElementById("lastRequest");

  if (!req || !req.url) {
    box.innerHTML = "No upstream APIv3 request recorded for this action.";
    lastUpstreamUrl = "";
    return;
  }

  lastUpstreamUrl = req.url;
  box.innerHTML = `
    <div><strong>Method:</strong> <span class="mono">${esc(req.method)}</span></div>
    <div style="margin-top:8px;"><strong>URL:</strong></div>
    <div class="mono" style="margin-top:5px; overflow-x:auto;">${esc(req.url)}</div>
  `;
}

async function copyLastUrl() {
  if (!lastUpstreamUrl) {
    out({ error: "No upstream URL to copy yet." });
    return;
  }

  await navigator.clipboard.writeText(lastUpstreamUrl);
  out({ copied: lastUpstreamUrl });
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

async function copyCsvTemplate() {
  const template = document.getElementById("csvTemplate")?.textContent || "";
  if (!template.trim()) {
    out({ error: "CSV template not found." });
    return;
  }

  await navigator.clipboard.writeText(template.trim() + "\n");
  out({ copied: "CSV template copied to clipboard." });
}

function downloadSampleCsv() {
  const template = document.getElementById("csvTemplate")?.textContent || "";
  if (!template.trim()) {
    out({ error: "CSV template not found." });
    return;
  }

  const blob = new Blob([template.trim() + "\n"], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");

  a.href = url;
  a.download = "esim_profile_activation_sample.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  out({ downloaded: "esim_profile_activation_sample.csv" });
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
