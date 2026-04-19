#!/usr/bin/env python3
"""
Push Replit environment secrets to Google Cloud Secret Manager.

Run this from the Replit terminal (where env vars are already set):
    python scripts/push_secrets_to_gcp.py

Requirements:
- GOOGLE_SERVICE_ACCOUNT_KEY env var must be set (the JSON key content)
- The service account must have roles/secretmanager.admin on the GCP project
"""

import base64
import json
import os
import sys

try:
    import google.auth.transport.requests
    import google.oauth2.service_account
    import requests as grequests
except ImportError:
    print("ERROR: google-auth not available. Run: pip install google-auth requests")
    sys.exit(1)

GCP_PROJECT = "safetyai-472110"
SECRET_MANAGER_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

SECRETS_TO_PUSH = [
    "GOOGLE_API_KEY",
    "GOOGLE_SERVICE_ACCOUNT_KEY",
    "GOOGLE_CLIENT_CREDENTIALS",
    "GOOGLE_DRIVE_CENTRAL_LIBRARY_FOLDER_ID",
    "GOOGLE_DRIVE_DONATION_FOLDER_ID",
    "ICD_API_CLIENT_ID",
    "ICD_API_CLIENT_SECRET",
    "ADZUNA_API_KEY",
    "ADZUNA_APP_ID",
    "RECAPTCHA_SECRET_KEY",
    "RECAPTCHA_SITE_KEY",
    "ADMIN_EMAILS",
]


def get_credentials():
    sa_key_raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "")
    if not sa_key_raw:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_KEY env var is not set.")
        sys.exit(1)
    try:
        sa_key = json.loads(sa_key_raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: GOOGLE_SERVICE_ACCOUNT_KEY is not valid JSON: {e}")
        sys.exit(1)

    creds = google.oauth2.service_account.Credentials.from_service_account_info(
        sa_key, scopes=[SECRET_MANAGER_SCOPE]
    )
    return creds


def get_access_token(creds):
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def secret_exists(token, project, secret_id):
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{secret_id}"
    resp = grequests.get(url, headers={"Authorization": f"Bearer {token}"})
    return resp.status_code == 200


def create_secret(token, project, secret_id):
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets"
    payload = {
        "replication": {"automatic": {}},
    }
    resp = grequests.post(
        url,
        params={"secretId": secret_id},
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    if resp.status_code not in (200, 409):
        print(f"  WARN: create secret returned {resp.status_code}: {resp.text}")
    return resp.status_code in (200, 409)


def add_secret_version(token, project, secret_id, value):
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{secret_id}:addVersion"
    encoded = base64.b64encode(value.encode("utf-8")).decode("utf-8")
    payload = {"payload": {"data": encoded}}
    resp = grequests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    return resp.status_code == 200, resp.text


def main():
    print(f"=== Pushing secrets to GCP project: {GCP_PROJECT} ===\n")

    creds = get_credentials()
    token = get_access_token(creds)
    print("Authenticated with service account.\n")

    success_count = 0
    fail_count = 0

    for secret_name in SECRETS_TO_PUSH:
        value = os.environ.get(secret_name, "")
        if not value:
            print(f"  SKIP  {secret_name}  (env var not set or empty)")
            continue

        print(f"  Processing: {secret_name} ...", end=" ")

        if not secret_exists(token, GCP_PROJECT, secret_name):
            created = create_secret(token, GCP_PROJECT, secret_name)
            if not created:
                print(f"FAILED to create secret.")
                fail_count += 1
                continue

        ok, resp_text = add_secret_version(token, GCP_PROJECT, secret_name, value)
        if ok:
            print("OK")
            success_count += 1
        else:
            print(f"FAILED to add version: {resp_text}")
            fail_count += 1

    print(f"\n=== Done: {success_count} succeeded, {fail_count} failed ===")

    if fail_count == 0:
        print("\nAll secrets pushed. Now run the Cloud Run deploy from Cloud Shell.")
    else:
        print("\nSome secrets failed. Check permissions on the service account.")
        sys.exit(1)


if __name__ == "__main__":
    main()
