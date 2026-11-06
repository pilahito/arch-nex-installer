#!/usr/bin/env python3
"""Inventario de dispositivos de bloque en modo de solo lectura."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


LSBLK_FIELDS = (
    "NAME,TYPE,SIZE,RO,RM,MODEL,FSTYPE,MOUNTPOINTS"
)


def _flag(value: Any) -> bool:
    """Interpreta los indicadores numéricos de lsblk."""
    return str(value).strip().lower() in {"1", "true", "yes"}


def _devices(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Devuelve discos y particiones sin incluir identificadores sensibles."""
    result: list[dict[str, Any]] = []
    for node in nodes:
        kind = node.get("type")
        if kind in {"disk", "part"}:
            result.append(
                {
                    "name": node.get("name"),
                    "type": kind,
                    "size_bytes": node.get("size"),
                    "read_only": _flag(node.get("ro")),
                    "removable": _flag(node.get("rm")),
                    "model": node.get("model"),
                    "filesystem": node.get("fstype"),
                    "mountpoints": [
                        item for item in (node.get("mountpoints") or []) if item
                    ],
                }
            )
        result.extend(_devices(node.get("children") or []))
    return result


def collect_report(run=subprocess.run) -> dict[str, Any]:
    """Consulta lsblk y devuelve un informe sin realizar operaciones de escritura."""
    completed = run(
        ["lsblk", "--json", "--bytes", "--output", LSBLK_FIELDS],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return {
        "schema_version": 1,
        "mode": "read-only",
        "write_operations_enabled": False,
        "devices": _devices(payload.get("blockdevices") or []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Genera un inventario de almacenamiento de solo lectura."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="crea el informe en este archivo; no sobrescribe archivos existentes",
    )
    args = parser.parse_args(argv)

    try:
        report = collect_report()
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            sys.stdout.write(serialized)
        else:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"Error al generar el informe: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
