#!/usr/bin/env python3
"""Regenerate index.html from data/picks.json and data/kills.json.

Run this after updating the JSON data files. Takes no arguments; reads
STATUS_BANNER env-style constants below (edit per-run) and embeds the
JSON verbatim into the page for the browser-side table/leaderboard logic.
"""
import json
import os
import statistics
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TODAY = "2026-07-20"
LAST_RUN_ET = "2026-07-20 07:55 AM EDT"
STATUS_OK = False
STATUS_LINES = [
    "LIVE PRICE REFRESH FAILED AGAIN THIS RUN -- 4th consecutive trading day this has happened (2026-07-15, 07-16, 07-17, and now 07-20): "
    "yfinance and direct HTTPS to every finance-data host (fc.yahoo.com, query1/query2.finance.yahoo.com, stooq.com, www.wsj.com) again "
    "returned 403 CONNECT-tunnel rejections at the network-proxy level, confirmed via the proxy's own status endpoint "
    "(recentRelayFailures: connect_rejected / 'gateway answered 403 to CONNECT') as a policy-level block, not a transient outage. This is "
    "unambiguously a persistent environment network-policy problem spanning multiple runs and now a full trading week -- it needs a human "
    "to allow-list finance-data hosts before automated price tracking can resume. A push notification was sent flagging this again today. "
    "Per the no-fabrication rule and the lesson from the 2026-07-17 run (a WebSearch-sourced price for KRMN was later found to be a stale/ "
    "mismatched snippet), NO prices were pulled via WebSearch this run either -- every open pick (FRO, CF, CAMT, LEU, POWL, KTOS, HBM, EE, "
    "METC, DSGX, SGH, CVCO, REX, RYAM) keeps its last successfully recorded price, unchanged and stale, not refreshed today. daily_opens "
    "backfill and price_at_rec backfill remain fully blocked until direct market-data access is restored.",
    "Today's picks are new (no picks dated 2026-07-20 existed yet), so a full sweep/scoring/kill-pass was run: roughly 30 stories screened "
    "across tariffs/regulatory (Section 122 expiring July 24, Section 301 16-country/60-country conclusions due today), geopolitical "
    "(Iran war 9th night of strikes, Hormuz traffic), trucking/freight capacity, inland-waterway drought/flooding, pharma reshoring, "
    "independent-refiner crack spreads, space launch policy, and biotech M&A. Only 1 new pick survived adversarial kill-pass -- KEX (Kirby "
    "Corporation) on a worsening, fresh dual-basin Rhine + Mississippi inland-waterway capacity crisis -- alongside 9 kills, mostly for "
    "being already fully priced-in/analyst-covered (RGEN, WST, PBF, DK, DINO), contradicted by the company's own disclosure (Ryder), "
    "gated on a future event with no near-term revenue mechanism (RKLB), stale (WNC), or already-reacted/weak hold-period fit (NEXT). See "
    "Considered and Rejected Today for full reasoning. A single new pick is a thinner day than usual by design -- most of the obvious "
    "second-order trades from this week's news were already consensus, and forcing a fuller slate would violate the quality bar.",
    "NEXT RUN MUST: retry direct price refresh (yfinance) first; this is now the 4th straight blocked attempt across a full trading week, "
    "so if still blocked, escalate rather than keep silently retrying -- this needs the user's manual network-policy intervention. Backfill "
    "price_at_rec for KEX and all still-pending tickers (HBM, EE, METC, DSGX, SGH, CVCO, REX, RYAM, KEX) once unblocked. Friday "
    "thesis-outcome review is still owed from 2026-07-17 (skipped that run for the same reason) -- do it as soon as prices are back.",
]

def load(name):
    with open(os.path.join(REPO, "data", name)) as f:
        return json.load(f)

picks = load("picks.json")
kills = load("kills.json")

def money(x, decimals=2):
    if x is None:
        return "pending"
    return f"${x:,.{decimals}f}"

def pct(x, decimals=2):
    if x is None:
        return "pending"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.{decimals}f}%"

priced_picks = [p for p in picks if p.get("price_at_rec") is not None]
pending_picks = [p for p in picks if p.get("price_at_rec") is None]

leaderboard = sorted(priced_picks, key=lambda p: (p.get("gain_loss_pct") if p.get("gain_loss_pct") is not None else -999), reverse=True)

