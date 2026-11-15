from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import math
import threading
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from pyproj import Transformer
import requests
import streamlit as st

try:  # lets worker threads use st.cache_data without "missing ScriptRunContext"
  from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except Exception:  # pragma: no cover - older/newer Streamlit layouts
  add_script_run_ctx = get_script_run_ctx = None

CDL_CROP_CODES = {
    1: "Corn",
    2: "Cotton",
    4: "Grain Sorghum",
    5: "Soybeans",
    6: "Sunflower",
    21: "Barley",
    23: "Spring Wheat",
    24: "Winter Wheat",
    27: "Winter Rye",
    28: "Oats",
    36: "Alfalfa",
    43: "Canola",
    53: "Peas",
    54: "Dry Beans",
    61: "Fallow / Idle Cropland",
    176: "Grassland / Pasture",
}


def compute_polygon_center_and_acres(
    points: list[tuple[float, float]]
) -> tuple[float, float, float]:
  if not points:
    return 38.0450, -100.7850, 0.0
  avg_lat = sum(p[0] for p in points) / len(points)
  avg_lon = sum(p[1] for p in points) / len(points)

  if len(points) < 3:
    return round(avg_lat, 4), round(avg_lon, 4), 160.0

  lat_m = 111320.0
  lon_m = 111320.0 * math.cos(math.radians(avg_lat))
  area_sq_m = 0.0
  n = len(points)
  for i in range(n):
    j = (i + 1) % n
    x1, y1 = points[i][1] * lon_m, points[i][0] * lat_m
    x2, y2 = points[j][1] * lon_m, points[j][0] * lat_m
    area_sq_m += x1 * y2 - x2 * y1
  acres = abs(area_sq_m) * 0.5 / 4046.86
  return round(avg_lat, 4), round(avg_lon, 4), round(max(1.0, acres), 1)


@st.cache_data(show_spinner=False)
def fetch_nasa_power_data(
    lat: float, lon: float, start_year: int = 2021, end_year: int = 2025
) -> tuple[pd.DataFrame, str]:
  """Returns (daily climate frame, source) where source is "live" or "unavailable"."""
  url = "https://power.larc.nasa.gov/api/temporal/daily/point"
  params = {
      "parameters": (
          "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,GWETROOT"
      ),
      "community": "AG",
      "longitude": lon,
      "latitude": lat,
      "start": f"{start_year}0101",
      "end": f"{end_year}1231",
      "format": "JSON",
  }
  try:
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999.0, pd.NA).dropna()
    if not df.empty:
      return df, "live"
  except Exception:
    pass

  date_rng = pd.date_range(
      start=f"{start_year}-01-01", end=f"{end_year}-12-31", freq="D"
  )
  np.random.seed(42)
  fallback_df = pd.DataFrame(
      {
          "T2M": np.random.normal(15, 10, len(date_rng)),
          "T2M_MAX": np.random.normal(25, 8, len(date_rng)),
          "T2M_MIN": np.random.normal(8, 9, len(date_rng)),
          "PRECTOTCORR": np.random.exponential(1.8, len(date_rng)),
          "ALLSKY_SFC_SW_DWN": np.random.uniform(10, 25, len(date_rng)),
          "GWETROOT": np.random.uniform(0.3, 0.7, len(date_rng)),
      },
      index=date_rng,
  )
  return fallback_df, "unavailable"


@st.cache_data(show_spinner=False)
def fetch_nasa_power_extras(
    lat: float, lon: float, start_year: int = 2021, end_year: int = 2025
) -> pd.DataFrame:
  """Extra NASA POWER parameters, one request each so a bad name cannot break the rest."""
  url = "https://power.larc.nasa.gov/api/temporal/daily/point"

  def one(param: str):
    try:
      resp = requests.get(
          url,
          params={
              "parameters": param, "community": "AG",
              "longitude": lon, "latitude": lat,
              "start": f"{start_year}0101", "end": f"{end_year}1231",
              "format": "JSON",
          },
          timeout=15,
      )
      resp.raise_for_status()
      series = resp.json()["properties"]["parameter"][param]
      s = pd.Series(series, dtype="float64")
      s.index = pd.to_datetime(s.index, format="%Y%m%d")
      s = s.where(s > -990.0)
      return param, (s if s.notna().any() else None)
    except Exception:
      return param, None

  params = ("RH2M", "WS2M", "EVPTRNS", "GWETPROF")
  with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(one, params))
  cols = {name: s for name, s in results if s is not None}
  return pd.DataFrame(cols) if cols else pd.DataFrame()


def _drought_index(precip: float, heat_days: float) -> int:
  return min(100, max(0, int((650 - precip) * 0.2 + heat_days * 1.5)))


ET_PER_DEGREE = 0.03


def apply_scenario(metrics: dict, climate_df: pd.DataFrame, rain_pct: float = 0.0,
                   temp_c: float = 0.0) -> dict:
  out = dict(metrics)
  out["annual_precipitation_mm"] = round(metrics["annual_precipitation_mm"] * (1 + rain_pct / 100.0), 1)
  if temp_c:
    summer = climate_df[climate_df.index.month.isin([6, 7, 8])]
    years = max(1, climate_df.index.year.nunique())
    hot = ((summer["T2M_MAX"].astype(float) + temp_c) > 35.0).sum() / years
    out["summer_heat_stress_days_avg"] = round(float(hot), 1)
  if "annual_et_mm" in out:
    out["annual_et_mm"] = round(out["annual_et_mm"] * (1 + ET_PER_DEGREE * temp_c), 1)
    out["water_balance_mm"] = round(out["annual_precipitation_mm"] - out["annual_et_mm"], 1)
  return out


def analyze_climate_stress(df: pd.DataFrame) -> dict:
  annual_precip = df["PRECTOTCORR"].resample("YE").sum().mean()
  summer_df = df[df.index.month.isin([6, 7, 8])]
  heat_stress_days = (
      summer_df["T2M_MAX"] > 35.0
  ).sum() / max(1, df.index.year.nunique())
  avg_root_moisture = df["GWETROOT"].mean()
  metrics = {
      "annual_precipitation_mm": round(float(annual_precip), 1),
      "summer_heat_stress_days_avg": round(float(heat_stress_days), 1),
      "avg_root_zone_soil_moisture": round(float(avg_root_moisture), 3),
  }

  if "RH2M" in df.columns and df["RH2M"].notna().any():
    metrics["avg_relative_humidity_pct"] = round(float(df["RH2M"].mean()), 1)
  if "WS2M" in df.columns and df["WS2M"].notna().any():
    metrics["avg_wind_speed_ms"] = round(float(df["WS2M"].mean()), 2)
  if "GWETPROF" in df.columns and df["GWETPROF"].notna().any():
    metrics["avg_profile_soil_moisture"] = round(float(df["GWETPROF"].mean()), 3)
  if "EVPTRNS" in df.columns and df["EVPTRNS"].notna().any():
    et_mm = float((df["EVPTRNS"] / 2.45).resample("YE").sum().mean())
    if 100.0 <= et_mm <= 2500.0:
      metrics["annual_et_mm"] = round(et_mm, 1)
      metrics["water_balance_mm"] = round(
          metrics["annual_precipitation_mm"] - et_mm, 1
      )
  return metrics


_CDL_URL = "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLValue"


def _to_albers(points: list) -> list:
  transformer = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
  return [transformer.transform(lon, lat) for lat, lon in points]


