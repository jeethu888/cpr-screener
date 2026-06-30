import os
import json
import hashlib
import requests
import urllib.parse
import webbrowser
from fyers_apiv3 import fyersModel

CONFIG_FILE = "fyers_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def main():
    print("=== CPR Screener: Cloud Trigger ===\n")
    cfg = load_config()

    client_id = cfg.get("client_id")
    secret_key = cfg.get("secret_key")
    redirect_uri = cfg.get("redirect_uri")
    github_pat = cfg.get("github_pat")

    if not client_id: client_id = input("Enter Fyers App ID: ").strip()
    if not secret_key: secret_key = input("Enter Fyers Secret Key: ").strip()
    if not redirect_uri: redirect_uri = input("Enter Redirect URI: ").strip()
    
    if not github_pat:
        print("\nTo trigger the cloud automatically, you need a GitHub Personal Access Token (PAT).")
        print("Create one at: https://github.com/settings/tokens?type=beta (Select your repo, grant 'Actions' Read/Write)")
        github_pat = input("Enter GitHub PAT (github_pat_...): ").strip()

    if not all([client_id, secret_key, redirect_uri, github_pat]):
        print("ERROR: All fields are required.")
        return

    # Save so we never ask again
    save_config({
        "client_id": client_id,
        "secret_key": secret_key,
        "redirect_uri": redirect_uri,
        "github_pat": github_pat
    })

    # 1. Get Fyers Token
    print("\n[1/2] Authenticating with Fyers...")
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        state="cpr"
    )
    webbrowser.open(session.generate_authcode())
    print("Browser opened! Log in to Fyers, then paste the full redirected URL below.")
    redirected_url = input("> Paste URL here: ").strip()

    try:
        parsed = urllib.parse.urlparse(redirected_url)
        auth_code = urllib.parse.parse_qs(parsed.query)['auth_code'][0]
    except:
        print("ERROR: Could not parse auth_code from URL.")
        return

    app_id_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()
    resp = requests.post(
        "https://api-t1.fyers.in/api/v3/validate-authcode",
        json={"grant_type": "authorization_code", "appIdHash": app_id_hash, "code": auth_code},
        headers={"Content-Type": "application/json"}
    )
    data = resp.json()
    
    if not (data.get("s") == "ok" and data.get("access_token")):
        print(f"❌ Fyers Auth Failed: {data.get('message')}")
        return
        
    fyers_token = data["access_token"]
    print("✅ Fyers Access Token generated!")

    # 2. Trigger GitHub Action
    print("\n[2/2] Sending task to GitHub Cloud servers...")
    gh_url = "https://api.github.com/repos/jeethu888/cpr-screener/actions/workflows/update_cpr.yml/dispatches"
    
    gh_resp = requests.post(
        gh_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_pat}",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        json={
            "ref": "main",
            "inputs": {
                "fyers_token": fyers_token
            }
        }
    )

    if gh_resp.status_code == 204:
        print("✅ SUCCESS! GitHub Cloud has started fetching your 200+ stocks.")
        print("You can close this window. Your website will update automatically in ~2 minutes.")
    elif gh_resp.status_code in [401, 403, 404]:
        print("❌ ERROR: GitHub PAT is invalid or lacks 'Actions' permissions.")
        print("Delete fyers_config.json to reset your PAT and try again.")
    else:
        print(f"❌ ERROR triggering GitHub: {gh_resp.status_code} - {gh_resp.text}")

if __name__ == "__main__":
    main()
