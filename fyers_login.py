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
    print(f"  Config saved to {CONFIG_FILE} (won't ask again)")

def main():
    print("=== Fyers API Token Generator ===\n")

    cfg = load_config()

    # Use saved values or prompt once
    client_id = cfg.get("client_id") or os.environ.get("FYERS_CLIENT_ID")
    secret_key = cfg.get("secret_key") or os.environ.get("FYERS_SECRET_KEY")
    redirect_uri = cfg.get("redirect_uri") or os.environ.get("FYERS_REDIRECT_URI")

    if not client_id:
        client_id = input("Enter Fyers App ID (e.g. WY1A1JUOA0-100): ").strip()
    if not secret_key:
        secret_key = input("Enter Fyers Secret Key: ").strip()
    if not redirect_uri:
        redirect_uri = input("Enter Redirect URI (e.g. http://127.0.0.1:8080/): ").strip()

    if not all([client_id, secret_key, redirect_uri]):
        print("ERROR: App ID, Secret Key, and Redirect URI are required.")
        return

    # Save config for next time
    if not cfg.get("client_id"):
        save_config({"client_id": client_id, "secret_key": secret_key, "redirect_uri": redirect_uri})
    else:
        print(f"  Using saved config: {client_id} | {redirect_uri}")

    # Generate auth URL using SDK
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        state="cpr_screener"
    )
    auth_url = session.generate_authcode()

    print("\n---------------------------------------------------------")
    print("Opening Fyers login in your browser automatically...")
    print("If it doesn't open, use this URL:")
    print(auth_url)
    print("---------------------------------------------------------")
    webbrowser.open(auth_url)

    print("\nAfter logging in, you will be redirected to your redirect URI.")
    print("The page may show 'This site can't be reached' - that is fine.")
    print("Copy the FULL URL from the browser address bar and paste it below.\n")

    redirected_url = input("> Paste the full redirected URL here:\n> ").strip()

    # Parse auth_code
    try:
        parsed = urllib.parse.urlparse(redirected_url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'auth_code' not in params:
            print("\nERROR: Could not find 'auth_code' in the URL. Make sure you copied the full URL.")
            return
        auth_code = params['auth_code'][0]
        print("\nAuth code extracted. Generating access token...")
    except Exception as e:
        print(f"\nERROR parsing URL: {e}")
        return

    # Exchange auth_code for access token via direct API call
    app_id_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()

    resp = requests.post(
        "https://api-t1.fyers.in/api/v3/validate-authcode",
        json={"grant_type": "authorization_code", "appIdHash": app_id_hash, "code": auth_code},
        headers={"Content-Type": "application/json"},
        timeout=15
    )

    data = resp.json()
    if data.get("s") == "ok" and data.get("access_token"):
        access_token = data["access_token"]
        print("\n✅ Success! Access token generated.")
        with open("fyers_token.txt", "w") as f:
            f.write(access_token)
        print("Token saved to fyers_token.txt\n")
    else:
        print(f"\n❌ Token exchange failed: code={data.get('code')} msg={data.get('message')}")
        print("Check your Secret Key matches your Fyers app settings exactly.")

if __name__ == "__main__":
    main()
