from pathlib import Path
import html
import json
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Respiratory FAERS2", page_icon="", layout="wide", initial_sidebar_state="collapsed")

ROOT = Path(__file__).resolve().parents[3]
AGENT = ROOT / "output" / "bigdata_si" / "agentic_layer"
DASH = ROOT / "output" / "bigdata_si" / "dashboard"
STRUCTURE_CATALOG = json.loads((DASH / "drug_structure_catalog.json").read_text(encoding="utf-8")) if (DASH / "drug_structure_catalog.json").exists() else {}


def _param(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value) if value is not None else ""


def _fmt_int(value) -> str:
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "NA"


def _fmt_rate(value) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "NA"


def _fmt_ratio(value) -> str:
    try:
        return f"{float(value):.2f}x"
    except Exception:
        return "NA"


def _openfda_api_url(drug: str, pt: str = "") -> str:
    if pt:
        q = f'patient.drug.medicinalproduct.exact:"{drug.upper()}" AND patient.reaction.reactionmeddrapt.exact:"{pt.upper()}"'
        return f"https://api.fda.gov/drug/event.json?search={quote(q)}&limit=10"
    q = f'patient.drug.medicinalproduct.exact:"{drug.upper()}"'
    return f"https://api.fda.gov/drug/event.json?search={quote(q)}&count=patient.reaction.reactionmeddrapt.exact&limit=500"


