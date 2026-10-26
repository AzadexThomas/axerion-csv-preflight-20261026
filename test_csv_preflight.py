"""Independent CLI acceptance tests, using synthetic data and stdlib only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name("csv_preflight.py")


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="csv-preflight-qa-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "private-source.csv"

    def run_cli(self, content, *args, code=None):
        self.source.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        proc = subprocess.run([sys.executable, str(TOOL), str(self.source), *map(str, args)],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before,
                         "The source CSV must never change")
        if code is not None:
            self.assertEqual(proc.returncode, code, proc.stderr or proc.stdout)
        return proc

    def report(self, content, *args, code=0):
        proc = self.run_cli(content, *args, code=code)
        self.assertEqual(proc.stderr, "")
        result = json.loads(proc.stdout)
        self.assertIn(result["status"], ("ok", "findings"))
        return result

    def error(self, content, *args):
        proc = self.run_cli(content, *args, code=2)
        self.assertEqual(proc.stdout, "")
        error = json.loads(proc.stderr)
        self.assertEqual(error["status"], "error")
        self.assertNotIn(str(self.source), proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        return error

    def test_clean_bom_and_non_ascii(self):
        r = self.report(b'\xef\xbb\xbfname,city\r\nRen\xc3\xa9,Montr\xc3\xa9al\r\n')
        self.assertEqual((r["data_records"], r["header_columns"], r["finding_count"]), (1, 2, 0))

    def test_quoted_commas_multiline_and_escaped_quotes(self):
        r = self.report('name,note\r\nAda,"one, two\r\nthree ""quoted"" words"\r\nBob,plain\r\n')
        self.assertEqual(r["data_records"], 2)
        self.assertEqual(r["findings"], {})

    def test_empty_and_casefold_duplicate_headers(self):
        r = self.report('Name, NAME , ,Straße,STRASSE\na,b,c,d,e\n', code=1)
        self.assertEqual(r["findings"]["empty_headers"]["count"], 1)
        self.assertEqual(r["findings"]["duplicate_headers"]["count"], 2)

    def test_ragged_and_duplicate_records(self):
        r = self.report('a,b\nx,y\nx\nx,y\nx,y,z\n', code=1)
        self.assertEqual(r["findings"]["ragged_records"]["count"], 2)
        self.assertEqual(r["findings"]["duplicate_records"]["count"], 1)
        self.assertEqual(r["findings"]["duplicate_records"]["examples"][0],
                         {"record": 4, "first_record": 2})

    def test_multiline_positions_count_csv_records(self):
        r = self.report('a,b\n"multi\nline",z\nshort\n', code=1)
        self.assertEqual(r["findings"]["ragged_records"]["examples"][0]["record"], 3)

    def test_whitespace_and_conservative_formula_prefixes(self):
        r = self.report('a,b,c,d,e,f,g\n =1,+2,-3,@x,plain,x=2,\t+4\n', code=1)
        self.assertEqual(r["findings"]["potential_formula_cells"]["count"], 5)
        self.assertEqual(r["findings"]["whitespace_cells"]["count"], 2)

    def test_required_columns_optional_and_normalized(self):
        self.report('Email, Name\nx,y\n', '--required-column', ' EMAIL ', code=1)
        r = self.report('Email,Name\nx,y\n', '--required-column', ' email ')
        self.assertNotIn("missing_required_columns", r["findings"])
        r = self.report('Email,Name\nx,y\n', '--required-column', 'secret_required_column', code=1)
        self.assertEqual(r["findings"]["missing_required_columns"]["count"], 1)
        self.assertNotIn('secret_required_column', json.dumps(r))

    def test_empty_required_column_rejected(self):
        self.error('a\nx\n', '--required-column', '   ')

    def test_empty_file_has_missing_header(self):
        r = self.report('', code=1)
        self.assertEqual(r["findings"]["missing_header"]["count"], 1)
        self.assertEqual(r["data_records"], 0)

    def test_malformed_quotes(self):
        for text in ('a\n"unclosed\n', 'a\nx"y\n', 'a\n"x"trailer\n'):
            with self.subTest(text=text):
                self.error(text)

    def test_invalid_utf8_and_nul(self):
        for data in (b'a\n\xff\n', b'a\nx\x00y\n'):
            with self.subTest(data=data):
                self.error(data)

    def test_byte_bound(self):
        self.error(b'a\n' + b'x' * (2 * 1024 * 1024))

    def test_row_and_column_bounds(self):
        self.error('a\n' + 'x\n' * 10001)
        self.error(','.join('c' + str(i) for i in range(101)) + '\n')

    def test_exact_bounds_accepted(self):
        r = self.report('a\n' + 'x' * (2 * 1024 * 1024 - 2))
        self.assertEqual(r['bytes_read'], 2 * 1024 * 1024)
        r = self.report('a\n' + ''.join(str(i) + '\n' for i in range(10000)))
        self.assertEqual(r['data_records'], 10000)
        r = self.report(','.join('c' + str(i) for i in range(100)) + '\n')
        self.assertEqual(r['header_columns'], 100)

    def test_duplicate_rows_are_exact_cell_matches(self):
        r = self.report('a\nx\nX\n x\n', code=1)
        self.assertNotIn('duplicate_records', r['findings'])

    def test_examples_bounded_without_losing_count(self):
        r = self.report('a\n' + ' x\n' * 30, code=1)
        item = r["findings"]["whitespace_cells"]
        self.assertEqual(item["count"], 30)
        self.assertLessEqual(len(item["examples"]), 10)

    def test_private_and_adversarial_cells_omitted(self):
        output_json, output_html = self.root / 'report.json', self.root / 'report.html'
        marker = self.root / 'must-not-be-created'
        private = 'PRIVATE_CUSTOMER_93F3'
        payload = '<svg onload="alert(1)"><script>PRIVATE_SCRIPT_83C2</script></svg>'
        # Quote the cell as CSV, so embedded quotes are data.
        data = 'private_header_74B2,other\n' + private + ',"' + payload.replace('"', '""') + '"\n'
        r = self.report(data, '--json-output', output_json, '--html-output', output_html)
        self.assertEqual(json.loads(output_json.read_text(encoding='utf-8')), r)
        for text in (output_json.read_text(encoding='utf-8'), output_html.read_text(encoding='utf-8')):
            for secret in (private, 'private_header_74B2', 'PRIVATE_SCRIPT_83C2', str(self.source)):
                self.assertNotIn(secret, text)
            self.assertNotIn('<svg', text)
            self.assertNotIn('<script', text)
        self.assertFalse(marker.exists())

    def test_code_and_binary_payloads_do_not_execute(self):
        marker = self.root / 'must-not-be-created'
        expression = "__import__('pathlib').Path(" + repr(str(marker)) + ").write_text('executed')"
        # A valid CSV code expression is parsed as an ordinary string.
        quoted = '"' + expression.replace('"', '""') + '"'
        self.report('value\n' + quoted + '\n')
        self.assertFalse(marker.exists())
        # Representative binary signatures fail UTF-8/NUL checks, without execution.
        for binary in (b'\x89PNG\r\n\x1a\n', b'PK\x03\x04\x00archive'):
            with self.subTest(binary=binary):
                self.error(binary)

    def test_no_overwrite_source_direct_or_normalized(self):
        for target in (self.source, self.root / '.' / self.source.name):
            with self.subTest(target=target):
                self.error('a\nx\n', '--json-output', target)

    def test_no_overwrite_source_hardlink(self):
        self.source.write_text('a\nx\n', encoding='utf-8')
        alias = self.root / 'hardlink.csv'
        try:
            os.link(self.source, alias)
        except OSError as error:
            self.skipTest('Hardlinks unavailable: ' + str(error))
        self.error('a\nx\n', '--html-output', alias)

    def test_no_overwrite_source_symlink(self):
        self.source.write_text('a\nx\n', encoding='utf-8')
        alias = self.root / 'symlink.csv'
        try:
            alias.symlink_to(self.source)
        except OSError as error:
            self.skipTest('Symlinks unavailable: ' + str(error))
        self.error('a\nx\n', '--json-output', alias)

    def test_existing_output_and_duplicate_outputs_rejected(self):
        target = self.root / 'existing.json'
        target.write_text('PRESERVE', encoding='utf-8')
        self.error('a\nx\n', '--json-output', target)
        self.assertEqual(target.read_text(encoding='utf-8'), 'PRESERVE')
        new = self.root / 'same-output'
        self.error('a\nx\n', '--json-output', new, '--html-output', new)
        self.assertFalse(new.exists())

    def test_invalid_input_creates_no_report(self):
        target = self.root / 'never-created.json'
        self.error(b'a\n\xff', '--json-output', target)
        self.assertFalse(target.exists())

    def test_missing_input_and_output_parent_errors_sanitized(self):
        missing = self.root / 'MISSING_PRIVATE_PATH.csv'
        proc = subprocess.run([sys.executable, str(TOOL), str(missing)], capture_output=True,
                              text=True, timeout=15)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stderr)["status"], "error")
        self.assertNotIn(str(missing), proc.stderr)
        self.error('a\nx\n', '--json-output', self.root / 'missing' / 'report.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
