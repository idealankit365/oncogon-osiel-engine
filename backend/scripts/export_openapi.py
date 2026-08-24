from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    target = project_root / "contracts" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Exported {target}")


if __name__ == "__main__":
    main()
