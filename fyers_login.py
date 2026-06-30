import os
import hashlib
import requests
import urllib.parse
from fyers_apiv3 import fyersModel

def main():
    print("=== Fyers API Token Generator ===")
    
    client_id    = os.environ.get("FYERS_CLIENT_ID")   or input("Enter Fyers App ID (e.g. WY1A1JUOA0-100): ").strip()
    secret_key   = os.environ.get("FYERS_SECRET_KEY")   or input("Enter Fyers Secret Key: ").strip()
    redirect_uri = os.environ.get("FYERS_REDIRECT_URI") or input("Enter Redirect URI (must match Fyers app settings exactly,\n  e.g. http://127.0.0.1:8080/): ").strip()

    if not all([client_id, secret_key, redirect_uri]):
        print("ERROR: App ID, Secret Key, and Redirect URI are required.")
        return

    # Step 1 – Use SDK to generate the official Fyers login URL
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        state="cpr_screener"
    )
    auth_url = session.generate_authcode()

    print("\n---------------------------------------------------------")
    print("1. Open this URL in your browser and log in to Fyers:")
    print(auth_url)
    print("---------------------------------------------------------")
    print("\n2. After login you will be redirected to your redirect URI.")
    print("   The page may show 'This site can't be reached' – that is fine.")
    print("   Copy the FULL URL from the browser address bar and paste it below.\n")

    redirected_url = input("> Paste the full redirected URL here:\n> ").strip()

    # Parse auth_code from the URL
    try:
        parsed = urllib.parse.urlparse(redirected_url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'auth_code' not in params:
            print("\nERROR: Could not find 'auth_code' in the URL. Make sure you pasted the full URL.")
            return
        auth_code = params['auth_code'][0]
        print(f"\nAuth code extracted successfully.")
    except Exception as e:
        print(f"\nERROR parsing URL: {e}")
        return

    # Step 2 – Exchange auth_code for access_token via Fyers v3 API (direct HTTP call)
    app_id_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()

    print("Exchanging auth code for access token...")
    resp = requests.post(
        "https://api-t1.fyers.in/api/v3/validate-authcode",
        json={
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code
        },
        headers={"Content-Type": "application/json"},
        timeout=15
    )

    data = resp.json()
    if data.get("s") == "ok" and data.get("access_token"):
        access_token = data["access_token"]
        print("\n✅ Success! Access Token generated.")
        print("\n=== YOUR ACCESS TOKEN ===")
        print(access_token)
        print("=========================")
        print("\nThis token is valid until midnight tonight.")
        with open("fyers_token.txt", "w") as f:
            f.write(access_token)
        print("Token saved to fyers_token.txt for automation.")
    else:
        print(f"\n❌ Token exchange failed:")
        print(f"   code={data.get('code')}  message={data.get('message')}")
        print("\nCommon reasons:")
        print("  - Secret Key is wrong (check myapi.fyers.in -> Apps -> your app -> Secret Key)")
        print("  - Redirect URI does not exactly match what is registered in your Fyers app")
        print("  - Auth code already used or expired (each code can only be used once)")

if __name__ == "__main__":
    main()