def _render_openfda_detail() -> None:
    drug = _param("openfda_drug").strip().upper()
    pt = _param("openfda_pt").strip().upper()
    if not drug:
        return

    df = pd.read_csv(AGENT / "openfda_federated_audit.csv")
    df["Drug_upper"] = df["Drug"].astype(str).str.upper()
    df["PT_upper"] = df["Preferred_Term"].astype(str).str.upper()
    drug_rows = df[df["Drug_upper"] == drug].copy()
    rows = drug_rows[drug_rows["PT_upper"] == pt].copy() if pt else drug_rows.copy()
    row = rows.iloc[0].to_dict() if not rows.empty else {}
    api_url = _openfda_api_url(drug, pt)
    label_drug = html.escape(drug.title())
    label_pt = html.escape(pt.title()) if pt else "Reaction profile"
    local_reports = _fmt_int(row.get("Local_Respiratory_Reports", drug_rows["Local_Respiratory_Reports"].sum() if not drug_rows.empty else ""))
    local_deaths = _fmt_int(row.get("Local_Deaths", drug_rows["Local_Deaths"].sum() if not drug_rows.empty else ""))
    openfda_count = _fmt_int(row.get("OpenFDA_Current_Count", drug_rows["OpenFDA_Current_Count"].sum() if not drug_rows.empty else ""))
    death_rate = _fmt_rate(row.get("Observed_Death_Rate", ""))
    ratio = _fmt_ratio(row.get("Current_to_Local_Ratio", ""))
    audit = html.escape(str(row.get("Audit_Status", "linked")).replace("_", " ").title())
    structure = STRUCTURE_CATALOG.get(drug, {})
    structure_svg = structure.get("svg", "")
    structure_kind = html.escape(str(structure.get("kind", "Structure context")))
    structure_summary = html.escape(str(structure.get("summary", drug.title())))
    structure_source = html.escape(str(structure.get("source_note", "local cache")))
    top_rows = (
        drug_rows.sort_values("OpenFDA_Current_Count", ascending=False)
        .head(8)
        .to_dict("records")
    )
    table_rows = "\n".join(
        f'''<tr>
          <td>{html.escape(str(r.get("Preferred_Term", "")).title())}</td>
          <td>{_fmt_int(r.get("Local_Respiratory_Reports", ""))}</td>
          <td>{_fmt_int(r.get("OpenFDA_Current_Count", ""))}</td>
          <td>{_fmt_int(r.get("Local_Deaths", ""))}</td>
          <td>{_fmt_ratio(r.get("Current_to_Local_Ratio", ""))}</td>
        </tr>'''
        for r in top_rows
    )

    st.markdown(
        '''
        <style>
        #MainMenu, header, footer {visibility:hidden;}
        .block-container {padding:0; max-width:100%;}
        .detail-shell {
          position:relative;
          overflow:hidden;
          min-height:100vh;
          padding:34px 42px 54px;
          color:#0f172a;
          font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter","Helvetica Neue",Arial,sans-serif;
          background:
            linear-gradient(rgba(15,23,42,.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(15,23,42,.035) 1px, transparent 1px),
            radial-gradient(circle at 78% 18%, rgba(16,166,159,.16), transparent 28%),
            radial-gradient(circle at 17% 82%, rgba(77,139,189,.16), transparent 30%),
            #f7f8fa;
          background-size:42px 42px,42px 42px,auto,auto,auto;
        }
        .detail-shell > * {position:relative; z-index:1;}
        .detail-ambient {
          position:absolute;
          right:-3vw;
          bottom:-12vh;
          width:min(620px,48vw);
          opacity:.075;
          pointer-events:none;
          z-index:0;
          animation: detailChemFloat 18s ease-in-out infinite;
        }
        .detail-ambient svg {
          width:100%;
          height:auto;
          filter:drop-shadow(0 24px 60px rgba(16,166,159,.18));
        }
        .detail-ambient svg rect {fill:transparent !important;}
        .detail-ambient svg text {display:none;}
        .detail-ambient svg line {stroke:rgba(15,23,42,.42) !important; stroke-width:2.2 !important;}
        .detail-ambient svg circle {opacity:.52;}
        .detail-top {display:flex; justify-content:space-between; gap:28px; align-items:flex-start;}
        .eyebrow {font-size:13px; letter-spacing:.16em; text-transform:uppercase; color:#64748b; font-weight:800;}
        h1 {font-size:72px; line-height:.9; margin:18px 0 18px; letter-spacing:-.045em; max-width:980px;}
        .sub {font-size:22px; line-height:1.45; color:#334155; max-width:820px; margin:0 0 28px;}
        .actions {display:flex; gap:12px; flex-wrap:wrap; margin-top:20px;}
        .btn {display:inline-flex; align-items:center; justify-content:center; min-height:44px; padding:0 18px; border-radius:14px; font-weight:800; text-decoration:none !important;}
        .btn-primary, .btn-primary:visited {background:#0f172a; color:white !important; box-shadow:0 18px 42px rgba(15,23,42,.18);}
        .btn-ghost, .btn-ghost:visited {background:rgba(255,255,255,.70); color:#0f172a !important; border:1px solid rgba(15,23,42,.10);}
        .stat-grid {display:grid; grid-template-columns:repeat(4,minmax(160px,1fr)); gap:14px; margin:34px 0 26px; max-width:1080px;}
        .card {background:rgba(255,255,255,.72); border:1px solid rgba(15,23,42,.10); border-radius:24px; padding:22px; box-shadow:0 22px 70px rgba(15,23,42,.08); backdrop-filter:blur(20px);}
        .metric {font-size:34px; line-height:1; font-weight:900; letter-spacing:-.035em;}
        .label {font-size:13px; margin-top:9px; color:#64748b; font-weight:700;}
        .chip {display:inline-flex; align-items:center; min-height:32px; padding:0 12px; border-radius:999px; background:rgba(16,166,159,.12); color:#0f766e; font-weight:900; font-size:13px;}
        .detail-side {min-width:260px; display:flex; flex-direction:column; gap:14px; align-items:flex-end;}
        .structure-card {width:260px; padding:14px; border-radius:24px; background:rgba(255,255,255,.70); border:1px solid rgba(15,23,42,.10); box-shadow:0 22px 70px rgba(15,23,42,.08); backdrop-filter:blur(20px);}
        .structure-visual svg {display:block; width:100%; height:auto;}
        .structure-kind {font-size:11px; letter-spacing:.13em; text-transform:uppercase; color:#64748b; font-weight:900; margin-top:8px;}
        .structure-summary {font-size:14px; color:#0f172a; font-weight:800; margin-top:4px; line-height:1.25;}
        .structure-source {font-size:11px; color:#94a3b8; font-weight:700; margin-top:6px;}
        .table-card {max-width:1080px; overflow:hidden;}
        table {width:100%; border-collapse:collapse; font-size:15px;}
        th {text-align:left; padding:0 0 13px; color:#64748b; font-size:12px; letter-spacing:.12em; text-transform:uppercase;}
        td {padding:15px 0; border-top:1px solid rgba(15,23,42,.08); font-weight:650;}
        td:not(:first-child), th:not(:first-child) {text-align:right;}
        .note {margin-top:14px; color:#64748b; font-size:13px; line-height:1.45; max-width:900px;}
        @media (max-width:900px) {
          h1 {font-size:48px;}
          .stat-grid {grid-template-columns:1fr 1fr;}
          .detail-shell {padding:26px 20px 44px;}
        }
        @keyframes detailChemFloat {
          0%, 100% {transform:translate3d(0,0,0) rotate(-8deg) scale(1);}
          50% {transform:translate3d(-22px,-18px,0) rotate(5deg) scale(1.04);}
        }
        </style>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'''
        <main class="detail-shell">
          <div class="detail-ambient" aria-hidden="true">{structure_svg}</div>
          <section class="detail-top">
            <div>
              <div class="eyebrow">openFDA linked evidence</div>
              <h1>{label_drug}<br>{label_pt}</h1>
              <p class="sub">Readable dashboard view for the selected FAERS recovery-map mark. Official API URLs are retained in the audit files, while this interface stays focused on readable evidence.</p>
              <div class="actions">
                <a class="btn btn-primary" href="http://localhost:8507/">Back to map</a>
              </div>
            </div>
            <aside class="detail-side">
              <div class="chip">{audit}</div>
              <div class="structure-card">
                <div class="structure-visual">{structure_svg}</div>
                <div class="structure-kind">{structure_kind}</div>
                <div class="structure-summary">{structure_summary}</div>
                <div class="structure-source">{structure_source}</div>
              </div>
            </aside>
          </section>
          <section class="stat-grid">
            <div class="card"><div class="metric">{local_reports}</div><div class="label">local respiratory reports</div></div>
            <div class="card"><div class="metric">{openfda_count}</div><div class="label">current openFDA count</div></div>
            <div class="card"><div class="metric">{local_deaths}</div><div class="label">local fatal reports</div></div>
            <div class="card"><div class="metric">{ratio}</div><div class="label">current-to-local ratio</div></div>
          </section>
          <section class="card table-card">
            <div class="eyebrow">Top recovered preferred terms for {label_drug}</div>
            <table>
              <thead><tr><th>Preferred term</th><th>Local</th><th>openFDA</th><th>Deaths</th><th>Ratio</th></tr></thead>
              <tbody>{table_rows}</tbody>
            </table>
            <p class="note">Observed death rate for the selected local pair: {death_rate}. Counts are recovered from the local 2025Q4 FAERS respiratory cohort and the current openFDA audit table used by this dashboard.</p>
          </section>
        </main>
        ''',
        unsafe_allow_html=True,
    )
    st.stop()


_render_openfda_detail()

HTML = r'''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
  --ink:#101417;
  --paper:#F6F4EE;
  --muted:#94A0AA;
  --line:rgba(255,255,255,.12);
  --teal:#10A69F;
  --amber:#E2B84D;
  --coral:#E76F51;
  --blue:#4D8BBD;
  --violet:#8E6BAE;
}
* { box-sizing:border-box; }
body {
  margin:0;
  background:
    linear-gradient(135deg, #F8FAFC 0%, #EEF2F6 44%, #F7F0E8 100%);
  color:#101417;
  font-family: Arial, Helvetica, sans-serif;
}
.shell {
  min-height: 940px;
  padding: 30px;
}
.hero {
  position:relative;
  min-height: 900px;
  overflow:hidden;
  border-radius: 22px;
  background:
    linear-gradient(90deg, rgba(42,55,68,.055) 1px, transparent 1px),
    linear-gradient(rgba(42,55,68,.045) 1px, transparent 1px),
    rgba(255,255,255,.72);
  background-size: 56px 56px, 56px 56px, auto;
  color:#111827;
  border:1px solid rgba(255,255,255,.76);
  box-shadow: 0 34px 90px rgba(44,56,73,.22), inset 0 1px 0 rgba(255,255,255,.75);
  backdrop-filter: blur(28px) saturate(1.22);
  animation: windowIn .75s cubic-bezier(.2,.8,.2,1) both;
}
.hero::after {
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background: linear-gradient(180deg, rgba(255,255,255,.18) 0%, rgba(255,255,255,.05) 38%, rgba(39,51,67,.045) 100%);
}
.chem-bg {
  position:absolute;
  inset:0;
  overflow:hidden;
  pointer-events:none;
  z-index:1;
}
.chem-stage {
  position:absolute;
  opacity:.10;
  filter: drop-shadow(0 30px 70px rgba(15,23,42,.12)) saturate(.92);
  mix-blend-mode:multiply;
}
.chem-stage.a {
  top:6%;
  right:2.2%;
  width:min(390px,29vw);
  opacity:.145;
  animation: chemDriftA 22s ease-in-out infinite;
}
.chem-stage.b {
  left:-4%;
  bottom:-9%;
  width:min(520px,38vw);
  opacity:.090;
  animation: chemDriftB 29s ease-in-out infinite;
}
.chem-stage.c {
  right:24%;
  bottom:7%;
  width:min(300px,22vw);
  opacity:.105;
  animation: chemDriftC 25s ease-in-out infinite;
}
.chem-stage.d {
  left:38%;
  top:3%;
  width:min(240px,17vw);
  opacity:.060;
  animation: chemDriftD 31s ease-in-out infinite;
}
.chem-stage.e {
  right:6%;
  bottom:29%;
  width:min(225px,16vw);
  opacity:.070;
  animation: chemDriftE 27s ease-in-out infinite;
}
.chem-stage.f {
  left:49%;
  bottom:-3%;
  width:min(360px,27vw);
  opacity:.078;
  animation: chemDriftA 34s ease-in-out infinite reverse;
}
.chem-stage.g {
  left:7%;
  top:57%;
  width:min(190px,14vw);
  opacity:.058;
  animation: chemDriftC 30s ease-in-out infinite reverse;
}
.chem-stage.h {
  right:-4%;
  top:47%;
  width:min(330px,24vw);
  opacity:.074;
  animation: chemDriftD 36s ease-in-out infinite reverse;
}
.chem-visual {
  transition: opacity .62s ease, transform .62s ease;
}
.chem-visual.fade {
  opacity:0;
  transform:scale(.965) rotate(3deg);
}
.chem-stage svg {
  display:block;
  width:100%;
  height:auto;
}
.chem-stage svg rect { fill:transparent !important; }
.chem-stage svg text { display:none; }
.chem-stage svg line {
  stroke:rgba(15,23,42,.36) !important;
  stroke-width:2 !important;
}
.chem-stage svg circle {
  opacity:.50;
  filter:saturate(1.14);
}
.topbar {
  position:relative;
  z-index:2;
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding: 18px 26px 0;
}
.traffic {
  display:flex;
  gap:8px;
  align-items:center;
}
.traffic i {
  display:block;
  width:12px;
  height:12px;
  border-radius:50%;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.12);
}
.traffic i:nth-child(1) { background:#FF5F57; }
.traffic i:nth-child(2) { background:#FFBD2E; }
.traffic i:nth-child(3) { background:#28C840; }
.titlebar-left {
  display:flex;
  gap:18px;
  align-items:center;
}
.brand {
  font-size:12px;
  font-weight:800;
  letter-spacing:.12em;
  color:#7A5C00;
  text-transform:uppercase;
}
.micro-links {
  display:flex;
  gap:10px;
  align-items:center;
  color:#5E6872;
  font-size:12px;
}
.micro-links span {
  border:1px solid rgba(30,41,59,.12);
  border-radius:999px;
  padding:7px 10px;
  background:rgba(255,255,255,.56);
  box-shadow: 0 6px 16px rgba(44,56,73,.06);
}
.layout {
  position:relative;
  z-index:2;
  display:grid;
  grid-template-columns: minmax(0, 1.08fr) 430px;
  gap:32px;
  padding: 38px 32px 26px;
  animation: riseIn .72s cubic-bezier(.2,.8,.2,1) .08s both;
}
h1 {
  max-width:920px;
  margin:0;
  font-size: clamp(48px, 5.8vw, 82px);
  line-height:.90;
  letter-spacing:-.05em;
  color:#0F172A;
}
.deck {
  max-width:780px;
  margin:20px 0 0;
  font-size:17px;
  line-height:1.55;
  color:#354253;
}
.proof-strip {
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap:14px;
  margin-top:34px;
  max-width:920px;
}
.proof {
  min-height:96px;
  border:1px solid rgba(30,41,59,.10);
  border-radius:12px;
  background:rgba(255,255,255,.66);
  padding:16px 18px 14px;
  backdrop-filter: blur(18px) saturate(1.16);
  box-shadow: 0 16px 40px rgba(44,56,73,.09);
  transition: transform .22s ease, box-shadow .22s ease;
}
.proof:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 56px rgba(44,56,73,.14);
}
.proof b {
  display:block;
  font-size:30px;
  line-height:1;
  letter-spacing:-.03em;
}
.proof span {
  display:block;
  margin-top:10px;
  color:#5E6872;
  font-size:13px;
  line-height:1.35;
}
.visual-card {
  margin-top:24px;
  max-width:920px;
  border:1px solid rgba(30,41,59,.11);
  border-radius:16px;
  background:rgba(255,255,255,.64);
  padding:20px 22px 14px;
  backdrop-filter: blur(20px) saturate(1.18);
  box-shadow: 0 18px 50px rgba(44,56,73,.10);
}
.card-head {
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:16px;
  margin-bottom:8px;
}
.card-head b {
  font-size:16px;
  letter-spacing:.02em;
  color:#111827;
}
.card-head span {
  color:#5E6872;
  font-size:12px;
  line-height:1.35;
  max-width:330px;
  text-align:right;
}
svg {
  width:100%;
  height:auto;
  overflow:visible;
}
.axis, .gridline {
  stroke:rgba(30,41,59,.12);
  stroke-width:1;
}
.diag {
  stroke:rgba(15,23,42,.55);
  stroke-width:1.5;
  stroke-dasharray:5 6;
}
.pt {
  opacity:.88;
  stroke:rgba(255,255,255,.86);
  stroke-width:1.2;
  transform-origin:center;
  animation: floatPoint 4.5s ease-in-out calc(var(--i) * .13s) infinite;
  transition: opacity .2s ease, transform .2s ease, filter .2s ease;
}
.pt:hover {
  opacity:1;
  transform: scale(1.22);
  filter: drop-shadow(0 8px 14px rgba(16,20,23,.20));
}
.pt, .drug-label, .openfda-link {
  cursor:pointer;
}
.openfda-link:focus {
  outline: none;
}
.openfda-link:focus .pt, .openfda-link:focus .drug-label {
  outline: none;
  filter: drop-shadow(0 0 0 rgba(0,0,0,0)) drop-shadow(0 0 12px rgba(16,166,159,.35));
}
.drug-label {
  fill:#111827;
  font-size:12px;
  font-weight:800;
  paint-order:stroke;
  stroke:rgba(255,255,255,.86);
  stroke-width:4px;
  animation: labelIn .8s cubic-bezier(.2,.8,.2,1) both;
}
.side {
  display:flex;
  flex-direction:column;
  gap:14px;
}
.panel {
  border:1px solid rgba(30,41,59,.11);
  border-radius:16px;
  background:rgba(255,255,255,.68);
  padding:20px;
  backdrop-filter: blur(20px) saturate(1.16);
  box-shadow: 0 18px 50px rgba(44,56,73,.10);
  transition: transform .22s ease, box-shadow .22s ease;
}
.panel:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 58px rgba(44,56,73,.14);
}
.panel h2 {
  margin:0 0 16px;
  font-size:13px;
  color:#637081;
  letter-spacing:.10em;
  text-transform:uppercase;
}
.score {
  display:flex;
  justify-content:space-between;
  gap:14px;
  align-items:flex-end;
  border-bottom:1px solid rgba(30,41,59,.10);
  padding:13px 0;
}
.score:first-of-type { padding-top:0; }
.score:last-child { border-bottom:0; padding-bottom:0; }
.score b {
  display:block;
  font-size:30px;
  letter-spacing:-.03em;
}
.score span {
  color:#637081;
  font-size:12px;
}
.score em {
  font-style:normal;
  color:#111827;
  font-size:13px;
  text-align:right;
}
.agent-row {
  display:flex;
  justify-content:space-between;
  gap:14px;
  padding:11px 0;
  border-bottom:1px solid rgba(30,41,59,.10);
  font-size:13px;
}
.agent-row:last-child { border-bottom:0; }
.agent-row span { color:#243040; }
.agent-row b { color:var(--teal); font-size:12px; }
.footer {
  position:relative;
  z-index:2;
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding: 0 34px 30px;
  color:#637081;
  font-size:12px;
}
.tooltip {
  position:fixed;
  opacity:0;
  transform:translate(-50%, -110%);
  pointer-events:none;
  background:rgba(255,255,255,.92);
  color:#101417;
  border-radius:8px;
  padding:8px 10px;
  font-size:12px;
  box-shadow:0 18px 44px rgba(44,56,73,.24);
  backdrop-filter: blur(16px);
  transition:opacity .12s ease;
  max-width:320px;
  z-index:20;
}
.mol-card {
  position:fixed;
  width:260px;
  opacity:0;
  transform:translate(12px, -50%) scale(.96);
  pointer-events:none;
  border:1px solid rgba(30,41,59,.12);
  border-radius:22px;
  background:rgba(255,255,255,.76);
  box-shadow:0 28px 70px rgba(44,56,73,.24);
  backdrop-filter: blur(22px) saturate(1.22);
  padding:12px;
  z-index:24;
  transition:opacity .16s ease, transform .16s ease;
}
.mol-card.show {
  opacity:1;
  transform:translate(16px, -50%) scale(1);
}
.mol-visual svg {
  display:block;
  width:100%;
  height:auto;
}
.mol-name {
  margin-top:8px;
  font-size:15px;
  font-weight:900;
  letter-spacing:-.01em;
  color:#0f172a;
}
.mol-meta {
  margin-top:3px;
  color:#64748b;
  font-size:12px;
  line-height:1.35;
  font-weight:700;
}
.mol-source {
  margin-top:7px;
  color:#94a3b8;
  font-size:10px;
  letter-spacing:.08em;
  text-transform:uppercase;
  font-weight:900;
}
@keyframes windowIn {
  from { opacity:0; transform: translateY(16px) scale(.985); }
  to { opacity:1; transform: translateY(0) scale(1); }
}
@keyframes riseIn {
  from { opacity:0; transform: translateY(14px); }
  to { opacity:1; transform: translateY(0); }
}
@keyframes floatPoint {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-3px) scale(1.045); }
}
@keyframes labelIn {
  from { opacity:0; transform: translateY(5px); }
  to { opacity:1; transform: translateY(0); }
}
@keyframes chemDriftA {
  0%, 100% { transform:translate3d(0,0,0) rotate(-9deg) scale(1); }
  45% { transform:translate3d(-18px,20px,0) rotate(4deg) scale(1.035); }
  72% { transform:translate3d(12px,-10px,0) rotate(-4deg) scale(.985); }
}
@keyframes chemDriftB {
  0%, 100% { transform:translate3d(0,0,0) rotate(8deg) scale(1); }
  50% { transform:translate3d(24px,-22px,0) rotate(-6deg) scale(1.04); }
}
@keyframes chemDriftC {
  0%, 100% { transform:translate3d(0,0,0) rotate(13deg) scale(1); }
  55% { transform:translate3d(-12px,-18px,0) rotate(-7deg) scale(1.05); }
}
@keyframes chemDriftD {
  0%, 100% { transform:translate3d(0,0,0) rotate(-15deg) scale(.98); }
  42% { transform:translate3d(18px,14px,0) rotate(-3deg) scale(1.055); }
  76% { transform:translate3d(-10px,-18px,0) rotate(6deg) scale(1.01); }
}
@keyframes chemDriftE {
  0%, 100% { transform:translate3d(0,0,0) rotate(18deg) scale(1); }
  48% { transform:translate3d(-22px,8px,0) rotate(5deg) scale(1.04); }
  82% { transform:translate3d(12px,-14px,0) rotate(11deg) scale(.99); }
}
@media (prefers-reduced-motion: reduce) {
  .chem-stage, .chem-visual, .pt, .hero, .layout { animation:none; transition:none; }
}
@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .side { display:grid; grid-template-columns:1fr 1fr; }
  h1 { font-size:64px; }
}
</style>
</head>
<body>
<div class="shell">
  <main class="hero">
    <div class="chem-bg" aria-hidden="true">
      <div class="chem-stage a"><div class="chem-visual" id="chemA"></div></div>
      <div class="chem-stage b"><div class="chem-visual" id="chemB"></div></div>
      <div class="chem-stage c"><div class="chem-visual" id="chemC"></div></div>
      <div class="chem-stage d"><div class="chem-visual" id="chemD"></div></div>
      <div class="chem-stage e"><div class="chem-visual" id="chemE"></div></div>
      <div class="chem-stage f"><div class="chem-visual" id="chemF"></div></div>
      <div class="chem-stage g"><div class="chem-visual" id="chemG"></div></div>
      <div class="chem-stage h"><div class="chem-visual" id="chemH"></div></div>
    </div>
    <div class="topbar">
      <div class="titlebar-left">
        <div class="traffic"><i></i><i></i><i></i></div>
        <div class="brand">FAERS 2025Q4 · agentic audit · Big Data SI</div>
      </div>
      <div class="micro-links">
        <span>provenance</span>
        <span>openFDA audit</span>
        <span>paper kit</span>
      </div>
    </div>
    <section class="layout">
      <div>
        <h1>Respiratory fatal-outcome intelligence</h1>
        <p class="deck">One screen for the strongest claim: a 1.93M-report FAERS respiratory cohort, temporally validated mortality modelling, six bounded audit agents, and current openFDA recovery of the local drug-event signal surface.</p>
        <div class="proof-strip">
          <div class="proof"><b>1,933,080</b><span>respiratory FAERS reports through 2025Q4</span></div>
          <div class="proof"><b>0.728</b><span>best held-out AUROC · Logistic Regression</span></div>
          <div class="proof"><b>80/80</b><span>drug-PT pairs recovered in current openFDA tables</span></div>
        </div>
        <div class="visual-card">
          <div class="card-head">
            <b>External recovery map</b>
          </div>
          <svg viewBox="0 0 680 380" role="img" aria-label="openFDA external recovery map">
            <line class="gridline" x1="58" y1="322" x2="610" y2="322" />
            <line class="gridline" x1="58" y1="229" x2="610" y2="229" />
            <line class="gridline" x1="58" y1="136" x2="610" y2="136" />
            <line class="gridline" x1="58" y1="42" x2="610" y2="42" />
            <line class="gridline" x1="58" y1="42" x2="58" y2="322" />
            <line class="gridline" x1="242" y1="42" x2="242" y2="322" />
            <line class="gridline" x1="426" y1="42" x2="426" y2="322" />
            <line class="gridline" x1="610" y1="42" x2="610" y2="322" />
            <line class="diag" x1="58" y1="322" x2="610" y2="42" />
            <a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=ASTHMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Asthma" data-drug="DUPIXENT" data-pt="ASTHMA" tabindex="0"><circle class="pt" style="--i:0" cx="610.0" cy="68.7" r="3.9" fill="#4D8BBD" data-tip="Dupixent · Asthma · local 13,769 · openFDA 14,268" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Dyspnoea" data-drug="DUPIXENT" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:1" cx="583.0" cy="79.8" r="5.0" fill="#4D8BBD" data-tip="Dupixent · Dyspnoea · local 11,346 · openFDA 12,150" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Cough" data-drug="DUPIXENT" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:2" cx="554.1" cy="95.6" r="3.6" fill="#4D8BBD" data-tip="Dupixent · Cough · local 9,223 · openFDA 9,676" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=NASAL+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Nasal Congestion" data-drug="DUPIXENT" data-pt="NASAL CONGESTION" tabindex="0"><circle class="pt" style="--i:3" cx="431.1" cy="156.8" r="2.8" fill="#4D8BBD" data-tip="Dupixent · Nasal Congestion · local 3,817 · openFDA 3,999" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Rhinorrhoea" data-drug="DUPIXENT" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:4" cx="404.1" cy="170.3" r="2.5" fill="#4D8BBD" data-tip="Dupixent · Rhinorrhoea · local 3,144 · openFDA 3,288" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Oropharyngeal Pain" data-drug="DUPIXENT" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:5" cx="392.1" cy="177.9" r="2.2" fill="#4D8BBD" data-tip="Dupixent · Oropharyngeal Pain · local 2,885 · openFDA 2,949" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=WHEEZING" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Wheezing" data-drug="DUPIXENT" data-pt="WHEEZING" tabindex="0"><circle class="pt" style="--i:6" cx="371.7" cy="185.6" r="2.9" fill="#4D8BBD" data-tip="Dupixent · Wheezing · local 2,492 · openFDA 2,638" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=DUPIXENT&amp;openfda_pt=NASAL+POLYPS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Dupixent and Nasal Polyps" data-drug="DUPIXENT" data-pt="NASAL POLYPS" tabindex="0"><circle class="pt" style="--i:7" cx="314.1" cy="211.4" r="2.2" fill="#4D8BBD" data-tip="Dupixent · Nasal Polyps · local 1,649 · openFDA 1,817" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Cough" data-drug="ENBREL" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:8" cx="572.5" cy="80.6" r="4.5" fill="#4D8BBD" data-tip="Enbrel · Cough · local 10,521 · openFDA 12,023" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Dyspnoea" data-drug="ENBREL" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:9" cx="492.4" cy="85.2" r="6.6" fill="#4D8BBD" data-tip="Enbrel · Dyspnoea · local 5,924 · openFDA 11,241" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Oropharyngeal Pain" data-drug="ENBREL" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:10" cx="484.4" cy="129.0" r="2.8" fill="#4D8BBD" data-tip="Enbrel · Oropharyngeal Pain · local 5,594 · openFDA 5,971" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Rhinorrhoea" data-drug="ENBREL" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:0" cx="422.3" cy="159.7" r="2.4" fill="#4D8BBD" data-tip="Enbrel · Rhinorrhoea · local 3,583 · openFDA 3,834" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=NASAL+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Nasal Congestion" data-drug="ENBREL" data-pt="NASAL CONGESTION" tabindex="0"><circle class="pt" style="--i:1" cx="392.0" cy="172.2" r="2.2" fill="#4D8BBD" data-tip="Enbrel · Nasal Congestion · local 2,884 · openFDA 3,201" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=RESPIRATORY+TRACT+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Respiratory Tract Congestion" data-drug="ENBREL" data-pt="RESPIRATORY TRACT CONGESTION" tabindex="0"><circle class="pt" style="--i:2" cx="352.6" cy="194.3" r="2.2" fill="#4D8BBD" data-tip="Enbrel · Respiratory Tract Congestion · local 2,173 · openFDA 2,327" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=PRODUCTIVE+COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Productive Cough" data-drug="ENBREL" data-pt="PRODUCTIVE COUGH" tabindex="0"><circle class="pt" style="--i:3" cx="337.3" cy="198.5" r="2.9" fill="#4D8BBD" data-tip="Enbrel · Productive Cough · local 1,948 · openFDA 2,190" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENBREL&amp;openfda_pt=SINUS+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Enbrel and Sinus Congestion" data-drug="ENBREL" data-pt="SINUS CONGESTION" tabindex="0"><circle class="pt" style="--i:4" cx="315.8" cy="215.1" r="2.2" fill="#4D8BBD" data-tip="Enbrel · Sinus Congestion · local 1,669 · openFDA 1,721" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Dyspnoea" data-drug="ENTRESTO" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:5" cx="530.4" cy="101.1" r="9.8" fill="#4D8BBD" data-tip="Entresto · Dyspnoea · local 7,782 · openFDA 8,940" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Cough" data-drug="ENTRESTO" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:6" cx="521.8" cy="110.2" r="5.8" fill="#4D8BBD" data-tip="Entresto · Cough · local 7,316 · openFDA 7,843" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=THROAT+CLEARING" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Throat Clearing" data-drug="ENTRESTO" data-pt="THROAT CLEARING" tabindex="0"><circle class="pt" style="--i:7" cx="301.4" cy="222.4" r="2.2" fill="#4D8BBD" data-tip="Entresto · Throat Clearing · local 1,505 · openFDA 1,549" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=PULMONARY+OEDEMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Pulmonary Oedema" data-drug="ENTRESTO" data-pt="PULMONARY OEDEMA" tabindex="0"><circle class="pt" style="--i:8" cx="209.6" cy="255.7" r="6.0" fill="#4D8BBD" data-tip="Entresto · Pulmonary Oedema · local 779 · openFDA 958" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Rhinorrhoea" data-drug="ENTRESTO" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:9" cx="206.9" cy="265.0" r="3.0" fill="#4D8BBD" data-tip="Entresto · Rhinorrhoea · local 764 · openFDA 837" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=DYSPNOEA+EXERTIONAL" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Dyspnoea Exertional" data-drug="ENTRESTO" data-pt="DYSPNOEA EXERTIONAL" tabindex="0"><circle class="pt" style="--i:10" cx="174.6" cy="267.5" r="3.8" fill="#4D8BBD" data-tip="Entresto · Dyspnoea Exertional · local 606 · openFDA 807" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=DYSPHONIA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Dysphonia" data-drug="ENTRESTO" data-pt="DYSPHONIA" tabindex="0"><circle class="pt" style="--i:0" cx="128.2" cy="299.9" r="2.2" fill="#4D8BBD" data-tip="Entresto · Dysphonia · local 434 · openFDA 505" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=ENTRESTO&amp;openfda_pt=CHRONIC+OBSTRUCTIVE+PULMONARY+DISEASE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Entresto and Chronic Obstructive Pulmonary Disease" data-drug="ENTRESTO" data-pt="CHRONIC OBSTRUCTIVE PULMONARY DISEASE" tabindex="0"><circle class="pt" style="--i:1" cx="124.6" cy="297.7" r="4.6" fill="#4D8BBD" data-tip="Entresto · Chronic Obstructive Pulmonary Disease · local 423 · openFDA 522" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Cough" data-drug="HUMIRA" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:2" cx="570.3" cy="82.0" r="5.7" fill="#4D8BBD" data-tip="Humira · Cough · local 10,361 · openFDA 11,784" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Dyspnoea" data-drug="HUMIRA" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:3" cx="559.5" cy="67.5" r="9.9" fill="#4D8BBD" data-tip="Humira · Dyspnoea · local 9,583 · openFDA 14,511" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Oropharyngeal Pain" data-drug="HUMIRA" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:4" cx="482.0" cy="126.9" r="3.4" fill="#4D8BBD" data-tip="Humira · Oropharyngeal Pain · local 5,499 · openFDA 6,161" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Rhinorrhoea" data-drug="HUMIRA" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:5" cx="393.1" cy="169.5" r="2.6" fill="#4D8BBD" data-tip="Humira · Rhinorrhoea · local 2,907 · openFDA 3,326" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=NASAL+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Nasal Congestion" data-drug="HUMIRA" data-pt="NASAL CONGESTION" tabindex="0"><circle class="pt" style="--i:6" cx="379.6" cy="176.9" r="2.9" fill="#4D8BBD" data-tip="Humira · Nasal Congestion · local 2,638 · openFDA 2,991" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=RESPIRATORY+TRACT+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Respiratory Tract Congestion" data-drug="HUMIRA" data-pt="RESPIRATORY TRACT CONGESTION" tabindex="0"><circle class="pt" style="--i:7" cx="343.8" cy="200.2" r="2.7" fill="#4D8BBD" data-tip="Humira · Respiratory Tract Congestion · local 2,040 · openFDA 2,135" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=ASTHMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Asthma" data-drug="HUMIRA" data-pt="ASTHMA" tabindex="0"><circle class="pt" style="--i:8" cx="332.2" cy="156.4" r="4.6" fill="#10A69F" data-tip="Humira · Asthma · local 1,877 · openFDA 4,020" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=HUMIRA&amp;openfda_pt=CHRONIC+OBSTRUCTIVE+PULMONARY+DISEASE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Humira and Chronic Obstructive Pulmonary Disease" data-drug="HUMIRA" data-pt="CHRONIC OBSTRUCTIVE PULMONARY DISEASE" tabindex="0"><circle class="pt" style="--i:9" cx="331.9" cy="202.5" r="8.1" fill="#4D8BBD" data-tip="Humira · Chronic Obstructive Pulmonary Disease · local 1,874 · openFDA 2,067" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Dyspnoea" data-drug="LETAIRIS" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:10" cx="512.4" cy="92.7" r="5.9" fill="#4D8BBD" data-tip="Letairis · Dyspnoea · local 6,836 · openFDA 10,094" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=NASAL+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Nasal Congestion" data-drug="LETAIRIS" data-pt="NASAL CONGESTION" tabindex="0"><circle class="pt" style="--i:0" cx="312.9" cy="194.4" r="2.6" fill="#4D8BBD" data-tip="Letairis · Nasal Congestion · local 1,635 · openFDA 2,322" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Cough" data-drug="LETAIRIS" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:1" cx="293.8" cy="188.8" r="2.7" fill="#4D8BBD" data-tip="Letairis · Cough · local 1,425 · openFDA 2,518" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=PULMONARY+ARTERIAL+HYPERTENSION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Pulmonary Arterial Hypertension" data-drug="LETAIRIS" data-pt="PULMONARY ARTERIAL HYPERTENSION" tabindex="0"><circle class="pt" style="--i:2" cx="194.9" cy="228.0" r="6.0" fill="#10A69F" data-tip="Letairis · Pulmonary Arterial Hypertension · local 701 · openFDA 1,430" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=PULMONARY+HYPERTENSION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Pulmonary Hypertension" data-drug="LETAIRIS" data-pt="PULMONARY HYPERTENSION" tabindex="0"><circle class="pt" style="--i:3" cx="167.6" cy="254.0" r="6.9" fill="#4D8BBD" data-tip="Letairis · Pulmonary Hypertension · local 576 · openFDA 981" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=RESPIRATORY+FAILURE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Respiratory Failure" data-drug="LETAIRIS" data-pt="RESPIRATORY FAILURE" tabindex="0"><circle class="pt" style="--i:4" cx="163.7" cy="273.5" r="7.4" fill="#4D8BBD" data-tip="Letairis · Respiratory Failure · local 560 · openFDA 740" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=EPISTAXIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Epistaxis" data-drug="LETAIRIS" data-pt="EPISTAXIS" tabindex="0"><circle class="pt" style="--i:5" cx="116.1" cy="275.0" r="2.4" fill="#4D8BBD" data-tip="Letairis · Epistaxis · local 398 · openFDA 725" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=LETAIRIS&amp;openfda_pt=CHRONIC+OBSTRUCTIVE+PULMONARY+DISEASE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Letairis and Chronic Obstructive Pulmonary Disease" data-drug="LETAIRIS" data-pt="CHRONIC OBSTRUCTIVE PULMONARY DISEASE" tabindex="0"><circle class="pt" style="--i:6" cx="105.6" cy="307.5" r="4.7" fill="#4D8BBD" data-tip="Letairis · Chronic Obstructive Pulmonary Disease · local 369 · openFDA 453" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Dyspnoea" data-drug="REVLIMID" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:7" cx="486.1" cy="124.5" r="8.5" fill="#4D8BBD" data-tip="Revlimid · Dyspnoea · local 5,661 · openFDA 6,376" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Cough" data-drug="REVLIMID" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:8" cx="411.7" cy="163.0" r="5.6" fill="#4D8BBD" data-tip="Revlimid · Cough · local 3,321 · openFDA 3,655" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=PULMONARY+EMBOLISM" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Pulmonary Embolism" data-drug="REVLIMID" data-pt="PULMONARY EMBOLISM" tabindex="0"><circle class="pt" style="--i:9" cx="388.3" cy="174.2" r="8.1" fill="#4D8BBD" data-tip="Revlimid · Pulmonary Embolism · local 2,808 · openFDA 3,110" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Rhinorrhoea" data-drug="REVLIMID" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:10" cx="249.7" cy="245.2" r="2.4" fill="#4D8BBD" data-tip="Revlimid · Rhinorrhoea · local 1,039 · openFDA 1,114" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=PULMONARY+THROMBOSIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Pulmonary Thrombosis" data-drug="REVLIMID" data-pt="PULMONARY THROMBOSIS" tabindex="0"><circle class="pt" style="--i:0" cx="241.9" cy="251.5" r="3.1" fill="#4D8BBD" data-tip="Revlimid · Pulmonary Thrombosis · local 982 · openFDA 1,017" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Oropharyngeal Pain" data-drug="REVLIMID" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:1" cx="238.0" cy="247.4" r="2.5" fill="#4D8BBD" data-tip="Revlimid · Oropharyngeal Pain · local 955 · openFDA 1,080" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=EPISTAXIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Epistaxis" data-drug="REVLIMID" data-pt="EPISTAXIS" tabindex="0"><circle class="pt" style="--i:2" cx="235.8" cy="244.6" r="4.0" fill="#4D8BBD" data-tip="Revlimid · Epistaxis · local 940 · openFDA 1,125" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=REVLIMID&amp;openfda_pt=DYSPHONIA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Revlimid and Dysphonia" data-drug="REVLIMID" data-pt="DYSPHONIA" tabindex="0"><circle class="pt" style="--i:3" cx="231.0" cy="254.2" r="3.1" fill="#4D8BBD" data-tip="Revlimid · Dysphonia · local 908 · openFDA 979" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Dyspnoea" data-drug="SPIRIVA" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:4" cx="547.3" cy="42.0" r="5.6" fill="#10A69F" data-tip="Spiriva · Dyspnoea · local 8,785 · openFDA 20,987" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Cough" data-drug="SPIRIVA" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:5" cx="371.2" cy="108.3" r="2.9" fill="#10A69F" data-tip="Spiriva · Cough · local 2,484 · openFDA 8,053" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=CHRONIC+OBSTRUCTIVE+PULMONARY+DISEASE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Chronic Obstructive Pulmonary Disease" data-drug="SPIRIVA" data-pt="CHRONIC OBSTRUCTIVE PULMONARY DISEASE" tabindex="0"><circle class="pt" style="--i:6" cx="336.4" cy="131.2" r="7.6" fill="#10A69F" data-tip="Spiriva · Chronic Obstructive Pulmonary Disease · local 1,935 · openFDA 5,789" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=ASTHMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Asthma" data-drug="SPIRIVA" data-pt="ASTHMA" tabindex="0"><circle class="pt" style="--i:7" cx="294.6" cy="95.7" r="3.2" fill="#E76F51" data-tip="Spiriva · Asthma · local 1,434 · openFDA 9,663" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=WHEEZING" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Wheezing" data-drug="SPIRIVA" data-pt="WHEEZING" tabindex="0"><circle class="pt" style="--i:8" cx="266.9" cy="128.7" r="3.0" fill="#E2B84D" data-tip="Spiriva · Wheezing · local 1,175 · openFDA 6,000" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=DYSPHONIA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Dysphonia" data-drug="SPIRIVA" data-pt="DYSPHONIA" tabindex="0"><circle class="pt" style="--i:9" cx="258.3" cy="195.6" r="2.4" fill="#10A69F" data-tip="Spiriva · Dysphonia · local 1,105 · openFDA 2,284" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Oropharyngeal Pain" data-drug="SPIRIVA" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:10" cx="173.0" cy="218.3" r="2.4" fill="#10A69F" data-tip="Spiriva · Oropharyngeal Pain · local 599 · openFDA 1,644" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SPIRIVA&amp;openfda_pt=PRODUCTIVE+COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Spiriva and Productive Cough" data-drug="SPIRIVA" data-pt="PRODUCTIVE COUGH" tabindex="0"><circle class="pt" style="--i:0" cx="171.9" cy="169.1" r="2.7" fill="#E2B84D" data-tip="Spiriva · Productive Cough · local 594 · openFDA 3,346" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Dyspnoea" data-drug="SYMBICORT" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:1" cx="511.6" cy="54.3" r="5.0" fill="#10A69F" data-tip="Symbicort · Dyspnoea · local 6,797 · openFDA 17,581" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=ASTHMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Asthma" data-drug="SYMBICORT" data-pt="ASTHMA" tabindex="0"><circle class="pt" style="--i:2" cx="409.7" cy="80.9" r="4.7" fill="#10A69F" data-tip="Symbicort · Asthma · local 3,273 · openFDA 11,958" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Cough" data-drug="SYMBICORT" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:3" cx="360.1" cy="110.3" r="3.3" fill="#10A69F" data-tip="Symbicort · Cough · local 2,293 · openFDA 7,827" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=CHRONIC+OBSTRUCTIVE+PULMONARY+DISEASE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Chronic Obstructive Pulmonary Disease" data-drug="SYMBICORT" data-pt="CHRONIC OBSTRUCTIVE PULMONARY DISEASE" tabindex="0"><circle class="pt" style="--i:4" cx="307.2" cy="156.5" r="4.8" fill="#10A69F" data-tip="Symbicort · Chronic Obstructive Pulmonary Disease · local 1,569 · openFDA 4,016" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=WHEEZING" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Wheezing" data-drug="SYMBICORT" data-pt="WHEEZING" tabindex="0"><circle class="pt" style="--i:5" cx="288.4" cy="132.3" r="2.2" fill="#E2B84D" data-tip="Symbicort · Wheezing · local 1,371 · openFDA 5,694" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=DYSPHONIA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Dysphonia" data-drug="SYMBICORT" data-pt="DYSPHONIA" tabindex="0"><circle class="pt" style="--i:6" cx="253.2" cy="202.4" r="2.4" fill="#4D8BBD" data-tip="Symbicort · Dysphonia · local 1,065 · openFDA 2,068" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Oropharyngeal Pain" data-drug="SYMBICORT" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:7" cx="168.8" cy="213.1" r="2.2" fill="#10A69F" data-tip="Symbicort · Oropharyngeal Pain · local 581 · openFDA 1,772" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=SYMBICORT&amp;openfda_pt=LUNG+DISORDER" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Symbicort and Lung Disorder" data-drug="SYMBICORT" data-pt="LUNG DISORDER" tabindex="0"><circle class="pt" style="--i:8" cx="154.9" cy="228.7" r="3.4" fill="#10A69F" data-tip="Symbicort · Lung Disorder · local 526 · openFDA 1,414" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=EPISTAXIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Epistaxis" data-drug="XARELTO" data-pt="EPISTAXIS" tabindex="0"><circle class="pt" style="--i:9" cx="454.1" cy="125.5" r="13.0" fill="#4D8BBD" data-tip="Xarelto · Epistaxis · local 4,501 · openFDA 6,281" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=PULMONARY+EMBOLISM" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Pulmonary Embolism" data-drug="XARELTO" data-pt="PULMONARY EMBOLISM" tabindex="0"><circle class="pt" style="--i:10" cx="430.8" cy="141.1" r="10.0" fill="#4D8BBD" data-tip="Xarelto · Pulmonary Embolism · local 3,809 · openFDA 5,018" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Dyspnoea" data-drug="XARELTO" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:0" cx="321.3" cy="130.0" r="6.4" fill="#10A69F" data-tip="Xarelto · Dyspnoea · local 1,736 · openFDA 5,884" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=HAEMOPTYSIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Haemoptysis" data-drug="XARELTO" data-pt="HAEMOPTYSIS" tabindex="0"><circle class="pt" style="--i:1" cx="299.7" cy="201.4" r="9.6" fill="#4D8BBD" data-tip="Xarelto · Haemoptysis · local 1,487 · openFDA 2,099" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=RESPIRATORY+FAILURE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Respiratory Failure" data-drug="XARELTO" data-pt="RESPIRATORY FAILURE" tabindex="0"><circle class="pt" style="--i:2" cx="163.2" cy="253.2" r="9.5" fill="#4D8BBD" data-tip="Xarelto · Respiratory Failure · local 558 · openFDA 993" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Cough" data-drug="XARELTO" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:3" cx="121.9" cy="196.8" r="3.4" fill="#E2B84D" data-tip="Xarelto · Cough · local 415 · openFDA 2,242" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=PULMONARY+HAEMORRHAGE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Pulmonary Haemorrhage" data-drug="XARELTO" data-pt="PULMONARY HAEMORRHAGE" tabindex="0"><circle class="pt" style="--i:4" cx="62.2" cy="322.0" r="6.3" fill="#4D8BBD" data-tip="Xarelto · Pulmonary Haemorrhage · local 270 · openFDA 367" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XARELTO&amp;openfda_pt=ACUTE+RESPIRATORY+FAILURE" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xarelto and Acute Respiratory Failure" data-drug="XARELTO" data-pt="ACUTE RESPIRATORY FAILURE" tabindex="0"><circle class="pt" style="--i:5" cx="58.0" cy="301.1" r="7.1" fill="#4D8BBD" data-tip="Xarelto · Acute Respiratory Failure · local 262 · openFDA 497" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=ASTHMA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Asthma" data-drug="XOLAIR" data-pt="ASTHMA" tabindex="0"><circle class="pt" style="--i:6" cx="493.3" cy="109.9" r="7.3" fill="#4D8BBD" data-tip="Xolair · Asthma · local 5,962 · openFDA 7,869" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=DYSPNOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Dyspnoea" data-drug="XOLAIR" data-pt="DYSPNOEA" tabindex="0"><circle class="pt" style="--i:7" cx="464.6" cy="122.5" r="5.8" fill="#4D8BBD" data-tip="Xolair · Dyspnoea · local 4,854 · openFDA 6,559" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Cough" data-drug="XOLAIR" data-pt="COUGH" tabindex="0"><circle class="pt" style="--i:8" cx="402.3" cy="151.4" r="4.8" fill="#4D8BBD" data-tip="Xolair · Cough · local 3,105 · openFDA 4,325" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=WHEEZING" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Wheezing" data-drug="XOLAIR" data-pt="WHEEZING" tabindex="0"><circle class="pt" style="--i:9" cx="353.5" cy="174.7" r="4.6" fill="#4D8BBD" data-tip="Xolair · Wheezing · local 2,187 · openFDA 3,088" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=PRODUCTIVE+COUGH" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Productive Cough" data-drug="XOLAIR" data-pt="PRODUCTIVE COUGH" tabindex="0"><circle class="pt" style="--i:10" cx="263.0" cy="220.8" r="4.3" fill="#4D8BBD" data-tip="Xolair · Productive Cough · local 1,143 · openFDA 1,587" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=OROPHARYNGEAL+PAIN" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Oropharyngeal Pain" data-drug="XOLAIR" data-pt="OROPHARYNGEAL PAIN" tabindex="0"><circle class="pt" style="--i:0" cx="245.8" cy="233.4" r="3.1" fill="#4D8BBD" data-tip="Xolair · Oropharyngeal Pain · local 1,010 · openFDA 1,322" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=NASAL+CONGESTION" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Nasal Congestion" data-drug="XOLAIR" data-pt="NASAL CONGESTION" tabindex="0"><circle class="pt" style="--i:1" cx="239.0" cy="233.6" r="3.6" fill="#4D8BBD" data-tip="Xolair · Nasal Congestion · local 962 · openFDA 1,319" /></a>
