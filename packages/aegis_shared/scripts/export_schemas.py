"""Export Pydantic contracts to JSON Schema.

These artifacts are the handoff to the frontend: the TypeScript client generator
consumes them so the UI can never silently drift from the backend contract.

Usage:
    python packages/aegis_shared/scripts/export_schemas.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from aegis_shared.contracts import api as api_contracts
from aegis_shared.contracts import agents as agent_contracts

DEFAULT_OUT = Path(__file__).resolve().parents[3] / "schemas" / "generated"


def _models(module: object) -> list[type[BaseModel]]:
    out: list[type[BaseModel]] = []
    for name in getattr(module, "__all__", dir(module)):
        obj = getattr(module, name, None)
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            out.append(obj)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    exported = 0
    for module in (agent_contracts, api_contracts):
        for model in _models(module):
            schema = model.model_json_schema()
            (args.out / f"{model.__name__}.json").write_text(
                json.dumps(schema, indent=2), encoding="utf-8"
            )
            exported += 1

    print(f"Exported {exported} JSON Schemas to {args.out}")


if __name__ == "__main__":
    main()
