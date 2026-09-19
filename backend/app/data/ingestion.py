from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


class FileIngestionService:
    """Read tabular files into a neutral list-of-dicts representation."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

    def read(self, filename: str, content: bytes) -> list[dict[str, Any]]:
        extension = Path(filename).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        buffer = BytesIO(content)
        if extension == ".csv":
            frame = pd.read_csv(buffer)
        else:
            frame = pd.read_excel(buffer)

        frame = frame.where(pd.notna(frame), None)
        return frame.to_dict(orient="records")

    def profile(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        columns = sorted({key for row in rows for key in row})
        return {
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": columns,
            "empty_rows": sum(not any(value not in (None, "") for value in row.values()) for row in rows),
        }