<a class="openfda-link" href="http://localhost:8507/?openfda_drug=XOLAIR&amp;openfda_pt=RHINORRHOEA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA query for Xolair and Rhinorrhoea" data-drug="XOLAIR" data-pt="RHINORRHOEA" tabindex="0"><circle class="pt" style="--i:2" cx="204.5" cy="252.7" r="3.1" fill="#4D8BBD" data-tip="Xolair · Rhinorrhoea · local 751 · openFDA 1,000" /></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=DUPIXENT" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Dupixent" data-drug="DUPIXENT" tabindex="0"><text class="drug-label" x="623.0" y="57.7" text-anchor="start">Dupixent</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=ENBREL" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Enbrel" data-drug="ENBREL" tabindex="0"><text class="drug-label" x="584.5" y="96.6" text-anchor="start">Enbrel</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=ENTRESTO" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Entresto" data-drug="ENTRESTO" tabindex="0"><text class="drug-label" x="460.4" y="89.1" text-anchor="end">Entresto</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=HUMIRA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Humira" data-drug="HUMIRA" tabindex="0"><text class="drug-label" x="496.3" y="97.0" text-anchor="end">Humira</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=LETAIRIS" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Letairis" data-drug="LETAIRIS" tabindex="0"><text class="drug-label" x="527.4" y="68.7" text-anchor="start">Letairis</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=SPIRIVA" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Spiriva" data-drug="SPIRIVA" tabindex="0"><text class="drug-label" x="465.3" y="18.0" text-anchor="end">Spiriva</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=SYMBICORT" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Symbicort" data-drug="SYMBICORT" tabindex="0"><text class="drug-label" x="527.6" y="83.3" text-anchor="start">Symbicort</text></a>
<a class="openfda-link drug-link" href="http://localhost:8507/?openfda_drug=XOLAIR" target="_blank" rel="noopener noreferrer" aria-label="Open openFDA reaction-count query for Xolair" data-drug="XOLAIR" tabindex="0"><text class="drug-label" x="417.3" y="140.9" text-anchor="end">Xolair</text></a>
            <text x="58" y="356" fill="#637081" font-size="12">local respiratory reports, log scale</text>
            <text x="14" y="222" fill="#637081" font-size="12" transform="rotate(-90 14 222)">current openFDA count</text>
            <text x="492" y="30" fill="#111827" font-size="12">Spearman 0.880</text>
          </svg>
        </div>
      </div>
      <aside class="side">
        <div class="panel">
          <h2>Model signal</h2>
          <div class="score"><div><b>0.728</b><span>AUROC</span></div><em>Logistic Regression</em></div>
          <div class="score"><div><b>0.371</b><span>AUPRC</span></div><em>LightGBM</em></div>
          <div class="score"><div><b>0.103</b><span>Brier score</span></div><em>Random Forest</em></div>
        </div>
        <div class="panel">
          <h2>Audit board · 6/6</h2>
          
        <div class="agent-row">
          <span>DataIntegrity</span>
          <b>PASS</b>
        </div>
        

        <div class="agent-row">
          <span>TemporalSplit</span>
          <b>PASS</b>
        </div>
        

        <div class="agent-row">
          <span>ModelSelection</span>
          <b>PASS</b>
        </div>
        

        <div class="agent-row">
          <span>XAITraceability</span>
          <b>PASS</b>
        </div>
        

        <div class="agent-row">
          <span>TemporalRobustness</span>
          <b>PASS</b>
        </div>
        

        <div class="agent-row">
          <span>FederatedOpenFDAAudit</span>
          <b>PASS · scoped</b>
        </div>
        
        </div>
      </aside>
    </section>
    <div class="footer">
      <div>Network and lineage views are intentionally secondary; the homepage foregrounds the strongest evidence.</div>
    </div>
  </main>
