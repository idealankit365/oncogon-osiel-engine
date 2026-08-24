from __future__ import annotations

import base64

from app.immutable_storage import ImmutableObjectStore
from app.plate_reader import PlateReaderService
from app.schemas import PlateReaderImportRequest


def request_for(csv_text: str) -> PlateReaderImportRequest:
    return PlateReaderImportRequest(
        filename="reader-export.csv",
        content_base64=base64.b64encode(csv_text.encode()).decode(),
        instrument_manufacturer="Reference Instruments",
        instrument_model="Reader 96",
        instrument_serial="SERIAL-001",
        software_version="1.0",
        signal_unit="RLU",
        expected_plate_format="96",
    )


def test_plate_reader_import_is_hashed_quarantined_and_qc_ready(repository, tmp_path):
    service = PlateReaderService(repository, ImmutableObjectStore(tmp_path / "objects"))
    csv_text = "plate_id,well,compound_id,concentration_um,replicate,raw_luminescence,control_type\nP1,A1,VEH,0,1,1000,vehicle\nP1,A2,POS,1,1,20,positive\nP1,B1,CMP-CUR-0001,0.1,1,540,sample\n"
    result = service.validate(request_for(csv_text), "student-1")
    assert result.schema_valid is True
    assert result.qc_ready is True
    assert result.quarantined is True
    assert result.training_eligible is False
    assert len(result.sha256) == 64
    assert result.object_uri.startswith("immutable://sha256/")


def test_plate_reader_import_blocks_duplicate_and_invalid_well(repository, tmp_path):
    service = PlateReaderService(repository, ImmutableObjectStore(tmp_path / "objects"))
    csv_text = "plate_id,well,compound_id,concentration_um,replicate,raw_luminescence,control_type\nP1,Z99,VEH,0,1,1000,vehicle\nP1,Z99,POS,1,1,20,positive\n"
    result = service.validate(request_for(csv_text), "student-1")
    assert result.schema_valid is True
    assert result.qc_ready is False
    assert result.duplicate_wells == ["P1:Z99"]
    assert result.invalid_wells == ["Z99"]
