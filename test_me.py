import requests

login_res = requests.post(
    "http://127.0.0.1:8000/api/v1/subscribers/auth/login/",
    json={
        "username": "peter",
        "password": "password123",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "device_name": "Test Phone"
    }
)
access = login_res.json().get("access")
if not access:
    print("Login failed:", login_res.text)
    exit(1)

me_res = requests.get(
    "http://127.0.0.1:8000/api/v1/subscribers/me/",
    headers={"Authorization": f"Bearer {access}"}
)
print("Me endpoint response:", me_res.text)
