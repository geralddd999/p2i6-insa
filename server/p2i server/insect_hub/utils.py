from pathlib import Path
import csv, datetime as _dt, statistics, json, typing as _t
import pandas as pd

def ensure_day_dirs(base: Path, day: str) -> Path:
    """
    Store files as   data/<YEAR>/<MONTH>/{csv,img}/…
    Example day == '2025-04-28'  →  data/2025/04/csv/
    """
    year, month, _ = day.split("-")
    month_dir = base / year / month
    (month_dir / "csv").mkdir(parents=True, exist_ok=True)
    (month_dir / "img").mkdir(exist_ok=True)
    return month_dir        # we now return the MONTH-level directory


def stats_last_3_days(data_dir: Path) -> dict:
    today = _dt.date.today()
    days = [(today - _dt.timedelta(days=i)).isoformat() for i in range(3)]
    numeric_cols: dict[str, list[float]] = {}
    insects_total = 0
    for d in days:
        csv_folder = data_dir / d / "csv"
        if not csv_folder.exists():
            continue
        for csv_file in csv_folder.glob("*.csv"):
            df = pd.read_csv(csv_file)
            insect_cols = [c for c in df.columns if "insect" in c.lower()]
            if insect_cols:
                insects_total += int(df[insect_cols[0]].sum())
            for col in df.select_dtypes(include=["number"]).columns:
                numeric_cols.setdefault(col, []).extend(df[col].dropna().tolist())
    averages = {col: statistics.mean(vals) for col, vals in numeric_cols.items() if vals}
    return {"insects": insects_total, "averages": averages}

def build_tree(data_dir: Path) -> list[dict]:
    tree = []
    for day in sorted(p.name for p in data_dir.iterdir() if p.is_dir()):
        day_dir = data_dir / day
        node = {"name": day, "path": f"/data/{day}", "files": []}
        for sub in (day_dir / "csv").glob("*.csv"):
            node["files"].append(sub.name)
        tree.append(node)
    return tree

def monthly_recap(data_dir: Path, year_month: str) -> dict:
    target = _dt.datetime.strptime(year_month, "%Y-%m")
    start = _dt.date(target.year, target.month, 1)
    next_month = (start.replace(day=28) + _dt.timedelta(days=4)).replace(day=1)
    days = [(start + _dt.timedelta(days=i)).isoformat() 
            for i in range((next_month - start).days)]
    insects = 0
    numeric: dict[str, list[float]] = {}
    for d in days:
        csv_folder = data_dir / d / "csv"
        if not csv_folder.exists():
            continue
        for f in csv_folder.glob("*.csv"):
            df = pd.read_csv(f)
            insect_cols = [c for c in df.columns if "insect" in c.lower()]
            if insect_cols:
                insects += int(df[insect_cols[0]].sum())
            for col in df.select_dtypes(include=["number"]).columns:
                numeric.setdefault(col, []).extend(df[col].dropna().tolist())
    averages = {col: statistics.mean(vals) for col, vals in numeric.items() if vals}
    return {"insects": insects, "averages": averages}


def build_nested_tree(data_dir: Path) -> dict:
    """
    Return  {year: {month: [file-names]}}
    """
    tree: dict[str, dict[str, list[str]]] = {}
    for year_dir in data_dir.glob("*"):
        if not year_dir.is_dir():
            continue
        for month_dir in year_dir.glob("*"):
            if not month_dir.is_dir():
                continue
            csv_files = sorted((month_dir / "csv").glob("*.csv"))
            if csv_files:
                tree.setdefault(year_dir.name, {})[month_dir.name] = [
                    f.name for f in csv_files
                ]
    return dict(sorted(tree.items()))
