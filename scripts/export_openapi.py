import json
from pathlib import Path

from backend.app.main import app


def main() -> None:
    destination = Path("artifacts/openapi.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
