"""TerraRotate: a crop-rotation decision-support app built on NASA and USDA data.

Flow: 1) farm goals and limits → 2) draw the field on a map → 3) plan with
summary, plan comparison, field data and a crop guide."""

import base64
import html as html_lib
import json
import math
from pathlib import Path

from branca.element import MacroElement, Template
import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from catalog import (
    ALL_CROP_NAMES,
    CONSTRAINTS,
    CROP_ECONOMICS,
    EQUIPMENT_OPTIONS,
    EXPANDED_CROP_CATALOG,
    GOAL_INFO,
    GOAL_PRESETS,
    HISTORY_YEARS,
    PRIMARY_GOALS,
    US_CITIES_COORDS,
)
from nasa import check_field_is_farmable, compute_polygon_center_and_acres, explain_plan, run_full_field_analysis
import action_plan as ap
from page_transition import (
    begin_transition,
    cancel_pending_transition,
    end_transition,
    start_pending_transition,
)


class MapModeControl(MacroElement):
  """Leaflet control placed under the zoom +/- buttons."""

  _template = Template(
      """
    {% macro script(this, kwargs) %}
    try { (function() {
      var map = {{ this._parent.get_name() }};
      var container = map.getContainer();
      var mode = "move";
      var btnMove = null;
      var btnSelect = null;

      var css = document.createElement("style");
      css.textContent =
        ".leaflet-bar.tr-mode a.tr-btn{display:flex;align-items:center;" +
        "justify-content:center;width:30px;height:30px;line-height:1;" +
        "color:#334155;background:#fff;}" +
        ".leaflet-bar.tr-mode a.tr-btn:hover{background:#F1F5F9;}" +
        ".leaflet-bar.tr-mode a.tr-btn.active{background:#15803D;color:#fff;}" +
        ".leaflet-container.tr-select," +
        ".leaflet-container.tr-select .leaflet-interactive" +
        "{cursor:crosshair !important;}";
      document.head.appendChild(css);

      var svgHead = '<svg xmlns="http://www.w3.org/2000/svg" width="18" ' +
        'height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">';
      var iconMove = svgHead +
        '<polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/>' +
        '<polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/>' +
        '<line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>';
      var iconSelect = svgHead +
        '<polygon points="12 3 21 9 18 20 6 20 3 9"/>' +
        '<circle cx="12" cy="3" r="1.6" fill="currentColor"/>' +
        '<circle cx="21" cy="9" r="1.6" fill="currentColor"/>' +
        '<circle cx="18" cy="20" r="1.6" fill="currentColor"/>' +
        '<circle cx="6" cy="20" r="1.6" fill="currentColor"/>' +
        '<circle cx="3" cy="9" r="1.6" fill="currentColor"/></svg>';

      function setMode(m) {
        mode = m;
        try { sessionStorage.setItem("tr_map_mode", m); } catch (e) {}
        btnMove.classList.toggle("active", m === "move");
        btnSelect.classList.toggle("active", m === "select");
        container.classList.toggle("tr-select", m === "select");
        if (m === "select") {
          map.dragging.disable();
          map.doubleClickZoom.disable();
          map.keyboard.disable();
        } else {
          map.dragging.enable();
          map.doubleClickZoom.enable();
          map.keyboard.enable();
        }
      }

      var ctrl = L.control({position: "topleft"});
      ctrl.onAdd = function() {
        var div = L.DomUtil.create("div", "leaflet-bar leaflet-control tr-mode");

        btnMove = L.DomUtil.create("a", "tr-btn", div);
        btnMove.href = "#";
        btnMove.title = "Move map";
        btnMove.setAttribute("role", "button");
        btnMove.innerHTML = iconMove;

        btnSelect = L.DomUtil.create("a", "tr-btn", div);
        btnSelect.href = "#";
        btnSelect.title = "Select field";
        btnSelect.setAttribute("role", "button");
        btnSelect.innerHTML = iconSelect;

        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.on(btnMove, "click", function(e) {
          L.DomEvent.preventDefault(e);
          setMode("move");
        });
        L.DomEvent.on(btnSelect, "click", function(e) {
          L.DomEvent.preventDefault(e);
          setMode("select");
        });
        return div;
      };
      ctrl.addTo(map);

      container.addEventListener("click", function(e) {
        var onControl = e.target.closest && e.target.closest(".leaflet-control");
        if (mode === "move" && !onControl) {
          e.stopImmediatePropagation();
        }
      }, true);

      var savedMode = "move";
      try { savedMode = sessionStorage.getItem("tr_map_mode") || "move"; } catch (e) {}
      setMode(savedMode);
    })(); } catch (err) { console.error("TerraRotate map control failed:", err); }
    {% endmacro %}
    """
  )


