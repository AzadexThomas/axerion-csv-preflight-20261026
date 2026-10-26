'use strict';
(() => {
  const MAX_BYTES = 2 * 1024 * 1024, MAX_ROWS = 10000, MAX_COLUMNS = 100;
  const $ = id => document.getElementById(id);
  const notice = 'Generic structural check only. No correctness, import compatibility or security guarantee. No data is rewritten. Formula flags are conservative and may include negative numbers.';
  const demo = 'item, item,quantity,notes\nWidget,blue,4,"Synthetic, example"\nWidget,blue,4,"Synthetic, example"\nGadget, green,-2,"Two\nlines"\nSample,red,3\n';
  let report = null, generation = 0;

  // Strict comma CSV state machine: quotes may begin only at field start;
  // after closing a quote only a quote, delimiter, newline or EOF is accepted.
  function parse(text) {
    const rows = []; let row = [], field = '', state = 'start', touched = false;
    function cell() { row.push(field); field = ''; if (row.length > MAX_COLUMNS) throw Error('A record exceeds the 100-column limit.'); }
    function record() { cell(); rows.push(row); row = []; touched = false; if (rows.length > MAX_ROWS + 1) throw Error('Input exceeds the 10,000-data-record limit.'); }
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (state === 'quoted') { if (c === '"') state = 'after'; else field += c; touched = true; continue; }
      if (state === 'after' && c === '"') { field += '"'; state = 'quoted'; continue; }
      if (c === ',') { cell(); state = 'start'; touched = true; continue; }
      if (c === '\r' || c === '\n') {
        // Empty physical records have zero cells, like the reference CLI.
        if (!touched && !row.length && field === '' && state === 'start') { rows.push([]); if (rows.length > MAX_ROWS + 1) throw Error('Input exceeds the 10,000-data-record limit.'); }
        else record();
        if (c === '\r' && text[i + 1] === '\n') i++;
        state = 'start'; touched = false; continue;
      }
      if (state === 'after') throw Error('Malformed CSV quoting.');
      if (c === '"') { if (state !== 'start') throw Error('Malformed CSV quoting.'); state = 'quoted'; touched = true; }
      else { field += c; state = 'plain'; touched = true; }
    }
    if (state === 'quoted') throw Error('Malformed CSV quoting.');
    if (touched || row.length || field.length) record();
    return rows;
  }
  function inspect(text, bytes) {
    if (bytes > MAX_BYTES) throw Error('Input exceeds the 2 MiB byte limit.');
    if (text.includes('\0')) throw Error('NUL characters are unsupported. Use UTF-8 CSV text.');
    const rows = parse(text), findings = {}, seen = new Map();
    const add = (kind, position) => { const item = findings[kind] || (findings[kind] = {count:0, examples:[]}); item.count++; if (item.examples.length < 10) item.examples.push(position); };
    const header = rows[0] || [], previous = new Map();
    if (!header.length) add('missing_header', {});
    header.forEach((value, i) => { const key = value.trim().toLowerCase(); if (!key) add('empty_headers', {record:1,column:i+1}); if (previous.has(key)) add('duplicate_headers', {record:1,column:i+1,first_column:previous.get(key)}); else previous.set(key,i+1); });
    rows.forEach((row, i) => {
      if (i) { if (row.length !== header.length) add('ragged_records',{record:i+1,expected_columns:header.length,actual_columns:row.length}); const key = JSON.stringify(row); if (seen.has(key)) add('duplicate_records',{record:i+1,first_record:seen.get(key)}); else seen.set(key,i+1); }
      row.forEach((value, j) => { if (value !== value.trim()) add('whitespace_cells',{record:i+1,column:j+1}); if (/^[=+\-@]/u.test(value.trimStart())) add('potential_formula_cells',{record:i+1,column:j+1}); });
    });
    return {schema_version:1,status:Object.keys(findings).length?'findings':'ok',bytes_read:bytes,data_records:Math.max(0,rows.length-1),header_columns:header.length,finding_count:Object.values(findings).reduce((n,v)=>n+v.count,0),findings,limits:{bytes:MAX_BYTES,data_records:MAX_ROWS,columns:MAX_COLUMNS,examples_per_finding:10},position_convention:'1-based CSV records including header; multiline fields count as one record; columns are 1-based.',header_comparison:'Trim plus JavaScript Unicode lowercase; not full Unicode casefold.',notice};
  }
  if (typeof module !== 'undefined' && module.exports) { module.exports = {parse, inspect}; return; }
  function clear() { generation++; report = null; $('csv-file').value=''; $('results').hidden=true; $('findings').replaceChildren(); $('summary').textContent=''; $('error').hidden=true; $('error').textContent=''; $('status').textContent='Ready. No CSV selected.'; }
  function show(result) {
    report = result; $('results').hidden=false; $('error').hidden=true; $('findings').replaceChildren();
    $('summary').textContent=`${result.data_records.toLocaleString()} data records · ${result.header_columns} header columns · ${result.finding_count} findings`;
    const labels={missing_header:'Missing header',empty_headers:'Empty headers',duplicate_headers:'Repeated headers',ragged_records:'Uneven data records',duplicate_records:'Repeated data records',whitespace_cells:'Cells with surrounding whitespace',potential_formula_cells:'Potential spreadsheet formula prefixes'};
    Object.entries(result.findings).forEach(([kind,item])=>{const section=document.createElement('section'), title=document.createElement('h4'); title.textContent=`${labels[kind]}: ${item.count}`; section.append(title); item.examples.forEach(position=>{const p=document.createElement('p'); p.textContent=Object.entries(position).map(([k,v])=>`${k.replaceAll('_',' ')} ${v}`).join(' · ')||'No header record found'; section.append(p);}); $('findings').append(section);});
    $('status').textContent=result.finding_count?'Check complete. Review findings and limits below.':'Check complete. No findings in these structural checks. Review the limits below.';
  }
  function fail() { report=null; $('results').hidden=true; $('findings').replaceChildren(); }
  $('csv-file').addEventListener('change', async () => {
    const file=$('csv-file').files[0]; clear(); if (!file) return; const token=generation;
    $('status').textContent='Checking locally…';
    try { if(file.size>MAX_BYTES) throw Error('Input exceeds the 2 MiB byte limit.'); const raw=await file.arrayBuffer(); if(token!==generation)return; let text; try{text=new TextDecoder('utf-8',{fatal:true}).decode(raw);}catch{throw Error('Input must use UTF-8 with an optional UTF-8 BOM.');} show(inspect(text,raw.byteLength)); }
    catch(error) { if(token!==generation)return; fail(); $('error').textContent=error.message; $('error').hidden=false; $('status').textContent='Not fully checked. Correct the input or choose another file.'; }
  });
  $('demo').addEventListener('click',()=>{clear();show(inspect(demo,new TextEncoder().encode(demo).length));});
  $('reset').addEventListener('click',clear);
  $('download').addEventListener('click',()=>{if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+'\n'],{type:'application/json'})); const a=document.createElement('a');a.href=url;a.download='csv-structural-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  function updateOffer() { const closed=Date.now()>=Date.parse('2026-11-08T18:00:00Z'); $('contact').hidden=closed; $('offer-state').textContent=closed?'Closed to new scope requests as of November 8, 2026 at 18:00 UTC. Existing agreed work follows its written terms.':'New scope requests close November 8, 2026 at 18:00 UTC.'; }
  $('contact').addEventListener('click',event=>{if(Date.now()>=Date.parse('2026-11-08T18:00:00Z')){event.preventDefault();updateOffer();}});
  updateOffer();setInterval(updateOffer,30000);document.addEventListener('visibilitychange',updateOffer);
})();
