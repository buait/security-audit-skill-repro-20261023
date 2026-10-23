#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_findings.py -- Python zero-dependency validator for findings.json.

A companion to validate-findings.cjs. This validator speaks the same
report-schema.json contract so teams that do not run Node can still gate
their Phase 4 / Phase 5 output on CI or in plain scripts.

It implements a small JSON-Schema keyword subset that covers everything
report-schema.json actually uses (type, required, properties, enum,
pattern, length/minItems constraints, items, oneOf, const, and the custom
visibleContent marker). Unknown keywords are ignored so the schema can
grow without breaking older validators.

Usage:
    python validate_findings.py <path-to-findings.json>
    python validate_findings.py <path-to-findings.json> --schema <path-to-report-schema.json>

Exit code 0 means the document validated; 1 means problems were found;
2 means the validator itself could not run (missing file, bad JSON, ...).
"""

import json
import re
import sys

# Custom keyword: a string field with visibleContent: true must contain at
# least one non-whitespace character. report-schema.json uses it to keep
# prose fields honest.
VISIBLE_RE = re.compile(r"\S")

SEVERITY_ORDER = ["critical", "high", "medium", "low", "informational"]


def _err(path, message):
    return {"path": path or "$", "message": str(message)}


def _validate_value(schema, value, path, errors, root):
    if schema.get("$comment"):
        pass  # documentation only, ignore

    if "const" in schema and value != schema["const"]:
        errors.append(_err(path, "expected const %r, got %r" % (schema["const"], value)))

    if "enum" in schema and value not in schema["enum"]:
        errors.append(_err(path, "value %r not in enum %r" % (value, schema["enum"])))

    expected_type = schema.get("type")
    if expected_type:
        ok = False
        if expected_type == "string":
            ok = isinstance(value, str)
        elif expected_type == "integer":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == "boolean":
            ok = isinstance(value, bool)
        elif expected_type == "array":
            ok = isinstance(value, list)
        elif expected_type == "object":
            ok = isinstance(value, dict)
        elif expected_type == "null":
            ok = value is None
        if not ok:
            errors.append(_err(path, "expected type %s, got %s" % (expected_type, type(value).__name__)))
            return

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(_err(path, "shorter than minLength %d" % schema["minLength"]))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(_err(path, "longer than maxLength %d" % schema["maxLength"]))
        if schema.get("visibleContent") and not VISIBLE_RE.search(value):
            errors.append(_err(path, "field must contain visible (non-whitespace) content"))
        pattern = schema.get("pattern")
        if pattern:
            try:
                if not re.search(pattern, value):
                    errors.append(_err(path, "does not match pattern %s" % pattern))
            except re.error as exc:
                errors.append(_err(path, "invalid schema pattern %s: %s" % (pattern, exc)))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(_err(path, "fewer items than minItems %d" % schema["minItems"]))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(_err(path, "more items than maxItems %d" % schema["maxItems"]))
        items = schema.get("items")
        if isinstance(items, dict):
            for idx, item in enumerate(value):
                _validate_value(items, item, "%s[%d]" % (path, idx), errors, root)

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for name, sub in props.items():
            if name in value:
                _validate_value(sub, value[name], "%s.%s" % (path, name), errors, root)
        for name in schema.get("required", []):
            if name not in value:
                errors.append(_err(path, "missing required property %r" % name))
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in props:
                    errors.append(_err(path, "additional property %r not allowed" % name))

    one_of = schema.get("oneOf")
    if one_of:
        best = None
        for subschema in one_of:
            branch_errors = []
            _validate_value(subschema, value, path, branch_errors, root)
            if not branch_errors:
                return
            # track the most plausible failing branch so the user sees
            # actionable errors instead of a silent "no branch matched"
            if best is None or len(branch_errors) < len(best):
                best = branch_errors
        errors.extend(best or [])


def _validate_document(instance, schema, root_path):
    errors = []
    _validate_value(schema, instance, root_path, errors, None)
    return errors


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv):
    if len(argv) < 2:
        print("usage: python validate_findings.py <findings.json> [--schema report-schema.json]")
        return 2

    findings_path = argv[1]
    schema_path = None
    if "--schema" in argv:
        try:
            schema_path = argv[argv.index("--schema") + 1]
        except IndexError:
            print("error: --schema requires a path")
            return 2

    try:
        findings = load_json(findings_path)
    except Exception as exc:
        print("error: cannot read %s: %s" % (findings_path, exc))
        return 2

    if schema_path is None:
        import pathlib
        schema_path = str(pathlib.Path(findings_path).parent / "report-schema.json")

    try:
        schema = load_json(schema_path)
    except Exception as exc:
        print("error: cannot read schema %s: %s" % (schema_path, exc))
        return 2

    errors = _validate_document(findings, schema, "$")
    if not errors:
        records = findings if isinstance(findings, list) else findings.get("findings", [])
        n = len(records) if isinstance(records, list) else 0
        print("OK: %d record(s) validated against %s" % (n, schema_path))
        return 0

    print("INVALID: %d problem(s)" % len(errors))
    for err in errors[:200]:
        print("  %s: %s" % (err["path"], err["message"]))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
