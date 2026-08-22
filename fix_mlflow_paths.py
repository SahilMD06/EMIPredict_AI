"""Re-point MLflow artifact paths at this folder's current location.

MLflow stores absolute artifact paths in mlflow.db. If the project folder is moved,
renamed, or copied to another machine, those paths go stale and the UI shows
"Loading artifact failed". Bare Windows paths like C:/... also break, because MLflow
parses the drive letter as a URI scheme.

This script rewrites every artifact location to a proper file:// URI pointing at the
folder this script lives in.

Usage (stop the MLflow server first):
    python fix_mlflow_paths.py
"""
import os
import pathlib
import sqlite3
import sys
import urllib.parse
import urllib.request

DB = "mlflow.db"
PROJECT_DIR = pathlib.Path(__file__).resolve().parent


def to_file_uri(path: pathlib.Path) -> str:
    """C:\\Labmentix\\EMIPredict AI  ->  file:///C:/Labmentix/EMIPredict%20AI

    pathlib handles the drive letter and percent-encoding correctly on both
    Windows and POSIX.
    """
    return path.as_uri()


def main():
    os.chdir(PROJECT_DIR)
    if not os.path.exists(DB):
        sys.exit(f"ERROR: {DB} not found in {PROJECT_DIR}")

    new_base = to_file_uri(PROJECT_DIR)
    print(f"Project folder : {PROJECT_DIR}")
    print(f"New artifact URI base: {new_base}\n")

    try:
        con = sqlite3.connect(DB)
    except sqlite3.OperationalError as e:
        sys.exit(f"ERROR: cannot open {DB} ({e}). Is the MLflow server still running?")

    # Every column that can hold an artifact location, across MLflow's schema.
    targets = []
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for row in con.execute(f"PRAGMA table_info({table})"):
            col = row[1]
            if any(k in col for k in ("location", "uri", "source")):
                targets.append((table, col))

    total = 0
    for table, col in targets:
        rows = con.execute(
            f"SELECT rowid, {col} FROM {table} WHERE {col} LIKE '%mlruns%'"
        ).fetchall()
        for rowid, value in rows:
            if not value:
                continue
            # Keep only the part from 'mlruns/' onwards, re-anchor it to this folder.
            marker = value.replace("\\", "/").find("mlruns/")
            if marker == -1:
                continue
            tail = value.replace("\\", "/")[marker:]
            new_value = f"{new_base}/{urllib.parse.quote(tail, safe='/')}"
            if new_value != value:
                con.execute(f"UPDATE {table} SET {col}=? WHERE rowid=?", (new_value, rowid))
                total += 1
        if rows:
            print(f"  {table}.{col}: {len(rows)} row(s) checked")

    con.commit()

    # Verify the rewritten locations point at directories that actually exist.
    # Uses the same URI -> filesystem path conversion MLflow's server performs.
    def uri_to_path(uri: str) -> str:
        return urllib.request.url2pathname(urllib.parse.urlparse(uri).path)

    ok = missing = 0
    for table, col in targets:
        for (value,) in con.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE 'file:///%'"):
            path = uri_to_path(value)
            if os.path.isdir(path):
                ok += 1
            else:
                missing += 1
                print(f"  MISSING: {path}")
    con.close()

    print(f"\nUpdated {total} path(s).")
    print(f"Verified: {ok} artifact location(s) exist on disk, {missing} missing.")
    if missing:
        print("(A small number of 'missing' entries is expected: the unused Default\n"
              " experiment and any deleted/failed runs never wrote artifacts.)")
    print("\nNow restart the server:")
    print("    mlflow ui --backend-store-uri sqlite:///mlflow.db")


if __name__ == "__main__":
    main()