def _cdl_value_xy(x: float, y: float, year: int, attempts: int = 2):
  for _ in range(attempts):
    try:
      resp = requests.get(
          _CDL_URL,
          params={"year": year, "x": round(x, 2), "y": round(y, 2)},
          timeout=8,
      )
      resp.raise_for_status()
      root = ET.fromstring(resp.text)
      for elem in root.iter():
        if elem.tag.endswith("Result") and elem.text:
          for part in elem.text.replace("{", "").replace("}", "").split(","):
            if "value:" in part:
              return int(part.split(":")[1].strip())
      return None
    except Exception:
      continue
  return None


@st.cache_data(show_spinner=False)
def fetch_usda_cdl_history(
    lat: float,
    lon: float,
    years: tuple = (2021, 2022, 2023, 2024, 2025),
    user_overrides: dict = None,
) -> dict:
  """Crop per year: prioritizes farmer-entered past crops, falls back to USDA NASS CDL satellite records."""
  user_overrides = user_overrides or {}
  (x, y), = _to_albers([(lat, lon)])
  todo = [yr for yr in years if not user_overrides.get(str(yr))]
  codes = {}
  if todo:
    with ThreadPoolExecutor(max_workers=len(todo)) as pool:
      for yr, code in zip(todo, pool.map(lambda yr: _cdl_value_xy(x, y, yr), todo)):
        codes[yr] = code

  crop_history = {}
  for year in years:
    y_str = str(year)
    if user_overrides.get(y_str):
      crop_history[y_str] = {
          "cdl_code": 999,
          "crop_name": user_overrides[y_str],
          "source": "Farmer entry",
      }
      continue
    code = codes.get(year)
    if code is not None and code in CDL_CROP_CODES:
      crop_history[y_str] = {
          "cdl_code": code,
          "crop_name": CDL_CROP_CODES[code],
          "source": "USDA NASS CDL",
      }
    else:
      crop_history[y_str] = {
          "cdl_code": None,
          "crop_name": "Not Found",
          "raw_cdl_code": code,
          "source": "Unavailable",
      }
  return crop_history


NON_FARMABLE_CDL = {
    111: "open water", 123: "developed land", 124: "developed land",
}
SOFT_WARN_CDL = {
    121: "open green space (lawn, park or golf course)",
    122: "land with scattered buildings",
    131: "barren land",
    141: "trees", 142: "trees", 143: "trees",
    190: "wetland", 195: "wetland",
}


def _point_in_polygon(lat: float, lon: float, pts) -> bool:
  inside = False
  n = len(pts)
  j = n - 1
  for i in range(n):
    yi, xi = pts[i]
    yj, xj = pts[j]
    if (xi > lon) != (xj > lon) and lat < (yj - yi) * (lon - xi) / (xj - xi + 1e-12) + yi:
      inside = not inside
    j = i
  return inside


def _sample_points(pts, target: int = 12) -> list:
  lats = [p[0] for p in pts]
  lons = [p[1] for p in pts]
  found = []
  for steps in (5, 8, 12):
    found = []
    for a in range(steps):
      for b in range(steps):
        lat = min(lats) + (max(lats) - min(lats)) * (a + 0.5) / steps
        lon = min(lons) + (max(lons) - min(lons)) * (b + 0.5) / steps
        if _point_in_polygon(lat, lon, pts):
          found.append((lat, lon))
    if len(found) >= target:
      break
  if len(found) > target:
    stride = len(found) / target
    found = [found[int(i * stride)] for i in range(target)]
  if not found:
    found = [(sum(lats) / len(lats), sum(lons) / len(lons))]
  return found


