from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pathlib import Path
import shutil, aiofiles, datetime as _dt, json, typing as _t
from .auth import verify_token, API_TOKEN
from .database import init_db, get_db, insert_upload, insert_photo, insert_health, insert_error, insert_log
from .utils import ensure_day_dirs, stats_last_3_days, build_tree, monthly_recap, build_nested_tree
import sqlite3
from starlette.requests import Request
import io, zipfile, os



DATA_DIR = Path("data")
init_db()

app = FastAPI(title="Insect Hub",
              root_path=os.getenv("ROOT_PATH", "/allinon"))

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

@app.post("/api/upload", dependencies=[Depends(verify_token)])
async def upload(
    csv: UploadFile | None = File(None),
    images: list[UploadFile] = File(default=[]),
    log: UploadFile | None = File(None),           
    health: str | None = Form(None),
    error: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
):
    day = _dt.date.today().isoformat()
    day_dir = ensure_day_dirs(DATA_DIR, day)

    csv_path = ""
    if csv is not None:
        day_csv = day_dir / "csv" / f"{day}.csv"
        is_new  = not day_csv.exists()

        # read entire incoming CSV into memory (usually < 50 kB)
        raw_text = (await csv.read()).decode()

        # drop the first line (header) if today's file already exists
        if not is_new:
            raw_text = "\n".join(raw_text.splitlines()[1:])

        # append (or create) in binary mode
        async with aiofiles.open(day_csv, "ab") as out:
            await out.write(raw_text.encode())

        csv_path = str(day_csv)
        await csv.close() 

    upload_id = insert_upload(db, day, csv_path)

    for img in images:
        img_dst = day_dir / "img" / img.filename
        async with aiofiles.open(img_dst, "wb") as out:
            while chunk := await img.read(1024 * 1024):
                await out.write(chunk)
        insert_photo(db, upload_id, str(img_dst))

    if health:
        try:
            insert_health(db, upload_id, json.loads(health))
        except json.JSONDecodeError:
            pass
    if error:
        try:
            insert_error(db, upload_id, json.loads(error))
        except json.JSONDecodeError:
            pass
    if csv is None and not images and log is None:
        raise HTTPException(400, "upload must contain csv ,images or logs")
    
    if log is not None:
        # one log file per day  ->   data/YYYY/MM/log/2025-06-04.log
        log_dst = day_dir / "log" / f"{day}.log"
    
        # append if it already exists, otherwise create
        async with aiofiles.open(log_dst, "ab") as out:     # ← "a" for append
            while chunk := await log.read(1024 * 1024):
                await out.write(chunk)
        await log.close()
    
        # store the path once (OPTIONAL)
        insert_log(db, upload_id, str(log_dst))

    db.commit()
    return {"ack": True}

@app.get("/api/summary/3d", dependencies=[Depends(verify_token)])
async def last_three_days():
    return stats_last_3_days(DATA_DIR)

@app.get("/api/tree", dependencies=[Depends(verify_token)])
async def data_tree():
    return build_tree(DATA_DIR)

@app.get("/api/monthly/{year_month}", dependencies=[Depends(verify_token)])
async def monthly(year_month: str):
    try:
        _ = _dt.datetime.strptime(year_month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YYYY-MM format")
    return monthly_recap(DATA_DIR, year_month)

@app.get("/api/maintenance", dependencies=[Depends(verify_token)])
async def maintenance(db: sqlite3.Connection = Depends(get_db)):
    # latest health JSON (kept for completeness)
    health_row = db.execute(
        "SELECT payload, created_at FROM health ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # latest log file
    log_row = db.execute(
        "SELECT file_path, created_at FROM logs ORDER BY id DESC LIMIT 1"
    ).fetchone()

    log_text = ""
    if log_row:
        try:
            with open(log_row["file_path"], "r", errors="ignore") as f:
                log_text = f.read()[-20_000:]   # show last 20 KB
        except FileNotFoundError:
            pass

    return {
        "health": json.loads(health_row[0]) if health_row else {},
        "health_time": health_row[1] if health_row else None,
        "log_text": log_text,
        "log_time": log_row["created_at"] if log_row else None,
    }

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    summary = stats_last_3_days(DATA_DIR)
    return templates.TemplateResponse("dashboard.html", {"request": request, "summary": summary})



@app.get("/data", response_class=HTMLResponse)
async def data_view(request: Request):
    tree  = build_nested_tree(DATA_DIR)
    token = os.getenv("API_TOKEN", "very-secret-and-difficult-token")   # server’s current token
    return templates.TemplateResponse(
        "data_tree.html",
        {"request": request, "tree": tree, "token": token},
    )

@app.get("/maintenance", response_class=HTMLResponse)
async def maintenance_view(request: Request, db: sqlite3.Connection = Depends(get_db)):
    health_row = db.execute(
        "SELECT payload, created_at FROM health ORDER BY id DESC LIMIT 1"
    ).fetchone()

    log_row = db.execute(
        "SELECT file_path, created_at FROM logs ORDER BY id DESC LIMIT 1"
    ).fetchone()

    log_text = ""
    if log_row:
        try:
            with open(log_row["file_path"], "r", errors="ignore") as f:
                log_text = f.read().replace("\r\n", "\n").replace("\r", "\n")
        except FileNotFoundError:
            pass

    data = {
        "health": json.loads(health_row[0]) if health_row else {},
        "health_time": health_row[1] if health_row else None,
        "log_text": log_text,
        "log_time": log_row["created_at"] if log_row else None,
    }
    return templates.TemplateResponse("maintenance.html", {"request": request, "data": data})


@app.get("/download/{day}", dependencies=[Depends(verify_token)])
async def download_day(day: str):
    day_dir = DATA_DIR / day
    if not day_dir.exists() or not day_dir.is_dir():
        raise HTTPException(status_code=404, detail="day not found")

    # in-memory ZIP so we don’t clutter the disk
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in day_dir.rglob("*"):
            zf.write(path, arcname=path.relative_to(DATA_DIR))
    zip_buffer.seek(0)

    filename = f"{day}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)

@app.get("/download/{path:path}", dependencies=[Depends(verify_token)])
async def download_path(path: str):
    base = DATA_DIR.resolve()              # absolute “data/” once
    full = (base / path).resolve()

    if base not in full.parents and full != base:
        raise HTTPException(status_code=403, detail="Forbidden")

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        if full.is_file():
            # <-- here
            zf.write(full, arcname=full.relative_to(base))
        else:
            for file in full.rglob("*"):
                if file.is_file():
                    # <-- and here
                    zf.write(file, arcname=file.relative_to(base))

    zbuf.seek(0)
    fname = f"{full.relative_to(base)}.zip".replace(os.sep, "-")
    return StreamingResponse(
        zbuf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )