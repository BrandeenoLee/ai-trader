"""Friday recap email and the static dashboard (docs/index.html, served by GitHub Pages)."""
from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText

from . import ai as ai_mod
from . import config, journal, state

WEEKLY_FILE = "weekly.jsonl"


# --- Email ----------------------------------------------------------------------

def recap_text(week: dict) -> str:
    lines = [f"AI trading tournament - week ending {week['date']}", ""]
    spy = week["benchmark"]
    lines.append(f"SPY benchmark: week {spy['week_ret']:+.2f}%, total {spy['total_ret']:+.2f}%")
    lines.append("")
    rows = sorted(week["strategies"].items(), key=lambda kv: -kv[1]["total_ret"])
    for sid, r in rows:
        name = config.STRATEGIES[sid]["name"]
        lines.append(f"{sid} {name}: week {r['week_ret']:+.2f}% | total {r['total_ret']:+.2f}% "
                     f"| vs SPY {r['vs_spy']:+.2f} pts | trades {r['trades']} | AI ${r['ai_cost_week']:.2f}")
        if r.get("self_assessment"):
            lines.append(f"   Claude: {r['self_assessment']}")
        lines.append(f"   Check-ins next week: {r['level']}/day")
    lines += ["", f"AI spend this month: ${week['month_spend']:.2f} "
                  f"(target ${config.MONTHLY_TARGET_USD:.0f}, cap ${config.MONTHLY_HARD_CAP_USD:.0f})",
              "Returns are net of simulated spread costs and each strategy's AI cost.",
              "Full trade log and charts are on the dashboard."]
    return "\n".join(lines)


def send_email(subject: str, body: str) -> bool:
    user, pw = os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_APP_PASSWORD")
    to = os.environ.get("EMAIL_TO") or user
    if not (user and pw):
        print("Email not configured; recap follows:\n" + body)
        return False
    msg = MIMEText(body)
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    return True


# --- Dashboard ------------------------------------------------------------------

def build_dashboard(led: dict) -> None:
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    notes = {sid: (config.NOTES_DIR / f"{sid}.md").read_text() for sid in config.STRATEGIES}
    entries = journal.entries(kinds=("decision", "fill", "order_closed", "review", "error"))[-1500:]
    data = {
        "strategies": {sid: {"name": s["name"], "level": led["strategies"][sid]["checkin_level"],
                             "ai_cost": round(led["strategies"][sid]["ai_cost"], 4),
                             "positions": led["strategies"][sid]["positions"],
                             "cash": round(led["strategies"][sid]["cash"], 2),
                             "penalty_paid": round(led["strategies"][sid]["penalty_paid"], 4)}
                       for sid, s in config.STRATEGIES.items()},
        "benchmark": config.BENCHMARK,
        "started": led["started"],
        "equity": led["equity_history"],
        "weekly": state.read_jsonl(WEEKLY_FILE),
        "journal": entries,
        "spend": ai_mod.spend(),
        "budget": {"target": config.MONTHLY_TARGET_USD, "cap": config.MONTHLY_HARD_CAP_USD},
        "notes": notes,
    }
    payload = json.dumps(data, default=str).replace("</", "<\\/")
    (config.DOCS_DIR / "data.json").write_text(json.dumps(data, default=str, indent=1))
    (config.DOCS_DIR / "index.html").write_text(TEMPLATE.replace("__DATA__", payload))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategy Tournament</title>
