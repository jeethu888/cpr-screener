import os
from fyers_apiv3 import fyersModel
import urllib.parse

def main():
    print("=== Fyers API Token Generator ===")
    
    # Try to get from env vars or prompt
    client_id = os.environ.get("FYERS_CLIENT_ID") or input("Enter Fyers App ID (Client ID): ").strip()
    secret_key = os.environ.get("FYERS_SECRET_KEY") or input("Enter Fyers Secret Key: ").strip()
    redirect_uri = os.environ.get("FYERS_REDIRECT_URI") or input("Enter Fyers Redirect URI (e.g. https://google.com): ").strip()
    
    if not all([client_id, secret_key, redirect_uri]):
        print("Error: Client ID, Secret Key, and Redirect URI are required.")
        return

    # Initialize Fyers session for auth
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        state="cpr_screener"
    )

    # 1. Generate Auth URL
    auth_url = session.generate_authcode()
    print("\n---------------------------------------------------------")
    print("1. Click the link below to login to Fyers and authorize:")
    print(auth_url)
    print("---------------------------------------------------------")

    # 2. User logs in, gets redirected, and pastes the URL back
    redirected_url = input("\n2. After login, you will be redirected. Paste the FULL redirected URL here:\n> ").strip()

    try:
        # Parse the auth_code from the URL
        parsed_url = urllib.parse.urlparse(redirected_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'auth_code' not in query_params:
            print("\nError: Could not find 'auth_code' in the provided URL.")
            return
            
        auth_code = query_params['auth_code'][0]
        
        # 3. Generate Access Token
        session.set_token(auth_code)
        response = session.generate_token()
        
        if response.get('s') == 'ok':
            access_token = response['access_token']
            print("\n✅ Success! Your Access Token is generated.")
            print("\n=== YOUR ACCESS TOKEN ===")
            print(access_token)
            print("=========================")
            print("\nCopy the above token. It is valid until the end of the day.")
            print("Set this as your FYERS_ACCESS_TOKEN GitHub Secret or Environment Variable.")
        else:
            print(f"\n❌ Error generating token: {response}")
            
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