# Portfolio summary: $1000 hypothetical per priced pick
portfolio_rows = []
total_invested = 0
total_value = 0
for p in priced_picks:
    if p.get("current_price") is None:
        continue
    shares = 1000.0 / p["price_at_rec"]
    value = shares * p["current_price"]
    total_invested += 1000
    total_value += value
    portfolio_rows.append((p["ticker"], value))

agg_return_pct = ((total_value - total_invested) / total_invested * 100) if total_invested else None

by_category = {}
by_confidence = {}
for p in priced_picks:
    if p.get("gain_loss_pct") is None:
        continue
    by_category.setdefault(p["category"], []).append(p["gain_loss_pct"])
    by_confidence.setdefault(p["confidence"], []).append(p["gain_loss_pct"])

def avg(lst):
    return sum(lst) / len(lst) if lst else None

returns = [p["gain_loss_pct"] for p in priced_picks if p.get("gain_loss_pct") is not None]
wins = [r for r in returns if r > 0]
losses = [r for r in returns if r <= 0]
hit_rate = (len(wins) / len(returns) * 100) if returns else None
median_return = statistics.median(returns) if returns else None
avg_win = avg(wins)
avg_loss = avg(losses)

kills_with_price = [k for k in kills if k.get("price_at_kill") is not None]

data_json = json.dumps({"picks": picks, "kills": kills}, indent=None)

def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

today_picks = [p for p in picks if p["date_recommended"] == TODAY]
today_kills = [k for k in kills if k["date"] == TODAY]

status_html = "".join(f"<p>{esc(l)}</p>" for l in STATUS_LINES)

pick_cards = []
for p in today_picks:
    pick_cards.append(f"""
    <div class="card">
      <h3>{esc(p['ticker'])} &mdash; {esc(p['company'])} <span class="tag {esc(p['confidence'].lower().replace(' ', '-'))}">{esc(p['confidence'])}</span> <span class="tag cat">{esc(p['category'])}</span></h3>
      <p><strong>News:</strong> {esc(p['news_overview'])}</p>
      <p><strong>Pick:</strong> {esc(p['pick_overview'])}</p>
      <p><strong>Why it benefits:</strong> {esc(p['rationale'])}</p>
      <p><strong>Hold period:</strong> {esc(p['target_hold_period'])} &nbsp; <strong>Exit plan:</strong> {esc(p['exit_plan'])}</p>
      <p><a href="{esc(p['source_url'])}" target="_blank" rel="noopener">Source</a> &middot; Price at rec: {money(p['price_at_rec'])} (pending market open)</p>
    </div>""")

kill_cards = []
for k in today_kills:
    kill_cards.append(f"""
    <div class="card kill">
      <h4>{esc(k['ticker'])} &mdash; {esc(k['company'])} <span class="tag kill-stage">{esc(k['kill_stage'])}</span></h4>
      <p><strong>Story:</strong> {esc(k['story'])}</p>
      <p><strong>Why killed:</strong> {esc(k['reason'])}</p>
    </div>""")

leaderboard_rows = []
for p in leaderboard:
    opens_json = json.dumps(p.get("daily_opens", {}))
    leaderboard_rows.append(f"""
      <tr class="lb-row" data-opens='{opens_json}' data-ticker="{esc(p['ticker'])}">
        <td>{esc(p['ticker'])}</td>
        <td>{esc(p['date_recommended'])}</td>
        <td>{money(p['price_at_rec'])}</td>
        <td>{money(p['current_price'])}</td>
        <td class="{'pos' if (p.get('gain_loss_pct') or 0) >= 0 else 'neg'}">{pct(p.get('gain_loss_pct'))}</td>
        <td class="{'pos' if (p.get('vs_spy_pct') or 0) >= 0 else 'neg'}">{pct(p.get('vs_spy_pct'))}</td>
        <td class="{'pos' if (p.get('vs_sector_pct') or 0) >= 0 else 'neg'}">{pct(p.get('vs_sector_pct'))}</td>
        <td>{esc(p['target_hold_period'])}</td>
        <td>{esc(p['status'])}</td>
      </tr>""")

for p in pending_picks:
    leaderboard_rows.append(f"""
      <tr class="lb-row pending-row">
        <td>{esc(p['ticker'])}</td>
        <td>{esc(p['date_recommended'])}</td>
        <td colspan="6">price pending -- market not yet open at time of recommendation, backfilling next run</td>
        <td>{esc(p['status'])}</td>
      </tr>""")