@st.cache_data(show_spinner=False)
def check_field_is_farmable(points: tuple, year: int = 2024) -> dict:
  pts = list(points)
  samples = _sample_points(pts)
  coords = _to_albers(samples)
  with ThreadPoolExecutor(max_workers=len(coords)) as pool:
    values = list(pool.map(lambda xy: _cdl_value_xy(xy[0], xy[1], year, attempts=1), coords))
  known = [v for v in values if v is not None]
  if len(known) < max(3, len(samples) // 2):
    return {"farmable": None, "reason": "", "share": 0.0, "note": ""}
  bad = [v for v in known if v in NON_FARMABLE_CDL]
  share = len(bad) / len(known)
  if share >= 0.6:
    kinds = {}
    for v in bad:
      kinds[NON_FARMABLE_CDL[v]] = kinds.get(NON_FARMABLE_CDL[v], 0) + 1
    main = max(kinds, key=kinds.get)
    return {"farmable": False, "reason": main, "share": share, "note": ""}

  soft = {}
  for v in known:
    if v in SOFT_WARN_CDL:
      soft[SOFT_WARN_CDL[v]] = soft.get(SOFT_WARN_CDL[v], 0) + 1
  note = ""
  if soft and sum(soft.values()) / len(known) >= 0.4:
    main = max(soft, key=soft.get)
    note = (
        f"Satellite land cover shows mostly {main} here, not typical cropland. "
        "The plan assumes you really farm this land; crop history may be empty."
    )
  return {"farmable": True, "reason": "", "share": share, "note": note}


def _soil_unavailable(status: str) -> dict:
  return {
      "status": status,
      "soil_unit_name": None,
      "soil_texture": None,
      "organic_matter": None,
      "drainage_class": None,
      "water_erosion_k_factor": None,
      "erosion_summary": "Data Unavailable",
      "hydrologic_soil_group": None,
      "wind_erodibility_group": None,
      "slope_pct": None,
      "available_water_capacity": None,
      "data_note": None,
  }


def _to_float(value):
  try:
    return float(value) if value not in (None, "") else None
  except (TypeError, ValueError):
    return None


_SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"


def _ssurgo_rows(lat: float, lon: float) -> list:
  sql = f"""
    SELECT mu.muname AS soil_name, c.cokey, c.compname, c.comppct_r,
           c.drainagecl, c.hydgrp, c.weg, c.slope_r,
           ch.chkey, ch.hzdept_r, ch.hzdepb_r, ch.kwfact, ch.kffact,
           ch.om_r, ch.awc_r, chtg.texdesc
    FROM mapunit AS mu
    INNER JOIN component AS c ON c.mukey = mu.mukey
    LEFT JOIN chorizon AS ch ON ch.cokey = c.cokey AND ch.hzdept_r < 30
    LEFT JOIN chtexturegrp AS chtg ON chtg.chkey = ch.chkey AND chtg.rvindicator = 'Yes'
    WHERE mu.mukey IN (
        SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({lon} {lat})')
    )
    ORDER BY c.comppct_r DESC, c.cokey, ch.hzdept_r
    """
  last_error = None
  data = None
  for _attempt in range(2):
    try:
      response = requests.post(
          _SDA_URL, json={"query": sql, "format": "JSON+COLUMNNAME"}, timeout=20
      )
      response.raise_for_status()
      data = response.json()
      break
    except Exception as exc:
      last_error = exc
  if data is None:
    raise RuntimeError(f"SSURGO request failed: {last_error}")
  table = data.get("Table") or []
  if len(table) < 2:
    return []
  cols = table[0]
  return [dict(zip(cols, row)) for row in table[1:]]


def _topsoil_mean(horizons: list, key: str, fallback: str = None):
  num = den = 0.0
  for h in horizons:
    v = _to_float(h.get(key))
    if v is None and fallback:
      v = _to_float(h.get(fallback))
    if v is None:
      continue
    top = max(0.0, _to_float(h.get("hzdept_r")) or 0.0)
    bottom = _to_float(h.get("hzdepb_r"))
    bottom = 30.0 if bottom is None else min(30.0, bottom)
    thickness = bottom - top
    if thickness <= 0:
      continue
    num += v * thickness
    den += thickness
  return num / den if den else None


def _summarize_soil(rows: list):
  comps = {}
  for r in rows:
    comps.setdefault(r.get("cokey"), []).append(r)
  first_cokey = rows[0].get("cokey") if rows else None
  for cokey, rs in comps.items():
    seen, horizons = set(), []
    for r in rs:
      chkey = r.get("chkey")
      if chkey is None or chkey in seen:
        continue
      seen.add(chkey)
      horizons.append(r)
    horizons.sort(key=lambda h: _to_float(h.get("hzdept_r")) or 0.0)
    om = _topsoil_mean(horizons, "om_r")
    k_val = _topsoil_mean(horizons, "kwfact", "kffact")
    awc = _topsoil_mean(horizons, "awc_r")
    if om is None and k_val is None and awc is None:
      continue
    head = rs[0]
    note = None
    if cokey != first_cokey:
      top = rows[0]
      note = (
          f"The largest map component ({top.get('compname')}, {top.get('comppct_r')}%) has no "
          f"soil data, so values come from {head.get('compname')} ({head.get('comppct_r')}%)."
      )
    return {
        "soil_name": head.get("soil_name"),
        "component": head.get("compname"),
        "drainage_class": head.get("drainagecl"),
        "hydrologic_group": head.get("hydgrp"),
        "weg": head.get("weg"),
        "slope_pct": _to_float(head.get("slope_r")),
        "om": om, "k": k_val, "awc": awc,
        "texture": next((h.get("texdesc") for h in horizons if h.get("texdesc")), None),
        "note": note,
    }
  return None


@st.cache_data(show_spinner=False)
def _fetch_ssurgo_cached(lat: float, lon: float) -> dict:
  try:
    rows = _ssurgo_rows(lat, lon)
    found = _summarize_soil(rows)
    note = None
    if found is None:
      offsets = [(0.003, 0.0), (-0.003, 0.0), (0.0, 0.003), (0.0, -0.003)]

      def nearby(off):
        try:
          return _summarize_soil(_ssurgo_rows(lat + off[0], lon + off[1]))
        except Exception:
          return None

      with ThreadPoolExecutor(max_workers=len(offsets)) as pool:
        for res in pool.map(nearby, offsets):
          if res:
            found = res
            note = "The soil survey has no data at this exact spot; values are from a map unit about 300 m away."
            break
    if found is None:
      out = _soil_unavailable("no_data")
      out["soil_unit_name"] = rows[0].get("soil_name") if rows else None
      out["data_note"] = (
          "The soil survey has no topsoil data here (the spot may be mapped as urban land, "
          "water or a pit). Move the outline onto open farmland for soil values."
      )
      return out
  except RuntimeError:
    raise
  except Exception as exc:
    raise RuntimeError(f"SSURGO response could not be read: {exc}") from exc

  k_val = round(found["k"], 2) if found["k"] is not None else None
  if k_val is None:
    erosion_level = "Data Unavailable"
  elif k_val >= 0.37:
    erosion_level = f"Elevated Risk (K={k_val})"
  elif k_val >= 0.20:
    erosion_level = f"Moderate Risk (K={k_val})"
  else:
    erosion_level = f"Low Risk (K={k_val})"

  notes = [n for n in (note, found["note"]) if n]
  return {
      "status": "success",
      "soil_unit_name": found["soil_name"],
      "soil_texture": found["texture"],
      "organic_matter": round(found["om"], 2) if found["om"] is not None else None,
      "drainage_class": found["drainage_class"],
      "water_erosion_k_factor": k_val,
      "erosion_summary": erosion_level,
      "hydrologic_soil_group": found["hydrologic_group"],
      "wind_erodibility_group": found["weg"],
      "slope_pct": found["slope_pct"],
      "available_water_capacity": round(found["awc"], 3) if found["awc"] is not None else None,
      "data_note": " ".join(notes) or None,
  }


def fetch_usda_ssurgo_soil(lat: float, lon: float) -> dict:
  try:
    return _fetch_ssurgo_cached(lat, lon)
  except Exception as exc:
    unavailable = _soil_unavailable("error")
    unavailable["error_detail"] = str(exc)[:300]
    return unavailable


# --- Data-driven scoring & USDA PLANTS / ARS LTAR Crop Traits ---------------
# Botanical family & functional group tags allow yield-loss prevention checks
# (breaking disease/pest cycles and balancing soil nitrogen across years).
CROP_PROFILES = {
    "Corn": {"water_mm": 650, "cover": 35, "om": 60, "forage": 55, "family": "grass", "n_demand": "high"},
    "Grain Sorghum": {"water_mm": 480, "cover": 50, "om": 62, "forage": 70, "family": "grass", "n_demand": "medium"},
    "Soybeans": {"water_mm": 520, "cover": 30, "om": 45, "forage": 50, "legume": True, "family": "legume", "n_demand": "low"},
    "Winter Wheat": {"water_mm": 450, "cover": 75, "om": 65, "forage": 70, "family": "grass", "n_demand": "medium"},
    "Spring Wheat": {"water_mm": 420, "cover": 60, "om": 60, "forage": 60, "family": "grass", "n_demand": "medium"},
    "Winter Rye": {"water_mm": 300, "cover": 92, "om": 88, "forage": 94, "cover_crop": True, "family": "grass", "n_demand": "low"},
    "Cover Crop": {"water_mm": 300, "cover": 90, "om": 85, "forage": 85, "cover_crop": True, "family": "cover", "n_demand": "low"},
    "Cotton": {"water_mm": 700, "cover": 30, "om": 40, "forage": 20, "family": "broadleaf", "n_demand": "high"},
    "Sunflower": {"water_mm": 500, "cover": 40, "om": 50, "forage": 40, "family": "broadleaf", "n_demand": "medium"},
    "Barley": {"water_mm": 400, "cover": 65, "om": 58, "forage": 65, "family": "grass", "n_demand": "medium"},
    "Oats": {"water_mm": 400, "cover": 62, "om": 60, "forage": 75, "family": "grass", "n_demand": "low"},
    "Alfalfa": {"water_mm": 800, "cover": 90, "om": 90, "forage": 95, "legume": True, "family": "legume", "n_demand": "low"},
    "Canola": {"water_mm": 450, "cover": 55, "om": 55, "forage": 40, "family": "brassica", "n_demand": "high"},
    "Peas": {"water_mm": 350, "cover": 45, "om": 55, "forage": 55, "legume": True, "family": "legume", "n_demand": "low"},
    "Field Peas": {"water_mm": 350, "cover": 45, "om": 55, "forage": 55, "legume": True, "family": "legume", "n_demand": "low"},
    "Dry Beans": {"water_mm": 400, "cover": 35, "om": 45, "forage": 35, "legume": True, "family": "legume", "n_demand": "low"},
    "Lentils": {"water_mm": 320, "cover": 45, "om": 50, "forage": 40, "legume": True, "family": "legume", "n_demand": "low"},
    "Chickpeas": {"water_mm": 350, "cover": 45, "om": 50, "forage": 35, "legume": True, "family": "legume", "n_demand": "low"},
    "Sugar Beets": {"water_mm": 620, "cover": 40, "om": 45, "forage": 30, "family": "broadleaf", "n_demand": "high"},
    "Potatoes": {"water_mm": 650, "cover": 35, "om": 35, "forage": 10, "family": "solanaceae", "n_demand": "high"},
    "Flaxseed": {"water_mm": 380, "cover": 45, "om": 50, "forage": 25, "family": "broadleaf", "n_demand": "low"},
    "Safflower": {"water_mm": 420, "cover": 45, "om": 55, "forage": 25, "family": "broadleaf", "n_demand": "low"},
    "Millet": {"water_mm": 340, "cover": 50, "om": 52, "forage": 65, "family": "grass", "n_demand": "low"},
    "Fallow / Idle Cropland": {"water_mm": 100, "cover": 15, "om": 15, "forage": 10, "family": "fallow", "n_demand": "low"},
    "Grassland / Pasture": {"water_mm": 450, "cover": 95, "om": 90, "forage": 90, "family": "grass", "n_demand": "low"},
}
DEFAULT_CROP_PROFILE = {"water_mm": 600, "cover": 40, "om": 45, "forage": 40, "family": "other", "n_demand": "medium"}


def crop_profile(name: str) -> dict:
  lowered = (name or "").lower()
  matches = [k for k in CROP_PROFILES if k.lower() in lowered]
  if not matches:
    return DEFAULT_CROP_PROFILE
  return CROP_PROFILES[max(matches, key=len)]


def analyze_past_crop_yield_risk(cdl_history: dict, climate_metrics: dict, soil_profile: dict) -> dict:
  """Evaluates 2021-2025 crop history (farmer inputs + USDA CDL) using USDA ARS LTAR
  & USDA PLANTS rotation rules to prevent next-season yield loss.
  """
  ordered_years = sorted(cdl_history.keys())
  valid_entries = [
      (yr, cdl_history[yr]["crop_name"], cdl_history[yr].get("source", "USDA NASS CDL"))
      for yr in ordered_years
      if cdl_history[yr].get("crop_name") and cdl_history[yr]["crop_name"] != "Not Found"
  ]

  precip = climate_metrics.get("annual_precipitation_mm", 650)
  is_dry = precip < 580

  if not valid_entries:
    rec_seq = ["Grain Sorghum", "Soybeans", "Winter Wheat"] if is_dry else ["Corn", "Soybeans", "Winter Wheat"]
    return {
        "has_history": False,
        "last_crop": None,
        "last_year": None,
        "risk_level": "unknown",
        "headline": "No 2021–2025 crop history found (neither entered nor in USDA CDL)",
        "diagnosis": (
            "Without past crop records, starting with a balanced legume-cereal rotation "
            "protects soil nitrogen and avoids single-crop pest buildup."
        ),
        "recommended_next_crop": rec_seq[0],
        "recommended_sequence": rec_seq,
        "data_sources_used": "USDA NASS CDL (no pixel match), NASA POWER, USDA NRCS SSURGO, USDA ARS LTAR",
    }

  last_year, last_crop, last_src = valid_entries[-1]
  last_prof = crop_profile(last_crop)
  recent_crops = [c for _, c, _ in valid_entries[-3:]]

  # Count consecutive years of the same crop or same botanical family at the end of the timeline
  consec_same_crop = 1
  for _, c, _ in reversed(valid_entries[:-1]):
    if c.lower() == last_crop.lower():
      consec_same_crop += 1
    else:
      break

  consec_same_family = 1
  last_fam = last_prof.get("family", "other")
  for _, c, _ in reversed(valid_entries[:-1]):
    if crop_profile(c).get("family", "other") == last_fam and last_fam != "other":
      consec_same_family += 1
    else:
      break

  user_count = sum(1 for _, _, s in valid_entries if s == "Farmer entry")
  cdl_count = sum(1 for _, _, s in valid_entries if s == "USDA NASS CDL")
  src_summary = []
  if user_count:
    src_summary.append(f"{user_count} yr(s) entered by you")
  if cdl_count:
    src_summary.append(f"{cdl_count} yr(s) from USDA NASS CDL")
  src_text = " + ".join(src_summary)

  # Case 1: Legume (Soybeans, Alfalfa, Dry Beans, Peas, Lentils, Chickpeas) was last crop
  if last_prof.get("legume"):
    if consec_same_crop >= 2 or consec_same_family >= 2:
      next_crop = "Grain Sorghum" if is_dry else "Corn (Maize)"
      rec_seq = (
          ["Grain Sorghum", "Winter Wheat", "Soybeans"]
          if is_dry
          else ["Corn", "Winter Wheat", "Soybeans"]
      )
      return {
          "has_history": True,
          "last_crop": last_crop,
          "last_year": last_year,
          "risk_level": "high",
          "headline": f"High yield-loss risk: {consec_same_family} consecutive years of legumes ({', '.join(recent_crops[-consec_same_family:])})",
          "diagnosis": (
              f"Based on your history ({src_text}), planting {last_crop} again risks severe yield drag "
              "from Soybean Cyst Nematode (SCN), white mold, and root rot pathogens (USDA ARS LTAR). "
              f"Switch immediately to a high-residue cereal ({next_crop}) to capitalize on fixed soil nitrogen."
          ),
          "recommended_next_crop": next_crop,
          "recommended_sequence": rec_seq,
          "data_sources_used": "Farmer History + USDA NASS CDL, USDA ARS LTAR, USDA PLANTS, NASA POWER",
      }
    else:
      next_crop = "Grain Sorghum" if is_dry else "Corn (Maize)"
      rec_seq = (
          ["Grain Sorghum", "Winter Wheat", "Soybeans"]
          if is_dry
          else ["Corn", "Winter Wheat", "Soybeans"]
      )
      return {
          "has_history": True,
          "last_crop": last_crop,
          "last_year": last_year,
          "risk_level": "low",
          "headline": f"Optimal nitrogen window after {last_crop} ({last_year})",
          "diagnosis": (
              f"Your history ({src_text}) shows {last_crop} in {last_year}, which leaves biological nitrogen credit "
              f"in the topsoil (USDA PLANTS). Planting {next_crop} next captures maximum yield while breaking legume disease cycles."
          ),
          "recommended_next_crop": next_crop,
          "recommended_sequence": rec_seq,
          "data_sources_used": "Farmer History + USDA NASS CDL, USDA ARS LTAR, USDA PLANTS, NASA POWER",
      }

  # Case 2: Grass / Cereal (Corn, Wheat, Sorghum, Barley, Oats) was last crop
  if last_fam == "grass":
    legume_pick = "Field Peas" if precip < 460 else "Soybeans"
    follow_cereal = "Winter Wheat" if "corn" in last_crop.lower() else ("Grain Sorghum" if is_dry else "Corn")
    rec_seq = [legume_pick, follow_cereal, "Winter Rye"]
    if consec_same_crop >= 2 or consec_same_family >= 2:
      return {
          "has_history": True,
          "last_crop": last_crop,
          "last_year": last_year,
          "risk_level": "high",
          "headline": f"High yield-loss risk: {consec_same_family} consecutive years of cereals/grasses ({', '.join(recent_crops[-consec_same_family:])})",
          "diagnosis": (
              f"Your history ({src_text}) shows continuous cereal/grass cropping ending with {last_crop} in {last_year}. "
              "USDA ARS LTAR trials show continuous cereals suffer 10–20% yield penalty from corn rootworm, Fusarium head blight, "
              f"and nitrogen depletion. Rotating into a nitrogen-fixing legume ({legume_pick}) next year restores yield potential."
          ),
          "recommended_next_crop": legume_pick,
          "recommended_sequence": rec_seq,
          "data_sources_used": "Farmer History + USDA NASS CDL, USDA ARS LTAR, USDA PLANTS, NASA POWER",
      }
    else:
      return {
          "has_history": True,
          "last_crop": last_crop,
          "last_year": last_year,
          "risk_level": "moderate",
          "headline": f"Rotate to a broadleaf/legume after {last_crop} ({last_year}) to protect yield",
          "diagnosis": (
              f"Your history ({src_text}) shows {last_crop} in {last_year}. Following a heavy nitrogen-consuming cereal "
              f"with {legume_pick} prevents grass-weed and rootworm buildup while cutting synthetic nitrogen needs."
          ),
          "recommended_next_crop": legume_pick,
          "recommended_sequence": rec_seq,
          "data_sources_used": "Farmer History + USDA NASS CDL, USDA ARS LTAR, USDA PLANTS, NASA POWER",
      }

  # Case 3: Broadleaf / Brassica / Other (Cotton, Sunflower, Canola, Sugar Beets, Potatoes, Fallow)
  next_cereal = "Winter Wheat" if is_dry else "Corn"
  legume_pick = "Field Peas" if precip < 460 else "Soybeans"
  rec_seq = [next_cereal, legume_pick, "Winter Rye"]
  return {
      "has_history": True,
      "last_crop": last_crop,
      "last_year": last_year,
      "risk_level": "high" if consec_same_crop >= 2 else "moderate",
      "headline": (
          f"Break broadleaf/specialty cycle after {last_crop} ({last_year})"
          + (f" ({consec_same_crop} yrs in a row)" if consec_same_crop >= 2 else "")
      ),
      "diagnosis": (
          f"Your history ({src_text}) ends with {last_crop} in {last_year}. Broadleaf and root crops leave low surface residue "
          f"and risk Sclerotinia/Verticillium buildup if repeated. Rotating to a fibrous-rooted cereal ({next_cereal}) "
          "rebuilds topsoil structure and prevents yield decline."
      ),
      "recommended_next_crop": next_cereal,
      "recommended_sequence": rec_seq,
      "data_sources_used": "Farmer History + USDA NASS CDL, USDA ARS LTAR, USDA PLANTS, NASA POWER",
  }


def _clamp(x: float, lo: float, hi: float) -> float:
  return max(lo, min(hi, x))


def _mean(values) -> float:
  values = list(values)
  return sum(values) / len(values) if values else 0.0


def water_efficiency_detail(seq: list, climate: dict, soil: dict) -> dict:
  profiles = [crop_profile(c) for c in seq] or [DEFAULT_CROP_PROFILE]
  cash = [p for p in profiles if not p.get("cover_crop")] or profiles
  demand = _mean(p["water_mm"] for p in cash)
  supply = climate["annual_precipitation_mm"]
  ratio = supply / demand
  base = 100.0 * min(1.0, ratio)
  heat_pen = min(15.0, climate.get("summer_heat_stress_days_avg", 0.0) * 0.25)
  cover_pen = 5.0 if any(p.get("cover_crop") for p in profiles) else 0.0
  awc = (soil or {}).get("available_water_capacity")
  awc_adj = _clamp((awc - 0.15) * 80.0, -8.0, 8.0) if awc else 0.0
  score = int(round(_clamp(base - heat_pen - cover_pen + awc_adj, 15.0, 97.0)))
  return {
      "score": score, "supply_mm": supply, "demand_mm": round(demand),
      "ratio": round(ratio, 2), "base": round(base),
      "heat_penalty": round(heat_pen, 1), "cover_penalty": cover_pen,
      "awc": awc, "awc_adjust": round(awc_adj, 1),
  }


def water_efficiency_score(seq: list, climate: dict, soil: dict) -> int:
  return water_efficiency_detail(seq, climate, soil)["score"]


def _weg_number(value):
  digits = "".join(ch for ch in str(value or "") if ch.isdigit())
  return int(digits[0]) if digits else None


def erosion_exposure_terms(soil: dict) -> list:
  soil = soil or {}
  terms = []
  k = soil.get("water_erosion_k_factor")
  if k is not None:
    terms.append(("Water erosion (K factor)", _clamp((k - 0.10) / 0.35, 0.0, 1.0), f"K={k}"))
  raw_weg = soil.get("wind_erodibility_group")
  weg = _weg_number(raw_weg)
  if weg is not None:
    terms.append(("Wind erosion (group 1 = worst)", _clamp((8 - weg) / 7.0, 0.0, 1.0), f"group {raw_weg}"))
  slope = soil.get("slope_pct")
  if slope is not None:
    terms.append(("Slope", _clamp(slope / 15.0, 0.0, 1.0), f"{slope}%"))
  hyd = str(soil.get("hydrologic_soil_group") or "").upper()
  hyd_risk = {"A": 0.1, "B": 0.3, "C": 0.6, "D": 0.9}
  hyd_vals = [hyd_risk[g] for g in hyd if g in hyd_risk]
  if hyd_vals:
    terms.append(("Runoff (hydrologic group)", max(hyd_vals), f"group {hyd}"))
  return terms


def erosion_exposure(soil: dict) -> float:
  terms = erosion_exposure_terms(soil)
  return _mean(t[1] for t in terms) if terms else 0.5


def explain_plan(seq: list, climate: dict, soil: dict) -> dict:
  profiles = [crop_profile(c) for c in seq] or [DEFAULT_CROP_PROFILE]
  terms = erosion_exposure_terms(soil)
  return {
      "water": water_efficiency_detail(seq, climate, soil),
      "erosion_terms": terms,
      "exposure": round(erosion_exposure(soil), 2),
      "exposure_has_data": bool(terms),
      "cover": round(_mean(p["cover"] for p in profiles)),
      "erosion_score": erosion_control_score(seq, soil),
      "om_score": organic_matter_score(seq),
      "soil_score": soil_protection_score(seq, soil),
      "legume_share": round(legume_share(seq), 2),
      "unrecognized": [c for c in seq if crop_profile(c) is DEFAULT_CROP_PROFILE],
  }


def erosion_control_score(seq: list, soil: dict) -> int:
  profiles = [crop_profile(c) for c in seq] or [DEFAULT_CROP_PROFILE]
  cover = _mean(p["cover"] for p in profiles)
  exposure = 0.5 + 0.5 * erosion_exposure(soil)
  return int(round(_clamp(100.0 - (100.0 - cover) * exposure, 10.0, 98.0)))


def organic_matter_score(seq: list) -> int:
  profiles = [crop_profile(c) for c in seq] or [DEFAULT_CROP_PROFILE]
  return int(round(_mean(p["om"] for p in profiles)))


def soil_protection_score(seq: list, soil: dict) -> int:
  return int(round(
      0.65 * erosion_control_score(seq, soil) + 0.35 * organic_matter_score(seq)
  ))


def legume_share(seq: list) -> float:
  profiles = [crop_profile(c) for c in seq]
  return _mean(1.0 if p.get("legume") else 0.0 for p in profiles)


GOAL_WEIGHTS = [
    (("profit",), (0.55, 0.45)),
    (("water", "drought", "conserve"), (0.75, 0.25)),
    (("organic", "carbon"), (0.25, 0.75)),
    (("erosion",), (0.25, 0.75)),
    (("livestock", "forage", "feed"), (0.45, 0.55)),
    (("quality", "protein"), (0.45, 0.55)),
    (("fertilizer", "input"), (0.40, 0.60)),
]


def goal_weights(farmer_prefs: dict) -> dict:
  goal = farmer_prefs.get("primary_goal", "").lower()
  water, soil = 0.55, 0.45
  for keywords, weights in GOAL_WEIGHTS:
    if any(k in goal for k in keywords):
      water, soil = weights
      break
  if farmer_prefs.get("water_availability") == "Low":
    water += 0.15
  elif farmer_prefs.get("water_availability") == "High":
    water = max(0.10, water - 0.10)
  total = water + soil
  return {
      "water_efficiency": round(water / total, 2),
      "soil_health_protection": round(soil / total, 2),
  }


def ranking_stability(strategies: list, weights: dict, runs: int = 500, seed: int = 7) -> dict:
  rng = np.random.default_rng(seed)
  keys = ("water_efficiency", "soil_health_protection")
  noise = np.array([5.0, 5.0])
  base_w = np.array([weights[k] for k in keys])
  scores = np.array([[s["scores"][k] for k in keys] for s in strategies], dtype=float)
  wins = np.zeros(len(strategies))
  for _ in range(runs):
    w = base_w * rng.uniform(0.7, 1.3, 2)
    w = w / w.sum()
    totals = (scores + rng.normal(0, 1, scores.shape) * noise) @ w
    wins[int(np.argmax(totals))] += 1
  return {s["strategy_id"]: round(float(n) / runs, 2) for s, n in zip(strategies, wins)}


def plan_evidence(strategy: dict, climate: dict, soil: dict, monoculture: bool = False) -> list:
  seq = strategy["crop_sequence"]
  ex = explain_plan(seq, climate, soil)
  w = ex["water"]
  items = [
      {"text": f"Rain is {w['supply_mm']:.0f} mm a year against about {w['demand_mm']} mm of crop water need "
               f"({w['ratio']:.0%} covered).", "source": "NASA POWER + crop water table"},
      {"text": f"{climate.get('summer_heat_stress_days_avg', 0):.0f} very hot days (above 35 C) a year "
               f"cost {w['heat_penalty']} water points.", "source": "NASA POWER"},
  ]
  if ex["exposure_has_data"]:
    parts = ", ".join(f"{label.split(' (')[0].lower()} {raw}" for label, _, raw in ex["erosion_terms"])
    items.append({"text": f"Erosion exposure is {ex['exposure']:.2f} of 1 ({parts}); these crops keep "
                          f"soil covered at {ex['cover']} of 100.", "source": "USDA SSURGO + crop table"})
  else:
    items.append({"text": "No soil survey data here, so erosion exposure is assumed medium.",
                  "source": "Gap: USDA SSURGO"})
  items.append({"text": f"Legumes are {ex['legume_share']:.0%} of the rotation; roots and residue score "
                        f"{ex['om_score']} of 100 for organic matter.", "source": "Crop table (estimates)"})
  if strategy["strategy_id"] == "STRAT_1_BASELINE" and monoculture:
    items.append({"text": "The same crop shows up in every recorded year, which builds pest and disease pressure.",
                  "source": "USDA CDL / Past History"})
  if ex["unrecognized"]:
    items.append({"text": "Not in the crop table, scored as an average row crop: " + ", ".join(ex["unrecognized"]) + ".",
                  "source": "Gap: crop table"})
  return items


def weighted_total(water: float, soil: float, w: dict) -> float:
  return round(
      water * w["water_efficiency"]
      + soil * w["soil_health_protection"],
      1,
  )


def score_five_pillars(
    sequence_text: str,
    precip: float,
    k_factor,
    climate_metrics: dict = None,
    soil_profile: dict = None,
) -> list:
  climate = dict(climate_metrics or {})
  climate.setdefault("annual_precipitation_mm", precip)
  soil = dict(soil_profile or {})
  if soil.get("water_erosion_k_factor") is None:
    soil["water_erosion_k_factor"] = k_factor
  seq = [c.strip() for c in sequence_text.split("➔") if c.strip()]
  profiles = [crop_profile(c) for c in seq] or [DEFAULT_CROP_PROFILE]
  cash = [p for p in profiles if not p.get("cover_crop")] or profiles
  demand = round(_mean(p["water_mm"] for p in cash))
  legumes = legume_share(seq)
  exposure = erosion_exposure(soil)
  return [
      {
          "dimension": "Nutrient Cycling",
          "score": int(round(_clamp(60 + 80 * legumes, 0, 100))),
          "note": f"Legumes are {legumes:.0%} of this rotation and fix nitrogen.",
      },
      {
          "dimension": "Erosion Control",
          "score": erosion_control_score(seq, soil),
          "note": (
              f"Crop cover vs. soil erosion exposure ({exposure:.2f} of 1;"
              f" K={soil.get('water_erosion_k_factor')})."
          ),
      },
      {
          "dimension": "Organic Matter",
          "score": organic_matter_score(seq),
          "note": "Average root and residue contribution of the crops.",
      },
      {
          "dimension": "Water Efficiency",
          "score": water_efficiency_score(seq, climate, soil),
          "note": f"{precip} mm rain vs. about {demand} mm crop water need.",
      },
      {
          "dimension": "Forage Potential",
          "score": int(round(_mean(p["forage"] for p in profiles))),
          "note": "Average grazing, silage and hay potential of the crops.",
      },
  ]


def build_tailored_farmer_advisory(
    farmer_name: str,
    farmer_prefs: dict,
    climate_metrics: dict,
    soil_profile: dict,
) -> dict:
  goal = farmer_prefs["primary_goal"]
  water_avail = farmer_prefs["water_availability"]
  equip_status = farmer_prefs["equipment_status"]
  precip = climate_metrics["annual_precipitation_mm"]
  k_factor = soil_profile.get("water_erosion_k_factor") or 0.25
  texture = soil_profile.get("soil_texture") or "Agricultural Loam"

  if precip >= 600:
    land_compliment = (
        f"Great news, {farmer_name}! Your field receives {precip} mm/year"
        f" rainfall and features {texture} soil, offering strong yield"
        " flexibility."
    )
  else:
    land_compliment = (
        f"High potential, {farmer_name}! Your {texture} soil retains nutrients"
        " well; pairing with resilient dryland crops ensures steady harvests."
    )

  goal_lower = goal.lower()

  if "profit" in goal_lower:
    if equip_status in ["Medium", "High"] and water_avail in ["Medium", "High"]:
      headline = (
          f"Recommended Focus for {farmer_name}: High-Margin Corn & Soybean Cycle"
      )
      bullets = [
          "Your strong equipment status and water access support high-yielding Corn and Soybeans.",
          "Rotating Soybeans can naturally reduce next season's nitrogen fertilizer costs.",
      ]
      top_pick = "Corn ➔ Soybeans"
    else:
      headline = (
          f"Recommended Focus for {farmer_name}: Water-Smart Grain Sorghum & Wheat"
      )
      bullets = [
          "Grain Sorghum uses ~28% less water than corn, protecting your profit margins.",
          "Winter Wheat provides stable revenue utilizing cooler spring moisture.",
      ]
      top_pick = "Grain Sorghum ➔ Winter Wheat ➔ Soybeans"
  elif (
      "water" in goal_lower
      or "drought" in goal_lower
      or "conserve" in goal_lower
  ):
    headline = (
        f"Recommended Focus for {farmer_name}: Moisture-Saving Dryland Rotation"
    )
    bullets = [
        "Shifting to Grain Sorghum reduces summer irrigation stress by up to 28%.",
        "Retaining crop residue on the surface preserves essential soil moisture.",
    ]
    top_pick = "Grain Sorghum ➔ Winter Wheat ➔ Cover Crop"
  elif "organic" in goal_lower or "carbon" in goal_lower:
    headline = f"Recommended Focus for {farmer_name}: Living Root Soil Shield"
    bullets = [
        "Planting Winter Rye post-harvest protects topsoil and steadily builds organic matter.",
        "Continuous root cover safeguards against wind and water soil erosion.",
    ]
    top_pick = "Corn ➔ Winter Rye (Cover) ➔ Soybeans ➔ Winter Wheat"
  else:
    headline = (
        f"Recommended Focus for {farmer_name}: Nutrient-Balanced Quality Rotation"
    )
    bullets = [
        "Legume-cereal rotation enhances grain protein quality and reduces input bills.",
        "Breaking monoculture cycles naturally suppresses pests and disease pressure.",
    ]
    top_pick = "Soybeans ➔ Winter Wheat ➔ Corn"

  five_pillars = score_five_pillars(
      top_pick, precip, k_factor, climate_metrics, soil_profile
  )

  return {
      "land_compliment": land_compliment,
      "advisory_headline": headline,
      "recommended_primary_sequence": top_pick,
      "plain_language_guidance": bullets,
      "five_pillar_evaluation": five_pillars,
  }


def rank_individual_crops(
    climate_metrics: dict, soil_profile: dict, farmer_prefs: dict
) -> list:
  def suitability(crop_name: str) -> int:
    water = water_efficiency_score([crop_name], climate_metrics, soil_profile)
    soil = soil_protection_score([crop_name], soil_profile)
    return int(round(0.5 * water + 0.5 * soil))

  crops = [
      {
          "crop": "Grain Sorghum",
          "suitability_score": suitability("Grain Sorghum"),
          "role": "Drought-Smart Grain",
          "reason": "Reduces irrigation needs by ~28% while matching standard headers.",
      },
      {
          "crop": "Winter Rye",
          "suitability_score": suitability("Winter Rye"),
          "role": "Soil Shield & Grazing",
          "reason": "Protects winter topsoil and supplies early spring livestock feed.",
      },
      {
          "crop": "Soybeans",
          "suitability_score": suitability("Soybeans"),
          "role": "Natural Nitrogen Fixer",
          "reason": "Enriches soil nitrogen and breaks multi-year pest cycles.",
      },
      {
          "crop": "Winter Wheat",
          "suitability_score": suitability("Winter Wheat"),
          "role": "Cool-Season Cash Crop",
          "reason": "Efficiently utilizes spring moisture prior to peak summer heat.",
      },
      {
          "crop": "Corn (Maize)",
          "suitability_score": suitability("Corn"),
          "role": "High-Yield Revenue Driver",
          "reason": "Strong moisture-dependent yield potential where water availability is Medium to High.",
      },
  ]
  return sorted(crops, key=lambda x: x["suitability_score"], reverse=True)


def evaluate_rotation_strategies(
    farmer_name: str,
    lat: float,
    lon: float,
    acres: float,
    region_name: str,
    climate_metrics: dict,
    cdl_history: dict,
    soil_profile: dict,
    farmer_prefs: dict,
) -> dict:
  precip = climate_metrics["annual_precipitation_mm"]
  heat_days = climate_metrics["summer_heat_stress_days_avg"]
  soil_moisture = climate_metrics["avg_root_zone_soil_moisture"]

  observed_crops = [
      v["crop_name"]
      for v in cdl_history.values()
      if v.get("crop_name") and v.get("crop_name") != "Not Found"
  ]
  unique_crops_count = len(set(observed_crops))
  is_monoculture = len(observed_crops) >= 2 and unique_crops_count == 1
  monoculture_penalty = 15 if is_monoculture else 0

  # Analyze 2021-2025 history (farmer entries + USDA CDL) to prevent yield loss
  yield_risk_info = analyze_past_crop_yield_risk(cdl_history, climate_metrics, soil_profile)

  k_factor = soil_profile.get("water_erosion_k_factor")
  drought_risk = _drought_index(precip, heat_days)
  moisture_deficit = soil_moisture < 0.45

  baseline_sequence = (
      observed_crops if observed_crops else ["Corn", "Soybeans", "Winter Wheat"]
  )
  weights = goal_weights(farmer_prefs)

  # History-tailored yield-protection rotation (Strategy 2 adapts to what was just planted)
  s2_sequence = yield_risk_info["recommended_sequence"]
  s3_sequence = ["Corn", "Winter Rye", "Soybeans", "Winter Wheat"]

  s1_water = water_efficiency_score(baseline_sequence, climate_metrics, soil_profile)
  s1_soil = max(
      15, soil_protection_score(baseline_sequence, soil_profile) - monoculture_penalty
  )
  s1_total = weighted_total(s1_water, s1_soil, weights)

  s2_water = water_efficiency_score(s2_sequence, climate_metrics, soil_profile)
  s2_soil = soil_protection_score(s2_sequence, soil_profile)
  # Bonus for breaking a high-risk repeat/monoculture sequence to protect yield
  yield_break_bonus = 4.0 if (yield_risk_info["has_history"] and yield_risk_info["risk_level"] in ("high", "moderate")) else 0.0
  s2_total = min(98.0, round(weighted_total(s2_water, s2_soil, weights) + yield_break_bonus, 1))

  s3_water = water_efficiency_score(s3_sequence, climate_metrics, soil_profile)
  s3_soil = soil_protection_score(s3_sequence, soil_profile)
  s3_total = weighted_total(s3_water, s3_soil, weights)

  owned_eq = [e.lower() for e in farmer_prefs.get("owned_equipment", [])]
  has_drill = any("drill" in e or "air seeder" in e for e in owned_eq)
  has_crimper = any("crimper" in e or "termination" in e or "sprayer" in e for e in owned_eq)
  s3_extra_warn = []
  if owned_eq and not has_drill:
    s3_extra_warn.append("Requires renting a grain drill/seeder for Winter Rye and Winter Wheat.")
  if owned_eq and not has_crimper:
    s3_extra_warn.append("Requires renting a roller-crimper or sprayer to terminate Winter Rye on time.")

  if yield_risk_info["has_history"]:
    s2_name = f"Yield-Guard Rotation (Start with {yield_risk_info['recommended_next_crop']})"
    s2_rationale = (
        f"Tailored to your 2021–2025 history ending in {yield_risk_info['last_crop']} ({yield_risk_info['last_year']}): "
        f"planting {yield_risk_info['recommended_next_crop']} next prevents yield drag and balances soil nutrients."
    )
    s2_adv = [
        f"Directly breaks disease, nematode, and nutrient-depletion pressure left by {yield_risk_info['last_crop']}.",
        "Aligns crop sequence with USDA ARS LTAR rotation principles and local NASA climate limits.",
    ]
  else:
    s2_name = "Water-Smart & Yield-Balanced Cycle"
    s2_rationale = "Alternates cereals and nitrogen-fixing legumes to prevent yield loss and cut water stress."
    s2_adv = [
        "Reduces summer irrigation demand while fixing biological nitrogen.",
        "Balances water demand and soil nutrient cycling across seasons.",
    ]

  s1_disadv = [
      "Vulnerable to multi-year pest accumulation and soil nutrient depletion.",
      "Higher irrigation demand during prolonged dry summer spells.",
  ]
  if yield_risk_info["risk_level"] == "high":
    s1_disadv.insert(0, f"High yield-loss risk: repeating {yield_risk_info['last_crop']} builds pathogen and nutrient-drag penalties.")

  strategies = [
      {
          "strategy_id": "STRAT_1_BASELINE",
          "name": "Current Historical Pattern (Past / USDA CDL)",
          "crop_sequence": baseline_sequence,
          "scores": {
              "overall_suitability": s1_total,
              "water_efficiency": s1_water,
              "soil_health_protection": s1_soil,
          },
          "rationale": (
              "Reflects your 2021–2025 entered crops and USDA CDL satellite records."
          ),
          "advantages": [
              "Zero transition friction since it matches established farm routines.",
              "Familiar equipment setup and field management timing.",
          ],
          "disadvantages": s1_disadv,
      },
      {
          "strategy_id": "STRAT_2_WATER_SMART",
          "name": s2_name,
          "crop_sequence": s2_sequence,
          "scores": {
              "overall_suitability": s2_total,
              "water_efficiency": s2_water,
              "soil_health_protection": s2_soil,
          },
          "rationale": s2_rationale,
          "advantages": s2_adv,
          "disadvantages": [
              "Requires verifying local seed availability and planting dates for the next crop.",
              "Slight management adjustment needed across crop transitions.",
          ],
      },
      {
          "strategy_id": "STRAT_3_SOIL_SHIELD",
          "name": "Soil Armor, Carbon & Forage Shield",
          "crop_sequence": s3_sequence,
          "scores": {
              "overall_suitability": s3_total,
              "water_efficiency": s3_water,
              "soil_health_protection": s3_soil,
          },
          "rationale": (
              "Winter roots curb erosion and steadily build organic carbon."
          ),
          "advantages": [
              "Maximum protection against wind and water topsoil erosion.",
              "Builds natural soil organic carbon and provides optional early livestock grazing.",
          ],
          "disadvantages": [
              "Demands precise spring cover crop termination to avoid moisture competition.",
              "Requires additional seeding pass in autumn.",
              *s3_extra_warn,
          ],
      },
  ]

  strategies_sorted = sorted(
      strategies, key=lambda x: x["scores"]["overall_suitability"], reverse=True
  )

  best = strategies_sorted[0]
  best_seq_text = " ➔ ".join(best["crop_sequence"])
  advisory = build_tailored_farmer_advisory(
      farmer_name, farmer_prefs, climate_metrics, soil_profile
  )
  advisory["advisory_headline"] = best["name"]
  advisory["recommended_primary_sequence"] = best_seq_text
  advisory["recommended_strategy_id"] = best["strategy_id"]
  advisory["plain_language_guidance"] = [best["rationale"], *best["advantages"]]
  advisory["five_pillar_evaluation"] = score_five_pillars(
      best_seq_text, precip, k_factor or 0.25,
      climate_metrics, soil_profile,
  )

  return {
      "metadata": {
          "farmer_name": farmer_name,
          "region": region_name,
          "estimated_acres": acres,
          "coordinates": {"latitude": lat, "longitude": lon},
          "disclaimer": (
              "Decision-Support Advisory: All insights derive from NASA and USDA"
              " estimates. Consult a local agronomist before making final"
              " operational commitments."
          ),
          "generated_at": datetime.now(timezone.utc).isoformat(),
      },
      "tailored_farmer_advisory": advisory,
      "yield_risk_analysis": yield_risk_info,
      "scoring_weights": weights,
      "observed_climate_nasa": {
          **climate_metrics,
          "calculated_drought_risk_index": drought_risk,
          "root_moisture_stress_detected": bool(moisture_deficit),
      },
      "historical_crops_usda_cdl": {
          "yearly_crops": cdl_history,
          "unique_crops_detected": unique_crops_count,
          "monoculture_stress_flag": is_monoculture,
      },
      "soil_profile_usda_ssurgo": soil_profile,
      "ranked_candidate_crops": rank_individual_crops(
          climate_metrics, soil_profile, farmer_prefs
      ),
      "rotation_strategies": strategies_sorted,
      "information_gaps_and_local_validation": [
          "Verify local well water pumping limits and equipment compatibility.",
          "Consult local agricultural extension for regional soil testing.",
      ],
  }


def _run_parallel(jobs: dict) -> dict:
  ctx = get_script_run_ctx() if get_script_run_ctx else None

  def wrap(fn, args):
    def inner():
      if ctx is not None and add_script_run_ctx is not None:
        add_script_run_ctx(threading.current_thread(), ctx)
      try:
        return fn(*args)
      except Exception as exc:
        return exc
    return inner

  with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
    futures = {name: pool.submit(wrap(fn, args)) for name, (fn, args) in jobs.items()}
    return {name: fut.result() for name, fut in futures.items()}


def run_full_field_analysis(
    farmer_name: str,
    lat: float,
    lon: float,
    acres: float,
    region_name: str,
    farmer_prefs: dict,
    user_overrides: dict = None,
    scenario: dict = None,
) -> tuple[dict, pd.DataFrame]:
  results = _run_parallel({
      "climate": (fetch_nasa_power_data, (lat, lon)),
      "extras": (fetch_nasa_power_extras, (lat, lon)),
      "cdl": (fetch_usda_cdl_history, (lat, lon, (2021, 2022, 2023, 2024, 2025), user_overrides)),
      "soil": (fetch_usda_ssurgo_soil, (lat, lon)),
  })
  for needed in ("climate", "cdl"):
    if isinstance(results[needed], Exception):
      raise results[needed]
  climate_df, climate_source = results["climate"]
  extra_cols = []
  extras_df = results["extras"]
  if climate_source == "live" and isinstance(extras_df, pd.DataFrame) and not extras_df.empty:
    climate_df = climate_df.join(extras_df, how="left")
    extra_cols = list(extras_df.columns)
  observed = analyze_climate_stress(climate_df)
  scn = scenario or {}
  rain_pct = float(scn.get("rain_pct") or 0.0)
  temp_c = float(scn.get("temp_c") or 0.0)
  scenario_on = bool(rain_pct or temp_c)
  climate_metrics = apply_scenario(observed, climate_df, rain_pct, temp_c) if scenario_on else observed
  cdl_history = results["cdl"]
  soil_profile = results["soil"]
  if isinstance(soil_profile, Exception):
    soil_profile = _soil_unavailable("error")
    soil_profile["error_detail"] = str(results["soil"])[:300]

  report = evaluate_rotation_strategies(
      farmer_name=farmer_name,
      lat=lat,
      lon=lon,
      acres=acres,
      region_name=region_name,
      climate_metrics=climate_metrics,
      cdl_history=cdl_history,
      soil_profile=soil_profile,
      farmer_prefs=farmer_prefs,
  )
  shake_runs = 500
  report["ranking_confidence"] = {
      "runs": shake_runs,
      "first_share": ranking_stability(report["rotation_strategies"], report["scoring_weights"], shake_runs),
  }
  mono = bool(report["historical_crops_usda_cdl"].get("monoculture_stress_flag"))
  for strat in report["rotation_strategies"]:
    strat["evidence"] = plan_evidence(strat, climate_metrics, soil_profile, mono)
  if scenario_on:
    scored = {
        **climate_metrics,
        "calculated_drought_risk_index": report["observed_climate_nasa"]["calculated_drought_risk_index"],
    }
    report["observed_climate_nasa"] = {
        **observed,
        "calculated_drought_risk_index": _drought_index(
            observed["annual_precipitation_mm"], observed["summer_heat_stress_days_avg"]),
        "root_moisture_stress_detected": bool(observed["avg_root_zone_soil_moisture"] < 0.45),
    }
    report["scenario"] = {"rain_pct": rain_pct, "temp_c": temp_c, "climate": scored}
    report["metadata"]["disclaimer"] += (
        f" Plan scores were calculated for a what-if scenario (rain {rain_pct:+.0f}%,"
        f" warming {temp_c:+.1f} C). Field facts show observed values."
    )
  found_years = sum(
      1 for v in cdl_history.values() if v.get("crop_name") != "Not Found"
  )
  report["data_status"] = {
      "nasa_power": climate_source,
      "nasa_power_extra_params": extra_cols,
      "usda_cdl_years_found": found_years,
      "usda_cdl_years_total": len(cdl_history),
      "usda_ssurgo": soil_profile.get("status", "error"),
      "usda_ssurgo_error": soil_profile.get("error_detail"),
  }
  return report, climate_df
