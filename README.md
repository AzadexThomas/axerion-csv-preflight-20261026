# RETIRED — October 27, 2026

The CSV revenue offer has been canceled. No CSV services or new requests are accepted. The hosted website has been removed. This repository preserves original utility code, license, tests and historical source only; it is not an active business offer.

# CSV structural preflight

An original AI-assisted Axerion LLC utility for inspecting a CSV **on your own
computer**. No file upload, API key, subscription, or package installation.
The code is available under the MIT license. AI-assisted authorship is disclosed;
no customer endorsement, human review by Edward Thomas, or exclusive rights are
claimed.

Python 3 standard-library CLI for a bounded, local structural check. No installs,
network access, telemetry, API calls, or CSV execution. The original input is opened
read-only. No values are inferred, repaired, normalized in the input, or rewritten.

```console
python csv_preflight.py example.csv
python csv_preflight.py example.csv --required-column id --required-column name --json-output summary.json --html-output report.html
```

JSON is printed to stdout. Optional JSON and self-contained HTML reports contain
counts and up to 10 positional examples per finding, with no raw cell values,
required-column names, input filename, or private input path. Output paths must be
new, distinct files and must not alias the input. Existing reports are not replaced.
On an input or output error no summary is emitted; a short JSON error goes to
stderr. Argument-parsing errors use Python argparse's standard usage/error text
on stderr. If writing a later report fails, an earlier report may already have
been created.

Exit codes: **0** checked with no findings; **1** checked with findings; **2** input,
usage, or output error. A limit error means the file was not fully checked.

Accepted input is comma-separated UTF-8, with or without a UTF-8 BOM, using double
quotes, doubled embedded quotes, and quoted multiline fields. Malformed quotes,
unsupported encoding, and NUL characters are rejected. Limits: **2 MiB** of input,
**10,000 data records** (excluding the header), and **100 columns per record**.
The first CSV record is the header. Empty physical lines are parsed as empty
records; a final newline does not add a record. Record positions are 1-based CSV
record numbers, including the header; a quoted multiline field remains one record.

Checks: empty headers, duplicate headers after trim plus Unicode casefold,
missing requested columns using the same comparison, ragged records, exact duplicate
data records (header excluded), leading/trailing Unicode whitespace in any cell,
and potential formula prefixes `=`, `+`, `-`, `@` after leading whitespace.
Formula flags are conservative and may include negative numbers. They are not a
complete security analysis. Missing required columns are identified by the 1-based
order of `--required-column` arguments to avoid disclosing their names.

This is a generic structural check, not a Shopify validator, business-accuracy
check, security scanner, or import guarantee. A clean result cannot establish data
correctness, compatibility, safety, or fitness for any downstream system. Reports
still reveal dimensions and issue positions; handle them according to your needs.

The included example is synthetic.

