/* SBRetire portfolio page (F-030). Reads window.SBRETIRE_PORTFOLIO (portfolio/portfolio.js, schema 1.x).
   Every data string goes through esc(); colours come only from theme tokens via CSS classes. */
(function () {
  'use strict';
  var DATA = window.SBRETIRE_PORTFOLIO || null;
  var KNOWN_MAJOR = '1';
  var MINUS = '−', DASH = '—';

  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }
  function signed(text, x) { return (x < 0 ? MINUS : '') + text; }
  var F = {
    gbp: function (x) { return isNum(x) ? signed('£' + Math.round(Math.abs(x)).toLocaleString('en-GB'), Math.round(x)) : DASH; },
    gbpK: function (x) { return isNum(x) ? signed('£' + (Math.abs(x) >= 1e6 ? (Math.abs(x) / 1e6).toFixed(2) + 'm' : Math.round(Math.abs(x) / 1000) + 'k'), x) : DASH; },
    trade: function (x) { return isNum(x) ? (x > 0 ? '+' : x < 0 ? MINUS : '') + '£' + Math.round(Math.abs(x)).toLocaleString('en-GB') : DASH; },
    w: function (x) { return isNum(x) ? signed((Math.abs(x) * 100).toFixed(1) + '%', x) : DASH; },
    r: function (x) { return isNum(x) ? signed((Math.abs(x) * 100).toFixed(2) + '%', x) : DASH; },
    s: function (x) { return isNum(x) ? signed(Math.abs(x).toFixed(2), x) : DASH; },
    dd: function (x) { return isNum(x) ? (x > 0 ? MINUS : '') + (Math.abs(x) * 100).toFixed(1) + '%' : DASH; },
    month: function (ym) {
      if (!ym) return DASH;
      var p = String(ym).split('-'), d = new Date(Date.UTC(+p[0], +p[1] - 1, 1));
      return isNaN(d) ? esc(ym) : d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    },
    date: function (iso) {
      var d = new Date(String(iso) + 'T00:00:00Z');
      return isNaN(d) ? esc(iso) : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
    }
  };
  var LABELS = { asset_class: 'Asset class', sector: 'Sector (look-through)', region: 'Region (look-through)', currency: 'Currency' };
  var WRAPPERS = { isa: 'ISA', sipp: 'SIPP', pension: 'Pension', taxable: 'Taxable' };

  function seriesName(id) {
    var f = DATA.frontier && DATA.frontier.names; return esc((f && f[id]) || id);
  }
  function unavailable(section, what) {
    return '<div class="card unavailable"><p><strong>' + esc(what) + ' is not available yet.</strong></p><p class="note">' +
      esc(section && section.reason ? section.reason : 'The analysis did not run.') + '</p></div>';
  }
  function body(id, html) { $('#' + id + '-body').innerHTML = html; }
  function card(html, extra) { return '<div class="card' + (extra ? ' ' + extra : '') + '">' + html + '</div>'; }
  function table(head, rows, cls) {
    return '<div class="table-box"><table class="t' + (cls ? ' ' + cls : '') + '"><thead><tr>' + head.map(function (h) {
      return '<th scope="col"' + (h.num ? ' class="num"' : '') + '>' + h.label + '</th>';
    }).join('') + '</tr></thead><tbody>' + rows.join('') + '</tbody></table></div>';
  }
  function td(v, num) { return '<td' + (num ? ' class="num"' : '') + '>' + v + '</td>'; }
  function hbars(rows, opts) {
    var max = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.share); }).concat([1e-9]));
    return '<div class="hbars">' + rows.map(function (r) {
      var muted = r.label === 'Unclassified' || r.label === 'Cash';
      return '<div class="hbar"><span class="hbar__label">' + esc(r.label) + '</span><span class="hbar__track"><span class="hbar__fill' +
        (muted ? ' hbar__fill--muted' : '') + '" style="width:' + (Math.abs(r.share) / max * 100).toFixed(2) + '%"></span></span>' +
        '<span class="hbar__value">' + (opts && opts.gbp ? F.gbpK(r.value) : F.w(r.share)) + '</span></div>';
    }).join('') + '</div>';
  }

  /* ---------------- chart primitives ---------------- */
  function scale(d0, d1, r0, r1) { var k = (r1 - r0) / ((d1 - d0) || 1); return function (v) { return r0 + (v - d0) * k; }; }
  function ticks(min, max, count) {
    var span = max - min || Math.abs(max) || 1, step0 = span / count, mag = Math.pow(10, Math.floor(Math.log10(step0))), e = step0 / mag;
    var step = (e >= 7.5 ? 10 : e >= 3.5 ? 5 : e >= 1.5 ? 2 : 1) * mag, out = [];
    for (var v = Math.ceil(min / step) * step; v <= max + step * 1e-6; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function svgOpen(w, h, label) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '" role="img" aria-label="' + esc(label) + '">'; }
  function txt(x, y, s, cls, anchor) { return '<text x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" class="' + (cls || 'lbl') + '"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + '>' + esc(s) + '</text>'; }
  function width(el) { return Math.max(320, Math.min(el.clientWidth || 720, 1100)); }
  function axes(X, Y, xs, ys, P, w, h, fx, fy) {
    var g = '<g class="ax">';
    ys.forEach(function (v) { g += '<line class="gridline" x1="' + P.l + '" x2="' + (w - P.r) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"></line>' + txt(P.l - 6, Y(v) + 4, fy(v), 'lbl', 'end'); });
    xs.forEach(function (v) { g += txt(X(v), h - P.b + 18, fx(v), 'lbl', 'middle'); });
    return g + '</g>';
  }
  function path(points) { return points.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(''); }

  /* ---------------- headline ---------------- */
  function renderHeadline() {
    var t = DATA.total, perf = DATA.performance, m = perf && perf.available ? perf.metrics : null;
    var owners = Object.keys(t.by_owner || {});
    var figs = '<div class="figs"><div class="fig-block"><span class="hl__eyebrow">Household total</span><span class="hl__figure">' + F.gbp(t.value_gbp) + '</span>' +
      '<span class="hl__se">of which cash ' + F.gbp(t.cash_gbp) + '</span></div>' +
      owners.map(function (o) { return '<div class="fig-block"><span class="hl__eyebrow">' + esc(o) + '</span><span class="hl__figure hl__figure--sm">' + F.gbp(t.by_owner[o]) + '</span></div>'; }).join('') + '</div>';
    var stats = m ? '<p class="hl__secondary">Back-test of today’s mix over ' + esc(m.months) + ' months: annual return <strong>' + F.r(m.annual_return) +
      '</strong>, volatility <strong>' + F.r(m.annual_volatility) + '</strong>, Sharpe ratio <strong>' + F.s(m.sharpe) + '</strong>, worst fall <strong>' + F.dd(m.max_drawdown) + '</strong>.</p>' : '';
    var paste = '<div class="paste"><span class="note">Paste into <code>config/model.yaml</code> under <code>portfolio:</code></span><code id="yaml-line">' + esc(t.starting_balance_yaml) +
      '</code><button id="copy-yaml" class="btn btn--quiet" type="button">Copy</button></div>';
    var rows = DATA.accounts.map(function (a) {
      return '<tr><th scope="row">' + esc(a.name) + '<span class="sub">' + esc(WRAPPERS[a.wrapper] || a.wrapper) + ' · ' + esc(a.provider) + ' · ' + esc(a.owner) + '</span></th>' +
        td(F.gbp(a.securities_gbp), 1) + td(F.gbp(a.cash_gbp), 1) + td('<span class="big">' + F.gbp(a.value_gbp) + '</span>', 1) +
        td(F.w(a.value_gbp / t.value_gbp), 1) + td(F.date(a.valuation_date) + (a.date_assumed ? ' <span class="tag tag--warn">assumed</span>' : '')) + '</tr>';
    });
    body('headline', card('<div class="hl">' + figs + stats + paste + '</div>') + card(table([
      { label: 'Account' }, { label: 'Investments', num: 1 }, { label: 'Cash', num: 1 }, { label: 'Total', num: 1 }, { label: 'Share', num: 1 }, { label: 'Valued on' }
    ], rows)));
    var btn = $('#copy-yaml');
    btn.addEventListener('click', function () {
      var text = t.starting_balance_yaml, done = function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy'; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
      else { var r = document.createRange(); r.selectNodeContents($('#yaml-line')); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }
    });
  }

  /* ---------------- allocation ---------------- */
  function renderAllocation() {
    var t = DATA.total.value_gbp;
    var byAccount = card('<h3 class="subhead">By account</h3>' + hbars(DATA.accounts.map(function (a) { return { label: a.name, share: a.value_gbp / t, value: a.value_gbp }; }), { gbp: true }));
    var ex = DATA.exposure;
    if (!ex.available) { body('allocation', byAccount + unavailable(ex, 'The look-through')); return; }
    var dims = ['asset_class', 'region', 'sector', 'currency'].map(function (d) {
      var rows = ex.tables[d].map(function (r) { return { label: r.label, share: r.share, value: r.value_gbp }; });
      var note = d === 'currency' && ex.approximated_currency_share > 0.0005 ? '<p class="note" style="margin-top:var(--space-3)">' + F.w(ex.approximated_currency_share) + ' of the currency split is taken from regions where a fund gives no currencies.</p>' : '';
      return card('<h3 class="subhead">' + LABELS[d] + '</h3>' + hbars(rows) + note);
    }).join('');
    var top = ex.top_holdings.length ? card('<h3 class="subhead">Largest underlying holdings</h3><p class="note" style="margin-bottom:var(--space-3)">Single stocks plus the largest holdings funds publish; funds list only their biggest positions, so this understates spread-out exposure.</p>' +
      table([{ label: 'Holding' }, { label: 'Value', num: 1 }, { label: 'Share', num: 1 }], ex.top_holdings.map(function (h) { return '<tr><th scope="row">' + esc(h.name) + '</th>' + td(F.gbp(h.value_gbp), 1) + td(F.w(h.share), 1) + '</tr>'; })))
      : '';
    body('allocation', byAccount + '<div class="grid-3" style="margin-top:var(--space-4)">' + dims + '</div>' + top);
  }

  /* ---------------- frontier ---------------- */
  var MIXES = [
    { key: 'today', label: 'Today', cls: 'fr-today', shape: 'square' },
    { key: 'min_variance', label: 'Minimum variance', cls: 'fr-minvar', shape: 'triangle' },
    { key: 'max_sharpe', label: 'Maximum Sharpe', cls: 'fr-sharpe', shape: 'diamond' },
    { key: 'target', label: 'Target', cls: 'fr-target', shape: 'circle' }
  ];
  function shape(kind, x, y, cls, s) {
    s = s || 6;
    if (kind === 'square') return '<rect x="' + (x - s) + '" y="' + (y - s) + '" width="' + 2 * s + '" height="' + 2 * s + '" class="' + cls + '"></rect>';
    if (kind === 'triangle') return '<path d="M' + x + ' ' + (y - s - 1) + 'L' + (x + s + 1) + ' ' + (y + s) + 'L' + (x - s - 1) + ' ' + (y + s) + 'Z" class="' + cls + '"></path>';
    if (kind === 'diamond') return '<path d="M' + x + ' ' + (y - s - 2) + 'L' + (x + s + 2) + ' ' + y + 'L' + x + ' ' + (y + s + 2) + 'L' + (x - s - 2) + ' ' + y + 'Z" class="' + cls + '"></path>';
    return '<circle cx="' + x + '" cy="' + y + '" r="' + (s + 1) + '" class="' + cls + '"></circle>';
  }
  function legendShape(kind, cls) { return '<svg viewBox="0 0 20 16" width="20" height="16" aria-hidden="true">' + shape(kind, 10, 8, cls, 5) + '</svg>'; }
  function weightsTitle(weights) {
    return Object.keys(weights).filter(function (k) { return weights[k] > 0.0005; }).sort(function (a, b) { return weights[b] - weights[a]; })
      .map(function (k) { return (DATA.frontier.names[k] || k) + ' ' + (weights[k] * 100).toFixed(1) + '%'; }).join(', ');
  }
  function drawFrontier() {
    var fr = DATA.frontier, el = $('#frontier-chart'); if (!el) return;
    var w = width(el), h = Math.round(Math.min(460, w * 0.62)), P = { l: 56, r: 24, t: 16, b: 44 };
    var pts = fr.points.concat(fr.holdings_points, MIXES.map(function (m) { return fr.mixes[m.key]; }));
    var vx = pts.map(function (p) { return p.volatility; }), vy = pts.map(function (p) { return p.return; }).concat([fr.risk_free]);
    var x1 = Math.max.apply(null, vx) * 1.08, y0 = Math.min(0, Math.min.apply(null, vy)), y1 = Math.max.apply(null, vy) * 1.08 || 0.01;
    var X = scale(0, x1, P.l, w - P.r), Y = scale(y0, y1, h - P.b, P.t);
    var g = svgOpen(w, h, 'Efficient frontier: annual return against volatility') + axes(X, Y, ticks(0, x1, 5), ticks(y0, y1, 5), P, w, h, function (v) { return (v * 100).toFixed(0) + '%'; }, function (v) { return (v * 100).toFixed(0) + '%'; });
    g += txt(w - P.r, h - 6, 'Volatility (a year)', 'lbl', 'end') + txt(P.l, P.t - 4 > 8 ? P.t - 4 : 10, 'Annual return', 'lbl');
    var best = fr.mixes.max_sharpe, slope = best.volatility > 0 ? (best.return - fr.risk_free) / best.volatility : 0;
    var xEnd = slope > 0 && fr.risk_free + slope * x1 > y1 ? (y1 - fr.risk_free) / slope : x1;  // stay inside the plot
    g += '<path class="fr-cml" d="' + path([[X(0), Y(fr.risk_free)], [X(xEnd), Y(fr.risk_free + slope * xEnd)]]) + '"><title>Capital market line from the risk-free rate through the maximum-Sharpe mix</title></path>';
    g += '<path class="fr-curve" d="' + path(fr.points.map(function (p) { return [X(p.volatility), Y(p.return)]; })) + '"><title>Efficient frontier</title></path>';
    fr.holdings_points.forEach(function (p) {
      g += '<g><circle cx="' + X(p.volatility).toFixed(1) + '" cy="' + Y(p.return).toFixed(1) + '" r="4" class="fr-dot"></circle>' +
        (X(p.volatility) > w * 0.7 ? txt(X(p.volatility) - 7, Y(p.return) + 4, fr.names[p.series] || p.series, 'lbl', 'end') : txt(X(p.volatility) + 7, Y(p.return) + 4, fr.names[p.series] || p.series, 'lbl')) + '<title>' + esc((fr.names[p.series] || p.series) + ' alone: return ' + (p.return * 100).toFixed(2) + '%, volatility ' + (p.volatility * 100).toFixed(2) + '%') + '</title></g>';
    });
    MIXES.forEach(function (m) {
      var p = fr.mixes[m.key];
      g += '<g tabindex="0">' + shape(m.shape, +X(p.volatility).toFixed(1), +Y(p.return).toFixed(1), m.cls) + '<title>' + esc(m.label + ': return ' + (p.return * 100).toFixed(2) + '%, volatility ' + (p.volatility * 100).toFixed(2) + '%. ' + weightsTitle(p.weights)) + '</title></g>';
    });
    el.querySelector('.chart-svg').innerHTML = g + '</svg>';
  }
  function renderFrontier() {
    var fr = DATA.frontier;
    if (!fr.available) { body('frontier', unavailable(fr, 'The efficient frontier')); return; }
    var legend = '<div class="chart-legend">' + MIXES.map(function (m) { return '<span class="legend__item">' + legendShape(m.shape, m.cls) + esc(m.label) + '</span>'; }).join('') +
      '<span class="legend__item"><svg viewBox="0 0 20 16" width="20" height="16" aria-hidden="true"><circle cx="10" cy="8" r="4" class="fr-dot"></circle></svg>Each holding alone</span></div>';
    var rows = MIXES.concat([{ key: 'within_accounts', label: 'Within accounts only' }]).map(function (m) {
      var p = fr.mixes[m.key];
      return '<tr><th scope="row">' + esc(m.label) + '</th>' + td(F.r(p.return), 1) + td(F.r(p.volatility), 1) + td(F.s(p.sharpe), 1) + '</tr>';
    });
    var caption = 'Built from the last ' + esc(DATA.settings.months) + ' months of monthly returns of the holdings with a full price history (' + F.w(fr.sleeve_share) +
      ' of today’s value); each capped at ' + F.w(fr.max_weight) + '. Risk uses a ' + (fr.covariance === 'shrunk' ? 'Ledoit–Wolf shrunk' : 'sample') + ' covariance. Past patterns, not a forecast. The dashed line runs from the risk-free rate through the maximum-Sharpe mix.';
    body('frontier', card(legend + '<figure class="chart" id="frontier-chart"><div class="chart-svg"></div><figcaption>' + caption + '</figcaption></figure>' +
      '<div style="margin-top:var(--space-4)">' + table([{ label: 'Mix' }, { label: 'Annual return', num: 1 }, { label: 'Volatility', num: 1 }, { label: 'Sharpe ratio', num: 1 }], rows) + '</div>'));
  }

  /* ---------------- re-weighting ---------------- */
  function drawDumbbell() {
    var fr = DATA.frontier, el = $('#dumbbell'); if (!el) return;
    var w = width(el), lane = 26, P = { l: Math.min(220, w * 0.38), r: 56, t: 10, b: 30 }, ids = fr.series.slice();
    var today = fr.mixes.today.weights, target = fr.mixes.target.weights;
    ids.sort(function (a, b) { return (target[b] - today[b]) - (target[a] - today[a]); });
    var h = P.t + ids.length * lane + P.b, mx = Math.max.apply(null, ids.map(function (k) { return Math.max(today[k], target[k]); }).concat([0.05]));
    var X = scale(0, mx * 1.05, P.l, w - P.r), g = svgOpen(w, h, 'Weight today and in the target mix, by holding');
    ticks(0, mx * 1.05, 4).forEach(function (v) { g += '<line class="gridline" x1="' + X(v).toFixed(1) + '" x2="' + X(v).toFixed(1) + '" y1="' + P.t + '" y2="' + (h - P.b) + '"></line>' + txt(X(v), h - P.b + 18, (v * 100).toFixed(0) + '%', 'lbl', 'middle'); });
    ids.forEach(function (k, i) {
      var y = P.t + i * lane + lane / 2;
      g += txt(P.l - 8, y + 4, fr.names[k] || k, 'lbl', 'end') + '<line class="db-line" x1="' + X(today[k]).toFixed(1) + '" x2="' + X(target[k]).toFixed(1) + '" y1="' + y + '" y2="' + y + '"></line>' +
        '<circle class="db-from" cx="' + X(today[k]).toFixed(1) + '" cy="' + y + '" r="5"><title>' + esc((fr.names[k] || k) + ' today ' + (today[k] * 100).toFixed(1) + '%') + '</title></circle>' +
        '<circle class="db-to" cx="' + X(target[k]).toFixed(1) + '" cy="' + y + '" r="5"><title>' + esc((fr.names[k] || k) + ' target ' + (target[k] * 100).toFixed(1) + '%') + '</title></circle>';
    });
    el.querySelector('.chart-svg').innerHTML = g + '</svg>';
  }
  function renderRebalance() {
    var rb = DATA.rebalance, fr = DATA.frontier;
    if (!rb.available) { body('rebalance', unavailable(rb, 'The re-weighting analysis')); return; }
    var kind = { 'same-risk': 'the mix with today’s volatility and the highest past return', 'max-sharpe': 'the maximum-Sharpe mix', 'min-variance': 'the minimum-variance mix' }[rb.target_kind] || 'the target mix';
    var t = fr.mixes.today, g = fr.mixes.target, wi = fr.mixes.within_accounts;
    var change = '<p class="hl__secondary">The model’s target is ' + kind + '. Against today, it would have changed the annual return by <strong>' + F.r(g.return - t.return) +
      '</strong>, volatility by <strong>' + F.r(g.volatility - t.volatility) + '</strong> and the Sharpe ratio by <strong>' + (isNum(g.sharpe) && isNum(t.sharpe) ? F.s(g.sharpe - t.sharpe) : DASH) + '</strong>. ' +
      'Trading only within each account would reach a Sharpe ratio of <strong>' + F.s(wi.sharpe) + '</strong>. Estimated on each half of the window, the target differs by a turnover of <strong>' + F.w(fr.turnover) + '</strong>: the higher this is, the less the target can be relied on.</p>';
    var legend = '<div class="chart-legend"><span class="legend__item"><svg viewBox="0 0 20 16" width="20" height="16" aria-hidden="true"><circle cx="10" cy="8" r="5" class="db-from"></circle></svg>Today</span>' +
      '<span class="legend__item"><svg viewBox="0 0 20 16" width="20" height="16" aria-hidden="true"><circle cx="10" cy="8" r="5" class="db-to"></circle></svg>Target</span></div>';
    var within = rb.within.length ? table([{ label: 'Account' }, { label: 'Holding' }, { label: 'Now', num: 1 }, { label: 'Target', num: 1 }, { label: 'Trade', num: 1 }, { label: 'Est. cost', num: 1 }],
      rb.within.map(function (x) { return '<tr><th scope="row">' + esc(x.account) + '</th>' + td(seriesName(x.series)) + td(F.gbp(x.current_gbp), 1) + td(F.gbp(x.target_gbp), 1) + td(F.trade(x.trade_gbp), 1) + td(F.gbp(x.cost_gbp), 1) + '</tr>'; }))
      + '<p class="note" style="margin-top:var(--space-3)">Estimated dealing costs in total: <strong>' + F.gbp(rb.total_cost_gbp) + '</strong>. Trades under ' + F.gbp(rb.min_trade_gbp) + ' are left out.</p>'
      : '<p class="note">No change within accounts: each account holds one priced holding, or every move is under ' + F.gbp(rb.min_trade_gbp) + '.</p>';
    var household = table([{ label: 'Holding' }, { label: 'Now', num: 1 }, { label: 'Target', num: 1 }, { label: 'Change', num: 1 }],
      rb.household.map(function (x) { return '<tr><th scope="row">' + seriesName(x.series) + '</th>' + td(F.gbp(x.current_gbp), 1) + td(F.gbp(x.target_gbp), 1) + td(F.trade(x.trade_gbp), 1) + '</tr>'; }));
    body('rebalance', card(change + legend + '<figure class="chart" id="dumbbell"><div class="chart-svg"></div><figcaption>Each holding’s share of the priced holdings today (hollow) and in the target mix (filled), largest increase first.</figcaption></figure>') +
      '<div class="grid-2" style="margin-top:var(--space-4)">' + card('<h3 class="subhead">Within each account</h3><p class="note" style="margin-bottom:var(--space-3)">Re-splitting each account’s money over the holdings it already has; nothing moves between accounts.</p>' + within) +
      card('<h3 class="subhead">The household as one portfolio</h3><p class="note" style="margin-bottom:var(--space-3)"><strong>Illustrative only:</strong> these moves cannot be made as shown, because money cannot move from a pension or SIPP to an ISA or taxable account.</p>' + household) + '</div>');
  }

  /* ---------------- performance ---------------- */
  function lineChart(el, series, months, opts) {
    var w = width(el), h = opts.height || 240, P = { l: 56, r: 20, t: 12, b: 32 }, n = months.length;
    var vals = []; series.forEach(function (s) { s.values.forEach(function (v) { if (isNum(v)) vals.push(v); }); });
    if (opts.zero) vals.push(0);
    var y0 = Math.min.apply(null, vals), y1 = Math.max.apply(null, vals); if (y0 === y1) { y0 -= 0.01; y1 += 0.01; }
    var X = scale(0, Math.max(1, n - 1), P.l, w - P.r), Y = scale(y0, y1, h - P.b, P.t);
    var xt = []; for (var i = 0; i < n; i += Math.max(1, Math.round(n / 6))) xt.push(i);
    var g = svgOpen(w, h, opts.label) + axes(X, Y, xt, ticks(y0, y1, Math.max(2, Math.round(h / 60))), P, w, h, function (i) { return F.month(months[i]); }, opts.fy);
    if (opts.zero) g += '<line class="zeroline" x1="' + P.l + '" x2="' + (w - P.r) + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"></line>';
    series.forEach(function (s) {
      var pts = []; s.values.forEach(function (v, i) { if (isNum(v)) pts.push([X(i), Y(v)]); });
      if (!pts.length) return;
      if (s.area) g += '<path class="pf-area" d="' + path(pts) + 'L' + pts[pts.length - 1][0].toFixed(1) + ' ' + Y(0).toFixed(1) + 'L' + pts[0][0].toFixed(1) + ' ' + Y(0).toFixed(1) + 'Z"></path>';
      else g += '<path class="' + s.cls + '" d="' + path(pts) + '"></path>';
    });
    el.querySelector('.chart-svg').innerHTML = g + '</svg>';
  }
  function drawPerformance() {
    var pf = DATA.performance; if (!pf.available) return;
    var months = pf.months.map(function (m) { return m.month; });
    var wealth = [1].concat(pf.months.map(function (m) { return m.wealth; })), wm = [null].concat(months);
    if ($('#growth')) lineChart($('#growth'), [{ values: wealth, cls: 'pf-line' }], wm.map(function (m, i) { return m || months[0]; }), { label: 'Growth of £1 invested in today’s mix', fy: function (v) { return '£' + v.toFixed(2); } });
    if ($('#underwater')) lineChart($('#underwater'), [{ values: pf.months.map(function (m) { return -m.drawdown; }), area: true }], months, { label: 'Fall below the previous high', height: 150, zero: true, fy: function (v) { return F.dd(-v); } });
    if ($('#rolling')) lineChart($('#rolling'), [{ values: pf.months.map(function (m) { return m.rolling_12m_return; }), cls: 'pf-line' }, { values: pf.months.map(function (m) { return m.rolling_12m_volatility; }), cls: 'pf-line pf-line--b' }],
      months, { label: 'Rolling twelve-month return and volatility', zero: true, fy: function (v) { return (v * 100).toFixed(0) + '%'; } });
  }
  function heatClass(v, scaleTo) {
    if (!isNum(v) || v === 0) return '';
    var k = Math.min(3, Math.ceil(Math.abs(v) / scaleTo * 3));
    return (v > 0 ? 'h-p' : 'h-n') + k;
  }
  function renderPerformance() {
    var pf = DATA.performance;
    if (!pf.available) { body('performance', unavailable(pf, 'The back-test')); return; }
    var m = pf.metrics;
    var figs = '<div class="figs">' + [['Annual return', F.r(m.annual_return)], ['Volatility', F.r(m.annual_volatility)], ['Sharpe ratio', F.s(m.sharpe)], ['Worst fall', F.dd(m.max_drawdown)]].map(function (f) {
      return '<div class="fig-block"><span class="hl__eyebrow">' + f[0] + '</span><span class="hl__figure hl__figure--sm">' + f[1] + '</span></div>';
    }).join('') + '</div>';
    var covered = pf.months.map(function (x) { return x.covered; }), avg = covered.reduce(function (a, b) { return a + b; }, 0) / (covered.length || 1);
    var note = '<p class="note" style="margin-top:var(--space-3)">' + esc(m.months) + ' months. On average ' + F.w(avg) + ' of today’s value had a return each month; the rest (holdings without prices) is left out and the weights rescaled.' +
      (m.max_drawdown > 0 ? ' The worst fall ran from ' + F.month(m.peak) + ' to ' + F.month(m.trough) + (m.recovery ? ' and was regained by ' + F.month(m.recovery) + '.' : ' and has not yet been regained.') : '') + '</p>';
    var calMax = 0.0001; pf.calendar.forEach(function (y) { y.months.forEach(function (v) { if (isNum(v)) calMax = Math.max(calMax, Math.abs(v)); }); });
    var names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var cal = '<div class="table-box"><table class="heat"><caption class="visually-hidden">Monthly returns by year</caption><thead><tr><th scope="col">Year</th>' + names.map(function (n) { return '<th scope="col">' + n + '</th>'; }).join('') + '<th scope="col">Year</th></tr></thead><tbody>' +
      pf.calendar.map(function (y) { return '<tr><th scope="row">' + esc(y.year) + '</th>' + y.months.map(function (v) { return '<td class="' + heatClass(v, calMax) + '">' + (isNum(v) ? F.r(v) : '') + '</td>'; }).join('') + '<td><strong>' + F.r(y.total) + '</strong></td></tr>'; }).join('') + '</tbody></table></div>';
    var dds = pf.drawdowns.length ? table([{ label: 'Fall' }, { label: 'From' }, { label: 'Low' }, { label: 'Regained' }, { label: 'Months down', num: 1 }, { label: 'Months to regain', num: 1 }],
      pf.drawdowns.map(function (d) { return '<tr><th scope="row">' + F.dd(d.depth) + '</th>' + td(d.peak ? F.month(d.peak) : 'start') + td(F.month(d.trough)) + td(d.recovery ? F.month(d.recovery) : 'not yet') + td(esc(d.months_to_trough), 1) + td(d.months_to_recover == null ? DASH : esc(d.months_to_recover), 1) + '</tr>'; }))
      : '<p class="note">No fall below a previous high in the window.</p>';
    var series = table([{ label: 'Holding' }, { label: 'Weight', num: 1 }, { label: 'Months', num: 1 }, { label: 'Annual return', num: 1 }, { label: 'Volatility', num: 1 }, { label: 'Sharpe ratio', num: 1 }, { label: 'Worst fall', num: 1 }],
      pf.series.map(function (s) { return '<tr><th scope="row">' + esc(s.name) + '</th>' + td(F.w(s.weight), 1) + td(esc(s.months), 1) + td(F.r(s.annual_return), 1) + td(F.r(s.annual_volatility), 1) + td(F.s(s.sharpe), 1) + td(F.dd(s.max_drawdown), 1) + '</tr>'; }));
    body('performance', card(figs + note) +
      card('<figure class="chart" id="growth"><div class="chart-svg"></div><figcaption>Growth of £1 invested in today’s mix at the start of the window.</figcaption></figure><figure class="chart" id="underwater" style="margin-top:var(--space-4)"><div class="chart-svg"></div><figcaption>How far the mix stood below its previous high each month.</figcaption></figure>') +
      card('<h3 class="subhead">Monthly returns</h3>' + cal + '<p class="note" style="margin-top:var(--space-3)">Rises shaded, falls shaded in italics; the figure is always shown.</p>') +
      '<div class="grid-2" style="margin-top:var(--space-4)">' +
      card('<h3 class="subhead">Rolling twelve months</h3><div class="chart-legend"><span class="legend__item"><svg viewBox="0 0 28 14" width="28" height="14" aria-hidden="true"><line x1="2" x2="26" y1="7" y2="7" class="pf-line"></line></svg>Return</span><span class="legend__item"><svg viewBox="0 0 28 14" width="28" height="14" aria-hidden="true"><line x1="2" x2="26" y1="7" y2="7" class="pf-line pf-line--b"></line></svg>Volatility</span></div><figure class="chart" id="rolling"><div class="chart-svg"></div><figcaption>Each point covers the twelve months up to it; empty until twelve months have passed.</figcaption></figure>') +
      card('<h3 class="subhead">Worst falls</h3>' + dds) + '</div>' + card('<h3 class="subhead">Each priced holding</h3>' + series));
  }

  /* ---------------- risk ---------------- */
  function renderRisk() {
    var rk = DATA.risk;
    if (!rk.available) { body('risk', unavailable(rk, 'The risk breakdown')); return; }
    var ids = rk.series, short = function (k) { return seriesName(k); };
    var heat = '<div class="table-box"><table class="heat"><caption class="visually-hidden">Correlation of monthly returns</caption><thead><tr><th scope="col"></th>' + ids.map(function (k) { return '<th scope="col">' + short(k) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      ids.map(function (k, i) { return '<tr><th scope="row">' + short(k) + '</th>' + rk.correlation[i].map(function (v, j) { return '<td class="' + (i === j ? '' : heatClass(v, 1)) + '">' + F.s(v) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
    var bars = '<div class="hbars">' + rk.contribution.map(function (c) {
      var mx = Math.max.apply(null, rk.contribution.map(function (x) { return Math.max(x.weight, x.risk_share); }).concat([1e-9]));
      return '<div class="hbar hbar--pair"><span class="hbar__label">' + short(c.series) + '</span><span><span class="hbar__track" style="display:block"><span class="hbar__fill" style="display:block;width:' + (c.weight / mx * 100).toFixed(2) + '%"></span></span>' +
        '<span class="hbar__track" style="display:block"><span class="hbar__fill hbar__fill--b" style="display:block;width:' + (Math.max(0, c.risk_share) / mx * 100).toFixed(2) + '%"></span></span></span><span class="hbar__value">' + F.w(c.weight) + '<br>' + F.w(c.risk_share) + '</span></div>';
    }).join('') + '</div>';
    body('risk', '<div class="grid-2">' + card('<h3 class="subhead">How the holdings move together</h3>' + heat + '<p class="note" style="margin-top:var(--space-3)">Correlation of monthly returns: 1 moves together, 0 unrelated, negative moves opposite (italic).</p>') +
      card('<h3 class="subhead">Weight and share of the ups and downs</h3><div class="chart-legend"><span class="legend__item"><span class="swatch" style="background:var(--chart-run-a)"></span>Weight</span><span class="legend__item"><span class="swatch" style="background:var(--chart-run-b)"></span>Share of volatility</span></div>' + bars +
        '<p class="note" style="margin-top:var(--space-3)">A holding whose share of volatility is well above its weight drives more of the swings than its size suggests.</p>') + '</div>');
  }

  /* ---------------- income and fees ---------------- */
  function drawIncome() {
    var inc = DATA.income, el = $('#income-chart'); if (!el || !inc.available) return;
    var w = width(el), h = 220, P = { l: 56, r: 16, t: 12, b: 32 }, n = inc.months.length;
    var up = inc.months.map(function (m) { return m.dividends_gbp + m.interest_gbp; }), down = inc.months.map(function (m) { return m.fees_gbp + m.tax_withheld_gbp; });
    var y1 = Math.max.apply(null, up.concat([1])), y0 = Math.min.apply(null, down.concat([0]));
    var X = scale(0, n, P.l, w - P.r), Y = scale(y0, y1, h - P.b, P.t), bw = (w - P.l - P.r) / n;
    var xt = []; for (var i = 0; i < n; i += 2) xt.push(i + 0.5);
    var g = svgOpen(w, h, 'Income and fees by month') + axes(X, Y, xt, ticks(y0, y1, 4), P, w, h, function (v) { return F.month(inc.months[Math.floor(v)].month); }, function (v) { return y1 - y0 < 5000 ? F.gbp(v) : F.gbpK(v); });
    g += '<line class="zeroline" x1="' + P.l + '" x2="' + (w - P.r) + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"></line>';
    inc.months.forEach(function (m, i) {
      var x = X(i) + bw * 0.15, bwid = bw * 0.34;
      var div = m.dividends_gbp, intr = m.interest_gbp, cost = m.fees_gbp + m.tax_withheld_gbp;
      g += '<rect class="pf-bar-up" x="' + x.toFixed(1) + '" width="' + bwid.toFixed(1) + '" y="' + Y(Math.max(div, 0)).toFixed(1) + '" height="' + Math.abs(Y(0) - Y(div)).toFixed(1) + '"><title>' + esc(F.month(m.month) + ' dividends ' + F.gbp(div)) + '</title></rect>';
      g += '<rect class="pf-bar-alt" x="' + (x + bwid).toFixed(1) + '" width="' + bwid.toFixed(1) + '" y="' + Y(Math.max(intr, 0)).toFixed(1) + '" height="' + Math.abs(Y(0) - Y(intr)).toFixed(1) + '"><title>' + esc(F.month(m.month) + ' interest ' + F.gbp(intr)) + '</title></rect>';
      g += '<rect class="pf-bar-down" x="' + x.toFixed(1) + '" width="' + (2 * bwid).toFixed(1) + '" y="' + Y(0).toFixed(1) + '" height="' + Math.abs(Y(cost) - Y(0)).toFixed(1) + '"><title>' + esc(F.month(m.month) + ' fees and tax withheld ' + F.gbp(cost)) + '</title></rect>';
    });
    el.querySelector('.chart-svg').innerHTML = g + '</svg>';
  }
  function renderIncome() {
    var inc = DATA.income;
    if (!inc.available) { body('income', unavailable(inc, 'Income and fees')); return; }
    var t = inc.totals;
    var legend = '<div class="chart-legend"><span class="legend__item"><span class="swatch" style="background:var(--chart-run-a)"></span>Dividends</span><span class="legend__item"><span class="swatch" style="background:var(--chart-fan-outer);outline:1px solid var(--chart-run-a)"></span>Interest</span><span class="legend__item"><span class="swatch" style="outline:1px solid var(--chart-run-b)"></span>Fees and tax withheld (below zero)</span></div>';
    var rows = inc.months.map(function (m) { return '<tr><th scope="row">' + F.month(m.month) + '</th>' + td(F.gbp(m.dividends_gbp), 1) + td(F.gbp(m.interest_gbp), 1) + td(F.gbp(m.fees_gbp), 1) + td(F.gbp(m.tax_withheld_gbp), 1) + '</tr>'; });
    rows.push('<tr class="is-group-start"><th scope="row">Twelve months</th>' + td(F.gbp(t.dividends_gbp), 1) + td(F.gbp(t.interest_gbp), 1) + td(F.gbp(t.fees_gbp), 1) + td(F.gbp(t.tax_withheld_gbp), 1) + '</tr>');
    body('income', card(legend + '<figure class="chart" id="income-chart"><div class="chart-svg"></div><figcaption>' + F.month(inc.first) + ' to ' + F.month(inc.last) + ', in pounds (US dollars converted at today’s rate). The table holds the same figures.</figcaption></figure>') +
      card(table([{ label: 'Month' }, { label: 'Dividends', num: 1 }, { label: 'Interest', num: 1 }, { label: 'Fees', num: 1 }, { label: 'Tax withheld', num: 1 }], rows)));
  }

  /* ---------------- holdings ---------------- */
  var sortKey = 'value_gbp', sortDir = -1;
  var HCOLS = [
    { key: 'name', label: 'Holding' }, { key: 'account', label: 'Account' }, { key: 'value_gbp', label: 'Value', num: 1, f: F.gbp },
    { key: 'weight', label: 'Weight', num: 1, f: F.w }, { key: 'return_ann', label: 'Annual return', num: 1, f: F.r },
    { key: 'volatility_ann', label: 'Volatility', num: 1, f: F.r }, { key: 'sharpe', label: 'Sharpe ratio', num: 1, f: F.s },
    { key: 'history_months', label: 'Months of prices', num: 1, f: function (v) { return esc(v); } }
  ];
  function renderHoldings() {
    var rows = DATA.holdings.slice().sort(function (a, b) {
      var x = a[sortKey], y = b[sortKey];
      if (x == null) return 1; if (y == null) return -1;
      return (typeof x === 'string' ? x.localeCompare(y) : x - y) * sortDir;
    });
    var head = '<tr>' + HCOLS.map(function (c) {
      return '<th scope="col"' + (c.num ? ' class="num"' : '') + (c.key === sortKey ? ' aria-sort="' + (sortDir > 0 ? 'ascending' : 'descending') + '"' : '') + '><button type="button" data-sort="' + c.key + '">' + c.label + '</button></th>';
    }).join('') + '</tr>';
    var bodyRows = rows.map(function (hd) {
      var flag = hd.status === 'full' ? '' : ' <span class="tag tag--warn">' + esc(hd.status === 'missing' ? 'no prices' : hd.status === 'short' ? 'short history' : 'gaps') + '</span>';
      return '<tr><th scope="row">' + esc(hd.name) + flag + '</th>' + HCOLS.slice(1).map(function (c) { return td(c.f ? c.f(hd[c.key]) : esc(hd[c.key]), c.num); }).join('') + '</tr>';
    }).join('');
    body('holdings', card('<div class="table-box"><table class="t sortable"><thead>' + head + '</thead><tbody>' + bodyRows + '</tbody></table></div>'));
    $$('[data-sort]').forEach(function (b) {
      b.addEventListener('click', function () { var k = b.dataset.sort; sortDir = k === sortKey ? -sortDir : (k === 'name' || k === 'account' ? 1 : -1); sortKey = k; renderHoldings(); });
    });
  }

  /* ---------------- actual returns (F-031) ---------------- */
  function renderReturns() {
    var ar = DATA.account_returns;
    if (!ar || !ar.available) { body('returns', unavailable(ar, 'Actual account returns')); return; }
    var all = ar.accounts.concat([ar.household]);
    var money = function (x, ccy) { return ccy === 'USD' ? (isNum(x) ? signed('$' + Math.round(Math.abs(x)).toLocaleString('en-GB'), Math.round(x)) : DASH) : F.gbp(x); };
    var rows = all.filter(function (a) { return a.available; }).map(function (a) {
      var mwr = F.r(a.mwr_period) + (isNum(a.mwr_annual) ? '<span class="sub">' + F.r(a.mwr_annual) + ' a year</span>' : '');
      return '<tr' + (a.account === 'household' ? ' class="is-group-start"' : '') + '><th scope="row">' + esc(a.account === 'household' ? 'Household (GBP)' : a.account) + '<span class="sub">' + F.date(a.start) + ' to ' + F.date(a.end) + '</span></th>' +
        td(money(a.start_value, a.currency), 1) + td(money(a.end_value, a.currency), 1) + td(money(a.net_flows, a.currency), 1) + td('<span class="big">' + F.r(a.twr) + '</span>', 1) + td(mwr, 1) + '</tr>';
    });
    var missing = all.filter(function (a) { return !a.available; }).map(function (a) { return '<li><strong>' + esc(a.account) + ':</strong> ' + esc(a.reason) + '</li>'; });
    var unmatched = ar.unmatched.length ? '<p class="note" style="margin-top:var(--space-3)">Transactions not yet matched to a price series (add <code>ledger_names</code> to the series in <code>securities.yaml</code>): ' +
      ar.unmatched.map(function (u) { return esc(u.account + ': ' + u.security); }).join('; ') + '.</p>' : '';
    body('returns', card((rows.length ? table([{ label: 'Account' }, { label: 'Start value', num: 1 }, { label: 'End value', num: 1 }, { label: 'Net money in', num: 1 }, { label: 'Time-weighted', num: 1 }, { label: 'Money-weighted', num: 1 }], rows)
      : '<p class="note">No account can be valued at every month-end yet.</p>') +
      '<p class="note" style="margin-top:var(--space-3)">Each account in its own currency; the household in pounds. Periods under a year are not annualised. Dividends, interest and fees count as return; contributions, tax relief and transfers in or out are money in or out.</p>' +
      (missing.length ? '<h3 class="subhead" style="margin-top:var(--space-4)">Not yet measured</h3><ul class="note">' + missing.join('') + '</ul>' : '') + unmatched));
  }

  /* ---------------- data and caveats ---------------- */
  function renderCaveats() {
    var s = DATA.settings;
    var warn = DATA.warnings.length ? '<ul class="note">' + DATA.warnings.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('') + '</ul>' : '<p class="note">No warnings.</p>';
    var kv = [
      ['Exports folder', esc(DATA.folder)], ['Return window', F.month(s.first) + ' to ' + F.month(s.last) + ' (' + esc(s.months) + ' months)'],
      ['Risk-free rate', isNum(s.risk_free_rate) ? F.r(s.risk_free_rate) + ' a year' : 'not set'], ['Largest weight per holding', F.w(s.max_weight)],
      ['US dollar rate', isNum(s.usd_gbp) ? '£' + s.usd_gbp.toFixed(4) + ' per $ (' + esc(s.usd_gbp_source) + ')' : 'not needed'],
      ['Risk estimate', s.covariance === 'shrunk' ? 'Ledoit–Wolf shrunk covariance' : 'sample covariance'], ['Generated', esc(DATA.generated)]
    ].map(function (r) { return '<tr><th scope="row">' + r[0] + '</th><td>' + r[1] + '</td></tr>'; });
    var files = DATA.data_files.length ? table([{ label: 'Price file' }, { label: 'Series' }, { label: 'From' }, { label: 'To' }, { label: 'Rows', num: 1 }, { label: 'Basis' }, { label: 'SHA-256' }],
      DATA.data_files.map(function (f) { return '<tr><th scope="row">' + esc(f.file) + '</th>' + td(esc(f.series)) + td(F.date(f.first)) + td(F.date(f.last)) + td(esc(f.rows), 1) + td(esc(f.basis)) + td('<code class="small">' + esc(String(f.sha256).slice(0, 12)) + '…</code>') + '</tr>'; }))
      : '<p class="note">No price files yet.</p>';
    body('caveats', '<div class="grid-2">' + card('<h3 class="subhead">Warnings</h3>' + warn) + card('<h3 class="subhead">Settings</h3>' + table([{ label: 'Setting' }, { label: 'Value' }], kv)) + '</div>' +
      card('<h3 class="subhead">Price files used</h3>' + files) +
      card('<h3 class="subhead">What this page does not do</h3><ul class="note"><li>Analysis, not advice: it describes past patterns under stated assumptions and never recommends a trade.</li>' +
        '<li>No tax is considered: no capital gains, dividend or income tax, and no wrapper allowances.</li><li>Moves between wrappers (pension or SIPP to an ISA or taxable account) cannot be made as the household view shows.</li>' +
        '<li>Past returns, volatility and correlations are estimates from a few years of monthly data and change with the window.</li><li>Nothing is sent anywhere: the page reads a file on this computer.</li></ul>'));
  }

  /* ---------------- meta, theme, print ---------------- */
  function renderMeta() {
    var chips = ['Exports ' + esc(DATA.folder), F.month(DATA.settings.first) + '–' + F.month(DATA.settings.last), DATA.synthetic ? 'Synthetic sample data' : null].filter(Boolean);
    $('#meta').innerHTML = '<div class="chips">' + chips.map(function (c) { return '<span class="chip chip--option">' + c + '</span>'; }).join('') + '</div>';
    $('#print-title').textContent = 'Portfolio · ' + DATA.folder + (DATA.synthetic ? ' · synthetic sample' : '');
  }
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
  var printUndo = null, savedTitle = null;
  function printPdf() {
    if (savedTitle === null) savedTitle = document.title;
    document.title = 'SBRetire portfolio ' + (DATA ? DATA.folder : '');
    window.print();
  }
  function wrapForPrint() {
    if (printUndo) return;
    var undo = [];
    printUndo = undo;
    $$('main .section').forEach(function (s) {
      var title = s.querySelector('.section__title');
      if (s.hidden || !title) return;
      try {
        var intro = s.querySelector(':scope > .section__intro'), bodyEl = s.querySelector(':scope > [id$="-body"]');
        var first = bodyEl ? bodyEl.querySelector('.card, figure, table') : null;
        var home = first ? first.parentNode : null, next = first ? first.nextSibling : null;
        var keep = document.createElement('div');
        keep.className = 'print-keep';
        if (first) home.insertBefore(keep, first); else s.appendChild(keep);
        keep.appendChild(title);
        if (intro) keep.appendChild(intro);
        if (first) keep.appendChild(first);
        undo.push(function () {
          if (first) home.insertBefore(first, next);
          s.insertBefore(title, s.firstElementChild);
          if (intro) title.after(intro);
          keep.remove();
        });
      } catch (e) { /* leave this section as it is */ }
    });
  }
  function unwrapAfterPrint() {
    if (savedTitle !== null) { document.title = savedTitle; savedTitle = null; }
    if (!printUndo) return;
    printUndo.reverse().forEach(function (f) { f(); });
    printUndo = null;
  }

  function drawCharts() { if (DATA.frontier.available) { drawFrontier(); drawDumbbell(); } drawPerformance(); drawIncome(); }
  function message(title, text) {
    $$('main > .section, .about').forEach(function (s) { s.hidden = true; });
    $('#message').innerHTML = '<div class="message"><div class="card"><h2>' + title + '</h2><p class="muted">' + text + '</p></div></div>';
  }
  function init() {
    initTheme();
    $('#pdf-button').addEventListener('click', printPdf);
    window.addEventListener('beforeprint', wrapForPrint);
    window.addEventListener('afterprint', unwrapAfterPrint);
    if (!DATA) { message('No portfolio analysis yet', 'Run <code>sbretire portfolio report</code>, then open this page again.'); return; }
    if (String(DATA.schema_version || '').split('.')[0] !== KNOWN_MAJOR) {
      message('This analysis uses a newer format', 'It was saved with format ' + esc(DATA.schema_version) + '; this page reads format ' + KNOWN_MAJOR + '.x. Run the report again with this version.');
      return;
    }
    renderMeta(); renderHeadline(); renderAllocation(); renderFrontier(); renderRebalance(); renderPerformance(); renderRisk(); renderIncome(); renderHoldings(); renderReturns(); renderCaveats();
    drawCharts();
    var lastW = window.innerWidth, timer;
    window.addEventListener('resize', function () { clearTimeout(timer); timer = setTimeout(function () { if (window.innerWidth !== lastW) { lastW = window.innerWidth; drawCharts(); } }, 120); });
  }
  init();
})();
