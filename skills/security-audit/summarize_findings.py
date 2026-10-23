#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
summarize_findings.py -- render findings.json as a human-readable Markdown report.

The audit pipeline stores its output as structured JSON so machines can
consume it, but nobody wants to read a 2 MB JSON file after a long run.
This helper turns the three verdict classes into a compact Markdown digest:

  * confirmed        -- table sorted by overall severity with file:line anchors
  * needs_validation -- blocked leads with the exact unresolved fact
  * rejected         -- disproved candidates, one line each

Output goes to stdout by default. Pass -o report.md to write a file instead.

Usage:
    python summarize_findings.py <findings.json>
    python summarize_findings.py <findings.json> -o SUMMARY.md
"""

import argparse
import json
import sys

SEVERITY_ORDER = ["critical", "high", "medium", "low", "informational"]


def _severity_key(record):
    sev = (record.get("severity") or {}).get("overall_severity") or {}
    if isinstance(sev, dict):
        label = sev.get("score", "informational")
    else:
        label = sev
    try:
        return SEVERITY_ORDER.index(label)
    except ValueError:
        return len(SEVERITY_ORDER)


def _first_anchor(record):
    """Return the first source anchor as `path:line` for the record."""
    trace = record.get("trace") or []
    evidence = record.get("evidence") or []
    for entry in trace + evidence:
        if isinstance(entry, dict) and entry.get("file"):
            return "%s:%s" % (entry["file"], entry.get("line", "?"))
    return "-"


def _confirm_line(record):
    severity = record.get("severity") or {}
    overall = severity.get("overall_severity")
    if isinstance(overall, dict):
        sev_label = overall.get("score", "?")
        sev_reason = overall.get("reason", "")
    else:
        sev_label = overall or "?"
        sev_reason = ""
    confidence = (record.get("confidence") or {}).get("score", "?")
    return (
        "| `%s` | **%s** | %s | %s | %s | %s |"
        % (
            record.get("fingerprint", "?"),
            sev_label,
            confidence,
            _first_anchor(record),
            record.get("title", "").replace("|", "\\|"),
            sev_reason.replace("|", "\\|"),
        )
    )


def render(findings):
    if isinstance(findings, dict):
        records = findings.get("findings", [])
    elif isinstance(findings, list):
        records = findings
    else:
        records = []

    confirmed = sorted(
        [r for r in records if r.get("verdict") == "confirmed"],
        key=_severity_key,
    )
    validation = [r for r in records if r.get("verdict") == "needs_validation"]
    rejected = [r for r in records if r.get("verdict") == "rejected"]

    lines = ["# Findings Summary", ""]
    lines.append("| Total | Confirmed | Needs validation | Rejected |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("| %d | %d | %d | %d |" % (len(records), len(confirmed), len(validation), len(rejected)))
    lines.append("")

    lines.append("## Confirmed findings (by severity)")
    lines.append("")
    if not confirmed:
        lines.append("_None._")
    else:
        lines.append("| Fingerprint | Severity | Confidence | Anchor | Title | Reason |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for record in confirmed:
            lines.append(_confirm_line(record))
    lines.append("")

    lines.append("## Needs validation")
    lines.append("")
    if not validation:
        lines.append("_None._")
    else:
        for record in validation:
            blockers = "; ".join(record.get("blockers") or ["unspecified blocker"])
            lines.append("- `%s` **%s** -- %s" % (record.get("fingerprint", "?"), record.get("title", ""), blockers))
    lines.append("")

    lines.append("## Rejected candidates")
    lines.append("")
    if not rejected:
        lines.append("_None._")
    else:
        for record in rejected:
            lines.append("- `%s` **%s** -- %s" % (record.get("fingerprint", "?"), record.get("title", ""), record.get("reason", "")))
    lines.append("")

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render findings.json as Markdown.")
    parser.add_argument("findings", help="path to findings.json")
    parser.add_argument("-o", "--output", help="write report to this file instead of stdout")
    args = parser.parse_args(argv)

    try:
        with open(args.findings, "r", encoding="utf-8") as handle:
            findings = json.load(handle)
    except Exception as exc:
        print("error: cannot read %s: %s" % (args.findings, exc), file=sys.stderr)
        return 2

    report = render(findings)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(report)
        print("written: %s" % args.output)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
