/* SBRetire results viewer. Reads window.SBRETIRE_RUNS (set by runs/runs.js). No network access. */
(function () {
  'use strict';

  var DATA = window.SBRETIRE_RUNS;
  var DASH = '\u2014', MINUS = '\u2212', NBSP = '\u00a0';
  var KNOWN_MAJOR = '1';
  var NULL_YEAR = 'No simulated future still running this year';
  var state = { a: null, b: null, allYears: false, tableRun: 'a' };

  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }

  /* ---------------- number rules (handoff §5) ---------------- */
  var F = {
    gbp: function (x) { if (!isNum(x)) return DASH; return (x < 0 ? MINUS : '') + '£' + Math.floor(Math.abs(x) + 1e-9).toLocaleString('en-GB'); },
    gbpShort: function (x) {
      var a = Math.abs(x), s;
      if (a >= 1e6) s = '£' + trim(a / 1e6) + 'm'; else if (a >= 1e3) s = '£' + trim(a / 1e3) + 'k'; else s = '£' + Math.round(a);
      return (x < 0 ? MINUS : '') + s;
    },
    rate: function (x) { if (!isNum(x)) return DASH; return (Math.floor(x * 10000 + 1e-7) / 100).toFixed(2) + '%'; },
    se: function (x) { if (!isNum(x)) return DASH; return '±' + (x * 100).toFixed(3) + '%'; },
    retVal: function (x) { return Math.ceil(x * 10000 - 1e-7) / 100; },
    ret: function (x) {
      if (!isNum(x)) return DASH;
      var v = F.retVal(x); return (v > 0 ? '+' : v < 0 ? MINUS : '') + Math.abs(v).toFixed(2) + '%';
    },
    assumed: function (x) { if (!isNum(x)) return DASH; var v = Math.round(x * 10000) / 100; return (v < 0 ? MINUS : '') + Math.abs(v).toFixed(2) + '%'; },
    target: function (p) { return +(p * 100).toFixed(4) + '%'; },
    int: function (n) { return isNum(n) ? Math.round(n).toLocaleString('en-GB') : DASH; },
    date: function (iso) {
      if (!iso) return DASH;
      var d = new Date(iso.length === 10 ? iso + 'T00:00:00Z' : iso);
      return isNaN(d) ? esc(iso) : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
    },
    dateTime: function (iso) {
      var d = new Date(iso); if (isNaN(d)) return esc(iso) || DASH;
      return d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC';
    },
    month: function (ym) {
      if (!ym) return DASH; var p = ym.split('-');
      return new Date(Date.UTC(+p[0], +p[1] - 1, 1)).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    }
  };
  function trim(v) { return v >= 100 ? String(Math.round(v)) : v >= 10 ? String(+v.toFixed(1)) : String(+v.toFixed(2)); }
  function signedPts(v) { return (v > 0 ? '+' : v < 0 ? MINUS : '') + Math.abs(v).toFixed(2); }

  /* ---------------- helpers ---------------- */
  function runs() { return state.b ? [{ k: 'a', r: DATA.runs[state.a] }, { k: 'b', r: DATA.runs[state.b] }] : [{ k: 'a', r: DATA.runs[state.a] }]; }
  function mark(k) { return '<span class="mark mark--' + k + '" aria-hidden="true"></span>'; }
  function runLabel(k, r) { return '<span class="runlabel">' + mark(k) + '<span>' + esc(r.run.name) + '</span></span>'; }
  function targetsOf(r) { return (r.budgets || []).map(function (b) { return b.target_probability; }); }
  function tKey(p) { return p.toFixed(6); }
  function unionTargets(lists) {
    var m = {}; lists.forEach(function (l) { (l || []).forEach(function (row) { m[tKey(row.target_probability)] = row.target_probability; }); });
    return Object.keys(m).map(function (k) { return m[k]; }).sort(function (a, b) { return a - b; });
  }
  function findT(list, p) { return (list || []).filter(function (row) { return tKey(row.target_probability) === tKey(p); })[0] || null; }
  function reserveOn(r) { return !!(r.reserve_summary && r.run.options && r.run.options.end_reserve_months > 0); }
  function col(r, file, key) { var c = r.columns && r.columns[file] && r.columns[file][key]; return c || null; }
  function info(r, file, key, label) {
    var c = col(r, file, key); if (!c) return '';
    return '<button type="button" class="info" data-tip="' + esc(c.meaning) + '" data-tip-unit="' + esc(c.unit) + '" aria-label="' + esc((label || key) + ': ' + c.meaning + ' (' + c.unit + ')') + '">i</button>';
  }
  function th(label, r, file, key, cls) { return '<th scope="col"' + (cls ? ' class="' + cls + '"' : '') + '><span class="th-wrap">' + label + (r ? info(r, file, key, label.replace(/<[^>]+>/g, '')) : '') + '</span></th>'; }
  function convergedCell(row) {
    if (row.converged === false) return '<span class="tag tag--warn" title="The search stopped at its cap or bound before reaching the tolerance">! Not converged</span>';
    return '<span class="muted small">Converged · ' + F.int(row.iterations) + ' steps</span>';
  }
  function compactConverged(row) {
    if (row.converged === false) return '<span class="tag tag--warn" style="margin-top:var(--space-1)" title="The search stopped at its cap or bound before reaching the tolerance">! Not converged</span>';
  }
  function nullCell(note) { return DASH + (note ? '<span class="cell-note">' + esc(note) + '</span>' : ''); }

  /* ---------------- years shown ---------------- */
  function spanEnd(r) {
    var n = r.summary.n_paths || r.run.paths || 1, last = 0;
    r.annual.forEach(function (row, i) { if (row.unresolved_paths / n >= 0.001) last = i; });
    return Math.min(r.annual.length - 1, last + 1);
  }
  function visibleRows(r) { return state.allYears ? r.annual : r.annual.slice(0, spanEnd(r) + 1); }

  /* ---------------- hash state ---------------- */
  function readHash() {
    var p = new URLSearchParams(location.hash.slice(1));
    return { run: p.get('run'), compare: p.get('compare') };
  }
  function writeHash() {
    var p = new URLSearchParams(); p.set('run', state.a); if (state.b) p.set('compare', state.b);
    history.replaceState(null, '', '#' + p.toString());
  }

  /* ---------------- run pickers ---------------- */
  function indexEntries() { return (DATA.index || []).filter(function (e) { return DATA.runs && DATA.runs[e.name]; }); }
  function entryMeta(e) {
    return F.date(e.created_at) + ' · ' + F.gbp(e.monthly_budget_today) + '/mo · ' + F.assumed(e.annual_return) + ' return · ' + F.rate(e.conservative_success_rate) + ' success';
  }
  function buildPickers() {
    var entries = indexEntries();
    var html = pickerHTML('a', 'Run', entries, false);
    if (entries.length > 1) html += pickerHTML('b', 'Compare with', entries, true);
    $('#pickers').innerHTML = html;
    $$('.picker').forEach(wirePicker);
  }
  function pickerHTML(key, label, entries, withNone) {
    var rows = '';
    if (withNone) rows += rowHTML(key, '', 'No comparison', 'Show one run on its own');
    entries.forEach(function (e) { rows += rowHTML(key, e.name, e.name, entryMeta(e)); });
    return '<div class="picker" data-key="' + key + '">' +
      '<span class="picker__label" id="pl-' + key + '">' + (key === 'b' ? mark('b') : mark('a')) + label + '</span>' +
      '<details class="picker__menu"><summary class="picker__button" aria-describedby="pl-' + key + '">' +
      '<span class="picker__current"><span class="picker__current-name"></span><span class="picker__current-meta"></span></span>' +
      '<span class="picker__chev" aria-hidden="true"></span></summary>' +
      '<div class="picker__panel">' + (entries.length > 6 ? '<input type="search" class="picker__filter" placeholder="Filter by name" aria-label="Filter runs by name">' : '') +
      '<div class="picker__list" role="radiogroup" aria-labelledby="pl-' + key + '">' + rows + '</div>' +
      '<p class="picker__empty" hidden>No run matches.</p></div></details></div>';
  }
  function rowHTML(key, value, name, meta) {
    return '<label class="picker__row" data-name="' + esc(value.toLowerCase()) + '"><input type="radio" name="pick-' + key + '" value="' + esc(value) + '">' +
      '<span class="picker__tick" aria-hidden="true"></span><span class="picker__name">' + esc(name) + '</span><span class="picker__meta">' + esc(meta) + '</span></label>';
  }
  function wirePicker(p) {
    var key = p.dataset.key, det = $('details', p), pointer = false;
    p.addEventListener('pointerdown', function () { pointer = true; });
    p.addEventListener('change', function (e) {
      if (e.target.name !== 'pick-' + key) return;
      var v = e.target.value || null;
      if (key === 'a') { state.a = v; if (state.b === v) state.b = null; } else state.b = v;
      writeHash(); syncPickers(); render();
      if (pointer) { det.open = false; $('summary', p).focus(); }
      pointer = false;
    });
    p.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && det.open) { det.open = false; $('summary', p).focus(); }
      if (e.key === 'Enter' && e.target.type === 'radio') { e.preventDefault(); det.open = false; $('summary', p).focus(); }
    });
    det.addEventListener('toggle', function () {
      if (!det.open) return;
      $$('details.picker__menu').forEach(function (d) { if (d !== det) d.open = false; });
      var c = $('input:checked', p) || $('input:not(:disabled)', p); if (c) c.focus();
    });
    var f = $('.picker__filter', p);
    if (f) f.addEventListener('input', function () {
      var q = f.value.trim().toLowerCase(), any = false;
      $$('.picker__row', p).forEach(function (row) { var show = !q || row.dataset.name === '' || row.dataset.name.indexOf(q) >= 0; row.hidden = !show; if (show) any = true; });
      $('.picker__empty', p).hidden = any;
    });
  }
  function syncPickers() {
    $$('.picker').forEach(function (p) {
      var key = p.dataset.key, val = key === 'a' ? state.a : (state.b || '');
      $$('input', p).forEach(function (inp) {
        inp.checked = inp.value === val;
        inp.disabled = key === 'b' && inp.value !== '' && inp.value === state.a;
      });
      var name = $('.picker__current-name', p), meta = $('.picker__current-meta', p);
      if (key === 'b' && !state.b) { name.textContent = 'No comparison'; meta.textContent = 'Pick a second run to see both side by side'; return; }
      var e = indexEntries().filter(function (x) { return x.name === val; })[0];
      name.textContent = val; meta.textContent = e ? entryMeta(e) : '';
    });
  }
  document.addEventListener('click', function (e) {
    $$('details.picker__menu[open]').forEach(function (d) { if (!d.contains(e.target)) d.open = false; });
  });

  /* ---------------- header meta ---------------- */
  function renderMeta() {
    var html = runs().map(function (o) {
      var r = o.r.run, opt = r.options || {};
      var chips = [
        'As of ' + F.date(r.as_of_date),
        'Horizon ' + r.horizon_years + ' years, to ' + F.month(r.last_month),
        F.int(r.paths) + ' simulated futures',
        F.gbp(r.monthly_budget_today) + '/month budget',
        F.assumed(r.annual_return) + ' assumed return'
      ].map(function (c) { return '<span class="chip">' + c + '</span>'; });
      if (opt.end_reserve_months > 0) chips.push('<span class="chip chip--option">' + opt.end_reserve_months + '-month reserve</span>');
      if (opt.spend_at_least_income) chips.push('<span class="chip chip--option">Spends at least income</span>');
      var seed = r.seed ? 'seed ' + esc(r.seed.value) + ' (' + esc(r.seed.source) + ')' : '';
      return '<div class="chips">' + (state.b ? runLabel(o.k, o.r) : '') + chips.join('') + '</div>' +
        '<p class="provenance">Created ' + F.dateTime(r.created_at) + ' · ' + esc(r.config_file) + ' · ' + seed + ' · SBRetire ' + esc(r.sbretire_version) +
        ' · config <code title="' + esc(r.config_sha256) + '">' + esc(String(r.config_sha256 || '').slice(0, 10)) + '…</code></p>';
    }).join('');
    $('#run-meta').innerHTML = html;
    $$('[data-fill="paths"]').forEach(function (el) { el.textContent = F.int(runs()[0].r.run.paths); });
  }

  /* ---------------- compare strip ---------------- */
  function inputValue(r, item) { var i = (r.inputs || []).filter(function (x) { return x.item === item; })[0]; return i ? i.value : null; }
  function renderCompare() {
    var sec = $('#compare');
    if (!state.b) { sec.hidden = true; return; }
    sec.hidden = false;
    var A = DATA.runs[state.a], B = DATA.runs[state.b];
    var rows = [
      ['Monthly budget (today’s money)', F.gbp(A.run.monthly_budget_today), F.gbp(B.run.monthly_budget_today)],
      ['Assumed annual return', F.assumed(A.run.annual_return), F.assumed(B.run.annual_return)],
      ['End-of-life reserve', resv(A), resv(B)],
      ['Spends at least income', yn(A.run.options.spend_at_least_income), yn(B.run.options.spend_at_least_income)],
      ['Starting balance', fmtInput({ value: inputValue(A, 'portfolio.starting_balance'), unit: 'GBP' }), fmtInput({ value: inputValue(B, 'portfolio.starting_balance'), unit: 'GBP' })],
      ['As-of date', F.date(A.run.as_of_date), F.date(B.run.as_of_date)],
      ['Horizon', A.run.horizon_years + ' years', B.run.horizon_years + ' years'],
      ['Simulated futures', F.int(A.run.paths), F.int(B.run.paths)],
      ['Targets', targetsOf(A).map(F.target).join(', '), targetsOf(B).map(F.target).join(', ')]
    ];
    var diff = rows.filter(function (x) { return x[1] !== x[2]; }), same = rows.filter(function (x) { return x[1] === x[2]; });
    var nInputs = inputDiffCount(A, B);
    var html = '<div class="card"><div class="table-box"><table class="diff"><thead><tr><th scope="col">Setting</th><th scope="col">' + runLabel('a', A) + '</th><th scope="col">' + runLabel('b', B) + '</th></tr></thead><tbody>' +
      (diff.length ? diff.map(function (x) { return '<tr><th scope="row">' + x[0] + '</th><td>' + x[1] + '</td><td>' + x[2] + '</td></tr>'; }).join('') :
        '<tr><td colspan="3" class="muted">The headline settings are identical.</td></tr>') +
      '</tbody></table></div>' +
      '<p class="note" style="margin-top:var(--space-3)">' + (same.length ? 'Same in both: ' + same.map(function (x) { return x[0].toLowerCase() + ' (' + x[1] + ')'; }).join(', ') + '. ' : '') +
      nInputs + ' of the run inputs differ in total; they are highlighted under <a href="#inputs">Inputs</a>.</p></div>';
    $('#compare-body').innerHTML = html;
  }
  function resv(r) { var n = r.run.options.end_reserve_months; return n > 0 ? n + ' months of budget' : 'Off'; }
  function yn(b) { return b ? 'Yes' : 'No'; }
  function inputDiffCount(A, B) {
    var m = {}; A.inputs.forEach(function (i) { m[i.item] = i.value; });
    var n = 0, seen = {};
    B.inputs.forEach(function (i) { seen[i.item] = 1; if (m[i.item] !== i.value) n++; });
    A.inputs.forEach(function (i) { if (!seen[i.item]) n++; });
    return n;
  }

  /* ---------------- headline ---------------- */
  function status(rate, targets) {
    var ts = targets.slice().sort(function (a, b) { return a - b; });
    if (!ts.length) return '';
    var met = ts.filter(function (t) { return rate >= t; });
    var cls = 'ok', icon = '✓', text;
    if (met.length === ts.length) text = 'Meets every target (' + ts.map(F.target).join(', ') + ')';
    else if (met.length) text = 'Meets the ' + F.target(met[met.length - 1]) + ' target, not ' + F.target(ts[met.length]);
    else { cls = 'warn'; icon = '!'; text = 'Below the ' + F.target(ts[0]) + ' target'; }
    return '<p class="status status--' + cls + '"><span class="status__icon" aria-hidden="true">' + icon + '</span>' + text + '</p>';
  }
  function renderHeadline() {
    var list = runs();
    var html = '<div class="headline' + (list.length > 1 ? ' headline--two' : '') + '">' + list.map(function (o) {
      var r = o.r, s = r.summary, rs = reserveOn(r) ? r.reserve_summary : null, n = s.n_paths || 1;
      var budget = F.gbp(r.run.monthly_budget_today);
      var fig = '<div><p class="hl__eyebrow">Success rate at ' + budget + '/month' + info(r, 'sustainability_results.csv', 'conservative_success_probability', 'Success rate') + '</p>' +
        '<p class="hl__figure">' + F.rate(s.conservative_success_rate) + '</p>' +
        '<p class="hl__se">' + F.se(s.conservative_standard_error) + ' simulation noise</p>' + status(s.conservative_success_rate, targetsOf(r)) + '</div>';
      if (rs) fig += '<div><p class="hl__eyebrow">…and leaving a ' + r.run.options.end_reserve_months + '-month reserve at the second death</p>' +
        '<p class="hl__figure hl__figure--sm">' + F.rate(rs.conservative_success_rate) + '</p>' +
        '<p class="hl__se">' + F.se(rs.conservative_standard_error) + ' · ' + F.int(rs.n_successful) + ' of ' + F.int(rs.n_paths) + '</p></div>';
      var pct = function (x) { return (x / n * 100) + '%'; };
      var counts = '<div class="counts"><div class="bar" role="img" aria-label="' + F.int(s.n_successful) + ' successful, ' + F.int(s.n_failed) + ' failed, ' + F.int(s.n_unresolved) + ' unresolved, out of ' + F.int(n) + '">' +
        (s.n_successful ? '<span class="bar__seg bar__seg--ok" style="flex-basis:' + pct(s.n_successful) + '"></span>' : '') +
        (s.n_failed ? '<span class="bar__seg bar__seg--fail" style="flex-basis:' + pct(s.n_failed) + '"></span>' : '') +
        (s.n_unresolved ? '<span class="bar__seg bar__seg--unres" style="flex-basis:' + pct(s.n_unresolved) + '"></span>' : '') + '</div>' +
        '<div class="legend">' +
        '<span class="legend__item"><span class="swatch swatch--ok" aria-hidden="true"></span><strong>' + F.int(s.n_successful) + '</strong> successful</span>' +
        '<span class="legend__item"><span class="swatch swatch--fail" aria-hidden="true"></span><strong>' + F.int(s.n_failed) + '</strong> ran out of money</span>' +
        '<span class="legend__item"><span class="swatch swatch--unres" aria-hidden="true"></span><strong>' + F.int(s.n_unresolved) + '</strong> unresolved' + info(r, 'sustainability_results.csv', 'unresolved_fraction', 'Unresolved') + '</span>' +
        '<span class="legend__item">of ' + F.int(n) + ' simulated futures</span></div></div>';
      var sec = s.completed_success_rate == null
        ? 'No simulated future completed within the horizon, so there is no completed-path rate.'
        : 'Among the <strong>' + F.int(s.n_completed) + '</strong> futures that completed within the horizon: <strong>' + F.rate(s.completed_success_rate) + '</strong> ' + F.se(s.completed_standard_error) + '.' +
          (s.n_unresolved === 0 ? ' Every future completed, so this equals the headline rate.' : '');
      if (s.n_failed === 0 && s.n_unresolved === 0) sec += ' All ' + F.int(n) + ' simulated futures succeeded, so the simulation noise is zero.';
      return '<article class="card hl">' + (list.length > 1 ? '<h3 class="subhead">' + runLabel(o.k, r) + '</h3>' : '') +
        '<div class="hl__figures">' + fig + '</div>' + counts + '<p class="hl__secondary">' + sec + '</p></article>';
    }).join('') + '</div>';
    html += '<p class="note" style="margin-top:var(--space-3)">The ± figure is one Monte Carlo standard error: the wobble from simulating a finite number of futures. It is not a confidence interval and says nothing about whether the inputs are right.</p>';
    $('#headline-body').innerHTML = html;
  }

  /* ---------------- budgets + reserve ---------------- */
  function renderBudgets() {
    var list = runs(), anyReserve = list.some(function (o) { return reserveOn(o.r); });
    var legend = '<div class="chart-legend">' +
      legendSvg('<circle cx="14" cy="7" r="5.5" class="mk-a"></circle>', 'Maximum sustainable budget') +
      (anyReserve ? legendSvg('<circle cx="14" cy="7" r="5" class="mk-a is-hollow"></circle>', '…while leaving the end-of-life reserve') : '') +
      legendSvg('<line x1="14" x2="14" y1="0" y2="14" class="ref-a"></line>', 'Current budget') +
      (list.length > 1 ? '<span class="legend__item">' + mark('a') + esc(list[0].r.run.name) + '</span><span class="legend__item">' + mark('b') + esc(list[1].r.run.name) + '</span>' : '') + '</div>';
    var html = '<div class="card">' + legend + '<figure class="chart" id="chart-budgets"><div class="chart-svg"></div>' +
      '<figcaption>Monthly budget in today’s money for each target. The tables below hold the same figures.</figcaption></figure></div>';
    html += '<div class="grid-2" style="margin-top:var(--space-4)">' + budgetTable(list, 'budgets', 'lifestyle_results.csv', 'Maximum sustainable budget', false);
    if (anyReserve) html += budgetTable(list, 'reserve_budgets', 'lifestyle_reserve_results.csv', 'Leaving an end-of-life reserve', true);
    html += '</div>';
    $('#budgets-body').innerHTML = html;
  }
  function legendSvg(inner, label) { return '<span class="legend__item"><svg viewBox="0 0 28 14" aria-hidden="true">' + inner + '</svg>' + label + '</span>'; }
  function budgetTable(list, field, file, title, isReserve) {
    var r0 = list[0].r;
    var targets = unionTargets(list.map(function (o) { return o.r[field]; }));
    var multi = list.length > 1;
    var head = '<tr>' + th('Target', r0, file, 'target_probability') + (multi ? '<th scope="col">Run</th>' : '') +
      th('Per month', r0, file, 'maximum_monthly_budget_today', 'num') +
      th('Success', r0, file, 'estimated_success_probability', 'num') +
      (isReserve ? '<th scope="col" class="num">Cost</th>' : '') + '</tr>';
    var body = '';
    targets.forEach(function (t) {
      list.forEach(function (o, j) {
        var row = findT(o.r[field], t), base = isReserve ? findT(o.r.budgets, t) : null;
        var cells = '';
        if (j === 0) cells += '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>' + F.target(t) + '</th>';
        if (multi) cells += '<td>' + runLabel(o.k, o.r) + '</td>';
        if (!row) {
          var why = isReserve && !reserveOn(o.r) ? 'Reserve off in this run' : 'Target not in this run';
          cells += '<td class="num" colspan="' + (isReserve ? 3 : 2) + '"><span class="muted">' + why + '</span></td>';
        } else {
          var m = row.maximum_monthly_budget_today;
          cells += '<td class="num">' + (m == null ? nullCell(row.note) : '<span class="big">' + F.gbp(m) + '</span><span class="sub">' + F.gbp(row.maximum_annual_budget_today) + ' a year</span>' + (row.converged === false ? compactConverged(row) : '') + (row.note ? '<span class="cell-note">' + esc(row.note) + '</span>' : '')) + '</td>' +
            '<td class="num">' + F.rate(row.estimated_success_probability) + '<span class="sub">' + F.se(row.standard_error) + '</span></td>';
          if (isReserve) {
            var cost = base && isNum(base.maximum_monthly_budget_today) && isNum(m) ? Math.floor(base.maximum_monthly_budget_today) - Math.floor(m) : null;
            cells += '<td class="num">' + (cost == null ? DASH : F.gbp(cost) + '<span class="sub">a month</span>') + '</td>';
          }
        }
        body += '<tr' + (multi && j === 0 ? ' class="is-group-start"' : '') + '>' + cells + '</tr>';
      });
    });
    var resvMonths = list.map(function (o) { return o.r.run.options.end_reserve_months; }).filter(function (n) { return n > 0; });
    var sub = isReserve ? '<p class="note" style="margin-bottom:var(--space-3)">The same search, but each future must also leave ' + (resvMonths.length ? resvMonths[0] + ' months' : 'N months') + ' of budget at the second death. The difference is what the reserve costs each month.</p>'
      : '<p class="note" style="margin-bottom:var(--space-3)">Today’s money, rising with inflation. Rounded down, so each figure meets its target.</p>';
    var allConv = list.every(function (o) { return (o.r[field] || []).every(function (x) { return x.converged !== false; }); });
    var tolRow = list.map(function (o) { return (o.r[field] || [])[0]; }).filter(Boolean)[0];
    var tol = tolRow && isNum(tolRow.budget_tolerance) ? F.gbp(tolRow.budget_tolerance) : 'its tolerance';
    var foot = '<p class="note" style="margin-top:var(--space-3)">' + (allConv ? '✓ Every search converged to within ' + tol + ' a month.' : 'Rows marked “Not converged” stopped before reaching the ' + tol + ' tolerance.') + (isReserve ? ' Cost is the drop in monthly budget from leaving the reserve.' : '') + '</p>';
    return '<div class="card"><h3 class="subhead">' + title + '</h3>' + sub + '<div class="table-box"><table class="t"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>' + foot + '</div>';
  }

  /* ---------------- required return ---------------- */
  function renderReturns() {
    var list = runs(), r0 = list[0].r, file = 'sustainability_results.csv', multi = list.length > 1;
    var targets = unionTargets(list.map(function (o) { return o.r.returns; }));
    var anyNeg = list.some(function (o) { return o.r.returns.some(function (x) { return isNum(x.required_annual_return) && x.required_annual_return < 0; }); });
    var head = '<tr>' + th('Target', r0, file, 'target_probability') + (multi ? '<th scope="col">Run</th>' : '') +
      th('Required return', r0, file, 'required_annual_return', 'num') + '<th scope="col" class="num">Assumed</th><th scope="col" class="num">Margin</th>' +
      th('Success at required return', r0, file, 'estimated_success_probability', 'num') + th('Search', r0, file, 'converged') + '</tr>';
    var body = '';
    targets.forEach(function (t) {
      list.forEach(function (o, j) {
        var row = findT(o.r.returns, t), cells = '';
        if (j === 0) cells += '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>' + F.target(t) + '</th>';
        if (multi) cells += '<td>' + runLabel(o.k, o.r) + '</td>';
        if (!row) { body += '<tr>' + cells + '<td class="num muted" colspan="5">Target not in this run</td></tr>'; return; }
        var req = row.required_annual_return, assumed = Math.round(o.r.run.annual_return * 10000) / 100, margin = '';
        if (isNum(req)) {
          var g = +(assumed - F.retVal(req)).toFixed(2);
          margin = g >= 0 ? '<span class="tag tag--ok">✓ ' + signedPts(g) + ' pts</span>' : '<span class="tag tag--warn">! ' + Math.abs(g).toFixed(2) + ' pts short</span>';
        } else margin = DASH;
        cells += '<td class="num">' + (isNum(req) ? '<span class="big">' + F.ret(req) + '</span>' : nullCell(row.note)) + '</td>' +
          '<td class="num">' + F.assumed(o.r.run.annual_return) + '</td><td class="num">' + margin + '</td>' +
          '<td class="num">' + F.rate(row.success_probability_at_required_return) + ' <span class="muted">' + F.se(row.standard_error_at_required_return) + '</span></td>' +
          '<td>' + convergedCell(row) + '</td>';
        body += '<tr' + (multi && j === 0 ? ' class="is-group-start"' : '') + '>' + cells + '</tr>';
      });
    });
    var legend = '<div class="chart-legend">' +
      legendSvg('<circle cx="14" cy="7" r="5.5" class="mk-a"></circle>', 'Required return') +
      legendSvg('<line x1="14" x2="14" y1="0" y2="14" class="ref-a"></line>', 'Assumed return') +
      legendSvg('<line x1="2" x2="26" y1="7" y2="7" class="gap-ok"></line>', 'Margin') +
      legendSvg('<line x1="2" x2="26" y1="7" y2="7" class="gap-short"></line>', 'Shortfall') +
      (multi ? '<span class="legend__item">' + mark('a') + esc(list[0].r.run.name) + '</span><span class="legend__item">' + mark('b') + esc(list[1].r.run.name) + '</span>' : '') + '</div>';
    var html = '<div class="card">' + legend + '<figure class="chart" id="chart-returns"><div class="chart-svg"></div><figcaption>Fixed annual return after fees, rounded up. The table below holds the same figures.</figcaption></figure>' +
      '<div class="table-box" style="margin-top:var(--space-4)"><table class="t"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>' +
      (anyNeg ? '<p class="note" style="margin-top:var(--space-3)">A negative required return means the plan would still meet that target even if the savings lost value every year.</p>' : '') +
      '<p class="note">Margin is the assumed return minus the required return, in percentage points.</p></div>';
    $('#returns-body').innerHTML = html;
  }

  /* ---------------- chart primitives ---------------- */
  function scale(d0, d1, r0, r1) { var k = (r1 - r0) / ((d1 - d0) || 1); var f = function (v) { return r0 + (v - d0) * k; }; f.inv = function (p) { return d0 + (p - r0) / k; }; return f; }
  function ticks(min, max, count) {
    var span = max - min || Math.abs(max) || 1, step0 = span / count, mag = Math.pow(10, Math.floor(Math.log10(step0))), e = step0 / mag;
    var step = (e >= 7.5 ? 10 : e >= 3.5 ? 5 : e >= 1.5 ? 2 : 1) * mag, out = [];
    for (var v = Math.ceil(min / step) * step; v <= max + step * 1e-6; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function svgOpen(w, h, label, focusable) {
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '" role="img" aria-label="' + esc(label) + '"' + (focusable ? ' tabindex="0"' : '') + '>';
  }
  function marker(k, x, y, hollow, size) {
    var s = size || 6, cls = 'mk-' + k + (hollow ? ' is-hollow' : '');
    return k === 'a' ? '<circle cx="' + x + '" cy="' + y + '" r="' + s + '" class="' + cls + '"></circle>'
      : '<rect x="' + (x - s + 0.5) + '" y="' + (y - s + 0.5) + '" width="' + (2 * s - 1) + '" height="' + (2 * s - 1) + '" class="' + cls + '"></rect>';
  }
  function txt(x, y, s, cls, anchor) { return '<text x="' + x + '" y="' + y + '" class="' + (cls || 'lbl') + '"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + '>' + esc(s) + '</text>'; }

  function dotChart(el, opts) {
    var list = runs(), w = Math.max(300, el.clientWidth), narrow = w < 560;
    var lane = 26, rowGap = 16, rowH = list.length * lane + rowGap;
    var P = { l: narrow ? 46 : 92, r: narrow ? 52 : 64, t: list.length > 1 ? 46 : 30, b: 30 };
    var targets = opts.targets, h = P.t + targets.length * rowH + P.b; P.w = w - P.l - P.r;
    var vals = [];
    list.forEach(function (o) { vals.push(opts.ref(o.r)); targets.forEach(function (t) { opts.values(o.r, t).forEach(function (v) { if (isNum(v)) vals.push(v); }); }); });
    if (opts.zero) vals.push(0);
    var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals), sp = (mx - mn) || Math.abs(mx) * 0.1 || 1;
    var lo = mn - sp * 0.22, hi = mx + sp * 0.18;
    if (opts.floorZero && lo < 0 && mn >= 0) lo = 0;
    var X = scale(lo, hi, P.l, P.l + P.w), g = ''; X.left = P.l + 4;
    var tk = ticks(lo, hi, narrow ? 3 : 6);
    g += '<g class="ax">';
    tk.forEach(function (v) { var x = X(v); g += '<line class="gridline" x1="' + x + '" x2="' + x + '" y1="' + (P.t - 6) + '" y2="' + (h - P.b) + '"></line>' + txt(x, h - P.b + 18, opts.fmtAxis(v), 'lbl', 'middle'); });
    g += '</g>';
    if (opts.zero && lo < 0 && hi > 0) g += '<line class="zeroline" x1="' + X(0) + '" x2="' + X(0) + '" y1="' + (P.t - 6) + '" y2="' + (h - P.b) + '"></line>';
    targets.forEach(function (t, ti) {
      var y0 = P.t + ti * rowH;
      if (ti > 0) g += '<line class="rowline" x1="0" x2="' + w + '" y1="' + (y0 - rowGap / 2) + '" y2="' + (y0 - rowGap / 2) + '"></line>';
      g += txt(P.l - 12, y0 + list.length * lane / 2 + 4, narrow ? F.target(t) : F.target(t) + ' target', 'lbl lbl--strong', 'end');
      list.forEach(function (o, j) { g += opts.drawRow(o, t, y0 + j * lane + lane / 2, X); });
    });
    list.forEach(function (o, j) {
      var x = X(opts.ref(o.r));
      g += '<line class="ref-' + o.k + '" x1="' + x + '" x2="' + x + '" y1="' + (P.t - 8 - (list.length - 1 - j) * 0) + '" y2="' + (h - P.b) + '"></line>';
      g += txt(Math.min(Math.max(x, P.l + 30), w - 30), P.t - 14 - j * 15, opts.refLabel(o.r, narrow), 'lbl lbl--' + o.k, 'middle');
    });
    el.innerHTML = svgOpen(w, h, opts.label) + g + '</svg>';
  }

  function drawBudgetChart() {
    var el = $('#chart-budgets .chart-svg'); if (!el) return;
    var list = runs();
    dotChart(el, {
      label: 'Maximum sustainable monthly budget by target, against the current budget',
      targets: unionTargets(list.map(function (o) { return o.r.budgets; }).concat(list.map(function (o) { return o.r.reserve_budgets; }))),
      ref: function (r) { return r.run.monthly_budget_today; },
      values: function (r, t) { var a = findT(r.budgets, t), b = findT(r.reserve_budgets, t); return [a && a.maximum_monthly_budget_today, b && b.maximum_monthly_budget_today]; },
      fmtAxis: F.gbpShort, floorZero: true,
      refLabel: function (r, narrow) { return (narrow ? '' : 'Budget ') + F.gbp(r.run.monthly_budget_today); },
      drawRow: function (o, t, cy, X) {
        var a = findT(o.r.budgets, t), b = reserveOn(o.r) ? findT(o.r.reserve_budgets, t) : null, s = '';
        var v = a && a.maximum_monthly_budget_today, rv = b && b.maximum_monthly_budget_today;
        if (!a) return '';
        if (!isNum(v)) return txt(X.left, cy + 4, DASH + ' ' + (a.note || 'No budget meets this target'), 'lbl');
        if (isNum(rv)) {
          s += '<line class="link-' + o.k + '" x1="' + X(rv) + '" x2="' + X(v) + '" y1="' + cy + '" y2="' + cy + '"></line>';
          s += marker(o.k, X(rv), cy, true, 5.5) + txt(X(rv) - 11, cy + 4, F.gbp(rv), 'lbl', 'end');
        }
        s += marker(o.k, X(v), cy, false) + txt(X(v) + 11, cy + 4, F.gbp(v), 'lbl lbl--strong');
        if (a.converged === false) s += txt(X(v) + 11, cy + 16, '! not converged', 'lbl lbl--warn');
        return s;
      }
    });
  }

  function drawReturnChart() {
    var el = $('#chart-returns .chart-svg'); if (!el) return;
    var list = runs();
    dotChart(el, {
      label: 'Required annual return by target, against the assumed return',
      targets: unionTargets(list.map(function (o) { return o.r.returns; })),
      ref: function (r) { return Math.round(r.run.annual_return * 10000) / 100; },
      values: function (r, t) { var a = findT(r.returns, t); return [a && isNum(a.required_annual_return) ? F.retVal(a.required_annual_return) : null]; },
      fmtAxis: function (v) { return (v < 0 ? MINUS : '') + Math.abs(+v.toFixed(2)) + '%'; }, zero: true,
      refLabel: function (r, narrow) { return (narrow ? '' : 'Assumed ') + F.assumed(r.run.annual_return); },
      drawRow: function (o, t, cy, X) {
        var a = findT(o.r.returns, t); if (!a) return '';
        if (!isNum(a.required_annual_return)) return txt(X(Math.round(o.r.run.annual_return * 10000) / 100) + 8, cy + 4, DASH + ' ' + (a.note || 'No solution in range'), 'lbl');
        var v = F.retVal(a.required_annual_return), ref = Math.round(o.r.run.annual_return * 10000) / 100, ok = ref >= v;
        var s = '<line class="' + (ok ? 'gap-ok' : 'gap-short') + '" x1="' + X(v) + '" x2="' + X(ref) + '" y1="' + cy + '" y2="' + cy + '"></line>';
        s += marker(o.k, X(v), cy, false);
        s += txt(ok ? X(v) - 11 : X(v) + 11, cy + 4, F.ret(a.required_annual_return), 'lbl lbl--strong', ok ? 'end' : 'start');
        return s;
      }
    });
  }

  function yearsUnion(sets) {
    var m = {}; sets.forEach(function (s) { s.rows.forEach(function (r) { m[r.year] = 1; }); });
    return Object.keys(m).map(Number).sort(function (a, b) { return a - b; });
  }
  function segments(rows, keys) {
    var out = [], cur = [];
    rows.forEach(function (r) { if (keys.every(function (k) { return isNum(r[k]); })) cur.push(r); else { if (cur.length) out.push(cur); cur = []; } });
    if (cur.length) out.push(cur); return out;
  }
  function linePath(rows, key, X, Y) {
    return segments(rows, [key]).map(function (seg) { return seg.map(function (r, i) { return (i ? 'L' : 'M') + X(r.year).toFixed(1) + ',' + Y(r[key]).toFixed(1); }).join(''); }).join('');
  }
  function bandPath(rows, lo, hi, X, Y) {
    return segments(rows, [lo, hi]).map(function (seg) {
      var top = seg.map(function (r, i) { return (i ? 'L' : 'M') + X(r.year).toFixed(1) + ',' + Y(r[hi]).toFixed(1); }).join('');
      var bot = seg.slice().reverse().map(function (r) { return 'L' + X(r.year).toFixed(1) + ',' + Y(r[lo]).toFixed(1); }).join('');
      return top + bot + 'Z';
    }).join('');
  }
  function frame(el, minH) {
    var w = Math.max(300, el.clientWidth), narrow = w < 560, h = narrow ? minH : Math.round(minH * 1.3);
    var P = { l: narrow ? 50 : 62, r: 14, t: 12, b: 30 }; P.w = w - P.l - P.r; P.h = h - P.t - P.b;
    return { w: w, h: h, P: P, narrow: narrow };
  }
  function axes(fr, X, Y, yt, xt, fmtY) {
    var P = fr.P, g = '<g class="ax">';
    yt.forEach(function (v) { var y = Y(v); g += '<line class="gridline" x1="' + P.l + '" x2="' + (P.l + P.w) + '" y1="' + y + '" y2="' + y + '"></line>' + txt(P.l - 8, y + 4, fmtY(v), 'lbl', 'end'); });
    xt.forEach(function (v) { g += txt(X(v), fr.h - P.b + 18, String(v), 'lbl', 'middle'); });
    g += '<line class="domain" x1="' + P.l + '" x2="' + (P.l + P.w) + '" y1="' + (P.t + P.h) + '" y2="' + (P.t + P.h) + '"></line></g>';
    return g;
  }
  function attachHover(fig, years, X, P, content) {
    var svg = $('svg', fig), tip = $('.chart-tip', fig), guide = $('.hover-line', svg), idx = -1;
    function show(i) {
      idx = Math.max(0, Math.min(years.length - 1, i));
      var x = X(years[idx]); guide.setAttribute('x1', x); guide.setAttribute('x2', x); guide.style.visibility = 'visible';
      tip.innerHTML = content(years[idx]); tip.hidden = false;
      var fw = fig.clientWidth, tw = tip.offsetWidth, left = x + 14; if (left + tw > fw) left = x - 14 - tw;
      tip.style.left = Math.max(0, left) + 'px'; tip.style.top = P.t + 'px';
    }
    function hide() { guide.style.visibility = 'hidden'; tip.hidden = true; }
    svg.addEventListener('pointermove', function (e) {
      var r = svg.getBoundingClientRect(), yr = X.inv(e.clientX - r.left), best = 0, bd = Infinity;
      years.forEach(function (y, i) { var d = Math.abs(y - yr); if (d < bd) { bd = d; best = i; } }); show(best);
    });
    svg.addEventListener('pointerleave', hide);
    svg.addEventListener('focus', function () { show(idx < 0 ? 0 : idx); });
    svg.addEventListener('blur', hide);
    svg.addEventListener('keydown', function (e) {
      var k = e.key;
      if (k === 'ArrowRight') show(idx + 1); else if (k === 'ArrowLeft') show(idx - 1); else if (k === 'Home') show(0); else if (k === 'End') show(years.length - 1); else if (k === 'Escape') { hide(); return; } else return;
      e.preventDefault();
    });
  }
  function rowAt(r, y) { return r.annual.filter(function (x) { return x.year === y; })[0] || null; }
  function tipRow(label, v) { return '<div class="chart-tip__row"><span>' + label + '</span><b>' + v + '</b></div>'; }

  function drawFan() {
    var fig = $('#chart-fan'); if (!fig) return;
    var el = $('.chart-svg', fig), list = runs(), fr = frame(el, 270), P = fr.P;
    var sets = list.map(function (o) { return { k: o.k, r: o.r, rows: visibleRows(o.r) }; });
    var years = yearsUnion(sets), x0 = years[0], x1 = years[years.length - 1];
    var ymax = 0; sets.forEach(function (s) { s.rows.forEach(function (r) { if (isNum(r.portfolio_p95)) ymax = Math.max(ymax, r.portfolio_p95); }); });
    var yt = ticks(0, ymax || 1, fr.narrow ? 4 : 5), y1 = Math.max(yt[yt.length - 1], ymax || 1);
    var X = scale(x0, x1, P.l, P.l + P.w), Y = scale(0, y1, P.t + P.h, P.t);
    var g = axes(fr, X, Y, yt, ticks(x0, x1, fr.narrow ? 4 : 8).filter(function (v) { return v % 1 === 0; }), F.gbpShort);
    var A = sets[0];
    g += '<path class="band-outer" d="' + bandPath(A.rows, 'portfolio_p05', 'portfolio_p95', X, Y) + '"></path>';
    g += '<path class="band-inner" d="' + bandPath(A.rows, 'portfolio_p25', 'portfolio_p75', X, Y) + '"></path>';
    g += '<path class="median" d="' + linePath(A.rows, 'portfolio_median', X, Y) + '"></path>';
    if (sets[1]) {
      var B = sets[1];
      g += '<path class="fan-b-edge" d="' + linePath(B.rows, 'portfolio_p05', X, Y) + linePath(B.rows, 'portfolio_p95', X, Y) + '"></path>';
      g += '<path class="fan-b-inner" d="' + linePath(B.rows, 'portfolio_p25', X, Y) + linePath(B.rows, 'portfolio_p75', X, Y) + '"></path>';
      g += '<path class="fan-b-median" d="' + linePath(B.rows, 'portfolio_median', X, Y) + '"></path>';
    }
    g += '<line class="hover-line" x1="0" x2="0" y1="' + P.t + '" y2="' + (P.t + P.h) + '"></line>';
    el.innerHTML = svgOpen(fr.w, fr.h, 'Portfolio fan chart, ' + x0 + ' to ' + x1 + '. Use the arrow keys to read each year.', true) + g + '</svg>';
    attachHover(fig, years, X, P, function (y) {
      return '<div class="chart-tip__year">' + y + '</div>' + sets.map(function (s) {
        var r = rowAt(s.r, y); if (!r) return '';
        var has = isNum(r.portfolio_median);
        return (sets.length > 1 ? '<div class="chart-tip__run">' + mark(s.k) + esc(s.r.run.name) + '</div>' : '') +
          (has ? tipRow('Median', F.gbp(r.portfolio_median)) + tipRow('Middle half', F.gbpShort(r.portfolio_p25) + '–' + F.gbpShort(r.portfolio_p75)) + tipRow('90 % of futures', F.gbpShort(r.portfolio_p05) + '–' + F.gbpShort(r.portfolio_p95))
            : '<div class="chart-tip__row"><span>' + NULL_YEAR + '</span></div>');
      }).join('');
    });
  }

  function drawSurvival() {
    var fig = $('#chart-survival'); if (!fig) return;
    var el = $('.chart-svg', fig), list = runs(), fr = frame(el, 250), P = fr.P;
    var sets = list.map(function (o) { return { k: o.k, r: o.r, rows: visibleRows(o.r) }; });
    var years = yearsUnion(sets), x0 = years[0], x1 = years[years.length - 1];
    var X = scale(x0, x1, P.l, P.l + P.w), Y = scale(0, 1, P.t + P.h, P.t);
    var g = axes(fr, X, Y, [0, 0.25, 0.5, 0.75, 1], ticks(x0, x1, fr.narrow ? 4 : 8).filter(function (v) { return v % 1 === 0; }), function (v) { return Math.round(v * 100) + '%'; });
    var A = sets[0];
    g += '<path class="ln ln-both" d="' + linePath(A.rows, 'probability_both_alive', X, Y) + '"></path>';
    g += '<path class="ln ln-p1" d="' + linePath(A.rows, 'probability_person_1_alive', X, Y) + '"></path>';
    g += '<path class="ln ln-p2" d="' + linePath(A.rows, 'probability_person_2_alive', X, Y) + '"></path>';
    sets.forEach(function (s) { g += '<path class="ln ln-money-' + s.k + '" d="' + linePath(s.rows, 'probability_not_depleted_yet', X, Y) + '"></path>'; });
    g += '<line class="hover-line" x1="0" x2="0" y1="' + P.t + '" y2="' + (P.t + P.h) + '"></line>';
    el.innerHTML = svgOpen(fr.w, fr.h, 'Survival and money-lasting lines, ' + x0 + ' to ' + x1 + '. Use the arrow keys to read each year.', true) + g + '</svg>';
    var pp = A.r.people || [];
    attachHover(fig, years, X, P, function (y) {
      var r = rowAt(A.r, y), out = '<div class="chart-tip__year">' + y + '</div>';
      if (r) out += tipRow(esc(pp[0] ? pp[0].name : 'Person 1') + ' alive', F.rate(r.probability_person_1_alive)) + tipRow(esc(pp[1] ? pp[1].name : 'Person 2') + ' alive', F.rate(r.probability_person_2_alive)) + tipRow('Both alive', F.rate(r.probability_both_alive));
      sets.forEach(function (s) { var q = rowAt(s.r, y); if (q) out += tipRow((sets.length > 1 ? mark(s.k) + ' ' : '') + 'Money not run out', F.rate(q.probability_not_depleted_yet)); });
      return out;
    });
  }

  function renderChartShells() {
    var list = runs(), multi = list.length > 1, A = list[0].r, pp = A.people || [];
    var fanLegend = '<div class="chart-legend">' +
      legendSvg('<rect x="0" y="0" width="28" height="14" class="sw-band-outer"></rect>', '5th–95th percentile') +
      legendSvg('<rect x="0" y="3" width="28" height="8" class="sw-band-inner"></rect>', '25th–75th percentile') +
      legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="median"></line>', 'Median' + (multi ? ' · ' + esc(A.run.name) : '')) +
      (multi ? legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="fan-b-median"></line>', 'Median · ' + esc(list[1].r.run.name)) +
        legendSvg('<line x1="0" x2="28" y1="3" y2="3" class="fan-b-edge"></line><line x1="0" x2="28" y1="11" y2="11" class="fan-b-edge"></line>', '5th / 95th · ' + esc(list[1].r.run.name)) : '') + '</div>';
    $('#portfolio-body').innerHTML = '<div class="card">' + fanLegend + '<figure class="chart" id="chart-fan"><div class="chart-svg"></div><div class="chart-tip" hidden></div>' +
      '<figcaption>Nominal pounds: not adjusted for inflation. Hover, or focus the chart and use the arrow keys, to read a year; the <a href="#years">year-by-year table</a> holds every value.' +
      (state.allYears ? '' : ' Showing years until fewer than 0.1 % of futures are still running.') + '</figcaption></figure></div>';
    var survLegend = '<div class="chart-legend">' +
      legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="ln ln-p1"></line>', esc(pp[0] ? pp[0].name : 'Person 1') + ' alive') +
      legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="ln ln-p2"></line>', esc(pp[1] ? pp[1].name : 'Person 2') + ' alive') +
      legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="ln ln-both"></line>', 'Both alive') +
      legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="ln ln-money-a"></line>', 'Money not run out yet' + (multi ? ' · ' + esc(A.run.name) : '')) +
      (multi ? legendSvg('<line x1="0" x2="28" y1="7" y2="7" class="ln ln-money-b"></line>', 'Money not run out yet · ' + esc(list[1].r.run.name)) : '') +
      info(A, 'annual_results.csv', 'probability_not_depleted_yet', 'Money not run out yet') + '</div>';
    $('#survival-body').innerHTML = '<div class="card">' + survLegend + '<figure class="chart" id="chart-survival"><div class="chart-svg"></div><div class="chart-tip" hidden></div>' +
      '<figcaption>Shares of all simulated futures.' + (multi ? ' Survival lines are from ' + esc(A.run.name) + '; they depend only on the people, not on the money.' : '') + ' The money line ends at the run’s success rate.</figcaption></figure></div>';
  }
  function drawCharts() { drawBudgetChart(); drawReturnChart(); drawFan(); drawSurvival(); }

  /* ---------------- year table ---------------- */
  function renderYears() {
    var list = runs();
    if (state.tableRun === 'b' && !state.b) state.tableRun = 'a';
    var o = list.filter(function (x) { return x.k === state.tableRun; })[0] || list[0], r = o.r, pp = r.people || [], file = 'annual_results.csv';
    var cols = [
      ['year', 'Year', null], ['months', 'Months', 'int'],
      ['probability_both_alive', 'Both alive', 'rate'], ['probability_person_1_alive', esc(pp[0] ? pp[0].name : 'Person 1') + ' alive', 'rate'], ['probability_person_2_alive', esc(pp[1] ? pp[1].name : 'Person 2') + ' alive', 'rate'],
      ['monthly_budget_nominal_median', 'Budget / month (median)', 'gbp'], ['annual_budget_nominal_median', 'Spending / year (median)', 'gbp'], ['annual_income_median', 'Household income / year (median)', 'gbp'], ['annual_net_withdrawal_median', 'Net withdrawal (median)', 'gbp'],
      ['portfolio_p05', 'Portfolio 5th', 'gbp'], ['portfolio_p25', '25th', 'gbp'], ['portfolio_median', 'Median', 'gbp'], ['portfolio_p75', '75th', 'gbp'], ['portfolio_p95', '95th', 'gbp'],
      ['probability_not_depleted_yet', 'Money not run out yet', 'rate'], ['estimated_lifetime_success_rate', 'Lifetime success estimate', 'rate'],
      ['completed_paths', 'Completed', 'int'], ['unresolved_paths', 'Unresolved', 'int']
    ];
    var head = '<tr>' + cols.map(function (c) { return th(c[1], r, file, c[0], c[2] ? 'num' : ''); }).join('') + '</tr>';
    var body = r.annual.map(function (row) {
      return '<tr>' + cols.map(function (c, i) {
        if (i === 0) return '<th scope="row">' + row.year + '</th>';
        var v = row[c[0]];
        if (v == null) return '<td class="num"><span class="null" title="' + NULL_YEAR + '">' + DASH + '</span></td>';
        return '<td class="num">' + (c[2] === 'rate' ? F.rate(v) : c[2] === 'gbp' ? F.gbp(v) : F.int(v)) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    var tabs = list.length > 1 ? '<div class="tabs" role="tablist" aria-label="Run shown in the table">' + list.map(function (x) {
      return '<button type="button" role="tab" class="seg__btn" data-table-run="' + x.k + '" aria-selected="' + (x.k === o.k) + '">' + mark(x.k) + esc(x.r.run.name) + '</button>';
    }).join('') + '</div>' : '';
    var det = $('#years-fold'), open = det ? det.open : false;
    $('#years-body').innerHTML = '<details class="fold" id="years-fold"' + (open ? ' open' : '') + '><summary>Show the table <span class="muted">' + r.annual.length + ' rows · ' + r.annual[0].year + '–' + r.annual[r.annual.length - 1].year + '</span></summary>' +
      '<div class="fold__body">' + tabs + '<div class="year-box"><table class="t"><caption class="visually-hidden">Year-by-year results for ' + esc(r.run.name) + '</caption><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>' +
      '<p class="note" style="margin-top:var(--space-3)">A dash means no simulated future was still running that year. Portfolio columns are year-end percentiles across futures.</p></div></details>';
    $$('[data-table-run]').forEach(function (b) { b.addEventListener('click', function () { state.tableRun = b.dataset.tableRun; renderYears(); var t = $('[data-table-run="' + state.tableRun + '"]'); if (t) t.focus(); }); });
  }

  /* ---------------- inputs ---------------- */
  var SECTION_TITLES = { model: 'Model', portfolio: 'Portfolio', budget: 'Budget', inflation: 'Inflation', mortality: 'Mortality', people: 'People', income: 'Household income', derived: 'Derived' };
  function pctTrim(x) { return String(+(x * 100).toFixed(2)) + '%'; }
  function fmtInput(i) {
    var v = i.value, u = i.unit || '';
    if (v === '' || v == null) return '<span class="muted">' + DASH + '</span>';
    if (v === 'true') return 'Yes'; if (v === 'false') return 'No';
    var num = isFinite(+v) && String(v).trim() !== '';
    if (/^GBP/.test(u) && num) {
      var rest = u.replace(/^GBP/, '').replace(/^\/month/, ' per month').replace(/^\/year/, ' per year').replace(/^,\s*/, ', ');
      return '£' + (+v).toLocaleString('en-GB', { maximumFractionDigits: 2 }) + esc(rest);
    }
    if (/^(share|annual effective rate|annual rate)/.test(u)) {
      var parts = String(v).split(';');
      if (parts.every(function (p) { return p !== '' && isFinite(+p); })) return parts.map(function (p) { return pctTrim(+p); }).join(', ');
    }
    if (u === 'date') return F.date(v);
    var shown = String(v).indexOf(';') >= 0 ? String(v).split(';').join(', ') : num && Math.abs(+v) >= 1000 ? (+v).toLocaleString('en-GB') : v;
    if (!u || u === 'file' || u === 'person id or household' || u === 'as written' || u === 'text') return esc(shown);
    return esc(shown) + ' <span class="muted">' + esc(u) + '</span>';
  }
  function unitText(u) { return !u || u === 'GBP' ? '' : esc(u.replace(/^GBP\//, 'per ').replace(/^GBP, /, '')); }
  function renderInputs() {
    var list = runs(), A = list[0].r, B = list[1] ? list[1].r : null;
    var order = [], bySec = {};
    function add(i, which) {
      if (!bySec[i.section]) { bySec[i.section] = { items: [], map: {} }; order.push(i.section); }
      var s = bySec[i.section], e = s.map[i.item];
      if (!e) { e = s.map[i.item] = { item: i.item, label: i.label, unit: i.unit }; s.items.push(e); }
      e[which] = i;
    }
    A.inputs.forEach(function (i) { add(i, 'a'); });
    if (B) B.inputs.forEach(function (i) { add(i, 'b'); });
    var html = '<div class="inputs' + (B ? '' : ' inputs--single') + '">' + order.map(function (sec) {
      if (sec === 'people') return peopleCard(list);
      if (sec === 'mortality') return mortalityCard(list);
      if (sec === 'inflation') return inflationCard(list);
      if (sec === 'income') return incomeCard(list);
      var s = bySec[sec];
      var rows = s.items.map(function (e) {
        var diff = B && (!e.a || !e.b || e.a.value !== e.b.value);
        return '<tr' + (diff ? ' class="is-diff"' : '') + '><th scope="row">' + esc(e.label) + (diff ? ' <span class="tag tag--warn">Differs</span>' : '') + '</th>' +
          '<td class="val">' + (e.a ? fmtInput(e.a) : '<span class="muted">not set</span>') + '</td>' +
          (B ? '<td class="val">' + (e.b ? fmtInput(e.b) : '<span class="muted">not set</span>') + '</td>' : '') + '</tr>';
      }).join('');
      return '<div class="card"><div class="table-box"><table class="t t--inputs"><caption>' + esc(SECTION_TITLES[sec] || sec) + '</caption><thead><tr>' +
        th('Setting', A, 'inputs.csv', 'label') + (B ? '<th scope="col">' + runLabel('a', A) + '</th><th scope="col">' + runLabel('b', B) + '</th>' : th('Value', A, 'inputs.csv', 'value')) +
        '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
    }).join('') + '</div>';
    $('#inputs-body').innerHTML = html;
  }

  function peopleOf(r) {
    var m = {}, ids = [];
    (r.inputs || []).forEach(function (i) {
      var x = /^people\[([^\]]+)\]\.(.+)$/.exec(i.item); if (!x) return;
      if (!m[x[1]]) { m[x[1]] = {}; ids.push(x[1]); }
      m[x[1]][x[2]] = i.value;
    });
    return ids.map(function (id) { return m[id]; });
  }
  function personCells(p) {
    var f = p.survivor_budget_factor, dob = p.date_of_birth ? F.month(p.date_of_birth.slice(0, 7)) : DASH;
    var sex = p.sex ? esc(p.sex.charAt(0).toUpperCase() + p.sex.slice(1)) : DASH;
    var surv = f === '' || f == null ? '<span class="muted">Household default</span>' : pctTrim(+f) + ' of budget';
    return '<td>' + dob + '</td><td>' + sex + '</td><td class="num">' + surv + '</td>';
  }
  function peopleCard(list) {
    var multi = list.length > 1, body = '';
    var all = list.map(function (o) { return peopleOf(o.r); }), n = Math.max.apply(null, all.map(function (a) { return a.length; }));
    for (var i = 0; i < n; i++) {
      list.forEach(function (o, j) {
        var p = all[j][i], key = function (q) { return q ? [q.name, q.date_of_birth, q.sex, q.survivor_budget_factor].join('|') : ''; };
        var diff = multi && key(all[0][i]) !== key(all[1][i]);
        body += '<tr' + (multi && j === 0 ? ' class="is-group-start"' : '') + (diff ? ' style="background:var(--color-warning-soft)"' : '') + '>' +
          (j === 0 ? '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>' + esc(p ? p.name : DASH) + '</th>' : '') +
          (multi ? '<td>' + runLabel(o.k, o.r) + (diff ? ' <span class="tag tag--warn">Differs</span>' : '') + '</td>' : '') +
          (p ? personCells(p) : '<td colspan="3" class="muted">not set</td>') + '</tr>';
      });
    }
    return '<div class="card"><div class="table-box"><table class="t"><caption>People</caption><thead><tr><th scope="col">Name</th>' + (multi ? '<th scope="col">Run</th>' : '') +
      '<th scope="col">Born</th><th scope="col">Sex (mortality table)</th><th scope="col" class="num">Budget as survivor</th></tr></thead><tbody>' + body + '</tbody></table></div>' +
      '<p class="note" style="margin-top:var(--space-3)">Only the year and month of birth are used.</p></div>';
  }

  var MORTALITY_SOURCES = { ONS_2024_BASED: 'ONS 2024-based mortality projections' };
  function mortalityName(r) {
    var v = inputValue(r, 'mortality.source'); if (!v) return DASH;
    if (MORTALITY_SOURCES[v]) return MORTALITY_SOURCES[v];
    var m = /^ONS_(\d{4})_BASED$/.exec(v);
    return m ? 'ONS ' + m[1] + '-based mortality projections' : v.replace(/_/g, ' ');
  }
  function mortalityCard(list) {
    var multi = list.length > 1, names = list.map(function (o) { return mortalityName(o.r); }), diff = multi && names[0] !== names[1];
    var rows = list.map(function (o, j) {
      return '<tr' + (diff ? ' style="background:var(--color-warning-soft)"' : '') + '>' + (j === 0 ? '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>Source</th>' : '') +
        (multi ? '<td>' + runLabel(o.k, o.r) + (diff ? ' <span class="tag tag--warn">Differs</span>' : '') + '</td>' : '') + '<td>' + esc(names[j]) + '</td></tr>';
    }).join('');
    return '<div class="card"><div class="table-box"><table class="t"><caption>Mortality</caption><tbody>' + rows + '</tbody></table></div></div>';
  }

  var INFLATION_SOURCES = { UK_CPI: 'UK Consumer Prices Index (CPI)' };
  function inflationRows(r) {
    var src = inputValue(r, 'inflation.source'), per = inputValue(r, 'inflation.source_period'), lm = inputValue(r, 'inflation.log_mean');
    var mean = lm !== null && lm !== '' && isFinite(+lm) ? pctTrim(Math.exp(+lm) - 1) + ' a year' : DASH;
    return [
      ['Source', src ? esc(INFLATION_SOURCES[src] || src.replace(/_/g, ' ')) : DASH],
      ['Years included', per ? esc(per).replace('-', '–') : DASH],
      ['Long-run average', mean]
    ];
  }
  function inflationCard(list) {
    var multi = list.length > 1, all = list.map(function (o) { return inflationRows(o.r); }), body = '';
    all[0].forEach(function (row, i) {
      var diff = multi && all[0][i][1] !== all[1][i][1];
      list.forEach(function (o, j) {
        body += '<tr' + (multi && j === 0 ? ' class="is-group-start"' : '') + (diff ? ' style="background:var(--color-warning-soft)"' : '') + '>' +
          (j === 0 ? '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>' + row[0] + '</th>' : '') +
          (multi ? '<td>' + runLabel(o.k, o.r) + (diff ? ' <span class="tag tag--warn">Differs</span>' : '') + '</td>' : '') +
          '<td>' + all[j][i][1] + '</td></tr>';
      });
    });
    return '<div class="card"><div class="table-box"><table class="t"><caption>Inflation</caption><tbody>' + body + '</tbody></table></div>' +
      '<p class="note" style="margin-top:var(--space-3)">Each simulated future draws its own inflation path around this long-run average.</p></div>';
  }

  function incomeOf(r) {
    var m = {}, ids = [];
    (r.inputs || []).forEach(function (i) {
      var x = /^income\[([^\]]+)\]\.(.+)$/.exec(i.item); if (!x) return;
      if (!m[x[1]]) { m[x[1]] = { _id: x[1] }; ids.push(x[1]); }
      m[x[1]][x[2]] = i.value;
    });
    return ids.map(function (id) { return m[id]; });
  }
  function incomeCells(r, s) {
    var who = s.recipient === 'household' || !s.recipient ? 'Household' : ((r.people || []).filter(function (p) { return p.id === s.recipient; })[0] || { name: s.recipient }).name;
    var amt = s.annual_amount_today !== '' && isFinite(+s.annual_amount_today) ? '£' + (+s.annual_amount_today).toLocaleString('en-GB', { maximumFractionDigits: 2 }) : DASH;
    var sp = s.survivor_percentage !== '' && s.survivor_percentage != null && isFinite(+s.survivor_percentage) ? pctTrim(+s.survivor_percentage) : DASH;
    return '<td>' + esc(who) + '</td><td>' + (s.start_date ? F.month(s.start_date.slice(0, 7)) : DASH) + '</td><td>' + (s.end_date ? F.month(s.end_date.slice(0, 7)) : '<span class="muted">No end</span>') + '</td>' +
      '<td class="num">' + amt + '</td><td>' + (s.inflation_linked === 'true' ? 'Yes' : s.inflation_linked === 'false' ? 'No' : DASH) + '</td><td class="num">' + sp + '</td>';
  }
  function incomeCard(list) {
    var multi = list.length > 1, all = list.map(function (o) { return incomeOf(o.r); }), ids = [], body = '';
    all.forEach(function (a) { a.forEach(function (s) { if (ids.indexOf(s._id) < 0) ids.push(s._id); }); });
    var key = function (q) { return q ? [q.name, q.recipient, q.start_date, q.end_date, q.annual_amount_today, q.inflation_linked, q.survivor_percentage].join('|') : ''; };
    ids.forEach(function (id) {
      var rows = all.map(function (a) { return a.filter(function (s) { return s._id === id; })[0] || null; });
      var diff = multi && key(rows[0]) !== key(rows[1]), first = rows[0] || rows[1];
      list.forEach(function (o, j) {
        body += '<tr' + (multi && j === 0 ? ' class="is-group-start"' : '') + (diff ? ' style="background:var(--color-warning-soft)"' : '') + '>' +
          (j === 0 ? '<th scope="row"' + (multi ? ' rowspan="' + list.length + '"' : '') + '>' + esc(first.name || id) + '</th>' : '') +
          (multi ? '<td>' + runLabel(o.k, o.r) + (diff ? ' <span class="tag tag--warn">Differs</span>' : '') + '</td>' : '') +
          (rows[j] ? incomeCells(o.r, rows[j]) : '<td colspan="6" class="muted">Not in this run</td>') + '</tr>';
      });
    });
    if (!ids.length) body = '<tr><td class="muted">No household income in this run.</td></tr>';
    return '<div class="card"><div class="table-box"><table class="t"><caption>Household income</caption>' + (ids.length ? '<thead><tr><th scope="col">Income</th>' + (multi ? '<th scope="col">Run</th>' : '') +
      '<th scope="col">Paid to</th><th scope="col">From</th><th scope="col">Until</th><th scope="col" class="num">Per year</th><th scope="col">Rises with inflation</th><th scope="col" class="num">After recipient’s death</th></tr></thead>' : '') +
      '<tbody>' + body + '</tbody></table></div>' +
      (ids.length ? '<p class="note" style="margin-top:var(--space-3)">Amounts in today’s money. “Until” is the first month no longer paid.</p>' : '') + '</div>';
  }

  /* ---------------- glossary ---------------- */
  var FILE_TITLES = { 'lifestyle_results.csv': 'Maximum sustainable budget', 'lifestyle_reserve_results.csv': 'Leaving an end-of-life reserve', 'sustainability_results.csv': 'Required return and success at the budget', 'annual_results.csv': 'Year by year', 'inputs.csv': 'Inputs' };
  function renderGlossary() {
    var r = runs()[0].r, cols = r.columns || {};
    var html = '<details class="fold"><summary>Every column, with its unit <span class="muted">from the run’s own column notes</span></summary><div class="fold__body gloss">' +
      Object.keys(cols).map(function (file) {
        return '<div><h3 class="subhead">' + esc(FILE_TITLES[file] || file) + ' <span class="muted small" style="font-family:var(--font-mono);font-weight:var(--weight-regular)">' + esc(file) + '</span></h3><dl>' +
          Object.keys(cols[file]).map(function (k) { var c = cols[file][k]; return '<dt>' + esc(k) + '</dt><dd>' + esc(c.meaning) + ' <span class="u">· ' + esc(c.unit) + '</span></dd>'; }).join('') + '</dl></div>';
      }).join('') + '</div></details>';
    $('#glossary-body').innerHTML = html;
  }

  /* ---------------- tooltips for (i) buttons ---------------- */
  var tipEl = $('#tip');
  function showTip(btn) {
    tipEl.innerHTML = esc(btn.dataset.tip) + (btn.dataset.tipUnit ? '<span class="tip__unit">Unit: ' + esc(btn.dataset.tipUnit) + '</span>' : '');
    tipEl.hidden = false;
    var b = btn.getBoundingClientRect(), t = tipEl.getBoundingClientRect();
    var left = Math.min(Math.max(8, b.left + b.width / 2 - t.width / 2), window.innerWidth - t.width - 8);
    var top = b.top - t.height - 8; if (top < 8) top = b.bottom + 8;
    tipEl.style.left = left + 'px'; tipEl.style.top = top + 'px';
  }
  function hideTip() { tipEl.hidden = true; }
  document.addEventListener('mouseover', function (e) { var b = e.target.closest && e.target.closest('[data-tip]'); if (b) showTip(b); });
  document.addEventListener('mouseout', function (e) { var b = e.target.closest && e.target.closest('[data-tip]'); if (b) hideTip(); });
  document.addEventListener('focusin', function (e) { if (e.target.dataset && e.target.dataset.tip) showTip(e.target); else hideTip(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideTip(); });
  window.addEventListener('scroll', hideTip, { passive: true });

  /* ---------------- theme toggle ---------------- */
  function initTheme() {
    var btn = $('#theme-toggle'), modes = ['auto', 'light', 'dark'], names = { auto: 'Auto', light: 'Light', dark: 'Dark' };
    var cur = document.documentElement.dataset.theme || 'auto';
    function apply() {
      if (cur === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = cur;
      btn.textContent = 'Theme: ' + names[cur];
      btn.setAttribute('aria-label', 'Colour theme: ' + (cur === 'auto' ? 'follows system' : names[cur]) + '. Activate to change.');
      try { if (cur === 'auto') localStorage.removeItem('sbretire-theme'); else localStorage.setItem('sbretire-theme', cur); } catch (e) {}
    }
    btn.addEventListener('click', function () { cur = modes[(modes.indexOf(cur) + 1) % 3]; apply(); });
    apply();
  }

  /* ---------------- years toggle ---------------- */
  $$('[data-years]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.allYears = b.dataset.years === 'all';
      $$('[data-years]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      renderChartShells(); drawFan(); drawSurvival();
    });
  });

  /* ---------------- render ---------------- */
  function setSectionsHidden(h) { $$('main > .section, #about').forEach(function (s) { if (s.id !== 'compare') s.hidden = h; }); }
  function message(title, body) {
    $('#message').innerHTML = '<div class="message"><div class="card"><h2>' + title + '</h2><p class="muted">' + body + '</p></div></div>';
  }
  function render() {
    var bad = runs().filter(function (o) { return String(o.r.schema_version || '').split('.')[0] !== KNOWN_MAJOR; });
    $('#message').innerHTML = '';
    if (bad.length) {
      setSectionsHidden(true); $('#compare').hidden = true; $('#run-meta').innerHTML = '';
      message('This run uses a newer results format', 'The run “' + esc(bad[0].r.run && bad[0].r.run.name) + '” was saved with results format ' + esc(bad[0].r.schema_version) + '; this page reads format ' + KNOWN_MAJOR + '.x. Update the viewer to read it.');
      return;
    }
    setSectionsHidden(false);
    renderMeta(); renderCompare(); renderHeadline(); renderBudgets(); renderReturns(); renderChartShells(); renderYears(); renderInputs(); renderGlossary();
    drawCharts();
  }

  function init() {
    initTheme();
    var entries = DATA && DATA.runs ? indexEntries() : [];
    if (!entries.length) {
      setSectionsHidden(true);
      message('No named runs yet', 'Run <code>sbretire run --config … --name &lt;name&gt;</code>, then open this page again.');
      return;
    }
    var h = readHash(), names = entries.map(function (e) { return e.name; });
    state.a = names.indexOf(h.run) >= 0 ? h.run : names[0];
    state.b = h.compare && h.compare !== state.a && names.indexOf(h.compare) >= 0 ? h.compare : null;
    buildPickers(); syncPickers(); render();
    var lastW = window.innerWidth, t;
    window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(function () { if (window.innerWidth !== lastW) { lastW = window.innerWidth; drawCharts(); } }, 120); });
    window.addEventListener('beforeprint', function () { var d = $('#years-fold'); if (d) d.open = true; });
  }
  init();
})();
