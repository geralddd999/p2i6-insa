import argparse, csv, random, datetime as _dt, time, requests, io

UTC = _dt.timezone.utc

def make_csv() -> io.BytesIO:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp", "sensor1", "insects"])
    for _ in range(random.randint(5, 20)):
        now = _dt.datetime.now(UTC).isoformat()
        w.writerow([now, round(random.uniform(20, 30), 2), random.randint(0, 5)])
    bio = io.BytesIO(buf.getvalue().encode())
    bio.name = f"{_dt.datetime.now(UTC).isoformat()}.csv"
    return bio

def blank_jpeg(name: str) -> io.BytesIO:
    RAW = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb0043000101"
        "010101010101010101010101010101010101010101010101010101"
        "0101010101010101ffc00011080100010103012200021101031101"
        "ffc40014000100000000000000000000000000ffda000c03010002"
        "110311003f00d2cf20ffd9"
    )
    bio = io.BytesIO(RAW)
    bio.name = name
    return bio

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--token", default="secret-token")
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    while True:
        csv_file = make_csv()
        images = [
            blank_jpeg(f"{_dt.datetime.now(UTC).isoformat()}.jpg")
            for _ in range(random.randint(0, 3))
        ]

        # ----- THIS is the important change -----
        files = [("csv", (csv_file.name, csv_file, "text/csv"))]
        for img in images:
            files.append(("images", (img.name, img, "image/jpeg")))
        # ----------------------------------------

        resp = requests.post(
            f"{args.server}/api/upload",
            files=files,
            headers={"Authorization": f"Bearer {args.token}"},
            timeout=30,
        )
        print("Upload status:", resp.status_code, resp.text)
        time.sleep(args.interval)
