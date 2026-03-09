#!/usr/bin/env python3
"""Strictly compare website MATRIX_DATA against LoC YAML sources."""

from __future__ import annotations

import ast
import argparse
import pathlib
import re
import sys
from typing import Any

import yaml


ROOT = pathlib.Path(__file__).resolve().parent.parent
MATRIX_DIR = ROOT / "matrix"
DEFAULT_HTML_PATH = ROOT.parent / "beegigurtsis" / "server" / "web" / "threat-matrix.html"


def strip_trailing_newlines(value: Any) -> Any:
    if isinstance(value, str):
        return value.rstrip("\n")
    if isinstance(value, list):
        return [strip_trailing_newlines(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_trailing_newlines(item) for key, item in value.items()}
    return value


def extract_matrix_literal(html: str) -> str:
    marker = "var MATRIX_DATA ="
    marker_index = html.find(marker)
    if marker_index == -1:
        raise ValueError("Could not find 'var MATRIX_DATA =' in HTML file.")

    start = html.find("[", marker_index)
    if start == -1:
        raise ValueError("Could not find MATRIX_DATA array start.")

    depth = 0
    in_string = False
    escape = False
    quote_char = ""

    for index in range(start, len(html)):
        char = html[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                in_string = False
            continue

        if char in ("'", '"'):
            in_string = True
            quote_char = char
            continue

        if char == "[":
            depth += 1
            continue

        if char == "]":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
            continue

    raise ValueError("Could not find MATRIX_DATA array end.")


def parse_html_matrix(path: pathlib.Path) -> list[dict[str, Any]]:
    html = path.read_text(encoding="utf-8")
    literal = extract_matrix_literal(html)
    literal = re.sub(r",(\s*[}\]])", r"\1", literal)
    literal = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', literal)

    try:
        data = ast.literal_eval(literal)
    except Exception as exc:
        raise ValueError(f"Failed to parse MATRIX_DATA from HTML: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Parsed MATRIX_DATA is not a list.")

    return strip_trailing_newlines(data)


def load_yaml_matrix() -> list[dict[str, Any]]:
    tactics: list[dict[str, Any]] = []
    for path in sorted(MATRIX_DIR.glob("*.yaml")):
        tactic = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(tactic, dict):
            raise ValueError(f"{path.name} did not parse to a mapping.")
        tactic["_source_file"] = path.name
        tactics.append(strip_trailing_newlines(tactic))
    return tactics


def compare_evidence(
    mismatches: list[str],
    tactic_name: str,
    technique_name: str,
    website_evidence: Any,
    yaml_evidence: Any,
) -> None:
    if not isinstance(website_evidence, list):
        mismatches.append(
            f"{tactic_name} > {technique_name} > evidence: website value is not a list: {website_evidence!r}"
        )
        return
    if not isinstance(yaml_evidence, list):
        mismatches.append(
            f"{tactic_name} > {technique_name} > evidence: YAML value is not a list: {yaml_evidence!r}"
        )
        return

    if len(website_evidence) != len(yaml_evidence):
        mismatches.append(
            f"{tactic_name} > {technique_name} > evidence count mismatch: website={len(website_evidence)} YAML={len(yaml_evidence)}"
        )

    for index, (website_entry, yaml_entry) in enumerate(zip(website_evidence, yaml_evidence), start=1):
        for field in ("title", "authors", "year", "url"):
            website_value = website_entry.get(field)
            yaml_value = yaml_entry.get(field)
            if website_value != yaml_value:
                mismatches.append(
                    f"{tactic_name} > {technique_name} > evidence[{index}].{field} mismatch:\n"
                    f"  website: {website_value!r}\n"
                    f"  YAML:    {yaml_value!r}"
                )


def compare_matrices(
    website_tactics: list[dict[str, Any]],
    yaml_tactics: list[dict[str, Any]],
) -> list[str]:
    mismatches: list[str] = []

    if len(website_tactics) != len(yaml_tactics):
        mismatches.append(
            f"Tactic count mismatch: website={len(website_tactics)} YAML={len(yaml_tactics)}"
        )

    for tactic_index, (website_tactic, yaml_tactic) in enumerate(
        zip(website_tactics, yaml_tactics), start=1
    ):
        tactic_name = website_tactic.get("name", f"tactic[{tactic_index}]")
        yaml_tactic_name = yaml_tactic.get("name", f"tactic[{tactic_index}]")

        for field in ("name", "description"):
            website_value = website_tactic.get(field)
            yaml_value = yaml_tactic.get(field)
            if website_value != yaml_value:
                mismatches.append(
                    f"{tactic_name} > {field} mismatch:\n"
                    f"  website: {website_value!r}\n"
                    f"  YAML:    {yaml_value!r}"
                )

        website_techniques = website_tactic.get("techniques")
        yaml_techniques = yaml_tactic.get("techniques")

        if not isinstance(website_techniques, list) or not isinstance(yaml_techniques, list):
            mismatches.append(
                f"{tactic_name} > techniques malformed: website={type(website_techniques).__name__} YAML={type(yaml_techniques).__name__}"
            )
            continue

        if len(website_techniques) != len(yaml_techniques):
            mismatches.append(
                f"{tactic_name} > technique count mismatch: website={len(website_techniques)} YAML={len(yaml_techniques)}"
            )

        for technique_index, (website_technique, yaml_technique) in enumerate(
            zip(website_techniques, yaml_techniques), start=1
        ):
            technique_name = website_technique.get("name", f"technique[{technique_index}]")
            yaml_technique_name = yaml_technique.get("name", f"technique[{technique_index}]")

            if technique_name != yaml_technique_name:
                mismatches.append(
                    f"{tactic_name} > technique[{technique_index}] name/order mismatch:\n"
                    f"  website: {technique_name!r}\n"
                    f"  YAML:    {yaml_technique_name!r}"
                )

            field_pairs = (
                ("name", "name"),
                ("level", "level"),
                ("description", "description"),
                ("capabilityStatus", "capability_status"),
                ("mitigations", "mitigations"),
            )
            for website_field, yaml_field in field_pairs:
                website_value = website_technique.get(website_field)
                yaml_value = yaml_technique.get(yaml_field)
                if website_value != yaml_value:
                    mismatches.append(
                        f"{tactic_name} > {technique_name} > {website_field}/{yaml_field} mismatch:\n"
                        f"  website: {website_value!r}\n"
                        f"  YAML:    {yaml_value!r}"
                    )

            compare_evidence(
                mismatches,
                tactic_name,
                technique_name,
                website_technique.get("evidence"),
                yaml_technique.get("evidence"),
            )

    return mismatches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare website MATRIX_DATA against LoC YAML files."
    )
    parser.add_argument(
        "--html-path",
        type=pathlib.Path,
        default=DEFAULT_HTML_PATH,
        help="Path to server/web/threat-matrix.html",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    website_tactics = parse_html_matrix(args.html_path.resolve())
    yaml_tactics = load_yaml_matrix()
    mismatches = compare_matrices(website_tactics, yaml_tactics)

    if mismatches:
        print("Matrix sync check failed:")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        return 1

    print("Matrix sync check passed: website MATRIX_DATA matches YAML sources exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
