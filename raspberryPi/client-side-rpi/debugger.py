import requests

SERVER_URL = "http://localhost:5000"
TOKEN = "your-secret-token"

# Upload test
files = {
    "csv_0": open("test.csv", "rb"),
    "img_0": open("test.jpg", "rb"),
}
headers = {"Authorization": f"Bearer {TOKEN}"}
resp = requests.post(f"{SERVER_URL}/api/upload", files=files, headers=headers)
print("Upload:", resp.status_code, resp.json())

# Status test
data = {"battery_pct": 75, "disk_free": 123456789}
resp = requests.post(f"{SERVER_URL}/api/status", json=data, headers=headers)
print("Status:", resp.status_code, resp.json())