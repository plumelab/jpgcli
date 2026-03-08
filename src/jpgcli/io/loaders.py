from __future__ import annotations

from pathlib import Path

import pandas as pd

from jpgcli.utils.errors import InputDataError


def load_input(path: Path, sheet: str | None = None) -> tuple[pd.DataFrame | None, str, str | None]:
    if not path.exists():
        raise InputDataError(f"Input file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path), "csv", None
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        frame = pd.read_excel(path, sheet_name=sheet or 0)
        resolved_sheet = sheet if sheet is not None else None
        return frame, "excel", resolved_sheet
    if suffix == ".txt":
        return None, "text", None
    raise InputDataError(f"Unsupported input type: {suffix}")


def load_text(path: Path) -> str:
    if not path.exists():
        raise InputDataError(f"Input file does not exist: {path}")
    return path.read_text(encoding="utf-8")
