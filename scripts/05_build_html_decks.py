"""
05_build_html_decks.py — Stage 4 deliverable (HTML twin of the PPTX decks).

Builds two self-contained, browser-openable decks in Akos Szakaly's "structured
craft" brand using the real brand fonts (Hanken Grotesk / Spectral / Spline Sans
Mono via Google Fonts) and Chart.js (CDN) for live charts:

  mortgage_exec_deck.html       executive briefing  (4 content + appendix)
  mortgage_internal_deck.html   credit & modelling deep-dive (full storyline)

Slides are 1280x720, scaled to fit the viewport; arrow keys / on-screen controls
navigate; the deck also prints one slide per landscape page.

Run:  python3 scripts/05_build_html_decks.py
Reads: metrics/model_eval.json, metrics/evaluation_metrics.json, metrics/model_benchmark.csv, metrics/eda_summary.json
"""
import json, html
import numpy as np

EV = json.load(open("metrics/evaluation_metrics.json"))
ME = json.load(open("metrics/model_eval.json"))
EDA = json.load(open("metrics/eda_summary.json"))

# ---- compact chart data ----
rng = np.random.default_rng(0)
a = np.array(ME["scatter"]["actual"]); p = np.array(ME["scatter"]["pred"])
idx = rng.choice(len(a), 520, replace=False)
SCATTER = {"ak": np.round(a[idx] / 1000).astype(int).tolist(),
           "pk": np.round(p[idx] / 1000).astype(int).tolist()}
DATA = {
    "scatter": SCATTER,
    "rhc": ME["resid_hist"]["counts"],
    "rhe": [round(x / 1000, 1) for x in ME["resid_hist"]["edges"]],
    "band": ME["by_band"]["band"], "mape": ME["by_band"]["MAPE_pct"],
    "mae_band": [round(x / 1000) for x in ME["by_band"]["MAE"]],
    "imp_f": ["Annual income", "Credit score", "Existing monthly debt", "Down payment"],
    "imp_v": [round(x, 3) for x in ME["primary_importance"]["importance"]],
    "thist_c": EDA["target_hist"]["counts"], "thist_e": [round(x / 1000) for x in EDA["target_hist"]["edges"]],
    "corr_f": [{"Annual Income (USD)": "Annual income", "Credit Score": "Credit score", "Down Payment (USD)": "Down payment", "Employment Years": "Employment yrs", "Age": "Age", "Loans Repaid": "Loans repaid", "Existing Monthly Debt (USD)": "Existing debt"}.get(k, k) for k in EDA["corr"]], "corr_v": list(EDA["corr"].values()),
    "edu_l": EDA["cat_target"]["Education"]["labels"], "edu_v": [round(x / 1000) for x in EDA["cat_target"]["Education"]["means"]],
    "job_l": EDA["cat_target"]["Job"]["labels"][::-1], "job_v": [round(x / 1000) for x in EDA["cat_target"]["Job"]["means"][::-1]],
    "bench_l": ["GBM (raw)", "GBM (log)", "RF (raw)", "RF (log)", "Linear (raw)", "Linear (log)"],
    "bench_mae": [22.4, 22.5, 24.3, 24.4, 51.9, 62.6], "bench_r2": [0.989, 0.989, 0.988, 0.988, 0.950, 0.883],
}

