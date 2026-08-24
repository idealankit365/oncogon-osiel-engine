from __future__ import annotations

import base64
import csv
import io
import re
from datetime import UTC, datetime

from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import PlateReaderImportRequest, PlateReaderValidation


REQUIRED_COLUMNS = ("plate_id", "well", "compound_id", "concentration_um", "replicate", "raw_luminescence", "control_type")


class PlateReaderService:
    def __init__(self, repository: Repository, store: ImmutableObjectStore | None = None) -> None:
        self.repository = repository
        self.store = store or object_store

    def validate(self, request: PlateReaderImportRequest, actor: str) -> PlateReaderValidation:
        try:
            raw = base64.b64decode(request.content_base64, validate=True)
        except Exception as exc:
            raise ValueError("content_base64 is not valid base64") from exc
        if not raw or len(raw) > 15_000_000:
            raise ValueError("Instrument file must contain 1 byte to 15 MB")
        if not request.filename.lower().endswith(".csv"):
            raise ValueError("Reference adapter accepts CSV; add a qualified adapter for this instrument format")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must be UTF-8 encoded") from exc
        reader = csv.DictReader(io.StringIO(text))
        headers = [value.strip().lower() for value in (reader.fieldnames or [])]
        mapped = [column for column in REQUIRED_COLUMNS if column in headers]
        missing = [column for column in REQUIRED_COLUMNS if column not in headers]
        rows = list(reader)
        plate_wells: set[tuple[str, str]] = set()
        duplicates: set[str] = set()
        invalid: set[str] = set()
        controls: set[str] = set()
        plates: set[str] = set()
        max_row = "H" if request.expected_plate_format == "96" else "P"
        max_col = 12 if request.expected_plate_format == "96" else 24
        pattern = re.compile(r"^([A-Z])(\d{1,2})$")
        for row in rows:
            normalized = {str(key).strip().lower(): str(value or "").strip() for key, value in row.items()}
            plate = normalized.get("plate_id", "")
            well = normalized.get("well", "").upper()
            plates.add(plate) if plate else None
            match = pattern.match(well)
            if not match or not ("A" <= match.group(1) <= max_row) or not (1 <= int(match.group(2)) <= max_col):
                invalid.add(well or "<blank>")
            key = (plate, well)
            if key in plate_wells:
                duplicates.add(f"{plate}:{well}")
            plate_wells.add(key)
            control = normalized.get("control_type", "").lower()
            if control:
                controls.add(control)
            for numeric in ("concentration_um", "replicate", "raw_luminescence"):
                if numeric in normalized:
                    try:
                        float(normalized[numeric])
                    except ValueError:
                        invalid.add(f"{plate}:{well}:{numeric}")
        warnings: list[str] = []
        if "vehicle" not in controls:
            warnings.append("Vehicle control not found")
        if "positive" not in controls:
            warnings.append("Positive control not found")
        if len(plates) != 1:
            warnings.append("A qualified import should contain exactly one plate_id")
        schema_valid = not missing and bool(rows)
        qc_ready = schema_valid and not duplicates and not invalid and not warnings
        import_id = self.repository.new_id("IMP")
        sha256, object_uri = self.store.put(raw, request.filename, {"import_id": import_id, "actor": actor, "instrument": {"manufacturer": request.instrument_manufacturer, "model": request.instrument_model, "serial": request.instrument_serial, "software_version": request.software_version}, "signal_unit": request.signal_unit})
        result = PlateReaderValidation(import_id=import_id, filename=request.filename, sha256=sha256, byte_count=len(raw), row_count=len(rows), mapped_columns=mapped, missing_columns=missing, duplicate_wells=sorted(duplicates), invalid_wells=sorted(invalid), control_types=sorted(controls), plate_ids=sorted(plates), schema_valid=schema_valid, qc_ready=qc_ready, object_uri=object_uri, warnings=warnings, created_at=datetime.now(UTC))
        self.repository.audit(actor, "plate_reader.import_validated", "instrument_import", import_id, result.model_dump(mode="json"))
        return result
