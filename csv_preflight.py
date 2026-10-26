#!/usr/bin/env python3
"""Bounded, local, read-only structural checks for UTF-8 comma-separated CSV."""
import argparse
import csv
import html
import io
import json
from pathlib import Path
import sys

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 10000  # Data records, excluding the header.
MAX_COLUMNS = 100
MAX_EXAMPLES = 10
DISCLAIMER = (
    "Generic structural check only. No business accuracy, Shopify compatibility, "
    "security scan, or import guarantee. No data is inferred or rewritten. "
    "Formula-prefix checks are conservative and may flag negative numbers."
)


class InputError(Exception):
    pass


def normalize(value):
    return value.strip().casefold()


def validate_quotes(text):
    """Reject bare quotes and trailing characters after a quoted field."""
    state = "start"
    for char in text:
        if state == "quoted":
            if char == '"':
                state = "after_quote"
        elif state == "after_quote":
            if char == '"':
                state = "quoted"
            elif char == ',':
                state = "start"
            elif char in '\r\n':
                state = "start"
            else:
                raise InputError("Malformed CSV quoting.")
        elif char == '"':
            if state != "start":
                raise InputError("Malformed CSV quoting.")
            state = "quoted"
        elif char == ',' or char in '\r\n':
            state = "start"
        else:
            state = "unquoted"
    if state == "quoted":
        raise InputError("Malformed CSV quoting.")


def inspect_csv(path, required_columns=()):
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        raise InputError("Input could not be read.") from None
    if len(raw) > MAX_BYTES:
        raise InputError("Input exceeds the 2 MiB byte limit.")
    try:
        text = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        raise InputError("Input must use UTF-8 (optional UTF-8 BOM).") from None
    if '\x00' in text:
        raise InputError("NUL bytes are unsupported; input must be UTF-8 CSV text.")
    validate_quotes(text)
    findings = {}

    def finding(kind, **position):
        item = findings.setdefault(kind, {"count": 0, "examples": []})
        item["count"] += 1
        if len(item["examples"]) < MAX_EXAMPLES:
            item["examples"].append(position)

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    header = None
    seen = {}
    count = 0
    # A field cannot be larger than the entire bounded input.
    old_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_BYTES)
    try:
        for record_number, row in enumerate(reader, 1):
            if len(row) > MAX_COLUMNS:
                raise InputError("A record exceeds the 100-column limit.")
            if header is None:
                header = row
                normalized = [normalize(value) for value in row]
                previous = {}
                for column, value in enumerate(normalized, 1):
                    if not value:
                        finding("empty_headers", record=1, column=column)
                    if value in previous:
                        finding("duplicate_headers", record=1, column=column,
                                first_column=previous[value])
                    else:
                        previous[value] = column
                for index, required in enumerate(required_columns, 1):
                    if normalize(required) not in normalized:
                        finding("missing_required_columns", required_column_index=index)
            else:
                count += 1
                if count > MAX_ROWS:
                    raise InputError("Input exceeds the 10000-data-record limit.")
                if len(row) != len(header):
                    finding("ragged_records", record=record_number,
                            expected_columns=len(header), actual_columns=len(row))
                key = tuple(row)
                if key in seen:
                    finding("duplicate_records", record=record_number,
                            first_record=seen[key])
                else:
                    seen[key] = record_number
            for column, value in enumerate(row, 1):
                if value != value.strip():
                    finding("whitespace_cells", record=record_number, column=column)
                if value.lstrip().startswith(('=', '+', '-', '@')):
                    finding("potential_formula_cells", record=record_number, column=column)
    except csv.Error:
        raise InputError("Malformed CSV structure or quoting.") from None
    finally:
        csv.field_size_limit(old_limit)
    if header is None:
        finding("missing_header")
        for index, _ in enumerate(required_columns, 1):
            finding("missing_required_columns", required_column_index=index)
    elif not header:
        finding("missing_header", record=1)
    return {
        "schema_version": 1,
        "status": "findings" if findings else "ok",
        "bytes_read": len(raw), "data_records": count,
        "header_columns": len(header) if header is not None else 0,
        "limits": {"bytes": MAX_BYTES, "data_records": MAX_ROWS,
                   "columns": MAX_COLUMNS, "examples_per_finding": MAX_EXAMPLES},
        "finding_count": sum(item["count"] for item in findings.values()),
        "findings": findings,
        "position_convention": "1-based CSV records including header; multiline fields count as one record; columns are 1-based. Required-column indices follow CLI order.",
        "notice": DISCLAIMER,
    }


def render_html(summary):
    safe = html.escape(json.dumps(summary, indent=2, ensure_ascii=True))
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>CSV structural preflight</title><style>body{font:16px system-ui;'
            'max-width:900px;margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap;'
            'overflow-wrap:anywhere;background:#f3f4f6;padding:1rem}</style>'
            '<h1>CSV structural preflight</h1><p>Values and input paths are omitted. '
            'Examples contain positions only and are limited per finding.</p><pre>'
            + safe + '</pre></html>\n')


def same_location(left, right):
    if left.resolve() == right.resolve():
        return True
    try:
        return left.samefile(right)
    except OSError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=DISCLAIMER)
    parser.add_argument("input", type=Path)
    parser.add_argument("--required-column", action="append", default=[], metavar="NAME")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--html-output", type=Path)
    args = parser.parse_args(argv)
    try:
        if any(not normalize(name) for name in args.required_column):
            raise InputError("Required-column names must not be empty or whitespace.")
        outputs = [p for p in (args.json_output, args.html_output) if p is not None]
        for output in outputs:
            if same_location(args.input, output):
                raise InputError("An output must not refer to the input file.")
            if output.exists() or output.is_symlink():
                raise InputError("Output already exists; choose a new output path.")
        if len(outputs) == 2 and same_location(*outputs):
            raise InputError("JSON and HTML outputs must use distinct paths.")
        summary = inspect_csv(args.input, args.required_column)
        payload = json.dumps(summary, indent=2, ensure_ascii=True) + '\n'
        for output, content in ((args.json_output, payload),
                                (args.html_output, render_html(summary))):
            if output is not None:
                with output.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
        sys.stdout.write(payload)
        return 1 if summary["finding_count"] else 0
    except (InputError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, InputError) else "Input or output operation failed."
        sys.stderr.write(json.dumps({"status": "error", "error": message}) + '\n')
        return 2


if __name__ == "__main__":
    sys.exit(main())