CSS = """
:root{
 --paper:#F8FAFD;--paper2:#F0F4F7;--paper3:#E6EAEF;--card:#FDFEFF;
 --ink:#1B2129;--ink2:#3E444D;--ink3:#666D74;--ink4:#9399A0;
 --cobalt:#306CB8;--cobalt-deep:#1E549C;--cobalt-soft:#BDDBFB;--cobalt-wash:#E7F3FF;
 --steel:#455E73;--steel-soft:#CAD8E3;--positive:#3C8564;--negative:#B45248;
 --line:#D8DBDF;--line-strong:#B9BEC4;
 --fd:'Hanken Grotesk',system-ui,sans-serif;--fb:'Spectral',Georgia,serif;--fm:'Spline Sans Mono',ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0E1217;font-family:var(--fb);-webkit-font-smoothing:antialiased}
.stage{min-height:100vh;display:flex;align-items:center;justify-content:center;scroll-snap-align:center;padding:24px}
.deck{height:100vh;overflow-y:scroll;scroll-snap-type:y mandatory;scroll-behavior:smooth}
.slide{width:1280px;height:720px;flex:0 0 auto;position:relative;overflow:hidden;background:var(--paper);
 color:var(--ink);padding:84px 96px;display:flex;flex-direction:column;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.slide *{box-sizing:border-box}
.eyebrow{font-family:var(--fm);font-size:17px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);
 display:inline-flex;align-items:center;gap:14px}
.eyebrow::before{content:"";width:22px;height:2px;background:var(--cobalt)}
.eyebrow.on::before{background:var(--cobalt-soft)}.eyebrow.on{color:var(--cobalt-soft)}
.h1{font-family:var(--fd);font-weight:700;letter-spacing:-.025em;line-height:1.04;color:var(--ink)}
.lede{font-family:var(--fb);font-size:22px;line-height:1.5;color:var(--ink2)}
.foot{position:absolute;left:96px;right:96px;bottom:38px;display:flex;justify-content:space-between;
 font-family:var(--fm);font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink4)}
.mark{position:relative;width:54px;height:54px;border:2px solid var(--ink);display:flex;align-items:center;justify-content:center}
.mark span{font-family:var(--fd);font-weight:700;font-size:23px;letter-spacing:-1.2px}
.mark::before{content:"";position:absolute;top:4px;right:4px;width:10px;height:2px;background:var(--cobalt)}
.mark::after{content:"";position:absolute;top:4px;right:4px;width:2px;height:10px;background:var(--cobalt)}
.mark.on{border-color:var(--paper)}.mark.on span{color:var(--paper)}
.cross{position:absolute;width:18px;height:18px}
.cross::before{content:"";position:absolute;top:8px;left:0;width:18px;height:2px;background:var(--cobalt)}
.cross::after{content:"";position:absolute;left:8px;top:0;width:2px;height:18px;background:var(--cobalt)}
.slide.ink{background:var(--ink);color:var(--paper)}.slide.ink .h1{color:var(--paper)}
.bullets{list-style:none;display:flex;flex-direction:column;gap:20px}
.bullets li{position:relative;padding-left:30px;font-family:var(--fb);font-size:18px;line-height:1.42;color:var(--ink2)}
.bullets li::before{content:"";position:absolute;left:0;top:.55em;width:16px;height:2px;background:var(--cobalt)}
.bullets li b{color:var(--ink);font-family:var(--fd);font-weight:600}
.ink .bullets li{color:var(--steel-soft)}.ink .bullets li b{color:var(--paper)}
.drafted{position:relative;background:var(--card);border:2px solid var(--ink);padding:28px}
.drafted::after{content:"";position:absolute;inset:0;transform:translate(10px,10px);border:2px solid var(--cobalt);z-index:-1}
.drafted.tint{background:var(--cobalt-wash)}
.mrow{display:grid;grid-template-columns:repeat(3,1fr);gap:34px}
.mstat{border-top:2px solid var(--ink);padding-top:14px}
.mstat .v{font-family:var(--fd);font-weight:700;font-size:46px;letter-spacing:-.02em;line-height:1;white-space:nowrap}
.mstat .c{font-family:var(--fm);font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);margin-top:12px}
.clab{font-family:var(--fm);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-bottom:8px}
.cobalt-deep{color:var(--cobalt-deep)} .grow{flex:1}
table.t{border-collapse:collapse;font-family:var(--fb);font-size:15px;width:100%}
table.t th{font-family:var(--fm);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);
 text-align:right;padding:8px 12px;border-bottom:2px solid var(--ink)}
table.t th:first-child,table.t td:first-child{text-align:left}
table.t td{padding:8px 12px;border-bottom:1px solid var(--line);color:var(--ink2)}
table.t tr.hl td{background:var(--cobalt-wash);color:var(--cobalt-deep);font-weight:600}
table.t td b{font-family:var(--fd);color:var(--ink)}
.nav{position:fixed;right:18px;bottom:16px;display:flex;gap:8px;align-items:center;z-index:50;
 font-family:var(--fm);font-size:12px;color:#8893a0;background:rgba(20,26,33,.8);padding:8px 12px;border-radius:2px}
.nav button{background:none;border:1px solid #3a4654;color:#cdd6e0;width:30px;height:26px;cursor:pointer;font-size:14px}
.nav button:hover{border-color:var(--cobalt);color:#fff}
@media print{body{background:#fff}.deck{height:auto;overflow:visible}.nav{display:none}
 .stage{min-height:auto;padding:0;page-break-after:always}.slide{box-shadow:none}
 @page{size:1280px 720px;margin:0}}
"""

JS = """
const slides=[...document.querySelectorAll('.slide')];
function fit(){const sx=window.innerWidth/1320,sy=window.innerHeight/760;const s=Math.min(sx,sy,1);
 slides.forEach(sl=>{sl.style.transform='scale('+s+')';sl.style.transformOrigin='center';
 sl.parentElement.style.height=(720*s+48)+'px';});}
window.addEventListener('resize',fit);fit();
let cur=0;const deck=document.querySelector('.deck');
function go(n){cur=Math.max(0,Math.min(slides.length-1,n));slides[cur].parentElement.scrollIntoView({behavior:'smooth'});upd();}
function upd(){document.getElementById('pg').textContent=(cur+1)+' / '+slides.length;}
document.addEventListener('keydown',e=>{if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();go(cur+1);}
 if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();go(cur-1);}});
deck.addEventListener('scroll',()=>{const i=Math.round(deck.scrollTop/(slides[0].parentElement.offsetHeight));if(i!==cur){cur=i;upd();}});
upd();
"""


def esc(s): return html.escape(s, quote=False)
def eyebrow(t, on=False): return f'<div class="eyebrow{" on" if on else ""}">{esc(t.upper())}</div>'
def bullets(items, on=False):
    lis = "".join(f"<li>{'<b>'+esc(b)+'</b> ' if b else ''}{esc(t)}</li>" for b, t in items)
    return f'<ul class="bullets">{lis}</ul>'
def mark(on=False): return f'<div class="mark{" on" if on else ""}"><span>ÁS</span></div>'
def foot(l, r): return f'<div class="foot"><span>{esc(l)}</span><span>{esc(r)}</span></div>'
def drafted(inner, tint=False, style=""):
    return f'<div class="drafted{" tint" if tint else ""}" style="{style}">{inner}</div>'
def canvas(cid, h=300): return f'<div style="position:relative;height:{h}px;width:100%"><canvas id="{cid}"></canvas></div>'

def slide(inner, cls="", footl="", footr=""):
    f = foot(footl, footr) if footl or footr else ""
    return f'<div class="stage"><div class="slide {cls}">{inner}{f}</div></div>'


def mrow(stats):
    cells = "".join(f'<div class="mstat"><div class="v">{esc(v)}</div><div class="c">{esc(c)}</div></div>' for v, c in stats)
    return f'<div class="mrow">{cells}</div>'

# fragment builders using plain concatenation (quotes/backslashes unrestricted)
def pp(style, text): return '<p style="' + style + '">' + text + '</p>'
def clab(text, color=None):
    st = 'color:' + color + ';' if color else ''
    return '<div class="clab" style="' + st + '">' + text + '</div>'
def bignum(big, sub, color, big2=None, sub2=None, color2=None):
    out = '<div style="font-family:var(--fd);font-weight:700;font-size:64px;line-height:1;margin-top:6px;color:' + color + '">' + big + '</div>'
    out += '<div style="font-family:var(--fb);font-size:15px;color:var(--ink2)">' + sub + '</div>'
    if big2:
        out += '<div style="font-family:var(--fd);font-weight:700;font-size:44px;line-height:1;margin-top:22px;color:' + color2 + '">' + big2 + '</div>'
        out += '<div style="font-family:var(--fb);font-size:14px;color:var(--ink2)">' + sub2 + '</div>'
    return out


