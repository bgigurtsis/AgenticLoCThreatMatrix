#!/usr/bin/env python3
"""Validate matrix YAML files against a simple schema."""

from __future__ import annotations

import pathlib
import sys

import yaml


ROOT = pathlib.Path(__file__).resolve().parent.parent
MATRIX_DIR = ROOT / "matrix"
VALID_LEVELS = {"full", "partial", "theoretical", "proposed"}


def expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_file(path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        return [f"{path.name}: failed to parse YAML: {exc}"]

    expect(isinstance(data, dict), f"{path.name}: top level must be a mapping", errors)
    if not isinstance(data, dict):
        return errors

    expect(isinstance(data.get("name"), str) and data["name"].strip(), f"{path.name}: missing tactic name", errors)
    expect(
        isinstance(data.get("description"), str) and data["description"].strip(),
        f"{path.name}: missing tactic description",
        errors,
    )
    techniques = data.get("techniques")
    expect(isinstance(techniques, list) and techniques, f"{path.name}: techniques must be a non-empty list", errors)
    if not isinstance(techniques, list):
        return errors

    for index, technique in enumerate(techniques, start=1):
        label = f"{path.name} technique #{index}"
        expect(isinstance(technique, dict), f"{label}: technique must be a mapping", errors)
        if not isinstance(technique, dict):
            continue

        for field in ("name", "description", "capability_status", "mitigations"):
            value = technique.get(field)
            expect(isinstance(value, str) and value.strip(), f"{label}: missing {field}", errors)

        level = technique.get("level")
        expect(level in VALID_LEVELS, f"{label}: invalid level {level!r}", errors)

        evidence = technique.get("evidence")
        expect(isinstance(evidence, list), f"{label}: evidence must be a list", errors)
        if isinstance(evidence, list):
            for evidence_index, entry in enumerate(evidence, start=1):
                evidence_label = f"{label} evidence #{evidence_index}"
                expect(isinstance(entry, dict), f"{evidence_label}: entry must be a mapping", errors)
                if not isinstance(entry, dict):
                    continue
                for field in ("title", "authors", "url"):
                    value = entry.get(field)
                    expect(isinstance(value, str) and value.strip(), f"{evidence_label}: missing {field}", errors)
                expect(isinstance(entry.get("year"), int), f"{evidence_label}: year must be an integer", errors)

    return errors


def main() -> int:
    all_errors: list[str] = []
    for path in sorted(MATRIX_DIR.glob("*.yaml")):
        all_errors.extend(validate_file(path))

    if all_errors:
        print("Matrix validation failed:", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Matrix validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
