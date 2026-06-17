"""
Debug script: upgrade nhóm Zalo lên Cộng đồng
Endpoint đúng: /api/group/upgrade/community
"""

import json
import time
import requests

CONFIG_FILE = "txa.json"


def load_main_bot_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for bot in data["data"]:
        if bot.get("is_main_bot"):
            return bot
    raise ValueError("Không tìm thấy main bot!")


def upgrade_community(group_id: str, cookies: dict, imei: str):
    headers = {
        "User-Agent"  : "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin"      : "https://chat.zalo.me",
        "Referer"     : "https://chat.zalo.me/",
    }

    params = {
        "zpw_ver" : 645,
        "zpw_type": 30,
    }

    ts = int(time.time() * 1000)
    payload = {
        "params": json.dumps({
            "grid": str(group_id),
            "imei": imei,
            "ts"  : ts,
        }, separators=(',', ':')),
    }

    print(f"\n[→] Gọi API upgrade community...")
    print(f"    Group ID : {group_id}")
    print(f"    Payload  : {payload['params']}")

    res = requests.post(
        "https://tt-group-wpa.chat.zalo.me/api/group/upgrade/community",
        params=params, data=payload, headers=headers, cookies=cookies, timeout=15,
    )

    print(f"\n[←] HTTP Status : {res.status_code}")
    print(f"[←] Body        : {res.text[:500]}")

    try:
        result   = res.json()
        err_code = result.get("error_code", -1)
        err_msg  = result.get("error_message", "")
        if err_code == 0:
            print(f"\n✅ Thành công! Nhóm {group_id} đã được nâng cấp lên Cộng đồng.")
        else:
            print(f"\n❌ Thất bại! error_code={err_code}, message={err_msg}")
    except Exception as e:
        print(f"\n[✗] Không parse được JSON: {e}")


if __name__ == "__main__":
    config   = load_main_bot_config()
    cookies  = config.get("session_cookies", {})
    imei     = config.get("imei", "")
    group_id = input("Group ID (Enter = Test 3): ").strip() or "6150866603217993790"

    upgrade_community(group_id, cookies, imei)