kill_rows = []
for k in kills:
    kill_rows.append(f"""
      <tr>
        <td>{esc(k['ticker'])}</td>
        <td>{esc(k['date'])}</td>
        <td>{esc(k['kill_stage'])}</td>
        <td>{money(k.get('price_at_kill'))}</td>
        <td>{money(k.get('current_price'))}</td>
        <td>{pct(k.get('would_be_gain_loss_pct'))}</td>
      </tr>""")

by_cat_rows = "".join(
    f"<tr><td>{esc(c)}</td><td>{len(v)}</td><td>{pct(avg(v))}</td></tr>" for c, v in sorted(by_category.items())
)
by_conf_rows = "".join(
    f"<tr><td>{esc(c)}</td><td>{len(v)}</td><td>{pct(avg(v))}</td></tr>" for c, v in sorted(by_confidence.items())
)

html = f"""<title>Second-Order News Stock Picks &mdash; Paper Trading Tracker</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 900px; margin: 0 auto; padding: 1rem 1rem 4rem; line-height: 1.5;
    background: #fafafa; color: #1a1a1a;
  }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #16181c; color: #e8e8e8; }}
    .card, table, .status {{ background: #21242b !important; border-color: #333 !important; }}
    a {{ color: #7bb0ff; }}
    th {{ background: #2a2e37 !important; }}
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  h2 {{ font-size: 1.15rem; border-bottom: 2px solid #ccc; padding-bottom: 0.3rem; margin-top: 2.2rem; }}
  .status {{ background: #fff3cd; border: 1px solid #e0c56a; border-radius: 8px; padding: 0.8rem 1rem; font-size: 0.9rem; }}
  .status.ok {{ background: #d9f2e3; border-color: #7ac99a; }}
  .status p {{ margin: 0.4rem 0; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 5px; font-weight: 600; font-size: 0.8rem; }}
  .badge.fail {{ background: #e0554f; color: white; }}
  .badge.ok {{ background: #2e9e5b; color: white; }}
  .card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 0.9rem 1rem; margin: 0.8rem 0; }}
  .card.kill {{ border-left: 4px solid #b9433c; }}
  .tag {{ display: inline-block; font-size: 0.7rem; padding: 0.1rem 0.45rem; border-radius: 10px; background: #e5e5e5; margin-left: 0.3rem; vertical-align: middle; }}
  .tag.high {{ background: #2e9e5b; color: white; }}
  .tag.med-high {{ background: #6aa84f; color: white; }}
  .tag.med {{ background: #e2b93b; }}
  .tag.low {{ background: #ccc; }}
  .tag.kill-stage {{ background: #b9433c; color: white; }}
  table {{ width: 100%; border-collapse: collapse; background: white; font-size: 0.85rem; }}
  th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.5rem; text-align: left; }}
  th {{ background: #f0f0f0; position: sticky; top: 0; }}
  .pos {{ color: #1b7d3b; font-weight: 600; }}
  .neg {{ color: #c0392b; font-weight: 600; }}
  .pending-row td {{ color: #888; font-style: italic; }}
  .scroll {{ overflow-x: auto; }}
  .lb-row {{ cursor: pointer; }}
  .opens-panel {{ display: none; background: #f7f7f7; font-size: 0.8rem; padding: 0.5rem; }}
  footer {{ margin-top: 3rem; font-size: 0.75rem; color: #888; border-top: 1px solid #ccc; padding-top: 1rem; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.6rem; }}
  .stat-box {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 0.7rem; text-align: center; }}
  .stat-box .v {{ font-size: 1.3rem; font-weight: 700; }}
  .stat-box .l {{ font-size: 0.75rem; color: #777; }}
</style>

<h1>Second-Order News Stock Picks</h1>
<p style="margin-top:0;color:#666;font-size:0.85rem;">Paper-trading experiment &middot; last run {esc(LAST_RUN_ET)}</p>

<div class="status {'ok' if STATUS_OK else ''}">
  <span class="badge {'ok' if STATUS_OK else 'fail'}">{'OK' if STATUS_OK else 'PARTIAL: PRICE REFRESH FAILED'}</span>
  {status_html}
</div>

<h2>Today's Picks &mdash; {esc(TODAY)}</h2>
{''.join(pick_cards) if pick_cards else '<p>No new picks today (reiteration day or no qualifying stories).</p>'}

<h2>Considered and Rejected Today</h2>
{''.join(kill_cards) if kill_cards else '<p>No kills logged today.</p>'}

<h2>Open Picks Leaderboard</h2>
<p style="font-size:0.85rem;color:#666;">Tap/click a row to expand its daily-open price history.</p>
<div class="scroll">
<table>
  <thead><tr><th>Ticker</th><th>Date</th><th>Price@Rec</th><th>Current</th><th>Gain/Loss</th><th>vs SPY</th><th>vs Sector</th><th>Hold Period</th><th>Status</th></tr></thead>
  <tbody>
  {''.join(leaderboard_rows)}
  </tbody>
</table>
</div>

<h2>Portfolio Summary</h2>
<div class="stat-grid">
  <div class="stat-box"><div class="v">{len(portfolio_rows)}</div><div class="l">priced positions ($1,000 each)</div></div>
  <div class="stat-box"><div class="v">{money(total_invested) if total_invested else '$0'}</div><div class="l">hypothetical invested</div></div>
  <div class="stat-box"><div class="v">{money(total_value) if total_value else '$0'}</div><div class="l">current value</div></div>
  <div class="stat-box"><div class="v">{pct(agg_return_pct)}</div><div class="l">aggregate return</div></div>
  <div class="stat-box"><div class="v">{len(pending_picks)}</div><div class="l">pending entry price</div></div>
</div>
<div class="scroll" style="margin-top:1rem;">
<table>
  <thead><tr><th>Category</th><th>Count</th><th>Avg return</th></tr></thead>
  <tbody>{by_cat_rows}</tbody>
</table>
</div>
<div class="scroll" style="margin-top:1rem;">
<table>
  <thead><tr><th>Confidence</th><th>Count</th><th>Avg return</th></tr></thead>
  <tbody>{by_conf_rows}</tbody>
</table>
</div>

<h2>Kills / Counterfactuals</h2>
<div class="scroll">
<table>
  <thead><tr><th>Ticker</th><th>Date</th><th>Kill Stage</th><th>Price@Kill</th><th>Current</th><th>Would-be Return</th></tr></thead>
  <tbody>{''.join(kill_rows)}</tbody>
</table>
</div>
<p style="font-size:0.85rem;color:#666;">Survivors vs Killed: {len(returns)} priced open picks averaging {pct(avg(returns))} vs {len(kills_with_price)} priced kills (would-be returns pending price backfill).</p>

<h2>Stats</h2>
<div class="stat-grid">
  <div class="stat-box"><div class="v">{pct(hit_rate) if hit_rate is not None else 'n/a'}</div><div class="l">hit rate (open picks, interim)</div></div>
  <div class="stat-box"><div class="v">{pct(median_return) if median_return is not None else 'n/a'}</div><div class="l">median return</div></div>
  <div class="stat-box"><div class="v">{pct(avg_win) if avg_win is not None else 'n/a'}</div><div class="l">avg win</div></div>
  <div class="stat-box"><div class="v">{pct(avg_loss) if avg_loss is not None else 'n/a'}</div><div class="l">avg loss</div></div>
</div>
<p style="font-size:0.8rem;color:#888;">No picks have closed their 60-trading-day window yet, so hit rate above reflects only currently-open unrealized positions, not resolved outcomes.</p>

<footer>
  Paper-trading experiment tracking whether second-order news reasoning generates alpha. Not investment advice.
  Data: <a href="data/picks.json">picks.json</a> &middot; <a href="data/kills.json">kills.json</a>
</footer>

<script>
  var EMBEDDED_DATA = {data_json};
  document.querySelectorAll('.lb-row').forEach(function(row) {{
    row.addEventListener('click', function() {{
      var existing = row.nextElementSibling;
      if (existing && existing.classList.contains('opens-panel')) {{
        existing.remove();
        return;
      }}
      var opens = JSON.parse(row.getAttribute('data-opens') || '{{}}');
      var keys = Object.keys(opens).sort();
      var html = '<tr><td colspan="9"><div class="opens-panel" style="display:block;"><strong>Daily opens for ' + row.getAttribute('data-ticker') + ':</strong><br>' +
        keys.map(function(k) {{ return k + ': $' + opens[k].toFixed(2); }}).join(' &nbsp; ') +
        (keys.length === 0 ? 'no data yet' : '') + '</div></td></tr>';
      var tr = document.createElement('tr');
      tr.innerHTML = html;
      row.parentNode.insertBefore(tr, row.nextSibling);
    }});
  }});
</script>
"""

with open(os.path.join(REPO, "index.html"), "w") as f:
    f.write(html)

print("wrote index.html,", len(html), "bytes")
