from __future__ import annotations

import csv
import importlib
import io
from datetime import UTC, datetime
from typing import Any

from ..immutable_storage import object_store


TDC_GROUPS = {
    "adme": "tdc.single_pred.ADME",
    "tox": "tdc.single_pred.Tox",
    "hts": "tdc.single_pred.HTS",
}


class TDCUnavailable(RuntimeError):
    pass


class TDCConnector:
    """Lazy adapter for the official PyTDC package and its dataset registry."""

    @staticmethod
    def available() -> bool:
        try:
            importlib.import_module("tdc")
            return True
        except ImportError:
            return False

    def fetch(self, group: str, dataset: str, *, max_records: int = 1000) -> dict[str, Any]:
        path = TDC_GROUPS.get(group.casefold())
        if path is None:
            raise ValueError(f"Unsupported TDC group; choose one of {', '.join(sorted(TDC_GROUPS))}")
        try:
            module_name, class_name = path.rsplit(".", 1)
            dataset_class = getattr(importlib.import_module(module_name), class_name)
        except (ImportError, AttributeError) as exc:
            raise TDCUnavailable("Install the optional PyTDC connector dependency") from exc
        instance = dataset_class(name=dataset)
        frame = instance.get_data()
        rows = frame.head(min(max(max_records, 1), 10_000)).to_dict(orient="records")
        buffer = io.StringIO()
        fieldnames = list(rows[0]) if rows else []
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
        raw = buffer.getvalue().encode("utf-8")
        digest, uri = object_store.put(
            raw,
            f"tdc-{group}-{dataset}.csv",
            {
                "source_code": "tdc",
                "group": group,
                "dataset": dataset,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "data_class": "raw-source-snapshot",
            },
        )
        return {
            "source_code": "tdc",
            "group": group,
            "dataset": dataset,
            "status": "quarantined-for-schema-qc",
            "record_count": len(rows),
            "columns": fieldnames,
            "record_preview": rows[:25],
            "sha256": digest,
            "object_uri": uri,
            "training_eligible": False,
            "next_gate": "dataset-specific licence review, split policy, schema QC and scientific approval",
        }
