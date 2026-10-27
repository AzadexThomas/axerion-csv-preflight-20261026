RETIRED October 27, 2026: CSV offer canceled; no service requests accepted. Hosted site removed. Source retained for reference only.

CSV browser preflight — original Axerion, AI-assisted prototype

Open index.html in a modern browser. No build, dependencies, packages, backend,
network APIs, upload, cookies, storage, analytics or service worker. Deploy these
static files only. _headers is Cloudflare Pages header configuration; verify the
headers after deployment. Opening a file locally does not apply _headers.

Select one UTF-8 comma CSV (optional BOM), or use the built-in synthetic example.
Limits: 2 MiB, 10,000 data records excluding header, 100 columns per record.
Strict double quotes, escaped doubled quotes, CR/LF/CRLF and quoted newlines are
supported. Bare/unclosed quotes and text after closing quotes are rejected.
Empty physical lines count as zero-cell records; trailing newline adds no record.
Header comparison uses trim plus JavaScript lowercase, not Python full casefold.
There is no required-column check in this browser edition.

Reports and JSON export include only counts, fixed labels, and positions. They
omit the chosen filename, header names and cell values. Record numbers include
the header. No CSV rewrite or automatic transformations. Reset invalidates any
pending file read, clears the file control, report and displayed data; downloaded
reports remain on the device. Browser/device memory disposal is browser-managed.

Generic structural check only; no correctness, import, privacy or security
guarantee. AI-generated code may have defects. Use synthetic/non-sensitive inputs.
The paid offer, contact CTA and scheduled offer timer have been removed.

Manual QA:
1. Open index.html; demo reports 4 data records, 4 header columns, repeated header,
   repeated record, whitespace, negative-value formula warning and uneven record.
2. Choose synthetic-example.csv; same structural results. Export JSON and verify
   it contains no item names, header names, cell values or original filename.
3. Try quotes with commas, doubled quotes and multiline fields; valid records
   parse. Reject a bare quote, unclosed quote, or text after a closing quote.
4. Test invalid UTF-8, NUL, >2 MiB, >100 columns, >10,000 data records; visible
   error, no result/export. Try empty file, blank line and final newline.
5. Reset after selecting and during pending read; data/results stay cleared.
6. Keyboard tab through controls, test mobile width, inspect live status/errors.
7. Browser network tools show no processing requests. Inspect deployed response
   CSP, nosniff and Referrer-Policy. Local files do not apply _headers.
8. Retirement check: no paid CTA, mailto or offer timer remains.

MIT License
Copyright (c) 2026 Axerion LLC
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
