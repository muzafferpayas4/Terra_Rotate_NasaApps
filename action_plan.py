"""Turns a chosen rotation plan into dated actions, advisor questions and exports.

Planting and harvest windows are placed relative to the field's own median
last-spring and first-fall frost dates (from NASA POWER daily minimum
temperature). Offsets are common agronomic rules of thumb, not local
recommendations: every output says so and asks the farmer to confirm locally.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math

import pandas as pd

# ------------------------------------------------------------------------------
# Frost dates
# ------------------------------------------------------------------------------


def frost_dates(climate_df: pd.DataFrame) -> dict | None:
  """Median last spring frost and first fall frost (day of year), T_min ≤ 0 °C."""
  if climate_df is None or climate_df.empty or "T2M_MIN" not in climate_df:
    return None
  tmin = climate_df["T2M_MIN"].astype(float)
  springs, falls = [], []
  for _, s in tmin.groupby(tmin.index.year):
    spring = s[(s.index.month < 7) & (s <= 0)]
    fall = s[(s.index.month > 7) & (s <= 0)]
    if not spring.empty:
      springs.append(spring.index.max().dayofyear)
    if not fall.empty:
      falls.append(fall.index.min().dayofyear)
  if not springs or not falls:
    return None
  last_spring = int(pd.Series(springs).median())
  first_fall = int(pd.Series(falls).median())
  return {
      "last_spring_doy": last_spring,
      "first_fall_doy": first_fall,
      "frost_free_days": first_fall - last_spring,
      "years": len(springs),
  }


def _doy(year: int, doy: int) -> date:
  return date(year, 1, 1) + timedelta(days=doy - 1)


# ------------------------------------------------------------------------------
# Crop timing rules (offsets in days from LF = last spring frost, FF = first
# fall frost). kind: summer = planted and harvested the same year; winter =
# planted in fall, harvested next summer; cover = planted in fall, ended in
# spring before the next crop.
# ------------------------------------------------------------------------------
CROP_RULES = {
    "corn": dict(kind="summer", plant=("LF", 14, 28), end=("FF", -50, -15),
                 tip="Plant once soil at 2 in. stays above 10 °C (50 °F)."),
    "grain sorghum": dict(kind="summer", plant=("LF", 30, 50), end=("FF", -40, -5),
                          tip="Sorghum needs warmer soil than corn: about 16 °C (60 °F)."),
    "soybeans": dict(kind="summer", plant=("LF", 21, 40), end=("FF", -45, -10),
                     tip="Inoculate seed if soybeans have not grown here in 3–5 years."),
    "sunflower": dict(kind="summer", plant=("LF", 30, 50), end=("FF", -35, 0),
                      tip="Harvest promptly to limit bird losses."),
    "cotton": dict(kind="summer", plant=("LF", 30, 50), end=("FF", -40, 10),
                   tip="Needs about 180 frost-free days and warm soil."),
    "dry beans": dict(kind="summer", plant=("LF", 25, 40), end=("FF", -40, -15),
                      tip="Avoid poorly drained ground; beans are prone to root rot."),
    "winter wheat": dict(kind="winter", plant=("FF", -40, -20), end=("LF", 70, 85),
                         tip="Plant after your county's Hessian fly-free date."),
    "winter rye": dict(kind="cover", plant=("FF", -25, 10), end=("LF", 0, 14),
                       tip="Seed right after harvest; earlier seeding gives more cover."),
    "spring wheat": dict(kind="summer", plant=("LF", -21, 0), end=("LF", 100, 120),
                         tip="Plant as early as the soil can be worked."),
    "barley": dict(kind="summer", plant=("LF", -21, 0), end=("LF", 85, 105),
                   tip="Plant early; barley tolerates cool soil."),
    "oats": dict(kind="summer", plant=("LF", -21, 0), end=("LF", 90, 110),
                 tip="Plant early; oats lose yield in summer heat."),
    "canola": dict(kind="summer", plant=("LF", -14, 7), end=("LF", 95, 115),
                   tip="Scout for flea beetles right after emergence."),
    "peas": dict(kind="summer", plant=("LF", -21, 0), end=("LF", 80, 100),
                 tip="Inoculate with pea-specific rhizobia."),
    "alfalfa": dict(kind="summer", plant=("LF", 0, 30), end=("FF", -30, 0),
                    tip="Perennial: plan for 3–5 years of hay cuttings."),
    "fallow / idle cropland": dict(kind="summer", plant=("LF", 0, 0), end=("FF", 0, 0),
                                   tip="Keep residue on the surface and control weeds."),
    "grassland / pasture": dict(kind="summer", plant=("LF", 0, 0), end=("FF", 0, 0),
                                tip="Grazing or hay season."),
}
GENERIC_RULE = dict(kind="summer", plant=("LF", 21, 40), end=("FF", -40, -10),
                    tip="Confirm planting dates for this crop with your local extension office.")

ACTION_VERBS = {
    "fallow / idle cropland": ("Fallow season starts", "Fallow season ends"),
    "grassland / pasture": ("Grassland season starts", "Grassland season ends"),
}


def _rule(crop: str) -> dict:
  key = crop.lower().replace("corn (maize)", "corn").strip()
  return CROP_RULES.get(key, GENERIC_RULE)


def _window(anchor: tuple, year: int, frost: dict) -> tuple[date, date]:
  ref, lo, hi = anchor
  doy = frost["last_spring_doy"] if ref == "LF" else frost["first_fall_doy"]
  base = _doy(year, doy)
  return base + timedelta(days=lo), base + timedelta(days=hi)


def build_schedule(sequence: list[str], frost: dict, start: date | None = None) -> list[dict]:
  """Places each crop of the rotation on the calendar, one after the other.

  Returns events sorted by date: {start, end, crop, action, tip, kind}.
  """
  start = start or date.today()
  cursor = start
  placed = []
  for crop in sequence:
    rule = _rule(crop)
    for year in range(cursor.year - 1, cursor.year + 4):
      p_lo, p_hi = _window(rule["plant"], year, frost)
      if p_hi >= cursor:
        break
    p_lo = max(p_lo, cursor)
    end_year = year + (1 if rule["kind"] in ("winter", "cover") else 0)
    e_lo, e_hi = _window(rule["end"], end_year, frost)
    placed.append(dict(crop=crop, rule=rule, plant=(p_lo, p_hi), end=(e_lo, e_hi)))
    cursor = e_lo

  # A cover crop ends 2–3 weeks before the next crop goes in.
  for cur, nxt in zip(placed, placed[1:]):
    if cur["rule"]["kind"] == "cover":
      n_lo = nxt["plant"][0]
      cur["end"] = (n_lo - timedelta(days=21), n_lo - timedelta(days=14))

  events = []
  if placed:
    first = placed[0]["plant"][0]
    events.append(dict(
        start=first - timedelta(days=45), end=first - timedelta(days=21),
        crop="Whole field", kind="prep",
        action="Take a soil test (pH, organic matter, N-P-K)",
        tip="Results guide fertilizer rates for the first crop of the plan.",
    ))
  for p in placed:
    crop, rule = p["crop"], p["rule"]
    verbs = ACTION_VERBS.get(crop.lower())
    if rule["kind"] == "cover":
      plant_txt, end_txt, end_kind = f"Seed {crop} as a cover crop", f"End the {crop} cover", "terminate"
    elif verbs:
      plant_txt, end_txt, end_kind = verbs[0], verbs[1], "harvest"
    else:
      plant_txt, end_txt, end_kind = f"Plant {crop}", f"Harvest {crop}", "harvest"
    events.append(dict(start=p["plant"][0], end=p["plant"][1], crop=crop,
                       kind="plant", action=plant_txt, tip=rule["tip"]))
    end_tip = ("Roll, crimp or spray; ending it too late uses moisture the next crop needs."
               if end_kind == "terminate" else "Leave residue on the surface after harvest.")
    events.append(dict(start=p["end"][0], end=p["end"][1], crop=crop,
                       kind=end_kind, action=end_txt, tip=end_tip))
  return sorted(events, key=lambda e: e["start"])


def fmt_range(a: date, b: date) -> str:
  if a == b:
    return a.strftime("%b %d, %Y").replace(" 0", " ")
  if a.year == b.year:
    return f"{a:%b} {a.day} – {b:%b} {b.day}, {b.year}"
  return f"{a:%b} {a.day}, {a.year} – {b:%b} {b.day}, {b.year}"


# ------------------------------------------------------------------------------
# Questions for the local advisor
# ------------------------------------------------------------------------------
CROP_QUESTIONS = {
    "corn": "What nitrogen rate fits this field given the crop before corn?",
    "grain sorghum": "Is there a nearby elevator or feedlot buying grain sorghum, and how does its price compare with corn?",
    "soybeans": "Do I need seed inoculant here, and is soybean cyst nematode present in this area?",
    "winter wheat": "What is this county's Hessian fly-free planting date, and which variety is recommended?",
    "winter rye": "Which way and when should I end the rye cover so it fits my herbicide program and the next crop?",
    "alfalfa": "Is my soil pH above 6.5, and does a 3–5 year alfalfa stand fit my plans?",
    "sunflower": "Is there a local buyer for sunflower, and how high is bird pressure here?",
}
GENERAL_QUESTIONS = [
    "Does my well capacity or irrigation allocation support this plan in a dry year?",
    "Should I soil-test before the first planting, and for what?",
    "Are there cost-share programs here (for example NRCS EQIP) for cover crops or rotation changes?",
]


def advisor_questions(strategy: dict) -> list[str]:
  seen, questions = set(), []
  for crop in strategy.get("crop_sequence", []):
    q = CROP_QUESTIONS.get(crop.lower())
    if q and q not in seen:
      seen.add(q)
      questions.append(q)
  return questions + GENERAL_QUESTIONS


# ------------------------------------------------------------------------------
# Calendar export (.ics, all-day events)
# ------------------------------------------------------------------------------


def _ics_escape(text: str) -> str:
  return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(events: list[dict], plan_name: str, field_label: str) -> bytes:
  stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
  lines = [
      "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TerraRotate//Rotation plan//EN",
      "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_ics_escape('TerraRotate: ' + plan_name)}",
  ]
  for i, e in enumerate(events):
    lines += [
        "BEGIN:VEVENT",
        f"UID:terrarotate-{stamp}-{i}@terrarotate.local",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{e['start']:%Y%m%d}",
        f"DTEND;VALUE=DATE:{e['end'] + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_ics_escape(e['action'])}",
        f"DESCRIPTION:{_ics_escape(e['tip'] + ' Estimated window for ' + field_label + '. Confirm locally.')}",
        "END:VEVENT",
    ]
  lines.append("END:VCALENDAR")
  return ("\r\n".join(lines) + "\r\n").encode("utf-8")


# ------------------------------------------------------------------------------
# PDF report
# ------------------------------------------------------------------------------
_PDF_REPLACE = {
    "→": "->", "➔": "->", "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'",
    "’": "'", "…": "...", "≈": "~", "·": "|", "✓": "v", "≤": "<=", "≥": ">=",
}


def _safe(text) -> str:
  """Core PDF fonts are Latin-1 only; map common typographic characters."""
  s = str(text)
  for a, b in _PDF_REPLACE.items():
    s = s.replace(a, b)
  return s.encode("latin-1", "replace").decode("latin-1")


def build_pdf(*, report: dict, strategy: dict, weights: dict, events: list[dict],
              frost: dict | None, questions: list[str], polygon: list, field_label: str,
              farmer: str, goal_label: str, data_status: dict) -> bytes:
  from fpdf import FPDF  # imported lazily so the app starts even without it

  green = (21, 128, 61)
  ink = (24, 24, 27)
  muted = (113, 113, 122)
  line = (228, 228, 231)

  pdf = FPDF(format="A4")
  pdf.set_auto_page_break(auto=True, margin=16)
  pdf.set_margins(16, 16, 16)
  pdf.add_page()
  w = pdf.epw

  def h(text, size=13, top=6):
    if pdf.get_y() > pdf.h - 50:  # keep headings with their content
      pdf.add_page()
    else:
      pdf.ln(top)
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*ink)
    pdf.multi_cell(w, size * 0.5, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

  def p(text, size=10, color=ink, style=""):
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(w, size * 0.48, _safe(text), new_x="LMARGIN", new_y="NEXT")

  def bullets(items, size=10):
    for it in items:
      pdf.set_font("Helvetica", "", size)
      pdf.set_text_color(*ink)
      pdf.cell(5, size * 0.48, "-")
      pdf.multi_cell(w - 5, size * 0.48, _safe(it), new_x="LMARGIN", new_y="NEXT")

  # Header
  pdf.set_font("Helvetica", "B", 9)
  pdf.set_text_color(*green)
  pdf.cell(w, 5, "TERRAROTATE  |  CROP ROTATION PLAN", new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "B", 20)
  pdf.set_text_color(*ink)
  pdf.cell(w, 10, _safe(f"{farmer}'s field"), new_x="LMARGIN", new_y="NEXT")
  meta = report["metadata"]
  coords = meta.get("coordinates", {})
  p(f"{field_label}  |  about {meta.get('estimated_acres', 0):,.0f} acres  |  "
    f"{coords.get('latitude')}, {coords.get('longitude')}  |  Goal: {goal_label}", 9, muted)
  p(f"Generated {datetime.now():%B %d, %Y}", 9, muted)

  # Field outline (vector), scaled into a box on the right of the plan summary
  top_y = pdf.get_y() + 4
  box = 52
  if polygon and len(polygon) >= 3:
    lats = [pt[0] for pt in polygon]
    lons = [pt[1] for pt in polygon]
    mid_lat = sum(lats) / len(lats)
    kx = math.cos(math.radians(mid_lat))
    xs = [lo * kx for lo in lons]
    span = max(max(xs) - min(xs), max(lats) - min(lats)) or 1e-6
    ox, oy = pdf.l_margin + w - box, top_y
    pts = [(ox + 4 + (x - min(xs)) / span * (box - 8),
            oy + 4 + (max(lats) - la) / span * (box - 8)) for x, la in zip(xs, lats)]
    pdf.set_draw_color(*line)
    pdf.rect(ox, oy, box, box)
    pdf.set_draw_color(*green)
    pdf.set_fill_color(220, 252, 231)
    pdf.set_line_width(0.6)
    pdf.polygon(pts, style="DF")
    pdf.set_line_width(0.2)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_xy(ox, oy + box + 1)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*muted)
    pdf.cell(box, 4, "Field outline (north up)", align="C")

  # Chosen plan
  pdf.set_xy(pdf.l_margin, top_y)
  narrow = w - box - 6
  pdf.set_font("Helvetica", "B", 9)
  pdf.set_text_color(*green)
  pdf.multi_cell(narrow, 5, "CHOSEN PLAN", new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "B", 15)
  pdf.set_text_color(*ink)
  pdf.multi_cell(narrow, 7, _safe(strategy["name"]), new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "", 11)
  pdf.multi_cell(narrow, 6, _safe(" -> ".join(strategy["crop_sequence"])), new_x="LMARGIN", new_y="NEXT")
  sc = strategy["scores"]
  pdf.set_font("Helvetica", "B", 22)
  pdf.cell(narrow, 11, f"{sc['overall_suitability']:.1f} / 100", new_x="LMARGIN", new_y="NEXT")
  labels = {"water_efficiency": "Water use", "soil_health_protection": "Soil protection"}
  wtxt = ", ".join(f"{labels[k]} {v:.0%}" for k, v in sorted(weights.items(), key=lambda kv: -kv[1]) if k in labels)
  pdf.set_font("Helvetica", "", 9)
  pdf.set_text_color(*muted)
  pdf.multi_cell(narrow, 4.5, _safe(f"Score weighted for your goal: {wtxt}."), new_x="LMARGIN", new_y="NEXT")
  pdf.set_y(max(pdf.get_y(), top_y + box + 6))

  h("Why this plan", 12)
  bullets([strategy["rationale"], *strategy.get("advantages", [])])
  h("Watch out for", 12, 3)
  bullets(strategy.get("disadvantages", []))

  # Comparison table
  h("All plans compared", 12)
  with pdf.table(col_widths=(55, 15, 15, 15), text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT"),
                 line_height=5.5, borders_layout="HORIZONTAL_LINES") as table:
    pdf.set_font("Helvetica", "B", 9)
    row = table.row()
    for c in ("Plan", "Water", "Soil", "Overall"):
      row.cell(c)
    pdf.set_font("Helvetica", "", 9)
    for s in report["rotation_strategies"]:
      row = table.row()
      mark = "  (chosen)" if s["strategy_id"] == strategy["strategy_id"] else ""
      row.cell(_safe(s["name"] + mark))
      row.cell(f"{s['scores']['water_efficiency']:.0f}")
      row.cell(f"{s['scores']['soil_health_protection']:.0f}")
      row.cell(f"{s['scores']['overall_suitability']:.1f}")

  # Action calendar
  h("Season calendar", 12)
  if events and frost:
    p(f"Windows are estimated from this field's median frost dates "
      f"(last spring frost ~{_doy(2025, frost['last_spring_doy']):%b %d}, first fall frost "
      f"~{_doy(2025, frost['first_fall_doy']):%b %d}; NASA POWER, {frost['years']} years). "
      "Confirm dates with your local extension office.", 9, muted)
    pdf.ln(2)
    with pdf.table(col_widths=(34, 46, 70), line_height=5, borders_layout="HORIZONTAL_LINES") as table:
      pdf.set_font("Helvetica", "B", 9)
      row = table.row()
      for c in ("When", "Action", "Note"):
        row.cell(c)
      pdf.set_font("Helvetica", "", 8.5)
      for e in events:
        row = table.row()
        row.cell(_safe(fmt_range(e["start"], e["end"])))
        row.cell(_safe(e["action"]))
        row.cell(_safe(e["tip"]))
  else:
    p("Dates could not be estimated because live NASA POWER climate data was not available.", 10, muted)

  # Field facts
  clim = report["observed_climate_nasa"]
  soil = report["soil_profile_usda_ssurgo"]
  h("Field facts", 12)
  facts = [
      ("Rain per year", f"{clim['annual_precipitation_mm']:.0f} mm"),
      ("Very hot days (>35 C)", f"{clim['summer_heat_stress_days_avg']:.0f} per year"),
      ("Drought risk index", f"{clim['calculated_drought_risk_index']} / 100"),
      ("Topsoil texture", soil.get("soil_texture") or "Unknown"),
      ("Organic matter", f"{soil.get('organic_matter')}%" if soil.get("organic_matter") else "Unknown"),
      ("Drainage", soil.get("drainage_class") or "Unknown"),
      ("Water erosion", soil.get("erosion_summary") or "Unknown"),
  ]
  if frost:
    facts.append(("Frost-free days (median)", f"{frost['frost_free_days']}"))
  with pdf.table(col_widths=(50, 100), line_height=5, borders_layout="NONE", first_row_as_headings=False) as table:
    pdf.set_font("Helvetica", "", 9)
    for k, v in facts:
      row = table.row()
      row.cell(_safe(k))
      row.cell(_safe(v))

  h("Questions for your advisor", 12)
  bullets(questions)

  h("Data sources", 12)
  cdl_found = data_status.get("usda_cdl_years_found", 0)
  cdl_total = data_status.get("usda_cdl_years_total", 0)
  bullets([
      f"NASA POWER daily climate 2021-2025: {data_status.get('nasa_power', 'unknown')}",
      f"USDA NASS Cropland Data Layer: {cdl_found} of {cdl_total} years found (or entered by the farmer)",
      f"USDA NRCS SSURGO soil survey: {data_status.get('usda_ssurgo', 'unknown')}",
  ], 9)
  pdf.ln(4)
  p(report["metadata"].get("disclaimer", ""), 8.5, muted, "I")
  return bytes(pdf.output())