</div>
<div class="tooltip" id="tooltip"></div>
<div class="mol-card" id="molCard">
  <div class="mol-visual" id="molVisual"></div>
  <div class="mol-name" id="molName"></div>
  <div class="mol-meta" id="molMeta"></div>
  <div class="mol-source" id="molSource"></div>
</div>
<script>
const tip = document.getElementById('tooltip');
const STRUCTURE_CATALOG = {"DUPIXENT": {"display": "Dupixent", "kind": "Biologic antibody", "summary": "Dupilumab, monoclonal antibody against IL-4R alpha", "components": [], "svg": "\n    <svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"Biologic structure class\">\n      <defs>\n        <linearGradient id=\"bioGrad\" x1=\"0\" x2=\"1\" y1=\"0\" y2=\"1\">\n          <stop offset=\"0%\" stop-color=\"#c7f3ef\"/>\n          <stop offset=\"55%\" stop-color=\"#d9e8ff\"/>\n          <stop offset=\"100%\" stop-color=\"#f7e7c2\"/>\n        </linearGradient>\n      </defs>\n      <rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"rgba(255,255,255,.68)\"/>\n      <path d=\"M38 96 C54 56, 73 38, 91 68 C109 98, 131 80, 145 42\" fill=\"none\" stroke=\"url(#bioGrad)\" stroke-width=\"15\" stroke-linecap=\"round\"/>\n      <path d=\"M39 96 C55 56, 74 38, 92 68 C110 98, 132 80, 146 42\" fill=\"none\" stroke=\"#0f172a\" stroke-opacity=\".22\" stroke-width=\"1.2\"/>\n      <circle cx=\"55\" cy=\"65\" r=\"8\" fill=\"#10A69F\" opacity=\".72\"/>\n      <circle cx=\"91\" cy=\"69\" r=\"9\" fill=\"#4D8BBD\" opacity=\".68\"/>\n      <circle cx=\"126\" cy=\"74\" r=\"7\" fill=\"#E2B84D\" opacity=\".76\"/>\n      <text x=\"14\" y=\"24\" font-size=\"10\" font-weight=\"900\" fill=\"#64748b\">BIOLOGIC</text>\n      <text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Macromolecule class glyph</text>\n    </svg>\n    ", "source_note": "Biologic class glyph; no small-molecule conformer used"}, "ENBREL": {"display": "Enbrel", "kind": "Biologic fusion protein", "summary": "Etanercept, TNF receptor Fc fusion protein", "components": [], "svg": "\n    <svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"Biologic structure class\">\n      <defs>\n        <linearGradient id=\"bioGrad\" x1=\"0\" x2=\"1\" y1=\"0\" y2=\"1\">\n          <stop offset=\"0%\" stop-color=\"#c7f3ef\"/>\n          <stop offset=\"55%\" stop-color=\"#d9e8ff\"/>\n          <stop offset=\"100%\" stop-color=\"#f7e7c2\"/>\n        </linearGradient>\n      </defs>\n      <rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"rgba(255,255,255,.68)\"/>\n      <path d=\"M38 96 C54 56, 73 38, 91 68 C109 98, 131 80, 145 42\" fill=\"none\" stroke=\"url(#bioGrad)\" stroke-width=\"15\" stroke-linecap=\"round\"/>\n      <path d=\"M39 96 C55 56, 74 38, 92 68 C110 98, 132 80, 146 42\" fill=\"none\" stroke=\"#0f172a\" stroke-opacity=\".22\" stroke-width=\"1.2\"/>\n      <circle cx=\"55\" cy=\"65\" r=\"8\" fill=\"#10A69F\" opacity=\".72\"/>\n      <circle cx=\"91\" cy=\"69\" r=\"9\" fill=\"#4D8BBD\" opacity=\".68\"/>\n      <circle cx=\"126\" cy=\"74\" r=\"7\" fill=\"#E2B84D\" opacity=\".76\"/>\n      <text x=\"14\" y=\"24\" font-size=\"10\" font-weight=\"900\" fill=\"#64748b\">BIOLOGIC</text>\n      <text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Macromolecule class glyph</text>\n    </svg>\n    ", "source_note": "Biologic class glyph; no small-molecule conformer used"}, "ENTRESTO": {"display": "Entresto", "kind": "Small-molecule combination", "summary": "Sacubitril + valsartan", "components": [{"name": "Sacubitril", "cid": "9811834", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/sacubitril/SDF?record_type=3d"}, {"name": "Valsartan", "cid": "60846", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/valsartan/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"61.7\" y1=\"74.3\" x2=\"61.7\" y2=\"85.8\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"61.7\" y1=\"74.3\" x2=\"68.3\" y2=\"70.7\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"66.7\" y1=\"93.1\" x2=\"61.7\" y2=\"85.8\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"80.1\" y1=\"62.5\" x2=\"73.9\" y2=\"63.6\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"70.8\" y1=\"21.6\" x2=\"67.7\" y2=\"31.8\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"61.6\" y1=\"32.5\" x2=\"67.7\" y2=\"31.8\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"70.4\" y1=\"74.0\" x2=\"73.8\" y2=\"85.1\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"70.4\" y1=\"74.0\" x2=\"73.9\" y2=\"63.6\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.8\" y1=\"85.1\" x2=\"62.5\" y2=\"93.1\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.8\" y1=\"85.1\" x2=\"81.4\" y2=\"90.9\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"62.5\" y1=\"93.1\" x2=\"54.5\" y2=\"88.3\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"54.5\" y1=\"88.3\" x2=\"43.7\" y2=\"96.8\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"54.5\" y1=\"88.3\" x2=\"61.7\" y2=\"85.8\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"81.4\" y1=\"90.9\" x2=\"94.3\" y2=\"85.7\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"94.3\" y1=\"85.7\" x2=\"103.1\" y2=\"90.2\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"94.3\" y1=\"85.7\" x2=\"97.4\" y2=\"76.4\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.9\" y1=\"63.6\" x2=\"69.0\" y2=\"53.4\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"103.1\" y1=\"90.2\" x2=\"115.0\" y2=\"85.4\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"97.4\" y1=\"76.4\" x2=\"109.4\" y2=\"71.6\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"69.0\" y1=\"53.4\" x2=\"72.7\" y2=\"41.8\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"118.2\" y1=\"76.1\" x2=\"115.0\" y2=\"85.4\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"118.2\" y1=\"76.1\" x2=\"109.4\" y2=\"71.6\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"118.2\" y1=\"76.1\" x2=\"130.5\" y2=\"71.1\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"72.7\" y1=\"41.8\" x2=\"67.7\" y2=\"31.8\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"130.5\" y1=\"71.1\" x2=\"138.6\" y2=\"75.4\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"130.5\" y1=\"71.1\" x2=\"134.4\" y2=\"61.9\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"68.3\" y1=\"70.7\" x2=\"67.4\" y2=\"57.9\" stroke=\"rgba(15,23,42,0.49)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"138.6\" y1=\"75.4\" x2=\"150.5\" y2=\"70.6\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"134.4\" y1=\"61.9\" x2=\"146.3\" y2=\"57.1\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"150.5\" y1=\"70.6\" x2=\"154.3\" y2=\"61.4\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"146.3\" y1=\"57.1\" x2=\"154.3\" y2=\"61.4\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><circle cx=\"81.4\" cy=\"90.9\" r=\"2.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"61.6\" cy=\"32.5\" r=\"2.9\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"97.4\" cy=\"76.4\" r=\"2.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"70.4\" cy=\"74.0\" r=\"3.0\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"62.5\" cy=\"93.1\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"94.3\" cy=\"85.7\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"109.4\" cy=\"71.6\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.8\" cy=\"85.1\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"69.0\" cy=\"53.4\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"43.7\" cy=\"96.8\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"67.7\" cy=\"31.8\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"54.5\" cy=\"88.3\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.9\" cy=\"63.6\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"138.6\" cy=\"75.4\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"103.1\" cy=\"90.2\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"118.2\" cy=\"76.1\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"72.7\" cy=\"41.8\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"150.5\" cy=\"70.6\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"115.0\" cy=\"85.4\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"130.5\" cy=\"71.1\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"70.8\" cy=\"21.6\" r=\"3.7\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"80.1\" cy=\"62.5\" r=\"3.9\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"61.7\" cy=\"85.8\" r=\"4.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"154.3\" cy=\"61.4\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"134.4\" cy=\"61.9\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"61.7\" cy=\"74.3\" r=\"4.2\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"66.7\" cy=\"93.1\" r=\"4.2\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"146.3\" cy=\"57.1\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"68.3\" cy=\"70.7\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"67.4\" cy=\"57.9\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Sacubitril</text></svg>", "source_note": "PubChem 3D SDF"}, "HUMIRA": {"display": "Humira", "kind": "Biologic antibody", "summary": "Adalimumab, monoclonal antibody against TNF", "components": [], "svg": "\n    <svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"Biologic structure class\">\n      <defs>\n        <linearGradient id=\"bioGrad\" x1=\"0\" x2=\"1\" y1=\"0\" y2=\"1\">\n          <stop offset=\"0%\" stop-color=\"#c7f3ef\"/>\n          <stop offset=\"55%\" stop-color=\"#d9e8ff\"/>\n          <stop offset=\"100%\" stop-color=\"#f7e7c2\"/>\n        </linearGradient>\n      </defs>\n      <rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"rgba(255,255,255,.68)\"/>\n      <path d=\"M38 96 C54 56, 73 38, 91 68 C109 98, 131 80, 145 42\" fill=\"none\" stroke=\"url(#bioGrad)\" stroke-width=\"15\" stroke-linecap=\"round\"/>\n      <path d=\"M39 96 C55 56, 74 38, 92 68 C110 98, 132 80, 146 42\" fill=\"none\" stroke=\"#0f172a\" stroke-opacity=\".22\" stroke-width=\"1.2\"/>\n      <circle cx=\"55\" cy=\"65\" r=\"8\" fill=\"#10A69F\" opacity=\".72\"/>\n      <circle cx=\"91\" cy=\"69\" r=\"9\" fill=\"#4D8BBD\" opacity=\".68\"/>\n      <circle cx=\"126\" cy=\"74\" r=\"7\" fill=\"#E2B84D\" opacity=\".76\"/>\n      <text x=\"14\" y=\"24\" font-size=\"10\" font-weight=\"900\" fill=\"#64748b\">BIOLOGIC</text>\n      <text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Macromolecule class glyph</text>\n    </svg>\n    ", "source_note": "Biologic class glyph; no small-molecule conformer used"}, "LETAIRIS": {"display": "Letairis", "kind": "Small molecule", "summary": "Ambrisentan", "components": [{"name": "Ambrisentan", "cid": "6918493", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/ambrisentan/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"60.8\" y1=\"70.6\" x2=\"71.7\" y2=\"70.9\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"60.8\" y1=\"70.6\" x2=\"66.0\" y2=\"81.1\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"101.0\" y1=\"64.3\" x2=\"89.0\" y2=\"64.9\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"101.0\" y1=\"64.3\" x2=\"117.0\" y2=\"66.7\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"86.0\" y1=\"49.2\" x2=\"88.7\" y2=\"48.4\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"90.9\" y1=\"35.6\" x2=\"88.7\" y2=\"48.4\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"121.5\" y1=\"61.9\" x2=\"117.0\" y2=\"66.7\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"121.5\" y1=\"61.9\" x2=\"137.4\" y2=\"64.3\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"126.7\" y1=\"73.5\" x2=\"117.0\" y2=\"66.7\" stroke=\"rgba(15,23,42,0.45)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"126.7\" y1=\"73.5\" x2=\"142.4\" y2=\"75.6\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"71.7\" y1=\"70.9\" x2=\"89.0\" y2=\"64.9\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"71.7\" y1=\"70.9\" x2=\"65.6\" y2=\"59.3\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"71.7\" y1=\"70.9\" x2=\"70.3\" y2=\"88.6\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"89.0\" y1=\"64.9\" x2=\"88.7\" y2=\"48.4\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"65.6\" y1=\"59.3\" x2=\"73.5\" y2=\"58.9\" stroke=\"rgba(15,23,42,0.45)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"65.6\" y1=\"59.3\" x2=\"52.7\" y2=\"49.8\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"70.3\" y1=\"88.6\" x2=\"55.0\" y2=\"95.1\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"70.3\" y1=\"88.6\" x2=\"84.4\" y2=\"97.1\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.5\" y1=\"58.9\" x2=\"68.0\" y2=\"48.4\" stroke=\"rgba(15,23,42,0.48)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"55.0\" y1=\"95.1\" x2=\"53.7\" y2=\"111.1\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"52.7\" y1=\"49.8\" x2=\"47.2\" y2=\"39.3\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"84.4\" y1=\"97.1\" x2=\"83.2\" y2=\"113.2\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"68.0\" y1=\"48.4\" x2=\"54.9\" y2=\"38.6\" stroke=\"rgba(15,23,42,0.49)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"53.7\" y1=\"111.1\" x2=\"67.8\" y2=\"120.2\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"47.2\" y1=\"39.3\" x2=\"54.9\" y2=\"38.6\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"83.2\" y1=\"113.2\" x2=\"67.8\" y2=\"120.2\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"137.4\" y1=\"64.3\" x2=\"148.5\" y2=\"71.2\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"137.4\" y1=\"64.3\" x2=\"142.8\" y2=\"59.2\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"142.4\" y1=\"75.6\" x2=\"148.5\" y2=\"71.2\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"142.4\" y1=\"75.6\" x2=\"153.4\" y2=\"83.2\" stroke=\"rgba(15,23,42,0.48)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><circle cx=\"66.0\" cy=\"81.1\" r=\"2.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"86.0\" cy=\"49.2\" r=\"2.8\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"60.8\" cy=\"70.6\" r=\"2.8\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"142.8\" cy=\"59.2\" r=\"2.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"88.7\" cy=\"48.4\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"89.0\" cy=\"64.9\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"71.7\" cy=\"70.9\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"137.4\" cy=\"64.3\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"121.5\" cy=\"61.9\" r=\"3.4\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"55.0\" cy=\"95.1\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"70.3\" cy=\"88.6\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"90.9\" cy=\"35.6\" r=\"3.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"53.7\" cy=\"111.1\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"84.4\" cy=\"97.1\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"67.8\" cy=\"120.2\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"83.2\" cy=\"113.2\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"52.7\" cy=\"49.8\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"148.5\" cy=\"71.2\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"65.6\" cy=\"59.3\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"117.0\" cy=\"66.7\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"101.0\" cy=\"64.3\" r=\"3.8\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"47.2\" cy=\"39.3\" r=\"4.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"142.4\" cy=\"75.6\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"126.7\" cy=\"73.5\" r=\"4.2\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.5\" cy=\"58.9\" r=\"4.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"54.9\" cy=\"38.6\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"153.4\" cy=\"83.2\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"68.0\" cy=\"48.4\" r=\"4.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Ambrisentan</text></svg>", "source_note": "PubChem 3D SDF"}, "REVLIMID": {"display": "Revlimid", "kind": "Small molecule", "summary": "Lenalidomide", "components": [{"name": "Lenalidomide", "cid": "216326", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/lenalidomide/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"96.5\" y1=\"97.8\" x2=\"98.3\" y2=\"85.3\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"80.9\" y1=\"64.8\" x2=\"71.1\" y2=\"67.6\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"32.5\" y1=\"62.4\" x2=\"44.7\" y2=\"66.3\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"88.4\" y1=\"74.5\" x2=\"73.4\" y2=\"76.7\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"88.4\" y1=\"74.5\" x2=\"94.9\" y2=\"60.8\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"88.4\" y1=\"74.5\" x2=\"98.3\" y2=\"85.3\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"56.8\" y1=\"63.6\" x2=\"71.1\" y2=\"67.6\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"56.8\" y1=\"63.6\" x2=\"44.7\" y2=\"66.3\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"120.0\" y1=\"41.1\" x2=\"121.7\" y2=\"55.6\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.4\" y1=\"76.7\" x2=\"63.1\" y2=\"73.0\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.4\" y1=\"76.7\" x2=\"71.1\" y2=\"67.6\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"63.1\" y1=\"73.0\" x2=\"47.4\" y2=\"75.1\" stroke=\"rgba(15,23,42,0.32)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"94.9\" y1=\"60.8\" x2=\"110.2\" y2=\"64.3\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"110.2\" y1=\"64.3\" x2=\"112.2\" y2=\"78.7\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"110.2\" y1=\"64.3\" x2=\"121.7\" y2=\"55.6\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"98.3\" y1=\"85.3\" x2=\"112.2\" y2=\"78.7\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"47.4\" y1=\"75.1\" x2=\"44.7\" y2=\"66.3\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"112.2\" y1=\"78.7\" x2=\"125.5\" y2=\"84.8\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"121.7\" y1=\"55.6\" x2=\"135.2\" y2=\"61.5\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"125.5\" y1=\"84.8\" x2=\"137.1\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"135.2\" y1=\"61.5\" x2=\"137.1\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><circle cx=\"63.1\" cy=\"73.0\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"47.4\" cy=\"75.1\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"120.0\" cy=\"41.1\" r=\"3.5\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"44.7\" cy=\"66.3\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"32.5\" cy=\"62.4\" r=\"3.5\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"94.9\" cy=\"60.8\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.4\" cy=\"76.7\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"88.4\" cy=\"74.5\" r=\"3.5\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"121.7\" cy=\"55.6\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"110.2\" cy=\"64.3\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"98.3\" cy=\"85.3\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"135.2\" cy=\"61.5\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"112.2\" cy=\"78.7\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"96.5\" cy=\"97.8\" r=\"3.6\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"137.1\" cy=\"76.0\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"125.5\" cy=\"84.8\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"56.8\" cy=\"63.6\" r=\"4.0\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"71.1\" cy=\"67.6\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"80.9\" cy=\"64.8\" r=\"4.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Lenalidomide</text></svg>", "source_note": "PubChem 3D SDF"}, "SPIRIVA": {"display": "Spiriva", "kind": "Small molecule", "summary": "Tiotropium", "components": [{"name": "Tiotropium", "cid": "5487427", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/tiotropium/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"117.4\" y1=\"39.5\" x2=\"114.8\" y2=\"55.5\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"117.4\" y1=\"39.5\" x2=\"113.8\" y2=\"31.5\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"138.0\" y1=\"79.5\" x2=\"121.8\" y2=\"81.3\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"138.0\" y1=\"79.5\" x2=\"136.0\" y2=\"96.5\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"36.9\" y1=\"83.6\" x2=\"51.7\" y2=\"79.0\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"36.9\" y1=\"83.6\" x2=\"47.2\" y2=\"87.8\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"91.1\" y1=\"74.4\" x2=\"77.2\" y2=\"77.4\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"91.1\" y1=\"74.4\" x2=\"102.4\" y2=\"72.0\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"101.3\" y1=\"72.4\" x2=\"102.4\" y2=\"72.0\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"127.3\" y1=\"65.1\" x2=\"116.6\" y2=\"68.6\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"49.5\" y1=\"62.9\" x2=\"57.0\" y2=\"64.6\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"49.5\" y1=\"62.9\" x2=\"50.0\" y2=\"78.6\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"49.5\" y1=\"62.9\" x2=\"56.8\" y2=\"51.7\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"49.5\" y1=\"62.9\" x2=\"33.9\" y2=\"58.2\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"57.0\" y1=\"64.6\" x2=\"51.7\" y2=\"79.0\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"57.0\" y1=\"64.6\" x2=\"73.5\" y2=\"65.3\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"50.0\" y1=\"78.6\" x2=\"47.2\" y2=\"87.8\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"50.0\" y1=\"78.6\" x2=\"65.7\" y2=\"80.8\" stroke=\"rgba(15,23,42,0.32)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"51.7\" y1=\"79.0\" x2=\"47.2\" y2=\"87.8\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"73.5\" y1=\"65.3\" x2=\"77.2\" y2=\"77.4\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"65.7\" y1=\"80.8\" x2=\"77.2\" y2=\"77.4\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"102.4\" y1=\"72.0\" x2=\"116.6\" y2=\"68.6\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"116.6\" y1=\"68.6\" x2=\"114.8\" y2=\"55.5\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"116.6\" y1=\"68.6\" x2=\"121.8\" y2=\"81.3\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"114.8\" y1=\"55.5\" x2=\"111.4\" y2=\"55.4\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"121.8\" y1=\"81.3\" x2=\"114.8\" y2=\"94.1\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"111.4\" y1=\"55.4\" x2=\"110.7\" y2=\"41.2\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"114.8\" y1=\"94.1\" x2=\"123.2\" y2=\"103.2\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"110.7\" y1=\"41.2\" x2=\"113.8\" y2=\"31.5\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"123.2\" y1=\"103.2\" x2=\"136.0\" y2=\"96.5\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"110.7\" cy=\"41.2\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"65.7\" cy=\"80.8\" r=\"3.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"50.0\" cy=\"78.6\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"123.2\" cy=\"103.2\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"111.4\" cy=\"55.4\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"136.0\" cy=\"96.5\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"56.8\" cy=\"51.7\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"33.9\" cy=\"58.2\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"49.5\" cy=\"62.9\" r=\"3.4\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"114.8\" cy=\"94.1\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"47.2\" cy=\"87.8\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"138.0\" cy=\"79.5\" r=\"3.5\" fill=\"#ca8a04\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"113.8\" cy=\"31.5\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"91.1\" cy=\"74.4\" r=\"3.6\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"121.8\" cy=\"81.3\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"77.2\" cy=\"77.4\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"114.8\" cy=\"55.5\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"36.9\" cy=\"83.6\" r=\"3.8\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"116.6\" cy=\"68.6\" r=\"3.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"57.0\" cy=\"64.6\" r=\"4.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"51.7\" cy=\"79.0\" r=\"4.0\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.5\" cy=\"65.3\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"102.4\" cy=\"72.0\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"117.4\" cy=\"39.5\" r=\"4.1\" fill=\"#ca8a04\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"127.3\" cy=\"65.1\" r=\"4.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"101.3\" cy=\"72.4\" r=\"4.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Tiotropium</text></svg>", "source_note": "PubChem 3D SDF"}, "SYMBICORT": {"display": "Symbicort", "kind": "Small-molecule combination", "summary": "Budesonide + formoterol", "components": [{"name": "Budesonide", "cid": "5281004", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/budesonide/SDF?record_type=3d"}, {"name": "Formoterol", "cid": "3410", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/formoterol/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"66.2\" y1=\"75.9\" x2=\"64.7\" y2=\"66.5\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"66.2\" y1=\"75.9\" x2=\"57.2\" y2=\"86.1\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"53.6\" y1=\"85.4\" x2=\"58.9\" y2=\"73.5\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"53.6\" y1=\"85.4\" x2=\"57.2\" y2=\"86.1\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"103.0\" y1=\"42.7\" x2=\"102.2\" y2=\"55.0\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"45.0\" y1=\"56.1\" x2=\"55.9\" y2=\"57.5\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"50.9\" y1=\"47.5\" x2=\"61.1\" y2=\"50.2\" stroke=\"rgba(15,23,42,0.49)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"151.3\" y1=\"85.2\" x2=\"142.1\" y2=\"78.6\" stroke=\"rgba(15,23,42,0.45)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"78.0\" y1=\"60.4\" x2=\"82.4\" y2=\"71.3\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"78.0\" y1=\"60.4\" x2=\"64.7\" y2=\"66.5\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"78.0\" y1=\"60.4\" x2=\"88.4\" y2=\"57.7\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"78.0\" y1=\"60.4\" x2=\"75.7\" y2=\"48.4\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"82.4\" y1=\"71.3\" x2=\"95.3\" y2=\"68.1\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"82.4\" y1=\"71.3\" x2=\"70.3\" y2=\"75.4\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"95.3\" y1=\"68.1\" x2=\"106.2\" y2=\"65.0\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"95.3\" y1=\"68.1\" x2=\"98.8\" y2=\"79.2\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"64.7\" y1=\"66.5\" x2=\"58.9\" y2=\"73.5\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"64.7\" y1=\"66.5\" x2=\"55.9\" y2=\"57.5\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"106.2\" y1=\"65.0\" x2=\"102.2\" y2=\"55.0\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"106.2\" y1=\"65.0\" x2=\"120.1\" y2=\"62.5\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"70.3\" y1=\"75.4\" x2=\"58.9\" y2=\"73.5\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"88.4\" y1=\"57.7\" x2=\"102.2\" y2=\"55.0\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"120.1\" y1=\"62.5\" x2=\"122.3\" y2=\"73.9\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"120.1\" y1=\"62.5\" x2=\"121.5\" y2=\"50.6\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"120.1\" y1=\"62.5\" x2=\"130.4\" y2=\"60.8\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"98.8\" y1=\"79.2\" x2=\"112.2\" y2=\"77.0\" stroke=\"rgba(15,23,42,0.32)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"112.2\" y1=\"77.0\" x2=\"122.3\" y2=\"73.9\" stroke=\"rgba(15,23,42,0.35)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"122.3\" y1=\"73.9\" x2=\"132.3\" y2=\"81.1\" stroke=\"rgba(15,23,42,0.38)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"55.9\" y1=\"57.5\" x2=\"61.1\" y2=\"50.2\" stroke=\"rgba(15,23,42,0.45)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"57.2\" y1=\"86.1\" x2=\"63.1\" y2=\"98.5\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"130.4\" y1=\"60.8\" x2=\"140.4\" y2=\"68.0\" stroke=\"rgba(15,23,42,0.48)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"63.1\" y1=\"98.5\" x2=\"66.9\" y2=\"99.8\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"132.3\" y1=\"81.1\" x2=\"142.1\" y2=\"78.6\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"140.4\" y1=\"68.0\" x2=\"142.1\" y2=\"78.6\" stroke=\"rgba(15,23,42,0.46)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"66.9\" y1=\"99.8\" x2=\"73.2\" y2=\"112.1\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><circle cx=\"70.3\" cy=\"75.4\" r=\"2.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"112.2\" cy=\"77.0\" r=\"2.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"98.8\" cy=\"79.2\" r=\"2.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"58.9\" cy=\"73.5\" r=\"2.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"53.6\" cy=\"85.4\" r=\"2.9\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"95.3\" cy=\"68.1\" r=\"3.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"82.4\" cy=\"71.3\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"122.3\" cy=\"73.9\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"75.7\" cy=\"48.4\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"132.3\" cy=\"81.1\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"45.0\" cy=\"56.1\" r=\"3.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"121.5\" cy=\"50.6\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"57.2\" cy=\"86.1\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"64.7\" cy=\"66.5\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"78.0\" cy=\"60.4\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"63.1\" cy=\"98.5\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"120.1\" cy=\"62.5\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"106.2\" cy=\"65.0\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"55.9\" cy=\"57.5\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"66.2\" cy=\"75.9\" r=\"3.8\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"142.1\" cy=\"78.6\" r=\"3.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"103.0\" cy=\"42.7\" r=\"4.0\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"151.3\" cy=\"85.2\" r=\"4.0\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"102.2\" cy=\"55.0\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"88.4\" cy=\"57.7\" r=\"4.1\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"66.9\" cy=\"99.8\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"130.4\" cy=\"60.8\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"73.2\" cy=\"112.1\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"61.1\" cy=\"50.2\" r=\"4.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"140.4\" cy=\"68.0\" r=\"4.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"50.9\" cy=\"47.5\" r=\"4.4\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Budesonide</text></svg>", "source_note": "PubChem 3D SDF"}, "XARELTO": {"display": "Xarelto", "kind": "Small molecule", "summary": "Rivaroxaban", "components": [{"name": "Rivaroxaban", "cid": "9875401", "source": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/rivaroxaban/SDF?record_type=3d"}], "svg": "<svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"3D conformer sketch\"><defs><radialGradient id=\"molGlow\" cx=\"50%\" cy=\"45%\" r=\"55%\"><stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\".95\"/><stop offset=\"100%\" stop-color=\"#dff7f4\" stop-opacity=\".16\"/></radialGradient></defs><rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"url(#molGlow)\"/><line x1=\"147.0\" y1=\"69.6\" x2=\"138.3\" y2=\"68.4\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"132.2\" y1=\"76.3\" x2=\"125.7\" y2=\"70.6\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"132.2\" y1=\"76.3\" x2=\"138.3\" y2=\"68.4\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"96.4\" y1=\"67.3\" x2=\"98.1\" y2=\"74.2\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"96.4\" y1=\"67.3\" x2=\"89.8\" y2=\"64.7\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"44.7\" y1=\"67.4\" x2=\"52.1\" y2=\"61.6\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"44.7\" y1=\"67.4\" x2=\"46.9\" y2=\"74.8\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"87.9\" y1=\"58.4\" x2=\"89.8\" y2=\"64.7\" stroke=\"rgba(15,23,42,0.33)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"53.2\" y1=\"82.6\" x2=\"53.2\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"117.0\" y1=\"81.3\" x2=\"118.5\" y2=\"74.2\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"86.2\" y1=\"70.3\" x2=\"90.1\" y2=\"77.1\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"86.2\" y1=\"70.3\" x2=\"79.3\" y2=\"70.1\" stroke=\"rgba(15,23,42,0.36)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"86.2\" y1=\"70.3\" x2=\"89.8\" y2=\"64.7\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"58.7\" y1=\"69.2\" x2=\"65.8\" y2=\"69.5\" stroke=\"rgba(15,23,42,0.41)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"58.7\" y1=\"69.2\" x2=\"56.7\" y2=\"61.5\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"58.7\" y1=\"69.2\" x2=\"53.2\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"113.3\" y1=\"69.3\" x2=\"105.9\" y2=\"72.0\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"113.3\" y1=\"69.3\" x2=\"118.5\" y2=\"74.2\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"98.1\" y1=\"74.2\" x2=\"90.1\" y2=\"77.1\" stroke=\"rgba(15,23,42,0.34)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"98.1\" y1=\"74.2\" x2=\"105.9\" y2=\"72.0\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"79.3\" y1=\"70.1\" x2=\"76.5\" y2=\"76.3\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"79.3\" y1=\"70.1\" x2=\"75.4\" y2=\"63.5\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"65.8\" y1=\"69.5\" x2=\"69.7\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"65.8\" y1=\"69.5\" x2=\"68.6\" y2=\"63.2\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"56.7\" y1=\"61.5\" x2=\"52.1\" y2=\"61.6\" stroke=\"rgba(15,23,42,0.47)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"76.5\" y1=\"76.3\" x2=\"69.7\" y2=\"76.0\" stroke=\"rgba(15,23,42,0.39)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"75.4\" y1=\"63.5\" x2=\"68.6\" y2=\"63.2\" stroke=\"rgba(15,23,42,0.37)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"53.2\" y1=\"76.0\" x2=\"46.9\" y2=\"74.8\" stroke=\"rgba(15,23,42,0.40)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"118.5\" y1=\"74.2\" x2=\"125.7\" y2=\"70.6\" stroke=\"rgba(15,23,42,0.42)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"125.7\" y1=\"70.6\" x2=\"127.9\" y2=\"62.9\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><line x1=\"127.9\" y1=\"62.9\" x2=\"135.3\" y2=\"61.7\" stroke=\"rgba(15,23,42,0.44)\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><line x1=\"135.3\" y1=\"61.7\" x2=\"138.3\" y2=\"68.4\" stroke=\"rgba(15,23,42,0.43)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"96.4\" cy=\"67.3\" r=\"3.1\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"87.9\" cy=\"58.4\" r=\"3.2\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"89.8\" cy=\"64.7\" r=\"3.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"90.1\" cy=\"77.1\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"53.2\" cy=\"82.6\" r=\"3.3\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"98.1\" cy=\"74.2\" r=\"3.3\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"86.2\" cy=\"70.3\" r=\"3.3\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"79.3\" cy=\"70.1\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"75.4\" cy=\"63.5\" r=\"3.4\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"76.5\" cy=\"76.3\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"68.6\" cy=\"63.2\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"53.2\" cy=\"76.0\" r=\"3.5\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"69.7\" cy=\"76.0\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"65.8\" cy=\"69.5\" r=\"3.6\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"132.2\" cy=\"76.3\" r=\"3.6\" fill=\"#ca8a04\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"147.0\" cy=\"69.6\" r=\"3.6\" fill=\"#16a34a\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"117.0\" cy=\"81.3\" r=\"3.7\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"58.7\" cy=\"69.2\" r=\"3.7\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"138.3\" cy=\"68.4\" r=\"3.7\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"46.9\" cy=\"74.8\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"118.5\" cy=\"74.2\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"125.7\" cy=\"70.6\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"135.3\" cy=\"61.7\" r=\"3.8\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"44.7\" cy=\"67.4\" r=\"3.9\" fill=\"#dc2626\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"105.9\" cy=\"72.0\" r=\"3.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"127.9\" cy=\"62.9\" r=\"3.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"113.3\" cy=\"69.3\" r=\"3.9\" fill=\"#2563eb\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"56.7\" cy=\"61.5\" r=\"3.9\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><circle cx=\"52.1\" cy=\"61.6\" r=\"4.2\" fill=\"#1f2937\" stroke=\"rgba(255,255,255,.82)\" stroke-width=\"0.8\"/><text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Rivaroxaban</text></svg>", "source_note": "PubChem 3D SDF"}, "XOLAIR": {"display": "Xolair", "kind": "Biologic antibody", "summary": "Omalizumab, monoclonal antibody against IgE", "components": [], "svg": "\n    <svg viewBox=\"0 0 180 140\" role=\"img\" aria-label=\"Biologic structure class\">\n      <defs>\n        <linearGradient id=\"bioGrad\" x1=\"0\" x2=\"1\" y1=\"0\" y2=\"1\">\n          <stop offset=\"0%\" stop-color=\"#c7f3ef\"/>\n          <stop offset=\"55%\" stop-color=\"#d9e8ff\"/>\n          <stop offset=\"100%\" stop-color=\"#f7e7c2\"/>\n        </linearGradient>\n      </defs>\n      <rect x=\"0\" y=\"0\" width=\"180\" height=\"140\" rx=\"18\" fill=\"rgba(255,255,255,.68)\"/>\n      <path d=\"M38 96 C54 56, 73 38, 91 68 C109 98, 131 80, 145 42\" fill=\"none\" stroke=\"url(#bioGrad)\" stroke-width=\"15\" stroke-linecap=\"round\"/>\n      <path d=\"M39 96 C55 56, 74 38, 92 68 C110 98, 132 80, 146 42\" fill=\"none\" stroke=\"#0f172a\" stroke-opacity=\".22\" stroke-width=\"1.2\"/>\n      <circle cx=\"55\" cy=\"65\" r=\"8\" fill=\"#10A69F\" opacity=\".72\"/>\n      <circle cx=\"91\" cy=\"69\" r=\"9\" fill=\"#4D8BBD\" opacity=\".68\"/>\n      <circle cx=\"126\" cy=\"74\" r=\"7\" fill=\"#E2B84D\" opacity=\".76\"/>\n      <text x=\"14\" y=\"24\" font-size=\"10\" font-weight=\"900\" fill=\"#64748b\">BIOLOGIC</text>\n      <text x=\"14\" y=\"126\" font-size=\"9\" font-weight=\"800\" fill=\"#64748b\">Macromolecule class glyph</text>\n    </svg>\n    ", "source_note": "Biologic class glyph; no small-molecule conformer used"}};
const molCard = document.getElementById('molCard');
const molVisual = document.getElementById('molVisual');
const molName = document.getElementById('molName');
const molMeta = document.getElementById('molMeta');
const molSource = document.getElementById('molSource');
const ambientKeys = Object.keys(STRUCTURE_CATALOG).filter(key => {
  const entry = STRUCTURE_CATALOG[key] || {};
  const components = entry.components || [];
  return components.length > 0 && Boolean(entry.svg);
});
const ambientSlots = [
  document.getElementById('chemA'),
  document.getElementById('chemB'),
  document.getElementById('chemC'),
  document.getElementById('chemD'),
  document.getElementById('chemE'),
  document.getElementById('chemF'),
  document.getElementById('chemG'),
  document.getElementById('chemH')
].filter(Boolean);
let ambientTick = 0;

function setAmbientMolecules() {
  if (!ambientKeys.length || !ambientSlots.length) return;
  ambientSlots.forEach((slot, i) => {
    const key = ambientKeys[(ambientTick + i * 3) % ambientKeys.length];
    const entry = STRUCTURE_CATALOG[key] || {};
    slot.classList.add('fade');
    window.setTimeout(() => {
      slot.innerHTML = entry.svg || '';
      slot.classList.remove('fade');
    }, 260);
  });
  ambientTick = (ambientTick + 1) % ambientKeys.length;
}

setAmbientMolecules();
window.setInterval(setAmbientMolecules, 4800);

function positionMolCard(ev) {
  const pad = 18;
  const cardW = molCard.offsetWidth || 260;
  const cardH = molCard.offsetHeight || 210;
  const x = Math.min(ev.clientX + 18, window.innerWidth - cardW - pad);
  const y = Math.max(pad + cardH / 2, Math.min(ev.clientY, window.innerHeight - pad - cardH / 2));
  molCard.style.left = x + 'px';
  molCard.style.top = y + 'px';
}

function showStructure(link, ev) {
  const drug = (link.dataset.drug || '').toUpperCase();
  const entry = STRUCTURE_CATALOG[drug];
  if (!entry) return;
  molVisual.innerHTML = entry.svg || '';
  molName.textContent = entry.display || drug;
  molMeta.textContent = (entry.kind || 'Structure context') + ' · ' + (entry.summary || '');
  molSource.textContent = entry.source_note || '';
  positionMolCard(ev);
  molCard.classList.add('show');
}

function hideStructure() {
  molCard.classList.remove('show');
}

document.querySelectorAll('.pt').forEach(el => {
  el.addEventListener('mousemove', ev => {
    tip.textContent = `${el.getAttribute('data-tip')} · openFDA`;
    tip.style.left = ev.clientX + 'px';
    tip.style.top = ev.clientY + 'px';
    tip.style.opacity = '1';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = '0'; });
});

document.querySelectorAll('.drug-label').forEach(el => {
  const drug = (el.textContent || '').trim();
  el.addEventListener('mousemove', ev => {
    tip.textContent = `${drug} · openFDA drug-event counts`;
    tip.style.left = ev.clientX + 'px';
    tip.style.top = ev.clientY + 'px';
    tip.style.opacity = '1';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = '0'; });
});

document.querySelectorAll('.openfda-link').forEach(link => {
  link.addEventListener('mousemove', ev => showStructure(link, ev));
  link.addEventListener('mouseleave', hideStructure);
  link.addEventListener('focus', ev => {
    const rect = link.getBoundingClientRect();
    showStructure(link, { clientX: rect.right, clientY: rect.top + rect.height / 2 });
  });
  link.addEventListener('blur', hideStructure);
});
</script>
</body>
</html>
'''

st.markdown(
    "<style>#MainMenu, header, footer {visibility:hidden;} .block-container {padding:0; max-width:100%;}</style>",
    unsafe_allow_html=True,
)
components.html(HTML, height=980, scrolling=True)
