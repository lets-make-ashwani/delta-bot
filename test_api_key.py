"""
Quick verification script to check your Public IP and Delta Exchange API Key whitelist status.
"""
import requests
import json
from config import config
from delta_rest_client import DeltaRestClient

def check_ip_and_auth():
    print("=" * 60)
    print("DELTA EXCHANGE IP & API KEY VERIFICATION")
    print("=" * 60)
    
    # 1. Fetch current public IP
    try:
        current_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
        print(f"\n[1] Your Current Machine Public IP: {current_ip}")
    except Exception as e:
        current_ip = "Unknown"
        print(f"\n[1] Could not fetch public IP: {e}")

    # 2. Test Delta Exchange API Key
    target_url = config.INDIA_LIVE_URL if config.MODE == "live" else config.DEMO_API_URL
    print(f"[2] Target Delta URL: {target_url} (Mode: {config.MODE})")
    print(f"[3] API Key: {config.API_KEY[:8]}...{config.API_KEY[-4:] if config.API_KEY else 'EMPTY'}")

    if not config.API_KEY or not config.API_SECRET:
        print("\n[!] Error: API_KEY or API_SECRET is empty in .env!")
        return

    client = DeltaRestClient(
        base_url=target_url,
        api_key=config.API_KEY,
        api_secret=config.API_SECRET
    )

    print("\n[4] Sending test authenticated request to Delta Exchange...")
    try:
        res = client.get_all_wallet_balances()
        print("\n[SUCCESS] API Key is authenticated and WHITELISTED!")
        print(f"Balances Response: {res}")
    except Exception as e:
        err_msg = str(e)
        print(f"\n[RESULT] Request received response:")
        if "ip_not_whitelisted_for_api_key" in err_msg:
            print("\n[!] IP NOT WHITELISTED YET!")
            try:
                json_start = err_msg.find("{")
                json_end = err_msg.rfind("}") + 1
                if json_start != -1 and json_end != -1:
                    err_json = json.loads(err_msg[json_start:json_end])
                    detected_ip = err_json.get("error", {}).get("context", {}).get("client_ip")
                    if detected_ip:
                        print(f"\n>>> DELTA SEES YOUR IP AS: {detected_ip}")
                        print(f">>> Please copy and paste '{detected_ip}' into your Delta Exchange API Whitelist box.")
            except Exception:
                pass
            print(f"\nRaw Error details: {err_msg}")
        else:
            print(f"\nError: {err_msg}")
    print("=" * 60)

if __name__ == "__main__":
    check_ip_and_auth()