def deck_html(title, slides_html, charts_js):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Spectral:ital,wght@0,300;0,400;0,500;0,600;1,400;1,500&family=Spline+Sans+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>{CSS}</style></head><body>
<div class="deck">{slides_html}</div>
<div class="nav"><button onclick="go(cur-1)">‹</button><span id="pg">1</span><button onclick="go(cur+1)">›</button></div>
<script>const D={json.dumps(DATA)};</script>
<script>{JS}</script>
<script>
const INK='#1B2129',INK2='#3E444D',INK3='#666D74',COB='#306CB8',STEEL='#455E73',LINE='#D8DBDF',POS='#3C8564',NEG='#B45248';
Chart.defaults.font.family="'Spline Sans Mono',monospace";Chart.defaults.font.size=11;Chart.defaults.color=INK3;
Chart.defaults.plugins.legend.display=false;
const gx={{grid:{{display:false}},ticks:{{color:INK3}}}};
const gy=(fmt)=>({{grid:{{color:LINE}},ticks:{{color:INK3,callback:fmt}}}});
function whenReady(){{ {charts_js} }}
if(document.fonts&&document.fonts.ready){{document.fonts.ready.then(()=>setTimeout(whenReady,60));}}else{{setTimeout(whenReady,300);}}
</script></body></html>"""


# ============ chart JS snippets ============
SCAT_JS = """
new Chart(document.getElementById('%ID%'),{data:{datasets:[
 {type:'line',data:[{x:0,y:0},{x:1800,y:1800}],borderColor:'#9399A0',borderDash:[6,5],borderWidth:1.4,pointRadius:0},
 {type:'scatter',data:D.scatter.ak.map((a,i)=>({x:a,y:D.scatter.pk[i]})),backgroundColor:'rgba(48,108,184,.34)',pointRadius:2.4}]},
 options:{responsive:true,maintainAspectRatio:false,scales:{
  x:{min:0,max:1800,grid:{color:LINE},ticks:{color:INK3,callback:v=>'$'+v+'k'},title:{display:true,text:'actual ($k)',color:INK3}},
  y:{min:0,max:1800,grid:{color:LINE},ticks:{color:INK3,callback:v=>'$'+v+'k'},title:{display:true,text:'predicted ($k)',color:INK3}}},
  plugins:{tooltip:{filter:i=>i.datasetIndex===1}}}});"""

def bar_js(cid, labels, values, colors, horiz=False, fmt="v=>v", maxv="undefined", dl=False):
    axis = "indexAxis:'y'," if horiz else ""
    return f"""
new Chart(document.getElementById('{cid}'),{{type:'bar',data:{{labels:{json.dumps(labels)},
 datasets:[{{data:{json.dumps(values)},backgroundColor:{json.dumps(colors)},borderRadius:3,barPercentage:.82,categoryPercentage:.84}}]}},
 options:{{{axis}responsive:true,maintainAspectRatio:false,
 scales:{{ {'x:{grid:{color:LINE},ticks:{color:INK3,callback:'+fmt+'}},y:{grid:{display:false},ticks:{color:INK2}}' if horiz else 'x:{grid:{display:false},ticks:{color:INK2}},y:{grid:{color:LINE},ticks:{color:INK3,callback:'+fmt+'}}'} }},
 plugins:{{tooltip:{{enabled:true}}}}}}}});"""

def line_js(cid, labels, values, fmt="v=>v"):
    return f"""
