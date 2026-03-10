#!/usr/bin/env python3
"""Reads matrix/*.yaml and generates README.md."""

import pathlib

import yaml

REPO_URL = "https://github.com/bgigurtsis/AgenticLoCThreatMatrix"
MATRIX_DIR = pathlib.Path(__file__).resolve().parent.parent / "matrix"
README_PATH = pathlib.Path(__file__).resolve().parent.parent / "README.md"

LEVEL_LABELS = {
    "full": "Full",
    "partial": "Partial",
    "theoretical": "Theoretical",
    "proposed": "Proposed",
}


def load_tactics():
    files = sorted(MATRIX_DIR.glob("*.yaml"))
    tactics = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            tactics.append(yaml.safe_load(fh))
    return tactics


def fmt_evidence(evidence_list):
    if not evidence_list:
        return "*None yet.*"
    lines = []
    for e in evidence_list:
        lines.append(
            f'- [{e["title"]}]({e["url"]}) - {e["authors"]}, {e["year"]}'
        )
    return "\n".join(lines)


def generate():
    tactics = load_tactics()

    lines = []

    # Header
    lines.append("# The Agentic Loss-of-Control Threat Matrix")
    lines.append("")
    lines.append(
        "A structured threat matrix mapping the tactics and techniques by which "
        "an AI agent could escalate from initial deployment to autonomous "
        "replication and persistence, modelled as a kill chain."
    )
    lines.append("")
    lines.append(
        "> Threat matrices such as this one should be living documents if we are "
        "to even come close to keeping up with how fast frontier models improve. "
        "The ability to suggest new entries, and to update existing ones, is "
        "essential. See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved."
    )
    lines.append("")

    # Legend
    lines.append("## Capability Levels")
    lines.append("")
    lines.append("| Level | Meaning |")
    lines.append("|-------|---------|")
    lines.append(
        "| **Full** | Agents have completed this technique end-to-end |"
    )
    lines.append(
        "| **Partial** | Agents have performed part of this technique |"
    )
    lines.append(
        "| **Theoretical** | Proposed in literature as a possibility |"
    )
    lines.append(
        "| **Proposed** | Proposed by the author as a possibility |"
    )
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Tactic | Technique | Level |")
    lines.append("|--------|-----------|-------|")
    for tactic in tactics:
        first = True
        for tech in tactic["techniques"]:
            tactic_cell = f"**{tactic['name']}**" if first else ""
            badge = LEVEL_LABELS.get(tech["level"], tech["level"].title())
            tech_link = f'[{tech["name"]}](#{tech["name"].lower().replace(" ", "-")})'
            lines.append(
                f"| {tactic_cell} | {tech_link} | {badge} |"
            )
            first = False
    lines.append("")

    # Detailed sections
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Reference")
    lines.append("")

    for tactic in tactics:
        lines.append(f"### {tactic['name']}")
        lines.append("")
        lines.append(tactic["description"].strip())
        lines.append("")

        for tech in tactic["techniques"]:
            lines.append(f"#### {tech['name']}")
            lines.append("")
            badge = LEVEL_LABELS.get(tech["level"], tech["level"].title())
            lines.append(f"**Level:** {badge}")
            lines.append("")
            lines.append(f"**Description:** {tech['description'].strip()}")
            lines.append("")
            lines.append(
                f"**Capability Status:** {tech['capability_status'].strip()}"
            )
            lines.append("")
            lines.append("**Evidence:**")
            lines.append("")
            lines.append(fmt_evidence(tech.get("evidence", [])))
            lines.append("")
            lines.append(f"**Mitigations:** {tech['mitigations'].strip()}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        f"*This README is auto-generated from the YAML files in [`matrix/`](matrix/). "
        f"Do not edit it by hand - see [CONTRIBUTING.md](CONTRIBUTING.md).*"
    )
    lines.append("")

    README_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {README_PATH}")


if __name__ == "__main__":
    generate()
