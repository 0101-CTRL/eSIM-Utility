# eSIM Utility

Standalone FastAPI browser UI for testing Cradlepoint / Ericsson Enterprise APIv3 beta eSIM endpoints.

## Endpoint Groups

### esim_profiles

Read-only eSIM profile inventory lookup.

Useful for viewing profile ID, ICCID, EID, carrier, profile name, nickname, active state, classification, and related net device ID.

### esim_profiles/manage

Creates profile management tasks.

Supported actions:

- Rename profile nickname
- Set active profile
- Delete profile

The UI includes confirmation guardrails for destructive actions.

### esim_profile_activations

Bulk CSV activation workflow.

Supported flow:

- Upload activation CSV
- Preview activation job
- Execute parent activation job
- Inspect parent activation status
- Inspect child activation jobs

## Local Run

Run:

    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install fastapi "uvicorn[standard]" httpx python-multipart
    ./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8011

Open:

    http://<server-ip>:8011/

## Security / Lab Use Warning

This tool is intended for local lab testing only. Do not expose the service publicly.

Bearer tokens are entered in the browser UI and sent to the local FastAPI proxy for each API request. The app does not intentionally persist tokens, but the service should still be treated as sensitive because it can perform real eSIM management actions.

## Optional systemd Service

A sample systemd service file is included under:

    systemd/api-v3-esim-ui.service
