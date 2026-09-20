from __future__ import annotations

from typing import Final

import pandas as pd


class DatasetNotFoundError(LookupError):
    """Raised when the requested dataset cannot be resolved."""


class DatasetService:
    """Application service that resolves a RiskIQ dataset into a DataFrame.

    The current implementation is a deterministic stub for the analyst contract.
    Replace the marked repository/bucket section when persistent dataset retrieval
    is enabled.
    """

    _COLUMNS: Final[tuple[str, ...]] = (
        "loan_id",
        "customer_id",
        "segment",
        "outstanding_principal",
        "dpd",
    )

    async def get_dataset_as_dataframe(self, dataset_id: str) -> pd.DataFrame:
        normalized_id = dataset_id.strip()
        if not normalized_id:
            raise DatasetNotFoundError("dataset_id is required")

        # TODO: Replace this stub with the persistent dataset lookup.
        # FUTURE DATABASE/BUCKET LOGIC:
        # 1. Resolve dataset metadata from MongoDB using dataset_id.
        # 2. Resolve the canonical portfolio records for that dataset.
        # 3. If the source is object storage, load the dataset from S3/GCS.
        # 4. Normalize the records into the AnalystEngine canonical schema.
        # 5. Raise DatasetNotFoundError when the dataset cannot be resolved.

        # Temporary deterministic fixture: useful for wiring and contract tests.
        seed = sum(ord(char) for char in normalized_id)
        rows = [
            {
                "loan_id": f"{normalized_id}-001",
                "customer_id": f"C{seed % 10000:04d}",
                "segment": "retail",
                "outstanding_principal": 10000.0,
                "dpd": 0,
            },
            {
                "loan_id": f"{normalized_id}-002",
                "customer_id": f"C{(seed + 1) % 10000:04d}",
                "segment": "microcredit",
                "outstanding_principal": 7500.0,
                "dpd": 35,
            },
            {
                "loan_id": f"{normalized_id}-003",
                "customer_id": f"C{(seed + 2) % 10000:04d}",
                "segment": "retail",
                "outstanding_principal": 12500.0,
                "dpd": 95,
            },
        ]
        return pd.DataFrame(rows, columns=self._COLUMNS)
