import os
import hashlib
import requests
import urllib.parse

def main():
    print("=== Fyers API Token Generator ===")
    
    client_id  = os.environ.get("FYERS_CLIENT_ID")  or input("Enter Fyers App ID (e.g. WY1A1JUOA0-100): ").strip()
    secret_key = os.environ.get("FYERS_SECRET_KEY")  or input("Enter Fyers Secret Key: ").strip()
    redirect_uri = os.environ.get("FYERS_REDIRECT_URI") or input("Enter Redirect URI (must match your Fyers app settings, e.g. http://127.0.0.1:8080/): ").strip()

    if not all([client_id, secret_key, redirect_uri]):
        print("ERROR: App ID, Secret Key, and Redirect URI are required.")
        return

    # Step 1 – build auth URL
    auth_url = (
        f"https://api-t2.fyers.in/api/v3/generate-authcode"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&response_type=code"
        f"&state=cpr_screener"
    )

    print("\n---------------------------------------------------------")
    print("1. Open this URL in your browser and log in to Fyers:")
    print(auth_url)
    print("---------------------------------------------------------")
    print("\n2. After login you will be redirected to your redirect URI.")
    print("   The page may show 'This site can't be reached' – that's fine.")
    print("   Just copy the FULL URL from the browser address bar and paste it below.\n")

    redirected_url = input("> Paste the full redirected URL here:\n> ").strip()

    # Parse auth_code
    try:
        parsed = urllib.parse.urlparse(redirected_url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'auth_code' not in params:
            print("\nERROR: Could not find 'auth_code' in the URL you pasted.")
            print("Make sure you copied the complete URL including all query parameters.")
            return
        auth_code = params['auth_code'][0]
    except Exception as e:
        print(f"\nERROR parsing URL: {e}")
        return

    # Step 2 – Exchange auth_code for access_token via Fyers v3 API
    app_id_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()

    resp = requests.post(
        "https://api-t2.fyers.in/api/v3/validate-authcode",
        json={
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code
        },
        headers={"Content-Type": "application/json"}
    )

    data = resp.json()
    if data.get("s") == "ok" and data.get("access_token"):
        access_token = data["access_token"]
        print("\n✅ Success! Your Fyers Access Token:")
        print("\n=== YOUR ACCESS TOKEN ===")
        print(access_token)
        print("=========================")
        print("\nThis token is valid until midnight tonight.")
        with open("fyers_token.txt", "w") as f:
            f.write(access_token)
        print("Token saved to fyers_token.txt for the bat script.")
    else:
        print(f"\n❌ Error getting token: code={data.get('code')} msg={data.get('message')}")
        print("Check that your Secret Key is correct and the redirect URI matches your Fyers app settings exactly.")

if __name__ == "__main__":
    main()