st.set_page_config(
    page_title="TerraRotate · Crop Rotation Advisor",
    page_icon=str(Path(__file__).parent / "logo.png") if (Path(__file__).parent / "logo.png").exists() else "🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container { max-width: 1140px; padding-top: 1.25rem; padding-bottom: 4rem; }
[data-testid="stHeader"] { background: transparent; }
h1, h2, h3 { letter-spacing: -0.02em; }
h1 { font-weight: 650 !important; }

.tr-top { display: flex; align-items: center; justify-content: space-between; gap: 16px;
  flex-wrap: wrap; padding-bottom: 14px; margin-bottom: 28px; border-bottom: 1px solid rgba(128,128,128,0.28); }
.tr-brand { display: flex; align-items: center; gap: 10px; font-weight: 650; font-size: 17px; color: inherit; }
.tr-brand span { color: #71717A; font-weight: 400; font-size: 13px; }
.tr-mark { width: 54px; height: 54px; border-radius: 10px; overflow: hidden; background: #F7F5F2;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.tr-mark img { width: 100%; height: 100%; object-fit: contain; }
.tr-steps { display: flex; gap: 4px; flex-wrap: wrap; }
.tr-step { display: flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px;
  border-radius: 999px; font-size: 13px; color: #71717A; }
.tr-step b { width: 22px; height: 22px; border-radius: 999px; display: grid; place-items: center;
  font-size: 12px; font-weight: 600; background: rgba(128,128,128,0.18); color: inherit; }
.tr-step.on { background: rgba(128,128,128,0.18); color: inherit; font-weight: 500; }
.tr-step.on b { background: #15803D; color: #FFFFFF; }
.tr-step.done b { background: #DCFCE7; color: #15803D; }

.tr-eyebrow { font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
  color: #15803D; margin-bottom: 2px; }
.tr-muted { color: #71717A; font-size: 14px; margin: 0; }
.tr-section { font-size: 16px; font-weight: 600; margin: 0 0 2px 0; color: inherit; }

.tr-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 10px 0; }
.tr-chip { border: 1px solid rgba(128, 128, 128, 0.35); background: var(--secondary-background-color); border-radius: 999px;
  padding: 3px 11px; font-size: 13px; font-weight: 500; color: var(--text-color); }
.tr-arrow { color: #A1A1AA; font-size: 13px; }

.tr-badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 18px 0; }
.tr-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500;
  padding: 2px 9px; border-radius: 6px; border: 1px solid; white-space: nowrap; }
.tr-badge::before { content: ""; width: 6px; height: 6px; border-radius: 999px; background: currentColor; }
.tr-badge.ok { color: #166534; background: #F0FDF4; border-color: #BBF7D0; }
.tr-badge.warn { color: #92400E; background: #FFFBEB; border-color: #FDE68A; }
.tr-badge.bad { color: #991B1B; background: #FEF2F2; border-color: #FECACA; }
.tr-badge.neutral { color: #3F3F46; background: #F4F4F5; border-color: #E4E4F7; }
.tr-badge.plain::before { display: none; }

.tr-hero { border: 1px solid #BBF7D0; background: #F7FDF9; border-radius: 12px; padding: 20px 22px; }
.tr-hero, .tr-hero h3, .tr-hero p, .tr-hero b, .tr-hero span { color: #18181B; }
.tr-hero h3 { margin: 2px 0 4px 0; font-size: 22px; font-weight: 650; padding: 0; }
.tr-hero ul { margin: 6px 0 0 0; padding-left: 18px; }
.tr-hero li { margin: 2px 0; color: #3F3F46; font-size: 14px; }

.tr-yield-box { border: 1px solid #BFDBFE; background: #EFF6FF; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; }
.tr-yield-box.warn { border-color: #FDE68A; background: #FFFBEB; }
.tr-yield-box, .tr-yield-box h4, .tr-yield-box p, .tr-yield-box b, .tr-yield-box span { color: #18181B; }
.tr-yield-box h4 { margin: 2px 0 6px 0; font-size: 16px; font-weight: 650; }
.tr-yield-box p { margin: 0 0 6px 0; font-size: 13.5px; color: #3F3F46; }
.tr-yield-box small { font-size: 12px; color: #52525B; }

.tr-score { font-size: 34px; font-weight: 650; letter-spacing: -0.03em; line-height: 1.1;
  font-variant-numeric: tabular-nums; color: inherit; }
.tr-score small { font-size: 14px; font-weight: 500; color: #71717A; letter-spacing: 0; }
.tr-bar { margin: 8px 0; }
.tr-bar-head { display: flex; justify-content: space-between; font-size: 13px; color: inherit; }
.tr-bar-head b { font-weight: 600; font-variant-numeric: tabular-nums; }
.tr-bar-track { height: 6px; background: rgba(128,128,128,0.18); border-radius: 999px; overflow: hidden; margin-top: 4px; }
.tr-bar-fill { height: 100%; border-radius: 999px; }
.tr-list { margin: 4px 0 0 0; padding-left: 18px; font-size: 14px; color: inherit; }
.tr-list li { margin: 3px 0; }
.tr-label { font-size: 12px; font-weight: 600; color: #71717A; text-transform: uppercase;
  letter-spacing: 0.05em; margin: 12px 0 2px 0; }

.tr-season { border-top: 3px solid; padding-top: 10px; }
.tr-season h4 { font-size: 15px; margin: 0 0 4px 0; padding: 0; font-weight: 600; }
.tr-season p { font-size: 13.5px; color: inherit; margin: 0 0 6px 0; }
.tr-season small { font-size: 12.5px; color: #71717A; }

.tr-howto { counter-reset: s; list-style: none; padding: 0; margin: 8px 0 4px 0; }
.tr-howto li { counter-increment: s; display: flex; gap: 10px; margin: 0 0 10px 0;
  font-size: 14px; color: inherit; line-height: 1.4; }
.tr-howto li::before { content: counter(s); flex-shrink: 0; width: 22px; height: 22px; border-radius: 999px;
  background: rgba(128,128,128,0.18); color: inherit; font-size: 12px; font-weight: 600; display: grid; place-items: center; }

/* ---- next-steps timeline ---- */
.tr-tl-year { font-size: 13px; font-weight: 600; color: #71717A; margin: 18px 0 2px 0; }
.tr-tl-row { display: grid; grid-template-columns: 200px 1fr; gap: 16px; padding: 11px 0;
  border-top: 1px solid rgba(128,128,128,0.28); }
.tr-tl-when { display: flex; align-items: baseline; gap: 9px; font-size: 14px; font-weight: 600;
  font-variant-numeric: tabular-nums; color: inherit; }
.tr-tl-dot { width: 8px; height: 8px; border-radius: 999px; flex-shrink: 0; transform: translateY(-1px); }
.tr-tl-what b { font-size: 14px; font-weight: 600; color: inherit; }
.tr-tl-what span { display: block; font-size: 13px; color: #71717A; margin-top: 1px; }
@media (max-width: 640px) { .tr-tl-row { grid-template-columns: 1fr; gap: 2px; } }

[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,0.28); border-radius: 10px; padding: 12px 14px; }
[data-testid="stMetricValue"] { font-size: 1.45rem !important; font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] p { color: #71717A !important; font-weight: 500; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { padding: 8px 4px; }
[data-testid="stTextInputRootElement"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [role="group"] {
  background-color: var(--secondary-background-color) !important;
  border-color: rgba(128, 128, 128, 0.35) !important;
}
[data-testid="stTextInputRootElement"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] div,
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] * {
  color: var(--text-color) !important;
  -webkit-text-fill-color: var(--text-color) !important;
  opacity: 1 !important;
}
[data-testid="stTextInputRootElement"] input::placeholder,
[data-testid="stSelectbox"] [data-baseweb="select"] input::placeholder {
  color: #71717A !important;
  -webkit-text-fill-color: #71717A !important;
  opacity: 1;
}
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stTextInputRootElement"] svg {
  fill: var(--text-color) !important;
  color: var(--text-color) !important;
}
[data-testid="stIFrame"] { display: none; }
[data-testid="stPlotlyChart"] { border: 1px solid rgba(128,128,128,0.28); border-radius: 10px; padding: 4px; }

/* Segmented control (Low / Medium / High) - scoped only to stSegmentedControl so stPills stays untouched */
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] {
  width: 100% !important;
}
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button {
  flex: 1 1 0% !important;
  min-width: 0 !important;
  padding: 4px 4px !important;
  font-size: 12.5px !important;
  border-color: rgba(82, 82, 91, 0.65) !important;
  white-space: nowrap !important;
}
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button p,
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button span {
  font-size: 12.5px !important;
  white-space: nowrap !important;
}
/* Darker fill & crisp border for the active/selected option (Low / Medium / High) */
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
  background-color: rgba(220, 38, 38, 0.18) !important;
  border-color: #B91C1C !important;
  color: #991B1B !important;
  font-weight: 600 !important;
}
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[aria-checked="true"] p,
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[aria-checked="true"] span,
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p,
[data-testid="stSegmentedControl"] [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] span {
  color: inherit !important;
  font-weight: 600 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

GREEN = "#15803D"
ZINC = "#71717A"
FIELD_KEEP_RADIUS_DEG = 0.25
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FALLBACK_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803D" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>'
    '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>'
)


def get_logo_html() -> str:
  return '<img src="data:image/png;base64,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" alt="TerraRotate Logo" />'


def html(markup: str):
  st.markdown(markup, unsafe_allow_html=True)


def esc(text) -> str:
  return html_lib.escape(str(text))


def top_bar(step: int):
  labels = ["Your farm", "Your field", "Your plan"]
  steps = ""
  for i, label in enumerate(labels, start=1):
    cls = "on" if i == step else ("done" if i < step else "")
    mark = "✓" if i < step else str(i)
    steps += f'<div class="tr-step {cls}"><b>{mark}</b>{label}</div>'
  html(
      '<div class="tr-top">'
      f'<div class="tr-brand"><div class="tr-mark">{get_logo_html()}</div>'
      "TerraRotate<span>Crop rotation advisor · NASA Earth data</span></div>"
      f'<div class="tr-steps">{steps}</div></div>'
  )


def chips(sequence) -> str:
  parts = [f'<span class="tr-chip">{esc(c)}</span>' for c in sequence]
  return '<div class="tr-chips">' + '<span class="tr-arrow">→</span>'.join(parts) + "</div>"


def badge(text: str, tone: str = "neutral") -> str:
  return f'<span class="tr-badge {tone}">{esc(text)}</span>'


def bar(label: str, value: float, color: str = GREEN, suffix: str = "") -> str:
  value = max(0, min(100, float(value)))
  return (
      '<div class="tr-bar"><div class="tr-bar-head">'
      f"<span>{esc(label)}</span><b>{value:.0f}{suffix}</b></div>"
      f'<div class="tr-bar-track"><div class="tr-bar-fill" style="width:{value}%;'
      f'background:{color}"></div></div></div>'
  )


def bullet_list(items) -> str:
  return '<ul class="tr-list">' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def score_color(value: float) -> str:
  if value >= 80:
    return GREEN
  if value >= 60:
    return "#CA8A04"
  return "#DC2626"


def scroll_to_top(token: str):
  st.iframe(
      f"""
      <script>
      // view: {token}
      (function() {{
        const d = window.parent.document;
        function up() {{
          ['[data-testid="stMain"]', 'section.main', '[data-testid="stAppViewContainer"]']
            .forEach(function(sel) {{
              const el = d.querySelector(sel);
              if (el) {{ el.scrollTop = 0; }}
            }});
          window.parent.scrollTo(0, 0);
        }}
        up(); setTimeout(up, 60); setTimeout(up, 300);
      }})();
      </script>
      """,
      height=1,
  )


def sync_sliders_to_goal():
  preset = GOAL_PRESETS.get(st.session_state.get("goal_widget"))
  if preset:
    st.session_state["slider_water"] = preset["water"]
    st.session_state["slider_equip"] = preset["equip"]
    st.session_state["slider_forage"] = preset["forage"]


def find_nearest_city(lat, lon):
  best, best_dist = ("Kansas", "Garden City (Finney County)"), float("inf")
  for state, cities in US_CITIES_COORDS.items():
    for city, (clat, clon) in cities.items():
      dist = math.hypot(clat - lat, clon - lon)
      if dist < best_dist:
        best, best_dist = (state, city), dist
  return best


WEIGHT_LABELS = {
    "water_efficiency": "Water use",
    "soil_health_protection": "Soil protection",
}


def weight_rows(weights: dict):
  return sorted(
      ((WEIGHT_LABELS[k], v) for k, v in weights.items() if k in WEIGHT_LABELS),
      key=lambda r: -r[1],
  )


KIND_COLORS = {"prep": "#A1A1AA", "plant": "#15803D", "harvest": "#CA8A04", "terminate": "#0284C7"}
RESULT_TABS = ["Summary", "Compare plans", "Yield & Profit", "Next steps", "Field data", "Crop guide"]


def choose_plan(strategy_id: str):
  st.session_state["chosen_plan"] = strategy_id
  st.session_state["result_tab"] = "Next steps"


def go_to_tab(name: str):
  st.session_state["result_tab"] = name


def timeline_html(events, limit=None) -> str:
  out, year = "", None
  for e in events[:limit] if limit else events:
    if limit is None and e["start"].year != year:
      year = e["start"].year
      out += f'<div class="tr-tl-year">{year}</div>'
    out += (
        '<div class="tr-tl-row"><div class="tr-tl-when">'
        f'<span class="tr-tl-dot" style="background:{KIND_COLORS.get(e["kind"], ZINC)}"></span>'
        f'{esc(ap.fmt_range(e["start"], e["end"]))}</div>'
        f'<div class="tr-tl-what"><b>{esc(e["action"])}</b><span>{esc(e["tip"])}</span></div></div>'
    )
  return out


def goal_short(goal: str) -> str:
  return GOAL_INFO.get(goal, (goal, ""))[0]


def advisor_question_guidance(question: str, plan: dict, clim: dict, soil: dict,
                              frost: dict | None, region_label: str) -> str:
  """Returns a field-data-grounded recommendation for each advisor question."""
  ql = question.lower()
  seq = plan.get("crop_sequence") or []
  precip = clim.get("annual_precipitation_mm", 0)
  drought_idx = clim.get("calculated_drought_risk_index", 0)
  heat_days = clim.get("summer_heat_stress_days_avg", 0)
  om = soil.get("organic_matter")
  texture = soil.get("soil_texture") or "your topsoil"
  drainage = soil.get("drainage_class") or "local drainage"

  if "hessian fly" in ql:
    ff_txt = ""
    if frost:
      ff = ap._doy(2025, frost["first_fall_doy"])
      ff_txt = f" Based on NASA POWER, your median first fall frost is around **{ff:%B} {ff.day}**, so target planting within 2–3 weeks before that window."
    return (
        f"**Suggested approach:** Planting Winter Wheat after your county's Hessian fly-free date prevents fall brood infestation and reduces winterkill risk.{ff_txt} "
        f"Ask your **{region_label}** extension agent for certified wheat varieties rated for local rust resistance and straw strength."
    )
  if "nitrogen rate" in ql:
    corn_idx = next((i for i, c in enumerate(seq) if "corn" in c.lower()), -1)
    prev_crop = seq[corn_idx - 1] if corn_idx > 0 else (seq[-1] if seq else "the prior crop")
    legume_prev = any(k in prev_crop.lower() for k in ("soybean", "alfalfa", "pea", "clover"))
    om_note = (
        f"Your USDA soil survey shows **{om}% organic matter** ({texture}), which mineralizes roughly {om * 20:.0f}–{om * 25:.0f} lb N/acre per year."
        if om is not None else
        f"Because surface organic matter wasn't reported for **{texture}**, a pre-plant nitrate test is especially valuable."
    )
    credit = (
        f"Since **{prev_crop}** precedes Corn in this sequence, you can typically claim a **30–45 lb N/acre legume credit**."
        if legume_prev else
        f"Since **{prev_crop}** is non-legume, plan for full yield-goal nitrogen plus early starter N to avoid residue tie-up."
    )
    return f"**Suggested approach:** {credit} {om_note} Split-applying nitrogen (starter + sidedress) protects yield under {precip:.0f} mm/yr rainfall."
  if "elevator or feedlot" in ql:
    return (
        f"**Suggested approach:** Grain Sorghum fits dryland or limited-irrigation budgets well—your field averages **{precip:.0f} mm/yr** rain with **{heat_days:.0f} days/yr** above 35 °C. "
        "Before seeding, lock in a local elevator or feedlot delivery basis (typically priced at 90–95% of corn) and verify drying/moisture dockage rules."
    )
  if "inoculant" in ql or "soybean cyst" in ql:
    return (
        "**Suggested approach:** Apply a fresh *Bradyrhizobium japonicum* seed inoculant if Soybeans have not grown on this field within the past 3–5 years—it is low-cost insurance for strong nodulation. "
        "Request a soil SCN egg-count test and select a resistant variety (PI 88788 or Peking source) if nematodes are present nearby."
    )
  if "end the rye" in ql or "rye cover" in ql:
    ls_txt = ""
    if frost:
      ls = ap._doy(2025, frost["last_spring_doy"])
      ls_txt = f" Your typical last spring frost is around **{ls:%B} {ls.day}**; terminating 14–21 days before cash-crop planting preserves topsoil moisture."
    return (
        f"**Suggested approach:** With **{precip:.0f} mm/yr** annual rainfall, terminate Winter Rye early (boot stage or ~12 inches tall) so it does not deplete spring seedbed moisture.{ls_txt} "
        "Ensure at least 10–14 days between burndown herbicide and corn planting to avoid green-bridge pest or allelopathy issues."
    )
  if "alfalfa" in ql:
    return (
        f"**Suggested approach:** Alfalfa requires well-drained soil (your field is classified as **{drainage}**) and a soil pH between **6.5 and 7.0** for strong nitrogen fixation. "
        "If pH is below 6.3, apply agricultural lime 6–12 months before seeding and confirm local hay/forage demand for a 3–5 year stand."
    )
  if "sunflower" in ql:
    return (
        "**Suggested approach:** Confirm whether nearby crushing plants or birdseed buyers offer forward contracts and check oleic vs. confection specs. "
        "Avoid planting adjacent to shelterbelts or wetlands where blackbird flocks roost, and keep at least 3–4 years between sunflower crops to prevent *Sclerotinia* white mold."
    )
  if "well capacity" in ql or "irrigation" in ql:
    water_note = (
        f"Your field receives **{precip:.0f} mm/yr** of rain with a drought risk index of **{drought_idx}/100**, meaning summer crops will rely heavily on stored soil moisture or irrigation."
        if precip < 650 else
        f"Your field averages **{precip:.0f} mm/yr** of rain (drought risk **{drought_idx}/100**), which supports dryland production in normal years but still benefits from supplemental water during heat waves."
    )
    return (
        f"**Suggested approach:** {water_note} Match peak July–August evapotranspiration demand against your well's GPM capacity or groundwater district allocation before finalizing acreage."
    )
  if "soil-test" in ql:
    return (
        f"**Suggested approach:** Yes—pull 0–6 inch composite cores for **pH, buffer pH, organic matter, P, K, and Zn**, plus a 0–24 inch profile core for **residual nitrate-N**. "
        f"USDA SSURGO lists **{texture}** here, so lab-verified baseline fertility ensures you only apply nutrients your first crop ({seq[0] if seq else 'first crop'}) actually needs."
    )
  if "cost-share" in ql or "eqip" in ql:
    return (
        "**Suggested approach:** Visit your local USDA NRCS Service Center before signing seed contracts—**EQIP (Environmental Quality Incentives Program)** and **CSP (Conservation Stewardship Program)** frequently pay per-acre incentives for multi-year crop rotation diversification, cover crops, and no-till residue management, provided you enroll *prior* to starting the practice."
    )
  return (
      f"**Suggested approach:** Bring your printed TerraRotate PDF summary for **{region_label}** ({precip:.0f} mm/yr rain, {texture}) to your local county extension agent or NRCS agronomist to calibrate variety selection, seeding rates, and input timing."
  )


DEFAULTS = {
    "step": "step1_city",
    "farmer_name": "",
    "selected_state": "Kansas",
    "selected_city": "Garden City (Finney County)",
    "polygon_points": [],
    "gps_point": None,
    "chosen_plan": None,
    "gps_town": None,
    "geo_waiting": False,
    "geo_error": None,
    "map_center": [37.9717, -100.8727],
    "map_zoom": 14,
    "user_past_crops": {},
    "goal_widget": PRIMARY_GOALS[0],
    "slider_water": "Medium",
    "slider_equip": "High",
    "slider_forage": "Low",
    "owned_equipment": [],
}
for k, v in DEFAULTS.items():
  if k not in st.session_state:
    st.session_state[k] = v


# Sayfa geçişi animasyonu (yalnızca sayfa değiştiğinde ve >1 sn sürdüğünde görünür)
_tx = begin_transition(st.session_state["step"])


# ==============================================================================
# STEP 1 — YOUR FARM
# ==============================================================================
if st.session_state["step"] == "step1_city":
  top_bar(1)
  _, col, _ = st.columns([0.45, 2.6, 0.45])

  with col:
    html('<div class="tr-eyebrow">Step 1 of 3</div>')
    st.title("Tell us about your farm")
    html(
        '<p class="tr-muted">Four quick answers. We combine them with NASA'
        " climate data and USDA soil and crop records to compare rotation"
        " options for your field.</p>"
    )
    st.write("")

    name_input = st.text_input(
        "Your name",
        value=st.session_state["farmer_name"],
        placeholder="e.g. John Miller",
    )

    st.write("")
    html('<p class="tr-section">What matters most this season?</p>')
    st.pills(
        "Main goal",
        PRIMARY_GOALS,
        key="goal_widget",
        format_func=goal_short,
        on_change=sync_sliders_to_goal,
        label_visibility="collapsed",
        required=True,
        wrap=True,
    )
    chosen_goal = st.session_state.get("goal_widget") or PRIMARY_GOALS[0]
    st.caption(GOAL_INFO[chosen_goal][1] + " Your limits below are automatically locked to match this goal.")

    st.write("")
    html('<p class="tr-section">Your limits</p>')
    html('<p class="tr-muted">Locked automatically based on your primary season goal above.</p>')
    for c, (key, label, help_text) in zip(st.columns(len(CONSTRAINTS), gap="small"), CONSTRAINTS):
      with c:
        st.segmented_control(
            label,
            ["Low", "Medium", "High"],
            key=key,
            help=help_text,
            width="stretch",
            disabled=True,
        )

    st.write("")
    html('<p class="tr-section">Equipment you own or can rent</p>')
    html('<p class="tr-muted">Select machinery you have on-farm or can easily rent locally.</p>')
    st.multiselect(
        "Available machinery",
        options=EQUIPMENT_OPTIONS,
        key="owned_equipment",
        label_visibility="collapsed",
        placeholder="Choose equipment you own or can rent...",
    )

    st.write("")
    html('<p class="tr-section">Where is your farm?</p>')
    loc1, loc2 = st.columns(2)
    states = list(US_CITIES_COORDS.keys())
    with loc1:
      state_choice = st.selectbox(
          "State", states, index=states.index(st.session_state["selected_state"])
      )
    with loc2:
      city_options = list(US_CITIES_COORDS[state_choice].keys())
      if st.session_state["selected_city"] not in city_options:
        st.session_state["selected_city"] = city_options[0]
      city_choice = st.selectbox(
          "Nearest town",
          city_options,
          index=city_options.index(st.session_state["selected_city"]),
      )

    if st.button("Use my current location", icon=":material/my_location:"):
      st.session_state["geo_request"] = st.session_state.get("geo_request", 0) + 1
      st.session_state["geo_waiting"] = True
      st.session_state["geo_error"] = None
    if st.session_state.get("geo_waiting"):
      geo = get_geolocation(component_key=f"geo_{st.session_state['geo_request']}")
      if geo is None:
        st.caption("Waiting for your browser… allow location access if it asks.")
      elif "coords" in geo:
        lat, lon = geo["coords"]["latitude"], geo["coords"]["longitude"]
        b_state, b_city = find_nearest_city(lat, lon)
        st.session_state.update(
            geo_waiting=False,
            gps_point=[lat, lon],
            gps_town=(b_state, b_city),
            selected_state=b_state,
            selected_city=b_city,
        )
        st.rerun()
      else:
        st.session_state["geo_waiting"] = False
        st.session_state["geo_error"] = geo.get("error", {}).get("message", "")
        st.rerun()

    if st.session_state.get("geo_error") is not None:
      reason = st.session_state["geo_error"]
      st.warning(
          "Could not read your location"
          + (f" ({reason})" if reason else "")
          + ". Allow location access in the browser, or pick the state and"
          " town above."
      )
    elif st.session_state.get("gps_point") and st.session_state.get("gps_town") == (
        state_choice, city_choice
    ):
      g_lat, g_lon = st.session_state["gps_point"]
      st.success(
          f"Using your location ({g_lat:.4f}, {g_lon:.4f}). Nearest town:"
          f" {city_choice}, {state_choice}."
      )

    st.write("")
    if st.button("Continue to map", type="primary", width="stretch"):
      st.session_state["farmer_name"] = name_input.strip() or "Farmer"
      st.session_state["selected_state"] = state_choice
      st.session_state["selected_city"] = city_choice
      st.session_state["geo_error"] = None
      if st.session_state.get("gps_point") and st.session_state.get("gps_town") == (
          state_choice, city_choice
      ):
        center = list(st.session_state["gps_point"])
      else:
        center = list(US_CITIES_COORDS[state_choice][city_choice])
      st.session_state["map_center"] = center
      st.session_state["map_zoom"] = 14
      pts = st.session_state["polygon_points"]
      if pts:
        p_lat = sum(p[0] for p in pts) / len(pts)
        p_lon = sum(p[1] for p in pts) / len(pts)
        if math.hypot(p_lat - center[0], p_lon - center[1]) > FIELD_KEEP_RADIUS_DEG:
          st.session_state["polygon_points"] = []
          st.session_state["field_cleared_notice"] = True
        else:
          st.session_state["map_center"] = [p_lat, p_lon]
      st.session_state["step"] = "step2_map"
      st.rerun()

  scroll_to_top("step1")


# ==============================================================================
# STEP 2 — YOUR FIELD
# ==============================================================================
elif st.session_state["step"] == "step2_map":
  top_bar(2)
  fname = st.session_state["farmer_name"]
  s_state = st.session_state["selected_state"]
  s_city = st.session_state["selected_city"]
  pts = st.session_state["polygon_points"]

  st.markdown(
      "<style>.block-container { max-width: min(1760px, 96vw) !important; }</style>",
      unsafe_allow_html=True,
  )
  html('<div class="tr-eyebrow">Step 2 of 3</div>')
  st.title("Outline your field")
  if pts:
    where = "your field"
  elif st.session_state.get("gps_point") and st.session_state.get("gps_town") == (s_state, s_city):
    where = f"your location near {s_city}, {s_state}"
  else:
    where = f"{s_city}, {s_state}"
  html(f'<p class="tr-muted">Map centered on {esc(where)}.</p>')
  if st.session_state.pop("field_cleared_notice", False):
    st.info(
        "Your earlier field outline was far from the new location, so it was"
        " cleared. Draw the field again here.",
        icon=":material/info:",
    )
  if st.session_state.get("not_farmable"):
    st.error(
        f"This outline covers mostly {st.session_state['not_farmable']} (buildings,"
        " roads, water), not farmland, so we can't give a rotation plan for it."
        " Move the corners onto open ground and try again. Trees, grass and a"
        " few buildings inside a larger field are fine.",
        icon=":material/block:",
    )
  st.write("")

  hist_col, map_col, side_col = st.columns([1.15, 3.0, 1.15], gap="medium")

  with hist_col:
    with st.container(border=True):
      html('<p class="tr-section">Optional: past crops</p>')
      st.caption(
          "Enter the crops you planted in past years. For any year left as"
          " 'Not sure', we automatically pull USDA NASS satellite crop records"
          " to recommend next seasons' crops without yield loss."
      )
      crop_options = [""] + ALL_CROP_NAMES
      new_history = {}
      for yr in HISTORY_YEARS:
        prev = st.session_state["user_past_crops"].get(str(yr), "")
        new_history[str(yr)] = st.selectbox(
            str(yr),
            crop_options,
            index=crop_options.index(prev) if prev in crop_options else 0,
            format_func=lambda v: v or "Not sure (auto-fetch USDA)",
        )
      st.session_state["user_past_crops"] = new_history

  with map_col:
    m = folium.Map(
        location=st.session_state["map_center"],
        zoom_start=st.session_state["map_zoom"],
        tiles=None,
    )
    folium.TileLayer(
        tiles="https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
        attr="USGS The National Map (NAIP imagery)",
        name="Satellite",
        max_native_zoom=16,
        max_zoom=19,
    ).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Streets", show=False).add_to(m)
    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    m.add_child(MapModeControl())

    fg = folium.FeatureGroup(name="field_boundary")
    for idx, pt in enumerate(pts):
      folium.CircleMarker(
          location=[pt[0], pt[1]],
          radius=6,
          color="#FACC15",
          weight=3,
          fill=True,
          fill_color="#FFFFFF",
          fill_opacity=1.0,
          tooltip=f"Corner {idx + 1}",
      ).add_to(fg)
    if len(pts) >= 2:
      folium.PolyLine(pts, color="#FACC15", weight=3).add_to(fg)
    if len(pts) >= 3:
      folium.Polygon(
          locations=pts,
          color="#FACC15",
          weight=3,
          fill=True,
          fill_color="#FACC15",
          fill_opacity=0.18,
          tooltip=f"{fname}'s field",
      ).add_to(fg)

    map_state = st_folium(
        m,
        feature_group_to_add=fg,
        height=520,
        use_container_width=True,
        key="draw_map",
        returned_objects=["last_clicked", "center", "zoom"],
    )

  if map_state:
    if map_state.get("center"):
      st.session_state["map_center"] = [
          map_state["center"]["lat"],
          map_state["center"]["lng"],
      ]
    if map_state.get("zoom"):
      st.session_state["map_zoom"] = map_state["zoom"]

  clicked = map_state.get("last_clicked") if map_state else None
  if clicked:
    click_key = (round(clicked["lat"], 5), round(clicked["lng"], 5))
    if click_key != st.session_state.get("last_processed_click"):
      st.session_state["last_processed_click"] = click_key
      st.session_state["polygon_points"].append(click_key)
      st.rerun()

  with side_col:
    with st.container(border=True):
      html('<p class="tr-section">How to draw</p>')
      html(
          '<ol class="tr-howto">'
          "<li><span>Use the <b>move</b> tool (under + / −) to pan and zoom to your field.</span></li>"
          "<li><span>Switch to the <b>corner</b> tool and click each corner of the field.</span></li>"
          "<li><span>Press <b>Analyze field</b> when the shape looks right.</span></li>"
          "</ol>"
      )
      st.divider()
      if len(pts) >= 3:
        _, _, est_acres = compute_polygon_center_and_acres(pts)
        st.metric("Field size", f"{est_acres:,.0f} acres", f"{len(pts)} corners", delta_color="off", delta_arrow="off")
      else:
        need = 3 - len(pts)
        st.metric("Corners placed", len(pts), f"{need} more to close the shape", delta_color="off", delta_arrow="off")

      b1, b2 = st.columns(2)
      with b1:
        if st.button("Undo", icon=":material/undo:", width="stretch", disabled=not pts):
          st.session_state["polygon_points"].pop()
          st.session_state.pop("not_farmable", None)
          st.rerun()
      with b2:
        if st.button("Clear", icon=":material/delete:", width="stretch", disabled=not pts):
          st.session_state["polygon_points"] = []
          st.session_state.pop("not_farmable", None)
          st.rerun()

      if st.button("Analyze field", type="primary", width="stretch"):
        pending_tx = start_pending_transition("step3_results")
        check = {}
        if len(pts) >= 3:
          check = check_field_is_farmable(tuple(pts))
          if check["farmable"] is False:
            st.session_state["not_farmable"] = check["reason"]
            cancel_pending_transition(pending_tx)
            st.rerun()
        st.session_state.pop("not_farmable", None)
        st.session_state["land_note"] = check.get("note", "") if len(pts) >= 3 else ""
        if len(pts) < 3:
          c = st.session_state["map_center"]
          st.session_state["polygon_points"] = [
              (c[0] - 0.005, c[1] - 0.006),
              (c[0] + 0.005, c[1] - 0.006),
              (c[0] + 0.005, c[1] + 0.006),
              (c[0] - 0.005, c[1] + 0.006),
          ]
        st.session_state["step"] = "step3_results"
        st.rerun()
      st.caption("No outline? We analyze a ~290-acre square at the map center.")

    if st.button("Back", icon=":material/arrow_back:"):
      st.session_state["step"] = "step1_city"
      st.rerun()

  scroll_to_top("step2")


# ==============================================================================
# STEP 3 — YOUR PLAN
# ==============================================================================
elif st.session_state["step"] == "step3_results":
  top_bar(3)
  fname = st.session_state["farmer_name"]
  s_state = st.session_state["selected_state"]
  s_city = st.session_state["selected_city"]
  pts = st.session_state["polygon_points"]
  goal = st.session_state.get("goal_widget") or PRIMARY_GOALS[0]

  prefs = {
      "primary_goal": goal,
      "water_availability": st.session_state.get("slider_water") or "Medium",
      "equipment_status": st.session_state.get("slider_equip") or "Medium",
      "forage_demand": st.session_state.get("slider_forage") or "Medium",
      "owned_equipment": st.session_state.get("owned_equipment") or [],
  }

  lat, lon, est_acres = compute_polygon_center_and_acres(pts)
  region_label = f"{s_city}, {s_state}"

  analysis_key = (
      fname, round(lat, 5), round(lon, 5), est_acres, region_label,
      json.dumps(prefs, sort_keys=True, default=str),
      json.dumps(st.session_state["user_past_crops"], sort_keys=True, default=str),
      st.session_state.get("data_retry", 0),
      st.session_state.get("scn_rain", 0), st.session_state.get("scn_temp", 0.0),
  )
  scenario = {
      "rain_pct": st.session_state.get("scn_rain", 0),
      "temp_c": st.session_state.get("scn_temp", 0.0),
  }
  scenario_on = bool(scenario["rain_pct"] or scenario["temp_c"])
  cached = st.session_state.get("analysis_cache")
  if cached and cached["key"] == analysis_key:
    report, climate_df, baseline = cached["report"], cached["climate_df"], cached.get("baseline")
  else:
    try:
      report, climate_df = run_full_field_analysis(
          fname, lat, lon, est_acres, region_label, prefs,
          user_overrides=st.session_state["user_past_crops"],
          scenario=scenario if scenario_on else None,
      )
      baseline = None
      if scenario_on:
        baseline, _ = run_full_field_analysis(
            fname, lat, lon, est_acres, region_label, prefs,
            user_overrides=st.session_state["user_past_crops"],
        )
    except Exception as e:
      end_transition(_tx)
      st.error(f"Could not load field data: {e}")
      st.stop()
    st.session_state["analysis_cache"] = {
        "key": analysis_key, "report": report, "climate_df": climate_df, "baseline": baseline,
    }

  if st.session_state.get("land_note"):
    st.info(st.session_state["land_note"], icon=":material/forest:")

  adv = report["tailored_farmer_advisory"]
  yrisk = report.get("yield_risk_analysis", {})
  status = report.get("data_status", {})
  clim = report["observed_climate_nasa"]
  soil = report["soil_profile_usda_ssurgo"]
  cdl = report["historical_crops_usda_cdl"]
  climate_live = status.get("nasa_power") == "live"
  weights = report.get("scoring_weights", {})

  strategies = report["rotation_strategies"]
  by_id = {sp["strategy_id"]: sp for sp in strategies}
  chosen = by_id.get(st.session_state.get("chosen_plan"))
  doc_plan = chosen or strategies[0]
  frost = ap.frost_dates(climate_df) if climate_live else None
  events = ap.build_schedule(doc_plan["crop_sequence"], frost) if frost else []
  questions = ap.advisor_questions(doc_plan)
  safe_name = "".join(ch for ch in fname if ch.isalnum()) or "Farmer"
  pdf_bytes = None
  pdf_error = None
  try:
    pdf_bytes = ap.build_pdf(
        report=report, strategy=doc_plan, weights=weights, events=events, frost=frost,
        questions=questions, polygon=pts, field_label=region_label, farmer=fname,
        goal_label=goal_short(goal), data_status=status,
    )
  except ImportError:
    pdf_error = "Install fpdf2 (`pip install fpdf2`) to enable PDF export."

  # ---- Header ---------------------------------------------------------------
  h1, h2 = st.columns([3, 1.1], vertical_alignment="bottom")
  with h1:
    html('<div class="tr-eyebrow">Your rotation plan</div>')
    st.title(f"{fname}'s field")
    html(
        f'<p class="tr-muted">{esc(region_label)} · about {est_acres:,.0f} acres'
        f" · Goal: {esc(goal_short(goal))}</p>"
    )
  with h2:
    a1, a2 = st.columns(2)
    with a1:
      with st.popover("Edit", icon=":material/edit:", width="stretch"):
        st.caption("What do you want to change? Your field outline is kept.")
        if st.button("Goal, limits or location", width="stretch"):
          st.session_state["step"] = "step1_city"
          st.rerun()
        if st.button("Field outline or past crops", width="stretch"):
          st.session_state["step"] = "step2_map"
          st.rerun()
    with a2:
      if pdf_bytes:
        st.download_button(
            "PDF report",
            icon=":material/picture_as_pdf:",
            data=pdf_bytes,
            file_name=f"TerraRotate_{safe_name}_plan.pdf",
            mime="application/pdf",
            width="stretch",
            help="Plan, season calendar, questions for your advisor and data sources.",
        )
      else:
        st.button("PDF report", icon=":material/picture_as_pdf:", disabled=True,
                  width="stretch", help=pdf_error or "PDF export unavailable.")

  # ---- Data source status ---------------------------------------------------
  cdl_found = status.get("usda_cdl_years_found", 0)
  cdl_total = status.get("usda_cdl_years_total", 0)
  soil_ok = status.get("usda_ssurgo") == "success"
  html(
      '<div class="tr-badges">'
      + badge(
          "NASA POWER climate · live" if climate_live else "NASA POWER climate · unavailable",
          "ok" if climate_live else "bad",
      )
      + badge(
          f"Crop history (User + USDA CDL) · {cdl_found} of {cdl_total} years",
          "ok" if cdl_found >= cdl_total - 1 else ("warn" if cdl_found else "bad"),
      )
      + badge("USDA soil survey · live" if soil_ok else "USDA soil survey · unavailable",
              "ok" if soil_ok else "bad")
      + "</div>"
  )
  extra = status.get("nasa_power_extra_params", [])
  st.caption(
      f"NASA POWER extra parameters: {', '.join(extra) if extra else 'none received'}"
      f" · Soil survey status: {status.get('usda_ssurgo', 'unknown')}"
  )
  if status.get("usda_ssurgo_error"):
    st.caption(f"Soil survey error: {status['usda_ssurgo_error']}")
  if not climate_live or not soil_ok or cdl_found < cdl_total - 1:
    if st.button("Try the data sources again", icon=":material/refresh:"):
      st.cache_data.clear()
      st.session_state["data_retry"] = st.session_state.get("data_retry", 0) + 1
      st.rerun()
  if not climate_live:
    st.error(
        "NASA POWER could not be reached, so the climate numbers on this page"
        " are placeholders, not measurements. Do not use them for decisions."
        " Try again in a minute.",
        icon=":material/cloud_off:",
    )

  if scenario_on:
    st.warning(
        f"What-if scenario on: rain {scenario['rain_pct']:+d}%, warming {scenario['temp_c']:+.1f} °C. "
        "The scores, plan and PDF below use it.",
        icon=":material/science:",
    )

  tab_summary, tab_compare, tab_econ, tab_next, tab_field, tab_crops = st.tabs(
      RESULT_TABS, key="result_tab", on_change="rerun"
  )

  # ---- Summary --------------------------------------------------------------
  with tab_summary:
    st.write("")
    # ---- What-if weather --------------------------------------------------------
    def _reset_scenario():
      st.session_state["scn_rain"] = 0
      st.session_state["scn_temp"] = 0.0

    with st.expander("What if the weather changes?", icon=":material/thermostat:", expanded=scenario_on):
      st.caption(
          "Move the sliders to test how the plans hold up in a drier or hotter future. "
          "Only the plan scores change; the field data stays as measured."
      )
      sc1, sc2, sc3 = st.columns([2, 2, 1], vertical_alignment="bottom")
      with sc1:
        st.slider("Yearly rain", -40, 40, 0, step=5, format="%d%%", key="scn_rain")
      with sc2:
        st.slider("Warming", 0.0, 4.0, 0.0, step=0.5, format="+%.1f °C", key="scn_temp")
      with sc3:
        st.button("Reset", icon=":material/restart_alt:", on_click=_reset_scenario,
                  disabled=not scenario_on, width="stretch")
      if scenario_on and baseline:
        sclim = report["scenario"]["climate"]
        st.caption(
            f"Scenario climate: {sclim['annual_precipitation_mm']:.0f} mm rain a year "
            f"(measured {clim['annual_precipitation_mm']:.0f}), "
            f"{sclim['summer_heat_stress_days_avg']:.0f} very hot days "
            f"(measured {clim['summer_heat_stress_days_avg']:.0f}), "
            f"drought risk {sclim['calculated_drought_risk_index']} / 100 "
            f"(measured {clim['calculated_drought_risk_index']})."
        )
        base_by_id = {sp["strategy_id"]: sp for sp in baseline["rotation_strategies"]}
        rows = []
        for sp in report["rotation_strategies"]:
          before = base_by_id[sp["strategy_id"]]["scores"]["overall_suitability"]
          after = sp["scores"]["overall_suitability"]
          rows.append({"Plan": sp["name"], "Measured climate": before,
                       "This scenario": after, "Change": round(after - before, 1)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        top_before = baseline["rotation_strategies"][0]["name"]
        top_after = report["rotation_strategies"][0]["name"]
        if top_before == top_after:
          st.success(f"The best plan stays the same: {top_after}.", icon=":material/check_circle:")
        else:
          st.warning(f"The best plan changes from {top_before} to {top_after}.", icon=":material/swap_horiz:")

    if yrisk:
      box_cls = "tr-yield-box warn" if yrisk.get("risk_level") == "high" else "tr-yield-box"
      html(
          f'<div class="{box_cls}">'
          f'<div class="tr-eyebrow" style="color:{"#92400E" if yrisk.get("risk_level") == "high" else "#1D4ED8"}">2021–2025 Crop History &amp; Yield-Loss Prevention</div>'
          f"<h4>{esc(yrisk.get('headline', ''))}</h4>"
          f"<p>{esc(yrisk.get('diagnosis', ''))}</p>"
          f"<p><b>Recommended next crop to prevent yield loss:</b> {esc(yrisk.get('recommended_next_crop', ''))} "
          f"(Sequence: {' → '.join(esc(c) for c in yrisk.get('recommended_sequence', []))})</p>"
          f"<small>Sources: {esc(yrisk.get('data_sources_used', ''))}</small>"
          "</div>"
      )

    best = report["rotation_strategies"][0]
    runner_up = report["rotation_strategies"][1]
    left, right = st.columns([1.7, 1], gap="large")
    with left:
      html(
          '<div class="tr-hero">'
          f'<div class="tr-eyebrow">Recommended for “{esc(goal_short(goal))}”</div>'
          f"<h3>{esc(best['name'])}</h3>"
          f"{chips(best['crop_sequence'])}"
          "</div>"
      )
      st.write("")
      if chosen and chosen["strategy_id"] == best["strategy_id"]:
        b1, b2 = st.columns([1, 1.4])
        b1.button("Plan chosen", icon=":material/check:", disabled=True, width="stretch")
        b2.button("See your next steps", type="primary", width="stretch",
                  on_click=go_to_tab, args=("Next steps",))
      else:
        st.button("Choose this plan", type="primary", icon=":material/check:",
                  on_click=choose_plan, args=(best["strategy_id"],))
        if chosen:
          st.caption(f"You chose “{chosen['name']}”. Change it any time in Compare plans.")

      st.write("")
      with st.expander(
          "Why we recommend this, supporting evidence, uncertainties & local checks",
          icon=":material/expand_more:",
          expanded=False,
      ):
        st.markdown("#### Why we recommend this")
        for item in [best["rationale"], *best.get("advantages", [])]:
          st.markdown(f"- {item}")

        st.markdown("#### What supports this")
        ev_items = best.get("evidence", [])
        if ev_items:
          for ev in ev_items:
            st.markdown(f"- {ev['text']} — :gray[{ev['source']}]")
        else:
          st.markdown(
              f"- Matched to **{clim['annual_precipitation_mm']:.0f} mm/yr** rainfall and "
              f"**{soil.get('soil_texture') or 'local'}** topsoil."
          )

        st.markdown("#### What we don't know / uncertainties")
        uncertainties = [
            "NASA POWER climate and USDA SSURGO soil layers are regional/field-center estimates, not in-field lab cores or rain gauges.",
            "Actual irrigation well GPM capacity, drainage tile condition, and local elevator delivery basis are not measured automatically.",
        ]
        if best.get("disadvantages"):
          uncertainties.extend(best["disadvantages"])
        for u in uncertainties:
          st.markdown(f"- {u}")

        st.markdown("#### Check locally before planting")
        for chk in report.get("information_gaps_and_local_validation", []):
          st.markdown(f"- {chk}")
    with right:
      with st.container(border=True):
        html('<p class="tr-label" style="margin-top:0">Plan score</p>')
        html(
            f'<div class="tr-score">{best["scores"]["overall_suitability"]:.1f}'
            "<small> / 100</small></div>"
        )
        gap = best["scores"]["overall_suitability"] - runner_up["scores"]["overall_suitability"]
        html(
            f'<p class="tr-muted">{gap:.1f} points ahead of “{esc(runner_up["name"])}”.</p>'
        )
        html('<p class="tr-label">Weighted for your goal</p>')
        html("".join(bar(lbl, pct * 100, ZINC, "%") for lbl, pct in weight_rows(weights)))
        st.caption("Compare all three plans in **Compare plans**.")

    st.write("")
    html('<p class="tr-section">Your field at a glance</p>')
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Rain per year",
        f"{clim['annual_precipitation_mm']:.0f} mm",
        help="Average yearly rainfall from NASA POWER (2021–2025).",
    )
    k2.metric(
        "Very hot days",
        f"{clim['summer_heat_stress_days_avg']:.0f} / yr",
        help="Summer days above 35 °C (95 °F), when many crops lose yield.",
    )
    k3.metric(
        "Drought risk",
        f"{clim['calculated_drought_risk_index']} / 100",
        help="Combines low rainfall and heat days. Higher means drier.",
    )
    k4.metric(
        "Topsoil",
        soil.get("soil_texture") or "Unknown",
        help="Surface soil texture from the USDA soil survey (SSURGO).",
    )

    st.write("")
    html(f'<p class="tr-section">Coming up for “{esc(doc_plan["name"])}”</p>')
    if events:
      html(timeline_html(events, limit=3))
      st.button("Full season calendar", icon=":material/calendar_month:",
                on_click=go_to_tab, args=("Next steps",))
    else:
      st.caption("Dates need live NASA POWER climate data, which is unavailable right now.")



  # ---- Compare plans --------------------------------------------------------
  with tab_compare:
    st.write("")
    html(
        '<p class="tr-muted">Three multi-year plans for your field, including'
        " the pattern you grow today. For your goal the score weighs "
        + ", ".join(f"{lbl.lower()} {pct:.0%}" for lbl, pct in weight_rows(weights))
        + ".</p>"
    )
    conf = report.get("ranking_confidence") or {}
    if conf:
      st.caption(
          f"How sure is the ranking? We shook the criteria weights by up to 30% and the scores by a few "
          f"points, {conf['runs']} times, and counted how often each plan came out first."
      )
    st.write("")
    for idx, strat in enumerate(report["rotation_strategies"]):
      sc = strat["scores"]
      tags = []
      if idx == 0:
        tags.append(badge("Best match", "ok"))
      if strat.get("strategy_id") == "STRAT_1_BASELINE":
        tags.append(badge("What you grow now", "neutral"))
      with st.container(border=True):
        html('<div class="tr-badges" style="margin:0 0 6px 0">' + "".join(tags) + "</div>")
        html(f'<p class="tr-section">{esc(strat["name"])}</p>')
        html(
            f'<div class="tr-score">{sc["overall_suitability"]:.1f}'
            "<small> / 100</small></div>"
        )
        html(chips(strat["crop_sequence"]))
        html(
            bar("Water efficiency", sc["water_efficiency"], score_color(sc["water_efficiency"]))
            + bar("Soil protection", sc["soil_health_protection"],
                  score_color(sc["soil_health_protection"]))
        )
        share = (conf.get("first_share") or {}).get(strat["strategy_id"])
        if share is not None:
          tone = "ok" if share >= 0.6 else ("warn" if share >= 0.25 else "neutral")
          html('<div class="tr-badges" style="margin:4px 0 8px 0">'
               + badge(f"First in {share:.0%} of {conf['runs']} tests", tone) + "</div>")
        html('<p class="tr-label">Why</p>')
        html(f'<p class="tr-muted">{esc(strat["rationale"])}</p>')
        if strat.get("evidence"):
          with st.expander("Evidence behind this plan"):
            for ev in strat["evidence"]:
              st.markdown(f"- {ev['text']} — :gray[{ev['source']}]")
        html('<p class="tr-label">Benefits</p>' + bullet_list(strat.get("advantages", [])))
        html('<p class="tr-label">Watch out for</p>' + bullet_list(strat.get("disadvantages", [])))
        st.write("")
        if chosen and chosen["strategy_id"] == strat["strategy_id"]:
          st.button("Chosen", icon=":material/check:", disabled=True, width="stretch",
                    key=f"chosen_{strat['strategy_id']}")
        else:
          st.button("Choose this plan", width="stretch", key=f"choose_{strat['strategy_id']}",
                    type="primary" if (idx == 0 and not chosen) else "secondary",
                    on_click=choose_plan, args=(strat["strategy_id"],))

  # ---- Yield & Profit -------------------------------------------------------
  with tab_econ:
    st.write("")
    total_ha = est_acres * 0.404686
    html('<p class="tr-section">Automatic Area, Seeding &amp; Revenue Estimator</p>')
    html(
        '<p class="tr-muted">Calculates plantable hectares from your map polygon, '
        'required seed volume, climate-adjusted harvest yield, and net profit using '
        'USDA NASS/ERS regional benchmarks. Adjust local prices or usable land % below.</p>'
    )
    st.write("")

    ec1, ec2, ec3 = st.columns([1.2, 1.2, 1.6], gap="medium")
    with ec1:
      plantable_pct = st.slider(
          "Plantable field share (%)",
          min_value=50, max_value=100, value=95, step=1,
          help="Excludes headlands, ditches, buffer strips, or farm roads.",
      )
    with ec2:
      price_adj_pct = st.slider(
          "Local market price adjustment (%)",
          min_value=-40, max_value=40, value=0, step=5, format="%+d%%",
          help="Shift all benchmark crop prices up or down to match your local elevator basis.",
      )
    with ec3:
      plan_names = {sp["strategy_id"]: sp["name"] for sp in strategies}
      selected_econ_id = st.selectbox(
          "Rotation plan to calculate",
          options=list(plan_names.keys()),
          index=list(plan_names.keys()).index(doc_plan["strategy_id"]),
          format_func=lambda sid: plan_names[sid],
      )

    plantable_ha = total_ha * (plantable_pct / 100.0)
    drought_idx = float(clim.get("calculated_drought_risk_index", 35))
    climate_yield_factor = max(0.75, min(1.10, 1.05 - (drought_idx / 400.0)))

    active_strat = by_id[selected_econ_id]
    seq_crops = active_strat["crop_sequence"]

    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mapped area", f"{total_ha:,.2f} ha", f"{est_acres:,.0f} acres", delta_color="off", delta_arrow="off")
    m2.metric("Net plantable area", f"{plantable_ha:,.2f} ha", f"{plantable_pct}% of field", delta_color="off", delta_arrow="off")

    econ_rows = []
    for yr_idx, crop_name in enumerate(seq_crops, start=1):
      base = CROP_ECONOMICS.get(
          crop_name,
          {"yield_t_ha": 3.5, "seed_kg_ha": 50.0, "price_usd_t": 250.0, "cost_usd_ha": 600.0},
      )
      adj_yield_ha = base["yield_t_ha"] * climate_yield_factor
      adj_price_t = base["price_usd_t"] * (1.0 + price_adj_pct / 100.0)
      total_seed_kg = base["seed_kg_ha"] * plantable_ha
      total_harvest_t = adj_yield_ha * plantable_ha
      gross_rev = total_harvest_t * adj_price_t
      total_cost = base["cost_usd_ha"] * plantable_ha
      net_profit = gross_rev - total_cost
      econ_rows.append({
          "Season": f"Year {yr_idx}",
          "Crop": crop_name,
          "Plantable (ha)": round(plantable_ha, 2),
          "Seed needed (kg)": round(total_seed_kg, 0),
          "Est. yield (t/ha)": round(adj_yield_ha, 2),
          "Total harvest (t)": round(total_harvest_t, 1),
          "Price ($/t)": round(adj_price_t, 0),
          "Gross revenue ($)": round(gross_rev, 0),
          "Est. cost ($)": round(total_cost, 0),
          "Net profit ($)": round(net_profit, 0),
      })

    df_econ = pd.DataFrame(econ_rows)
    total_net = float(df_econ["Net profit ($)"].sum())
    avg_annual_net = total_net / max(1, len(econ_rows))
    m3.metric("Avg annual net profit", f"${avg_annual_net:,.0f} / yr", f"${avg_annual_net / max(0.01, plantable_ha):,.0f} / ha", delta_color="off", delta_arrow="off")
    m4.metric(f"{len(econ_rows)}-year total net profit", f"${total_net:,.0f}", active_strat["name"], delta_color="off", delta_arrow="off")

    st.write("")
    html('<p class="tr-section">Season-by-season seeding &amp; revenue breakdown</p>')
    st.dataframe(df_econ, hide_index=True, width="stretch")

    st.write("")
    html('<p class="tr-section">Edit prices or yields manually (live recalculation)</p>')
    st.caption("Double-click any Price ($/t), Yield (t/ha), or Cost ($/ha) cell below to test your exact local figures.")
    editable_input = pd.DataFrame([
        {
            "Crop": r["Crop"],
            "Yield (t/ha)": r["Est. yield (t/ha)"],
            "Seed rate (kg/ha)": CROP_ECONOMICS.get(r["Crop"], {"seed_kg_ha": 50.0})["seed_kg_ha"],
            "Price ($/t)": r["Price ($/t)"],
            "Cost ($/ha)": round(r["Est. cost ($)"] / max(0.01, plantable_ha), 0),
        }
        for r in econ_rows
    ])
    edited_df = st.data_editor(
        editable_input,
        hide_index=True,
        width="stretch",
        disabled=["Crop"],
        key=f"econ_editor_{selected_econ_id}_{price_adj_pct}_{plantable_pct}",
    )

    custom_rows = []
    for idx_r, row in edited_df.iterrows():
      seed_tot = float(row["Seed rate (kg/ha)"]) * plantable_ha
      harv_tot = float(row["Yield (t/ha)"]) * plantable_ha
      rev_tot = harv_tot * float(row["Price ($/t)"])
      cost_tot = float(row["Cost ($/ha)"]) * plantable_ha
      net_tot = rev_tot - cost_tot
      custom_rows.append({
          "Season": f"Year {idx_r + 1} · {row['Crop']}",
          "Total seed (kg)": round(seed_tot, 0),
          "Total harvest (t)": round(harv_tot, 1),
          "Gross revenue ($)": round(rev_tot, 0),
          "Total cost ($)": round(cost_tot, 0),
          "Net profit ($)": round(net_tot, 0),
      })
    df_custom = pd.DataFrame(custom_rows)

    g_left, g_right = st.columns([1.3, 1], gap="medium")
    with g_left:
      fig_econ = go.Figure()
      fig_econ.add_bar(
          x=df_custom["Season"], y=df_custom["Gross revenue ($)"],
          name="Gross revenue ($)", marker_color="#0EA5E9",
      )
      fig_econ.add_bar(
          x=df_custom["Season"], y=df_custom["Total cost ($)"],
          name="Production cost ($)", marker_color="#F59E0B",
      )
      fig_econ.add_bar(
          x=df_custom["Season"], y=df_custom["Net profit ($)"],
          name="Net profit ($)", marker_color=GREEN,
      )
      fig_econ.update_layout(
          barmode="group", template="plotly_white", height=300,
          margin=dict(l=8, r=8, t=12, b=8),
          font=dict(family="Geist, sans-serif", size=12, color="#3F3F46"),
          legend=dict(orientation="h", y=1.15, x=0),
          yaxis=dict(title="USD ($)", gridcolor="#F4F4F5"),
      )
      st.plotly_chart(fig_econ, width="stretch", theme=None, config={"displayModeBar": False})
    with g_right:
      html('<p class="tr-section">All 3 plans · net profit comparison</p>')
      comp_rows = []
      for sp in strategies:
        sp_net = 0.0
        for c_nm in sp["crop_sequence"]:
          b_c = CROP_ECONOMICS.get(c_nm, {"yield_t_ha": 3.5, "price_usd_t": 250.0, "cost_usd_ha": 600.0})
          y_adj = b_c["yield_t_ha"] * climate_yield_factor
          p_adj = b_c["price_usd_t"] * (1.0 + price_adj_pct / 100.0)
          sp_net += (y_adj * p_adj - b_c["cost_usd_ha"]) * plantable_ha
        comp_rows.append({
            "Plan": sp["name"],
            "Avg annual net ($/yr)": round(sp_net / max(1, len(sp["crop_sequence"])), 0),
            "Total net ($)": round(sp_net, 0),
        })
      st.dataframe(pd.DataFrame(comp_rows), hide_index=True, width="stretch")
      st.caption(
          f"Climate yield factor applied: {climate_yield_factor:.2f}x (based on field drought risk "
          f"{drought_idx:.0f}/100). Source: USDA NASS & ERS commodity cost/return benchmarks."
      )

  # ---- Next steps -----------------------------------------------------------
  with tab_next:
    st.write("")
    if not chosen:
      st.info(
          "You have not chosen a plan yet. These steps are for the recommended"
          " plan; choose it below or pick another in Compare plans.",
          icon=":material/info:",
      )
    html(f'<div class="tr-eyebrow">{"Your chosen plan" if chosen else "Recommended plan"}</div>')
    html(f'<h3 style="margin:2px 0 0 0;padding:0">{esc(doc_plan["name"])}</h3>')
    html(chips(doc_plan["crop_sequence"]))
    if not chosen:
      st.button("Choose this plan", type="primary", icon=":material/check:",
                key="choose_from_next", on_click=choose_plan, args=(doc_plan["strategy_id"],))

    left, right = st.columns([1.8, 1], gap="large")
    with left:
      html('<p class="tr-section" style="margin-top:12px">Season calendar</p>')
      if events:
        ls = ap._doy(2025, frost["last_spring_doy"])
        ff = ap._doy(2025, frost["first_fall_doy"])
        html(
            '<p class="tr-muted">Windows are estimated from this field\'s typical'
            f" frost dates: last spring frost around {ls:%B} {ls.day}, first fall"
            f" frost around {ff:%B} {ff.day} (NASA POWER, {frost['years']} years)."
            " Confirm them with your local extension office.</p>"
        )
        html(timeline_html(events))
      else:
        st.warning(
            "Dates cannot be estimated because live NASA POWER climate data is"
            " unavailable. Try again in a minute.",
            icon=":material/cloud_off:",
        )
    with right:
      with st.container(border=True):
        html('<p class="tr-section">Take it with you</p>')
        if pdf_bytes:
          st.download_button(
              "Download PDF report", icon=":material/picture_as_pdf:", type="primary",
              data=pdf_bytes, file_name=f"TerraRotate_{safe_name}_plan.pdf",
              mime="application/pdf", width="stretch", key="pdf_next",
          )
        else:
          st.button(
              "Download PDF report", icon=":material/picture_as_pdf:",
              disabled=True, width="stretch", key="pdf_next_disabled",
              help=pdf_error or "PDF export unavailable.",
          )
          if pdf_error:
            st.caption(pdf_error)
        if events:
          st.download_button(
              "Add to calendar (.ics)", icon=":material/event:",
              data=ap.to_ics(events, doc_plan["name"], region_label),
              file_name=f"TerraRotate_{safe_name}_calendar.ics",
              mime="text/calendar", width="stretch",
          )
        st.download_button(
            "Raw data (JSON)", icon=":material/data_object:",
            data=json.dumps({**report, "chosen_plan": doc_plan["strategy_id"]}, indent=2),
            file_name=f"TerraRotate_{safe_name}_data.json",
            mime="application/json", width="stretch",
        )
        st.caption("The PDF has the plan, this calendar, the questions below and the data sources.")
      st.write("")
      with st.container(border=True):
        html('<p class="tr-section">Questions for your advisor</p>')
        st.caption("Click any question to see a tailored suggestion based on your field data.")
        for q_text in questions:
          with st.expander(q_text, icon=":material/help_outline:"):
            st.markdown(advisor_question_guidance(q_text, doc_plan, clim, soil, frost, region_label))
        st.caption("Your county extension office or NRCS service center can help with these.")

  # ---- Field data -----------------------------------------------------------
  with tab_field:
    st.write("")
    precip = clim["annual_precipitation_mm"]
    avg_temp = clim.get("annual_mean_temp_c")
    if avg_temp is None and "T2M" in climate_df.columns:
      avg_temp = float(climate_df["T2M"].astype(float).mean())
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.metric("Rain per year", f"{precip:.0f} mm",
              "Below 650 mm (dry)" if precip < 650 else "650 mm or more",
              delta_color="off", delta_arrow="off")
    f2.metric("Avg temperature", f"{avg_temp:.1f} °C" if avg_temp is not None else "Unknown",
              "2021–2025 mean", delta_color="off", delta_arrow="off")
    f3.metric("Very hot days", f"{clim['summer_heat_stress_days_avg']:.0f} / yr",
              "Above 35 °C", delta_color="off", delta_arrow="off")
    om = soil.get("organic_matter")
    f4.metric("Organic matter", f"{om}%" if om is not None else "Unknown", soil.get("soil_texture") or "",
              delta_color="off", delta_arrow="off")
    k_val = soil.get("water_erosion_k_factor")
    f5.metric("Water erosion (K)", f"{k_val}" if k_val is not None else "Unknown",
              (soil.get("erosion_summary") or "").split(" (")[0], delta_color="off", delta_arrow="off")

    if soil.get("data_note"):
      st.caption(soil["data_note"])
    elif soil.get("status") == "error":
      st.caption("The USDA soil service did not answer. Use the retry button to ask again.")

    agg_dict = {"PRECTOTCORR": "sum", "T2M_MAX": "mean", "GWETROOT": "mean"}
    if "T2M" in climate_df.columns:
      agg_dict["T2M"] = "mean"
    monthly = climate_df.resample("ME").agg(agg_dict)
    clim_m = monthly.groupby(monthly.index.month).mean()
    wet_m = int(clim_m["PRECTOTCORR"].idxmax())
    hot_m = int(clim_m["T2M_MAX"].idxmax())

    st.write("")
    g1, g2 = st.columns(2, gap="medium")
    with g1:
      html('<p class="tr-section">Typical year: rain and heat</p>')
      fig = go.Figure()
      fig.add_bar(x=MONTHS, y=clim_m["PRECTOTCORR"].round(0), name="Rain (mm)",
                  marker_color="#0EA5E9", hovertemplate="%{x}: %{y} mm<extra></extra>")
      fig.add_scatter(x=MONTHS, y=clim_m["T2M_MAX"].round(1), name="Daily high (°C)", yaxis="y2",
                      line=dict(color="#EA580C", width=2.5), mode="lines+markers",
                      hovertemplate="%{x}: %{y} °C<extra></extra>")
      if "T2M" in clim_m.columns:
        fig.add_scatter(x=MONTHS, y=clim_m["T2M"].round(1), name="Avg temp (°C)", yaxis="y2",
                        line=dict(color="#EAB308", width=2.2, dash="dot"), mode="lines+markers",
                        hovertemplate="%{x}: %{y} °C<extra></extra>")
      fig.update_layout(
          template="plotly_white", height=280, margin=dict(l=8, r=8, t=8, b=8),
          font=dict(family="Geist, sans-serif", size=12, color="#3F3F46"),
          legend=dict(orientation="h", y=1.14, x=0),
          yaxis=dict(title="mm", gridcolor="#F4F4F5"),
          yaxis2=dict(title="°C", overlaying="y", side="right", showgrid=False),
      )
      st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})
      avg_caption = f" Yearly mean temp: {avg_temp:.1f} °C." if avg_temp is not None else ""
      st.caption(
          f"Wettest month: {MONTHS[wet_m - 1]} ({clim_m['PRECTOTCORR'].max():.0f} mm on average)."
          f" Hottest month: {MONTHS[hot_m - 1]} (average daily high"
          f" {clim_m['T2M_MAX'].max():.0f} °C).{avg_caption} Source: NASA POWER, 2021–2025."
      )
    with g2:
      html('<p class="tr-section">Root-zone soil moisture</p>')
      rz = monthly["GWETROOT"]
      rz_mean = float(rz.mean())
      fig2 = go.Figure()
      fig2.add_scatter(x=rz.index, y=rz.round(3), mode="lines", name="Monthly",
                       line=dict(color=GREEN, width=2.5),
                       hovertemplate="%{x|%b %Y}: %{y}<extra></extra>")
      fig2.add_hline(y=rz_mean, line=dict(color=ZINC, dash="dot", width=1.5),
                     annotation_text="your field's average", annotation_position="top left",
                     annotation_font=dict(size=11, color=ZINC))
      fig2.update_layout(
          template="plotly_white", height=280, margin=dict(l=8, r=8, t=8, b=8),
          font=dict(family="Geist, sans-serif", size=12, color="#3F3F46"),
          yaxis=dict(title="wetness (0–1)", gridcolor="#F4F4F5"), showlegend=False,
      )
      st.plotly_chart(fig2, width="stretch", theme=None, config={"displayModeBar": False})
      driest = rz.idxmin()
      st.caption(
          f"Lowest point: {driest:%B %Y} at {rz.min():.2f}, against your field's"
          f" average of {rz_mean:.2f}. Values are compared with this field's own"
          " history, because normal moisture differs a lot between regions."
      )

    st.write("")
    d1, d2, d3 = st.columns([1.2, 1, 1], gap="medium")
    with d1:
      html('<p class="tr-section">Field boundary</p>')
      mini = folium.Map(location=[lat, lon], zoom_start=14, tiles=None)
      folium.TileLayer(
          tiles="https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
          attr="USGS The National Map", max_native_zoom=16, max_zoom=19,
      ).add_to(mini)
      if len(pts) >= 3:
        folium.Polygon(locations=pts, color="#FACC15", weight=3, fill=True,
                       fill_color="#FACC15", fill_opacity=0.18).add_to(mini)
      st_folium(mini, height=240, use_container_width=True, key="mini_map", returned_objects=[])
    with d2:
      html('<p class="tr-section">Past crops (2021–2025)</p>')
      hist = pd.DataFrame(
          [
              {
                  "Year": y,
                  "Crop": "No record" if d["crop_name"] == "Not Found" else d["crop_name"],
                  "Source": d.get("source", "USDA NASS CDL"),
              }
              for y, d in cdl["yearly_crops"].items()
          ]
      )
      st.dataframe(hist, hide_index=True, width="stretch", height=240)
      if cdl.get("monoculture_stress_flag"):
        st.caption("The same crop shows up every year. Rotating breaks pest and disease cycles.")
    with d3:
      html('<p class="tr-section">Soil</p>')
      soil_rows = pd.DataFrame(
          [
              {"Property": "Soil unit", "Value": soil.get("soil_unit_name") or "Unknown"},
              {"Property": "Texture", "Value": soil.get("soil_texture") or "Unknown"},
              {"Property": "Organic matter", "Value": f"{om}%" if om is not None else "Unknown"},
              {"Property": "Drainage", "Value": soil.get("drainage_class") or "Unknown"},
              {"Property": "Erosion", "Value": soil.get("erosion_summary") or "Unknown"},
          ]
      )
      st.dataframe(soil_rows, hide_index=True, width="stretch", height=240)

    st.write("")
    with st.container(border=True):
      html('<p class="tr-section">How the recommended plan scores on five factors</p>')
      pillars = adv["five_pillar_evaluation"]
      pc = st.columns(2, gap="large")
      for i, p in enumerate(pillars):
        with pc[i % 2]:
          html(bar(p["dimension"], p["score"], score_color(p["score"])))
          st.caption(p["note"])

    st.write("")
    with st.expander("Detailed information: where the data comes from and how the scores are calculated"):
      scored_clim = report.get("scenario", {}).get("climate") or clim
      ex = explain_plan(adv["recommended_primary_sequence"].split(" ➔ "), scored_clim, soil)
      w = ex["water"]

      st.markdown("**Where each piece of data comes from**")
      st.dataframe(
          pd.DataFrame([
              {"Data": "Rain, hot days, soil moisture, frost dates", "Source": "NASA POWER, daily, 2021–2025, at the center of your field"},
              {"Data": "Humidity, wind, evapotranspiration", "Source": "NASA POWER extra parameters (shown only if received)"},
              {"Data": "Soil texture, organic matter, drainage, erosion, water storage", "Source": "USDA NRCS SSURGO soil map, at the center of your field"},
              {"Data": "Past crops (2021–2025)", "Source": "Your entries first; any 'Not sure' year is filled from USDA NASS Cropland Data Layer"},
              {"Data": "Yield-loss prevention rotation", "Source": "USDA ARS LTAR rotation rules + USDA PLANTS nutrient/family profiles"},
          ]),
          hide_index=True, width="stretch",
      )
      gaps = []
      for y, d in cdl["yearly_crops"].items():
        if d["crop_name"] == "Not Found":
          code = d.get("raw_cdl_code")
          gaps.append(
              f"{y}: the satellite class ({code}) is not in this app's crop list" if code
              else f"{y}: no answer from the service, or not published yet"
          )
      if gaps:
        st.caption("Years shown as “No record”: " + "; ".join(gaps) + ".")

      st.markdown(f"**Water efficiency: {w['score']}**")
      lines = [
          f"- Rain {w['supply_mm']:.0f} mm a year against about {w['demand_mm']} mm of crop water need: {w['base']} points.",
          f"- Heat: −{w['heat_penalty']} ({scored_clim['summer_heat_stress_days_avg']:.0f} days above 35 °C a year).",
      ]
      if w["cover_penalty"]:
        lines.append(f"- Cover crop: −{w['cover_penalty']:.0f} because it uses spring moisture.")
      if w["awc"]:
        lines.append(f"- Soil water storage ({w['awc']} cm/cm): {w['awc_adjust']:+}.")
      st.markdown("\n".join(lines))

      st.markdown(f"**Soil protection: {ex['soil_score']}** (65% erosion control, 35% organic matter)")
      if ex["exposure_has_data"]:
        lines = [f"- {lbl}: {raw}, exposure {val:.2f} of 1" for lbl, val, raw in ex["erosion_terms"]]
        lines.append(f"- Average exposure {ex['exposure']} of 1. Crop cover averages {ex['cover']} of 100, so erosion control is {ex['erosion_score']}.")
      else:
        lines = [f"- No soil survey values were available, so a neutral exposure of 0.5 was used. Erosion control is {ex['erosion_score']}."]
      lines.append(f"- Organic matter contribution of the crops: {ex['om_score']}.")
      st.markdown("\n".join(lines))

      extra_lines = []
      if "annual_et_mm" in clim:
        extra_lines.append(f"Evapotranspiration about {clim['annual_et_mm']:.0f} mm a year, so rain minus evapotranspiration is {clim['water_balance_mm']:+.0f} mm.")
      if "avg_relative_humidity_pct" in clim:
        extra_lines.append(f"Average humidity {clim['avg_relative_humidity_pct']}%.")
      if "avg_wind_speed_ms" in clim:
        extra_lines.append(f"Average wind {clim['avg_wind_speed_ms']} m/s.")
      if extra_lines:
        st.caption("Also measured, shown for information and not used in the scores: " + " ".join(extra_lines))
      if ex["unrecognized"]:
        st.caption("These crops are not in the app's crop list and were scored as a typical row crop: " + ", ".join(ex["unrecognized"]) + ".")
      st.caption("Scores are decision support, not measurements. Confirm with your local extension office.")

    with st.expander("What do these terms mean?", icon=":material/menu_book:"):
      st.markdown(
          "- **Evapotranspiration (ET):** water that leaves the field as vapor, from soil and from plants. "
          "Rain minus ET is the **water balance**: negative means the field dries out without irrigation.\n"
          "- **Root-zone soil moisture:** how full the soil is where roots reach, from 0 (dry) to 1 (saturated). "
          "NASA POWER models it from satellite and weather data; it is not a probe in your soil.\n"
          "- **Very hot days:** summer days with a maximum above 35 °C, when corn and many crops lose yield.\n"
          "- **Drought risk index (0-100):** rises as yearly rain falls below 650 mm and as hot days increase. "
          "It is a simple screening number, not a forecast.\n"
          "- **Frost-free days:** days between the median last spring frost and first fall frost "
          "(daily minimum at or below 0 °C). They set which crops fit your season.\n"
          "- **K factor:** how easily water carries the topsoil away, from about 0.02 (resists) to 0.69 (erodes easily).\n"
          "- **Wind erodibility group:** 1 means very easily blown away, 8 means hardly at all.\n"
          "- **Hydrologic soil group:** A drains fast; D sheds most rain as runoff.\n"
          "- **Organic matter:** decayed plant material. More of it holds more water and nutrients.\n"
          "- **Satellite vs. ground:** satellites and models cover every field the same way but at coarse "
          "resolution; a soil test or a rain gauge on your farm is more exact for one spot. Use both."
      )

  # ---- Crop guide -----------------------------------------------------------
  with tab_crops:
    st.write("")
    q = st.text_input(
        "Search crops",
        placeholder="Search by name or role, e.g. drought, nitrogen, forage",
        label_visibility="collapsed",
        icon=":material/search:",
    )
    st.caption(
        "General notes for 20 crops, not a score for your field. Confirm local"
        " varieties and timing with your county extension office."
    )
    ql = q.strip().lower()
    crops = [
        c for c in EXPANDED_CROP_CATALOG
        if not ql or ql in (c["name"] + " " + c["role"] + " " + c["desc"]).lower()
    ]
    if not crops:
      st.info("No crops match that search.")
    cc = st.columns(3, gap="medium")
    for i, crop in enumerate(crops):
      with cc[i % 3]:
        with st.container(border=True):
          src_links = [(lbl, url) for lbl, url in crop.get("sources", [])]
          sources_html = " · ".join(
              f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(lbl)}</a>'
              for lbl, url in src_links
          )
          html(
              f'<p class="tr-section">{esc(crop["name"])}</p>'
              f'<div class="tr-badges" style="margin:4px 0 8px 0">{badge(crop["role"], "plain neutral")}</div>'
              f'<p class="tr-muted">{esc(crop["desc"])}</p>'
          )
          with st.expander("Needs and risks"):
            st.markdown(crop["reqs"].replace("Required Equipment:", "**Equipment:**"))
            st.markdown(crop["watchouts"].replace("Key Watchouts:", "**Watch:**"))
            st.markdown(crop["avoid_if"].replace("Avoid if:", "**Skip it if:**"))
          if sources_html:
            html(f'<p class="tr-muted" style="font-size:12px;margin-top:8px">Source: {sources_html}</p>')

  st.divider()
  st.caption(report["metadata"]["disclaimer"])
  scroll_to_top("results")

# Sayfa geçiş animasyonunu kapat (1 sn altındaysa hiç göstermez, >1 sn ise %100'e tamamlayıp söndürür)
end_transition(_tx)
