from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pathlib import Path
import shutil, aiofiles, datetime as _dt, json, typing as _t
from .auth import verify_token
from .database import init_db, get_db, insert_upload, insert_photo, insert_health, insert_error
from .utils import ensure_day_dirs, stats_last_3_days, build_tree, monthly_recap, build_nested_tree
import sqlite3
from starlette.requests import Request
import io, zipfile, os

DATA_DIR = Path("data")
init_db()

app = FastAPI(title="Insect Hub")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

@app.post("/api/upload", dependencies=[Depends(verify_token)])
async def upload(
    csv: UploadFile | None = File(None),
    images: list[UploadFile] = File(default=[]),
    health: str | None = Form(None),
    error: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
):
    day = _dt.date.today().isoformat()
    day_dir = ensure_day_dirs(DATA_DIR, day)

    csv_path = ""
    if csv is not None:
        csv_dst = day_dir / "csv" / csv.filename
        async with aiofiles.open(csv_dst, "wb") as out:
            while chunk := await csv.read(1024 * 1024):
                await out.write(chunk)
        csv_path = str(csv_dst)

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
    if csv is None and not images:
        raise HTTPException(400, "upload must contain csv and/or images")

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
    row = db.execute("SELECT payload, created_at FROM health ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        return {"payload": json.loads(row[0]), "timestamp": row[1]}
    return {"payload": {}, "timestamp": None}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    summary = stats_last_3_days(DATA_DIR)
    return templates.TemplateResponse("dashboard.html", {"request": request, "summary": summary})



@app.get("/data", response_class=HTMLResponse)
async def data_view(request: Request):
    tree  = build_nested_tree(DATA_DIR)
    token = os.getenv("API_TOKEN", "secret-token")   # server’s current token
    return templates.TemplateResponse(
        "data_tree.html",
        {"request": request, "tree": tree, "token": token},
    )

@app.get("/maintenance", response_class=HTMLResponse)
async def maintenance_view(request: Request, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT payload, created_at FROM health ORDER BY id DESC LIMIT 1").fetchone()
    return templates.TemplateResponse("maintenance.html", {"request": request, "health": row})

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