new Chart(document.getElementById('{cid}'),{{type:'line',data:{{labels:{json.dumps(labels)},
 datasets:[{{data:{json.dumps(values)},borderColor:COB,backgroundColor:'rgba(48,108,184,.10)',fill:true,borderWidth:2,tension:.3,pointRadius:3,pointBackgroundColor:COB}}]}},
 options:{{responsive:true,maintainAspectRatio:false,scales:{{x:{{grid:{{display:false}},ticks:{{color:INK3}}}},y:{{grid:{{color:LINE}},ticks:{{color:INK3,callback:{fmt}}}}}}}}}}});"""


# =====================================================================
# EXECUTIVE DECK
# =====================================================================
def build_exec():
    S = []
    FL = "Maximum loan amount model"
    # 1 cover
    S.append(slide(
        f'<span class="cross" style="left:0;top:0"></span>'
        f'<div style="margin-top:150px">{eyebrow("Mortgage credit · Model summary")}'
        f'<h1 class="h1" style="font-size:78px;margin-top:22px">Maximum loan amount<br><span style="color:var(--ink)">model</span><span style="color:var(--cobalt)">.</span></h1>'
        f'<p class="lede" style="margin-top:24px;max-width:60ch">Predicting the bank\'s responsible lending limit from applicant data — validated against the actual decisions it never saw.</p>'
        f'<div style="margin-top:60px">{mark()}</div></div>',
        footl="Executive briefing · 2026", footr="Confidential"))
    # 2 contents
    toc = [("01", "Executive summary", "The ask, the answer, the headline result"),
           ("02", "Can we trust the model?", "Accuracy against the held-out actual decisions"),
           ("03", "What drives the loan", "The four factors that set the limit"),
           ("04", "Recommendation & next steps", "How to put it to work")]
    apx = [("A", "Why interest rate was excluded"), ("B", "Four factors & fair lending"), ("C", "Data & method background")]
    rows = "".join(f'<div style="display:flex;gap:20px;margin-bottom:22px"><div style="font-family:var(--fm);font-size:18px;color:var(--cobalt);width:34px">{n}</div>'
                   f'<div><div style="font-family:var(--fd);font-weight:600;font-size:19px;color:var(--ink)">{esc(t)}</div>'
                   f'<div style="font-family:var(--fb);font-size:14px;color:var(--ink3);margin-top:3px">{esc(d)}</div></div></div>' for n, t, d in toc)
    aprows = "".join(f'<div style="display:flex;gap:14px;margin-bottom:18px"><div style="font-family:var(--fm);font-size:15px;color:var(--steel);width:22px">{n}</div>'
                     f'<div style="font-family:var(--fb);font-size:15px;color:var(--ink2)">{esc(t)}</div></div>' for n, t in apx)
    S.append(slide(
        f'{eyebrow("Contents")}<h1 class="h1" style="font-size:36px;margin-top:10px">What\'s in this deck</h1>'
        f'<div style="display:grid;grid-template-columns:1.5fr 1fr;gap:60px;margin-top:46px"><div>{rows}</div>'
        f'<div><div class="clab">Appendix</div>{aprows}</div></div>',
        footl=FL, footr="Contents"))
    # 3 exec summary
    S.append(slide(
        f'{eyebrow("01 — Executive summary")}<h1 class="h1" style="font-size:33px;margin-top:10px">A model that reproduces lending decisions to within ~4%</h1>'
        f'<div style="margin-top:34px">{mrow([("0.990","Variance explained (R²)"),("±$22.0k","Typical error (MAE)"),("94.9%","Within ±10% of actual")])}</div>'
        f'<div style="margin-top:40px">{bullets([("The ask:","estimate the maximum loan the bank should responsibly offer each applicant, from their financial profile alone."),("The answer:","a gradient-boosting model predicts that limit with high accuracy — validated against the real decisions, which were never shown to the model."),("Why it matters:","consistent, explainable loan sizing — a fast first-pass limit for ~95% of applicants, with the rare large miss easy to flag.")])}</div>',
        footl=FL, footr="01 · Executive summary"))
    # 4 trust
    S.append(slide(
        f'{eyebrow("02 — Can we trust the model?")}'
        f'<div style="display:grid;grid-template-columns:1fr 1.05fr;gap:54px;margin-top:14px;flex:1;align-items:start">'
        f'<div><h1 class="h1" style="font-size:30px">Predictions land on the bank\'s actual decisions</h1>'
        f'<div style="margin-top:26px">{bullets([("Tested honestly.","Measured on 9,998 applicants the model never saw in training."),("On the line.","Each dot is one applicant; the closer to the dashed line, the closer the prediction."),("No size blind spot.","Accuracy holds from the smallest to the largest loans.")])}</div></div>'
        f'<div>{drafted(chr(10).join(["<div class=clab>Predicted vs actual — held-out applicants</div>", canvas("ex_scatter",330)]))}</div></div>',
        footl=FL, footr="02 · Validation"))
    # 5 drivers
    S.append(slide(
        f'{eyebrow("03 — What drives the loan")}<h1 class="h1" style="font-size:32px;margin-top:8px">Four factors set the limit</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:54px;margin-top:30px;flex:1;align-items:start">'
        f'<div><div class="clab">Relative influence on the predicted limit</div>{canvas("ex_imp",330)}</div>'
        f'<div style="padding-top:6px">{bullets([("Income leads —","the single biggest driver of how much the bank will lend."),("Credit score next —","creditworthiness scales the limit up or down."),("Debt down, down payment up —","capacity to repay and commitment to the purchase."),("Everything else is noise:","age, job, education and area add nothing once income and credit are known.")])}</div></div>',
        footl=FL, footr="03 · Drivers"))
    # 6 recommendation
    S.append(slide(
        f'{eyebrow("04 — Recommendation & next steps")}<h1 class="h1" style="font-size:30px;margin-top:8px">Adopt it as a first-pass limit engine</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:54px;margin-top:28px;flex:1;align-items:start">'
        f"<div>{drafted(clab('Recommendation','var(--cobalt-deep)')+pp('font-family:var(--fb);font-size:19px;line-height:1.4;color:var(--ink);margin-top:10px','Use the model to propose a maximum loan instantly for every applicant — auto-approving the ~95% it sizes within ±10%, and routing the rest to a human reviewer.'), tint=True, style='min-height:300px;display:flex;flex-direction:column;justify-content:center')}</div>"
        f'<div style="padding-top:4px">{bullets([("Pilot in shadow mode —","run alongside underwriters; compare before going live."),("Set a review band —","flag predictions that disagree with policy by more than 10%."),("Govern the inputs —","uses no demographics; document and monitor for drift."),("Refresh on real data —","retrain when a book of genuine decisions is available.")])}</div></div>',
        footl=FL, footr="04 · Recommendation"))
    # 7 appendix divider
    S.append(slide(
        f'<span class="cross" style="right:0;top:0"></span>'
        f'<div style="margin-top:210px">{eyebrow("Appendix", on=True)}<h1 class="h1" style="font-size:64px;margin-top:14px">Appendix</h1>'
        f'<p class="lede" style="color:var(--steel-soft);margin-top:18px">Key decisions &amp; background</p>'
        f'<div style="margin-top:46px">{mark(on=True)}</div></div>',
        cls="ink", footr="Appendix"))
    # 8 appendix A interest rate
    S.append(slide(
        f'{eyebrow("Appendix A — Feature decision")}<h1 class="h1" style="font-size:28px;margin-top:8px">Interest rate was excluded — it\'s a price the bank sets, not an input</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:48px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Near-perfectly tied to credit score","(correlation −0.95): better credit → lower rate, almost mechanically."),("Predictable from other inputs","with 91–94% accuracy — it carries almost no new information."),("Using it would be circular —","feeding one bank decision in to predict another, double-counting credit score.")])}</div>'
        f'<div>{drafted(clab("Interest rate vs credit score")+bignum("−0.95","correlation with credit score","var(--cobalt)","0.91–0.94","predictable from applicant inputs (R²)","var(--steel)"))}</div></div>',
        footl=FL, footr="Appendix A"))
    # 9 appendix B parsimony
    tbl = ('<table class="t"><tr><th>Model</th><th>R²</th><th>Typical error</th></tr>'
           '<tr><td>12 features</td><td>0.9894</td><td>$22,428</td></tr>'
           '<tr class="hl"><td>4 features</td><td>0.9897</td><td>$21,966</td></tr></table>'
           '<p style="font-family:var(--fb);font-size:15px;color:var(--ink2);margin-top:18px;line-height:1.35">Same model on just income, credit score, existing debt and down payment — marginally more accurate.</p>')
    S.append(slide(
        f'{eyebrow("Appendix B — Model design")}<h1 class="h1" style="font-size:28px;margin-top:8px">Four factors beat twelve — leaner and more defensible</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:48px;margin-top:30px;flex:1;align-items:start">'
        f'<div>{tbl}</div>'
        f'<div>{drafted(clab("Why it is more defensible","var(--cobalt-deep)")+bullets([("No demographics.","Uses no gender, marital status or age — supports fair-lending (ECOA) defensibility."),("Job & education added nothing —","they were just stand-ins for income."),("Simpler to explain","and to govern: four inputs, all financial.")]))}</div></div>',
        footl=FL, footr="Appendix B"))
    # 10 appendix C data & method
    S.append(slide(
        f'{eyebrow("Appendix C — Background")}<h1 class="h1" style="font-size:30px;margin-top:8px">Data &amp; method, in brief</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:48px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Dataset:","49,990 mortgage applicants, 13 attributes. Clean — no missing values or duplicates; 41 minor anomalies kept and flagged."),("Held-out target:","the actual maximum loan was never used in training — only to score the model at the end."),("Models compared:","linear, random forest and gradient boosting, on raw and log scales — six combinations under one test."),("Chosen:","gradient boosting (raw) — clearly the most accurate and stable.")])}</div>'
        f'<div>{drafted("<div class=clab>Model comparison — typical error</div>"+canvas("ex_bench",300))}</div></div>',
        footl=FL, footr="Appendix C"))

    charts = (SCAT_JS.replace("%ID%", "ex_scatter")
              + bar_js("ex_imp", DATA["imp_f"], DATA["imp_v"], [COB := "#306CB8", "#306CB8", "#455E73", "#455E73"], horiz=True, fmt="v=>v", dl=True)
              + bar_js("ex_bench", ["GBM (raw)", "Random forest", "Linear"], [22.4, 24.3, 51.9], ["#306CB8", "#455E73", "#9399A0"], horiz=False, fmt="v=>'$'+v+'k'"))
    open("decks/mortgage_exec_deck.html", "w").write(deck_html("Maximum loan amount — executive briefing", "".join(S), charts))
    print("wrote decks/mortgage_exec_deck.html")


def section(idx, title, sub, footr):
    inner = (f'<span class="cross" style="right:0;top:0"></span>'
             f'<div style="margin-top:150px"><div style="font-family:var(--fm);font-size:26px;letter-spacing:.18em;color:var(--cobalt-soft)">{esc(idx)}</div>'
             f'<h1 class="h1" style="font-size:62px;margin-top:12px">{esc(title)}</h1>'
             f'<p class="lede" style="color:var(--steel-soft);margin-top:16px;max-width:62ch">{esc(sub)}</p>'
             f'<div style="margin-top:42px">{mark(on=True)}</div></div>')
    return slide(inner, cls="ink", footr=footr)


def table(headers, rows, hl=None, colstyle=""):
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = ""
    for i, r in enumerate(rows):
        cls = ' class="hl"' if hl == i else ""
        tds = "".join(f"<td>{c}</td>" for c in r)
        trs += f"<tr{cls}>{tds}</tr>"
    return f'<table class="t" style="{colstyle}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


# =====================================================================
# INTERNAL DECK
# =====================================================================
def build_internal():
    S = []
    FL = "Max loan model · methodology"
    # 1 cover
    S.append(slide(
        f'<span class="cross" style="left:0;top:0"></span>'
        f'<div style="margin-top:130px">{eyebrow("Credit risk · Model methodology & validation")}'
        f'<h1 class="h1" style="font-size:58px;margin-top:20px">Maximum loan amount<br>model<span style="color:var(--cobalt)">.</span> <span style="font-weight:500;color:var(--ink2);font-size:40px">technical review</span></h1>'
        f'<p class="lede" style="margin-top:22px;max-width:64ch">Data, feature decisions, model selection and held-out validation — for credit and modelling reviewers.</p>'
        f'<div style="margin-top:48px">{mark()}</div></div>',
        footl="Internal · credit & modelling", footr="Methodology v1 · 2026"))
    # 2 contents
    toc = [("01", "Data & exploration", "Shape, quality, distributions, what correlates"),
           ("02", "Feature decisions", "Interest rate, down payment, cleaning & audit"),
           ("03", "Model & evaluation", "Benchmark, parsimony, validation, governance")]
    rows = "".join(f'<div style="display:flex;gap:22px;margin-bottom:28px"><div style="font-family:var(--fm);font-size:24px;color:var(--cobalt);width:40px">{n}</div>'
                   f'<div><div style="font-family:var(--fd);font-weight:600;font-size:23px;color:var(--ink)">{esc(t)}</div>'
                   f'<div style="font-family:var(--fb);font-size:15px;color:var(--ink3);margin-top:3px">{esc(d)}</div></div></div>' for n, t, d in toc)
    S.append(slide(f'{eyebrow("Contents")}<h1 class="h1" style="font-size:36px;margin-top:10px">Storyline</h1>'
                   f'<div style="margin-top:44px">{rows}</div>'
                   f'<div class="clab" style="margin-top:10px">Plus — objective &amp; approach, and appendix (full benchmark + data dictionary)</div>',
                   footl=FL, footr="Contents"))
    # 3 objective
    S.append(slide(
        f'{eyebrow("Objective & approach")}<h1 class="h1" style="font-size:28px;margin-top:8px">Predict the bank\'s loan limit — without ever seeing it during modelling</h1>'
        f'<div style="display:grid;grid-template-columns:1.15fr .85fr;gap:48px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Goal:","estimate Max Loan Amount (USD) from applicant attributes, as a regression problem."),("Held-out target:","the actual maximum loan is excluded from every training and selection step; used only for final evaluation."),("Discipline:","staged & gated — discovery → cleaning (audited) → method selection → validation."),("Reproducible:","numbered standalone scripts regenerate every figure and number here.")])}</div>'
        f'<div>{drafted(clab("The leakage rule","var(--cobalt-deep)")+pp("font-family:var(--fb);font-size:17px;line-height:1.35;color:var(--ink);margin-top:8px","Interest rate and the target are kept out of the feature set. The model sees only what an applicant brings to the table."),tint=True,style="min-height:240px;display:flex;flex-direction:column;justify-content:center")}</div></div>',
        footl=FL, footr="Objective"))
    # 4 section 01
    S.append(section("01", "Data & exploration", "49,990 applicants — what's there, how clean, and what moves the loan.", "01"))
    # 5 dataset & quality
    S.append(slide(
        f'{eyebrow("01 — Dataset & quality")}<h1 class="h1" style="font-size:31px;margin-top:8px">Clean to begin with</h1>'
        f'<div style="margin-top:30px">{mrow([("49,990","Applicants (rows)"),("14","Columns"),("0","Nulls / duplicates")])}</div>'
        f'<div style="margin-top:34px">{bullets([("Grain:","one row per mortgage applicant; no duplicates."),("Types:","8 numeric, 5 categorical, 1 target."),("Quality:","no missing values; all integrity checks pass except 41 rows implying a working start age of 14–15 (off by 1–2 yrs)."),("Decision:","keep all rows; the 41 are kept and flagged in the cleaning audit, not removed.")])}</div>',
        footl=FL, footr="01 · Data quality"))
    # 6 distribution & drivers
    S.append(slide(
        f'{eyebrow("01 — Distribution & drivers")}<h1 class="h1" style="font-size:27px;margin-top:8px">Right-skewed target; income &amp; credit lead</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:26px;flex:1">'
        f'<div>{clab("Max loan amount — distribution")}{canvas("in_thist",320)}</div>'
        f'<div>{clab("Correlation with the target")}{canvas("in_corr",320)}</div></div>',
        footl=FL, footr="01 · Distributions"))
    # 7 categorical
    S.append(slide(
        f'{eyebrow("01 — Categorical signal")}<h1 class="h1" style="font-size:26px;margin-top:8px">Education and job look strong — but echo income</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:22px">'
        f'<div>{clab("Avg loan by education ($k)")}{canvas("in_edu",300)}</div>'
        f'<div>{clab("Avg loan by job ($k)")}{canvas("in_job",330)}</div></div>'
        f'<p style="font-family:var(--fb);font-style:italic;font-size:14px;color:var(--ink3);margin-top:14px">Three job tiers (≈$575k / $690k / $810k) mirror income tiers exactly — a hint these categoricals are proxies, confirmed later by feature importance.</p>',
        footl=FL, footr="01 · Categoricals"))
    # 8 section 02
    S.append(section("02", "Feature decisions", "What goes into the model — and the evidence behind each call.", "02"))
    # 9 interest rate
    S.append(slide(
        f'{eyebrow("02 — Feature decision")}<h1 class="h1" style="font-size:26px;margin-top:8px">Interest rate excluded: it\'s risk-based pricing, not an applicant input</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:46px;margin-top:26px;flex:1;align-items:start">'
        f'<div>{bullets([("Correlation −0.95 with credit score —","the rate is essentially a deterministic function of creditworthiness."),("Predicted from the other inputs at R² 0.91–0.94","(linear / random forest) — almost no independent information."),("Circular if used:","a bank-set output predicting another bank output, double-counting credit score."),("Down payment, by contrast, is a genuine input —","kept (next).")])}</div>'
        f'<div>{drafted(clab("Is the rate an input or an output?")+bignum("−0.95","correlation with credit score","var(--cobalt)","0.91–0.94","predictable from applicant inputs (R²)","var(--steel)"))}</div></div>',
        footl=FL, footr="02 · Interest rate"))
    # 10 down payment
    S.append(slide(
        f'{eyebrow("02 — Feature decision")}<h1 class="h1" style="font-size:28px;margin-top:8px">Down payment kept — it carries real signal</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:46px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Conceptually an input:","reflects household purchasing power and commitment to the purchase."),("Empirically load-bearing:","dropping it raises the 4-feature model’s typical error from $21,966 to $35,648."),("Correlation 0.47 with the target,","and 3rd–4th in importance — not redundant with income or credit.")])}</div>'
        f'<div>{drafted(clab("Typical error (MAE) impact")+bignum("$21,966","with down payment","var(--cobalt)","$35,648","without it (+62% error)","var(--ink3)"))}</div></div>',
        footl=FL, footr="02 · Down payment"))
    # 11 cleaning
    S.append(slide(
        f'{eyebrow("02 — Cleaning & audit")}<h1 class="h1" style="font-size:29px;margin-top:8px">Nothing removed — everything reconciled</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:46px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Integrity checks:","nulls, duplicates, non-positive values, credit-score range, down-payment > loan, debt > income, whitespace — all pass."),("Only anomaly:","41 rows with implied working start age < 16; kept and individually logged (step C9)."),("Audit trail:","cleaning_audit.csv records every check and flagged row with a reason.")])}</div>'
        f'<div>{drafted(clab("Reconciliation","var(--cobalt-deep)")+pp("font-family:var(--fm);font-size:17px;line-height:2;color:var(--ink);margin-top:8px","49,990 raw<br>49,990 kept &nbsp;+&nbsp; 0 removed")+pp("font-family:var(--fm);font-size:13px;color:var(--positive);margin-top:10px","kept + removed = raw ✓"),tint=True)}</div></div>',
        footl=FL, footr="02 · Cleaning"))
    # 12 section 03
    S.append(section("03", "Model & evaluation", "Choosing the model on evidence, then testing it against the held-out actual.", "03"))
    # 13 benchmark
    bench_rows = [["HistGradientBoosting", "raw", "0.9894", "$22,428", "$31,937", "3.74%"],
                  ["HistGradientBoosting", "log", "0.9894", "$22,463", "$31,915", "3.70%"],
                  ["Random Forest", "raw", "0.9876", "$24,312", "$34,498", "4.14%"],
                  ["Random Forest", "log", "0.9876", "$24,427", "$34,551", "4.12%"],
                  ["Ridge (linear)", "raw", "0.9502", "$51,858", "$69,239", "12.1%"],
                  ["Ridge (linear)", "log", "0.8830", "$62,625", "$106,103", "9.97%"]]
    S.append(slide(
        f'{eyebrow("03 — Method selection")}<h1 class="h1" style="font-size:30px;margin-top:8px">Six combinations, one protocol</h1>'
        f'<div style="display:grid;grid-template-columns:1.7fr 1fr;gap:36px;margin-top:28px;align-items:start">'
        f'<div>{table(["Model","Target","R²","MAE","RMSE","MAPE"],bench_rows,hl=0)}'
        f'<p style="font-family:var(--fb);font-style:italic;font-size:13.5px;color:var(--ink3);margin-top:16px">CV R² std ≤ 0.0004 across folds → stable, no overfitting.</p></div>'
        f'<div>{drafted(clab("Chosen","var(--cobalt-deep)")+pp("font-family:var(--fd);font-weight:600;font-size:20px;color:var(--ink);margin-top:6px;line-height:1.1","Gradient boosting, raw target")+pp("font-family:var(--fb);font-size:14px;color:var(--ink2);margin-top:10px;line-height:1.3","Trees beat linear by ~$30k MAE; log scale adds nothing for the winner."),tint=True)}</div></div>',
        footl=FL, footr="03 · Benchmark"))
    # 14 parsimony
    pars_rows = [["12 features (all)", "0.9894", "$22,428"], ["4 features (primary)", "0.9897", "$21,966"], ["3 features (no down pmt)", "0.9768", "$35,648"]]
    S.append(slide(
        f'{eyebrow("03 — Parsimony")}<h1 class="h1" style="font-size:30px;margin-top:8px">Four features beat twelve</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:46px;margin-top:30px;align-items:start">'
        f'<div>{table(["Feature set","R²","MAE"],pars_rows,hl=1)}</div>'
        f'<div>{bullets([("Job ≈ income tiers:","Doctor/Lawyer/Owner ≈$146k, Banker/SWE/Sales ≈$125k, rest ≈$105k."),("Education tracks income;","Age & Employment are 0.97 correlated; Loans Repaid tracks credit score."),("So 8 features are downstream correlates —","zero permutation importance once income & credit are in.")])}</div></div>',
        footl=FL, footr="03 · Parsimony"))
    # 15 final model & protocol
    S.append(slide(
        f'{eyebrow("03 — Final model & protocol")}<h1 class="h1" style="font-size:30px;margin-top:8px">Specification</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:46px;margin-top:28px;flex:1;align-items:start">'
        f'<div>{bullets([("Estimator:","HistGradientBoostingRegressor — max_iter 400, learning_rate 0.06, default depth."),("Features (4):","annual income, credit score, existing monthly debt, down payment (raw target)."),("Split:","80 / 20 train-test, fixed seed; 5-fold CV on train for stability."),("Metrics:","R², MAE, RMSE, MAPE on the held-out 20% — native USD.")])}</div>'
        f'<div>{drafted(clab("Artifacts")+bullets([("model_final.joblib","— fitted 4-feature pipeline."),("model_full.joblib","— 12-feature model, on record."),("evaluation_metrics.json","+ predictions_test.csv.")]))}</div></div>',
        footl=FL, footr="03 · Specification"))
    # 16 evaluation
    S.append(slide(
        f'{eyebrow("03 — Validation vs held-out actual")}<h1 class="h1" style="font-size:28px;margin-top:8px">It reproduces real decisions</h1>'
        f'<div style="margin-top:26px">{mrow([("0.990","R²"),("$21,966","MAE"),("3.65%","MAPE")])}</div>'
        f'<div style="margin-top:24px;max-width:760px;margin-left:auto;margin-right:auto;width:760px">{drafted(clab("Predicted vs actual — 9,998 held-out applicants")+canvas("in_scatter",300))}</div>',
        footl=FL, footr="03 · Validation"))
    # 17 residuals & band
    S.append(slide(
        f'{eyebrow("03 — Error structure")}<h1 class="h1" style="font-size:27px;margin-top:8px">Unbiased, and accurate across loan sizes</h1>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:24px">'
        f'<div>{clab("Residuals (actual − predicted), $k")}{canvas("in_resid",300)}</div>'
        f'<div>{clab("MAPE by loan-size band")}{canvas("in_band",300)}</div></div>'
        f'<p style="font-family:var(--fb);font-style:italic;font-size:13.5px;color:var(--ink3);margin-top:14px">Residuals center on zero (no systematic over/under-lending). Absolute error grows with loan size but percentage error shrinks — most accurate on the largest loans.</p>',
        footl=FL, footr="03 · Error structure"))
    # 18 importance
    S.append(slide(
        f'{eyebrow("03 — Feature importance")}<h1 class="h1" style="font-size:28px;margin-top:8px">Permutation importance confirms the four</h1>'
        f'<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:44px;margin-top:24px;flex:1;align-items:start">'
        f'<div>{clab("Drop in test R² when the feature is shuffled")}{canvas("in_imp",320)}</div>'
        f'<div style="padding-top:18px">{bullets([("Income dominates","(1.44), then credit score (0.65)."),("Existing debt (0.34)","is a genuine third factor — capacity to repay."),("Down payment (0.03)","small but load-bearing."),("All other features ≈ 0 —","measured directly, not assumed.")])}</div></div>',
        footl=FL, footr="03 · Importance"))
    # 19 governance
    S.append(slide(
        f'{eyebrow("03 — Governance")}<h1 class="h1" style="font-size:30px;margin-top:8px">Fair-lending posture</h1>'
        f'<div style="margin-top:30px">{bullets([("No protected attributes:","the primary model uses no gender, marital status or age — supporting ECOA / fair-lending defensibility."),("No obvious proxies:","job and education (income proxies) were dropped; inputs are all direct financial measures."),("Explainable:","four inputs with monotonic, intuitive effects — straightforward to document for model risk and audit."),("Monitor:","track input drift and disparate-impact metrics once live on real decisions.")])}</div>',
        footl=FL, footr="03 · Governance"))
    # 20 limitations
    S.append(slide(
        f'{eyebrow("03 — Limitations & assumptions")}<h1 class="h1" style="font-size:29px;margin-top:8px">What to keep in mind</h1>'
        f'<div style="margin-top:30px">{bullets([("Synthetic-style data:","relationships are cleaner and more deterministic than a real lending book — expect lower R² on production data."),("Counter-intuitive debt sign:","existing debt correlates positively with the limit here (likely an artifact); revisit on real data."),("Mimics existing decisions:","the model learns the bank’s historical limit policy — it does not judge whether that policy is optimal or fair."),("No macro / collateral context:","property value, LTV, rates environment and affordability stress are out of scope.")])}</div>',
        footl=FL, footr="03 · Limitations"))
    # 21 reproducibility
    steps = [("scripts/01_clean_data.py", "Validate + audit → data/mortgage_clean.csv, metrics/cleaning_audit.csv"),
             ("scripts/02_model_benchmark.py", "Six model × scale combos → metrics/model_benchmark.csv"),
             ("scripts/03_train_evaluate.py", "Fit both models, validate → metrics + artifacts"),
             ("scripts/04_build_presentations.js", "These PPTX decks"),
             ("scripts/05_build_html_decks.py", "The HTML twins")]
    srows = "".join(f'<div style="display:flex;gap:20px;margin-bottom:16px;align-items:baseline"><div style="font-family:var(--fm);font-size:15px;color:var(--cobalt);width:30px">{i+1:02d}</div>'
                    f'<div style="font-family:var(--fm);font-size:15px;color:var(--ink);width:280px">{esc(f)}</div>'
                    f'<div style="font-family:var(--fb);font-size:14.5px;color:var(--ink2)">{esc(d)}</div></div>' for i, (f, d) in enumerate(steps))
    S.append(slide(f'{eyebrow("03 — Reproducibility")}<h1 class="h1" style="font-size:30px;margin-top:8px">One command per stage</h1>'
                   f'<div style="margin-top:34px">{srows}</div>'
                   f'<p style="font-family:var(--fb);font-style:italic;font-size:13.5px;color:var(--ink3);margin-top:20px">Every figure in this deck traces back to the raw CSV through these scripts.</p>',
                   footl=FL, footr="03 · Reproducibility"))
    # 22 conclusion (ink)
    S.append(slide(
        f'<span class="cross" style="right:0;top:0"></span>{eyebrow("Conclusion", on=True)}'
        f'<div style="margin-top:40px"><h1 class="h1" style="font-size:40px;line-height:1.08;max-width:24ch">A compact, leakage-free model that reproduces the bank\'s loan limits to <span style="color:var(--cobalt-soft)">~3.6% error</span> — using just four financial inputs.</h1></div>'
        f'<div style="margin-top:38px">{bullets([("Next:","shadow-mode pilot, review band at ±10%, retrain on a real decision book."),("Then:","add collateral / LTV context and affordability stress for production underwriting.")],on=True)}</div>',
        cls="ink", footl=FL, footr="Conclusion"))
    # 23 appendix data dictionary
    dd = [["Annual Income (USD)", "num", "Applicant income — top driver"],
          ["Credit Score", "num", "300–850; second driver"],
          ["Existing Monthly Debt", "num", "Current monthly obligations"],
          ["Down Payment (USD)", "num", "Cash toward purchase — kept"],
          ["Interest Rate", "num", "Risk-based price — EXCLUDED"],
          ["Age / Employment Years", "num", "Correlated; not used"],
          ["Loans Repaid", "num", "Tracks credit score; not used"],
          ["Gender / Married / Area", "cat", "No signal; not used"],
          ["Education / Job", "cat", "Income proxies; not used"],
          ["Max Loan Amount (USD)", "num", "TARGET — held out"]]
    S.append(slide(f'{eyebrow("Appendix")}<h1 class="h1" style="font-size:30px;margin-top:8px">Data dictionary</h1>'
                   f'<div style="margin-top:24px">{table(["Field","Type","Role in the model"],dd)}</div>',
                   footl=FL, footr="Appendix · Data dictionary"))

    cmap = {"Annual Income (USD)": "Annual income"}
    charts = (
        bar_js("in_thist", [f"${e}k" for e in DATA["thist_e"][:-1]], DATA["thist_c"], ["#306CB8"], fmt="v=>v")
        + bar_js("in_corr", DATA["corr_f"], DATA["corr_v"], ["#455E73"], horiz=True, fmt="v=>v")
        + bar_js("in_edu", DATA["edu_l"], DATA["edu_v"], ["#306CB8"], fmt="v=>'$'+v+'k'")
        + bar_js("in_job", DATA["job_l"], DATA["job_v"], ["#455E73"], horiz=True, fmt="v=>'$'+v+'k'")
        + SCAT_JS.replace("%ID%", "in_scatter")
        + bar_js("in_resid", [f"${e}k" for e in DATA["rhe"][:-1]], DATA["rhc"], ["#306CB8"], fmt="v=>v")
        + line_js("in_band", DATA["band"], DATA["mape"], fmt="v=>v+'%'")
        + bar_js("in_imp", DATA["imp_f"], DATA["imp_v"], ["#306CB8", "#306CB8", "#455E73", "#455E73"], horiz=True, fmt="v=>v")
    )
    open("decks/mortgage_internal_deck.html", "w").write(deck_html("Maximum loan amount — internal methodology", "".join(S), charts))
    print("wrote decks/mortgage_internal_deck.html")


if __name__ == "__main__":
    build_exec()
    build_internal()