<style>
:root{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1b;--muted:#6b6a65;--line:#e4e2db;--good:#2f7d4f;--bad:#b0412e;
--c1:#2e6bd9;--c2:#d9822e;--c3:#2fa37d;--c4:#a13fbf;--c5:#c2a91f;--spy:#1d1d1b}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--card:#1f1f1c;--ink:#ecebe6;--muted:#9c9a92;--line:#33322d;--spy:#ecebe6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,system-ui,Segoe UI,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 64px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.muted{color:var(--muted)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.kpi .v{font-size:22px;font-weight:600}.kpi .l{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13.5px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:12px}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.good{color:var(--good)}.bad{color:var(--bad)}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.tabs button{background:none;border:1px solid var(--line);color:var(--ink);border-radius:999px;padding:4px 12px;margin:0 6px 6px 0;cursor:pointer;font:inherit;font-size:13px}
.tabs button.on{background:var(--ink);color:var(--bg)}pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace;margin:0}
.scroll{overflow-x:auto}svg text{fill:var(--muted);font-size:11px}
</style></head><body><main>
<h1>AI Strategy Tournament</h1><div class="muted" id="sub"></div>
<h2>Standings</h2><div class="card scroll"><table id="standings"></table></div>
<h2>Equity vs SPY</h2><div class="card"><div id="chart"></div><div id="legend" class="muted" style="font-size:13px"></div></div>
<h2>Weekly results</h2><div class="card scroll"><table id="weekly"></table></div>
<h2>Does confidence predict results?</h2><div class="card scroll"><table id="conf"></table>
<div class="muted" style="font-size:12.5px;margin-top:8px">Average return of filled buys by the confidence the AI stated, measured from fill to latest price or exit.</div></div>
<h2>AI spend</h2><div class="card grid" id="spend"></div>
<h2>Trade log</h2><div class="tabs" id="logtabs"></div><div class="card scroll" style="max-height:560px;overflow-y:auto"><table id="log"></table></div>
<h2>Strategy notes</h2><div class="tabs" id="notetabs"></div><div class="card"><pre id="notes"></pre></div>
</main><script>
const D=__DATA__;
const COL={A:'var(--c1)',B:'var(--c2)',C:'var(--c3)',D:'var(--c4)',E:'var(--c5)',[D.benchmark]:'var(--spy)'};
const S=Object.keys(D.strategies),start=500,esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(x,d=2)=>x==null?'n/a':`<span class="${x>=0?'good':'bad'}">${x>=0?'+':''}${x.toFixed(d)}%</span>`;
const last=D.equity[D.equity.length-1]||{};
document.getElementById('sub').textContent=`Started ${D.started} · last update ${last.date||'n/a'} · paper trading`;
// standings
{const spyEq=last[D.benchmark]||start;const rows=S.map(s=>({s,eq:last[s]??start})).sort((a,b)=>b.eq-a.eq);
let h='<tr><th>Strategy</th><th class="num">Net equity</th><th class="num">Total</th><th class="num">vs SPY</th><th class="num">Check-ins/day</th><th class="num">AI cost</th><th>Holdings</th></tr>';
for(const r of rows){const st=D.strategies[r.s];const hold=Object.entries(st.positions).map(([k,v])=>`${k} ${(+v.qty).toFixed(2)}`).join(', ')||'cash';
h+=`<tr><td><span class="dot" style="background:${COL[r.s]}"></span>${r.s} · ${esc(st.name)}</td><td class="num">$${r.eq.toFixed(2)}</td><td class="num">${pct((r.eq/start-1)*100)}</td><td class="num">${pct((r.eq/spyEq-1)*100)}</td><td class="num">${st.level}</td><td class="num">$${st.ai_cost.toFixed(2)}</td><td>${esc(hold)}</td></tr>`;}
h+=`<tr><td><span class="dot" style="background:${COL[D.benchmark]}"></span>${D.benchmark} buy &amp; hold</td><td class="num">$${spyEq.toFixed(2)}</td><td class="num">${pct((spyEq/start-1)*100)}</td><td></td><td></td><td></td><td>${D.benchmark}</td></tr>`;
document.getElementById('standings').innerHTML=h;}
// chart
{const keys=[...S,D.benchmark],E=D.equity;const el=document.getElementById('chart');
if(E.length<2){el.innerHTML='<div class="muted">The chart appears after two days of data.</div>';}else{
const W=1000,H=300,p={l:52,r:12,t:12,b:28};let lo=1e9,hi=-1e9;for(const r of E)for(const k of keys)if(r[k]!=null){lo=Math.min(lo,r[k]);hi=Math.max(hi,r[k]);}
const pad=(hi-lo)*.1||5;lo-=pad;hi+=pad;const x=i=>p.l+i*(W-p.l-p.r)/(E.length-1),y=v=>p.t+(hi-v)*(H-p.t-p.b)/(hi-lo);
let g='';for(let i=0;i<5;i++){const v=lo+i*(hi-lo)/4;g+=`<line x1="${p.l}" x2="${W-p.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${p.l-6}" y="${y(v)+4}" text-anchor="end">$${v.toFixed(0)}</text>`;}
const step=Math.ceil(E.length/8);E.forEach((r,i)=>{if(i%step===0)g+=`<text x="${x(i)}" y="${H-8}" text-anchor="middle">${r.date.slice(5)}</text>`;});
g+=`<line x1="${p.l}" x2="${W-p.r}" y1="${y(start)}" y2="${y(start)}" stroke="var(--muted)" stroke-dasharray="3 4"/>`;
for(const k of keys){const pts=E.map((r,i)=>r[k]==null?null:`${x(i)},${y(r[k])}`).filter(Boolean).join(' ');
g+=`<polyline points="${pts}" fill="none" stroke="${COL[k]}" stroke-width="${k===D.benchmark?2.5:1.75}" ${k===D.benchmark?'stroke-dasharray="6 4"':''}/>`;}
el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Equity by strategy">${g}</svg>`;
document.getElementById('legend').innerHTML=keys.map(k=>`<span style="margin-right:14px"><span class="dot" style="background:${COL[k]}"></span>${k}</span>`).join('');}}
// weekly
{let h='<tr><th>Week ending</th>'+S.map(s=>`<th class="num">${s}</th>`).join('')+`<th class="num">${D.benchmark}</th><th>Notes</th></tr>`;
for(const w of [...D.weekly].reverse()){h+=`<tr><td>${w.date}</td>`+S.map(s=>`<td class="num">${pct(w.strategies[s]?.week_ret)}</td>`).join('')+`<td class="num">${pct(w.benchmark.week_ret)}</td><td class="muted">${esc(w.strategies.E?.self_assessment||'')}</td></tr>`;}
if(!D.weekly.length)h+='<tr><td colspan="8" class="muted">First recap arrives Friday after the close.</td></tr>';
document.getElementById('weekly').innerHTML=h;}
// confidence
{const lw=D.weekly[D.weekly.length-1];const c=lw?.confidence||{};let h='<tr><th>Confidence</th><th class="num">Filled buys</th><th class="num">Avg return</th></tr>';
for(const t of ['1-4','5-7','8-10']){const r=c[t];h+=`<tr><td>${t}</td><td class="num">${r?r.n:0}</td><td class="num">${r&&r.n?pct(r.avg):'n/a'}</td></tr>`;}
if(lw&&lw.e_confidence_log&&lw.e_confidence_log.length){h+=`<tr><td colspan="3" class="muted">Strategy E's weekly confidence it would beat SPY: ${lw.e_confidence_log.map(x=>`${x.week}: ${x.confidence}/10 → ${x.beat==null?'pending':(x.beat?'beat':'missed')}`).join(' · ')}</td></tr>`;}
document.getElementById('conf').innerHTML=h;}
// spend
{const m=Object.keys(D.spend).sort().pop();const cur=m?D.spend[m]:{total:0,calls:0,by_strategy:{}};
const kp=(v,l)=>`<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
document.getElementById('spend').innerHTML=kp('$'+cur.total.toFixed(2),`spent in ${m||'this month'}`)+kp('$'+D.budget.target.toFixed(0),'monthly target')+kp('$'+D.budget.cap.toFixed(0),'hard cap')+kp(cur.calls,'AI calls');}
// log
{const tabs=document.getElementById('logtabs');let cur='all';const draw=()=>{const rows=D.journal.filter(r=>cur==='all'||r.strategy===cur).slice().reverse().slice(0,200);
let h='<tr><th>Time (UTC)</th><th>Strat</th><th>Event</th><th>Detail</th></tr>';
for(const r of rows){let d='';if(r.kind==='decision'){d=esc(r.summary)+(r.orders||[]).map(o=>`<div>• ${esc(o.action)} ${esc(o.symbol)} conf ${esc(o.confidence)}: ${esc(o.reasoning)} <span class="muted">→ ${esc(o.result)}</span></div>`).join('')||'<div class="muted">hold</div>';}
else if(r.kind==='fill'){d=`${r.side} ${(+r.qty).toFixed(4)} ${esc(r.symbol)} @ ${(+r.fill_price).toFixed(2)}`+(r.pnl!=null?` · P&L ${(+r.pnl).toFixed(2)}`:'');}
else if(r.kind==='review'){d=esc(r.lessons);}else{d=esc(r.status||r.error||r.note||'');}
h+=`<tr><td class="muted">${r.ts.slice(0,16).replace('T',' ')}</td><td>${r.strategy||''}</td><td>${r.kind}</td><td>${d}</td></tr>`;}
document.getElementById('log').innerHTML=h;tabs.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.k===cur));};
tabs.innerHTML=['all',...S].map(k=>`<button data-k="${k}">${k==='all'?'All':k}</button>`).join('');tabs.onclick=e=>{if(e.target.dataset.k){cur=e.target.dataset.k;draw();}};draw();}
// notes
{const tabs=document.getElementById('notetabs');let cur=S[0];const draw=()=>{document.getElementById('notes').textContent=D.notes[cur];tabs.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.k===cur));};
tabs.innerHTML=S.map(k=>`<button data-k="${k}">${k} · ${esc(D.strategies[k].name)}</button>`).join('');tabs.onclick=e=>{if(e.target.dataset.k){cur=e.target.dataset.k;draw();}};draw();}
</script></body></html>"""
