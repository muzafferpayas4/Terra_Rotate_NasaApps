[README.md](https://github.com/user-attachments/files/34884810/README.md)
# 🌱 TerraRotate: Crop Rotation Advisor

**TerraRotate** is a decision-support web app that tells a farmer *what to plant next* on a specific field. You outline your field on a map, and the app pulls **NASA** and **USDA** Earth data for that exact spot, then ranks crop rotation plans against your own goals (profit, water saving, soil health, and more).

Built with Python and [Streamlit](https://streamlit.io/).

> ⚠️ **Decision-support only.** All results are estimates built from satellite, model and survey data. Confirm planting dates, varieties and inputs with a local agronomist or county extension office before committing.

---

## ✨ Features

- **3-step guided flow**
  1. **Tell us about your farm:** name, primary goal, water availability, equipment, livestock feed need, location (pick a US state/city or use browser geolocation), and optionally the crops you grew in 2021–2025.
  2. **Outline your field:** draw the field polygon on an interactive map. Area (acres) and center point are computed automatically.
  3. **Get your plan:** results in six tabs (below).
- **Field checks:** samples satellite land cover inside your polygon and warns if the land is water, developed, or not typical cropland.
- **Crop history:** uses your entered history, or falls back to the USDA satellite crop record (2021–2025).
- **Rotation logic:** detects monoculture and repeated legume/cereal/broadleaf cycles and recommends a rotation that breaks pest, disease and nitrogen-depletion cycles.
- **Goal-weighted scoring:** each plan gets *Water Efficiency* and *Soil Health Protection* scores. Weights change with your goal and water availability. A 500-run Monte Carlo test shows how stable the ranking is.
- **What-if weather:** sliders for yearly rain (±40%) and warming (up to +4 °C) re-score the plans for a drier or hotter future.
- **Dated action plan:** planting and harvest windows are placed relative to the field's own median last-spring and first-fall frost dates (from NASA POWER).
- **Exports:** PDF report, calendar file (`.ics`), and raw JSON data.
- **Crop guide:** searchable notes for 20 crops (needs, risks, equipment, when to avoid) with extension/SARE source links.
- **Transition animation:** a tractor loading bar appears when a page takes longer than 1 second to load.

### Result tabs

| Tab | What it shows |
|---|---|
| **Summary** | Best plan, headline advice, what-if weather panel |
| **Compare plans** | Side-by-side strategies with scores, pros/cons, evidence and ranking confidence |
| **Yield & Profit** | Per-hectare yield, seed, price and cost estimates with adjustable plantable area and price |
| **Next steps** | Dated season calendar, questions to ask your advisor, PDF/ICS/JSON downloads |
| **Field data** | Climate, soil and crop history facts for your field |
| **Crop guide** | Searchable crop catalog |

---

## 🛰️ Data Sources

| Source | Used for |
|---|---|
| **[NASA POWER](https://power.larc.nasa.gov/)** (daily, AG community) | Temperature, precipitation, solar radiation, root-zone soil moisture, humidity, wind, evapotranspiration, frost dates, heat-stress days, drought index |
| **[USDA NASS Cropland Data Layer (CDL)](https://nassgeodata.gmu.edu/)** | Satellite crop history 2021–2025, farmability check |
| **[USDA NRCS SSURGO](https://sdmdataaccess.sc.egov.usda.gov/)** (Soil Data Access) | Soil texture, organic matter, drainage, erodibility (K factor, wind group), slope, hydrologic group, available water capacity |
| **USDA ARS LTAR / USDA PLANTS / extension & SARE** | Rotation rules and crop traits used in the scoring tables |

> **Coverage:** CDL and SSURGO are **United States** datasets, so field analysis currently works for locations inside the US. If a live service does not answer, the app tells you what data is missing instead of guessing (NASA POWER has a synthetic fallback and is marked as `unavailable` in the data status).

---

## 🗂️ Project Structure

```
.
├── app.py              # Streamlit UI: 3-step flow, tabs, map, charts, exports
├── nasa.py             # Data fetching (NASA POWER, USDA CDL, SSURGO) + scoring engine
├── action_plan.py      # Frost-based planting calendar, advisor questions, .ics and PDF export
├── catalog.py          # Static data: US locations, goals, 20-crop catalog, equipment, economics
├── page_transition.py  # Tractor loading-bar page transition
└── requirements.txt
```

---

## 🚀 Getting Started

**Requirements:** Python 3.10+ and an internet connection (live NASA/USDA requests).

```bash
# 1. Clone
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. (Recommended) virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 🧭 How It Works

1. The field polygon gives a center point, acreage and sample points.
2. In parallel, the app queries NASA POWER (5 years of daily climate), USDA CDL (crop history), and USDA SSURGO (topsoil profile).
3. Climate stress metrics are computed: annual rain, very hot days (>35 °C), root-zone moisture, water balance, and a drought risk index.
4. Past crops are analyzed for rotation risk (consecutive legumes, cereals or broadleaf crops).
5. Three strategies are built and scored: **Current Pattern**, **Yield-Guard / Water-Smart Rotation** (adapts to what you just grew), and **Soil Armor, Carbon & Forage Shield**.
6. Scores are weighted by your goal, ranked, stress-tested, and turned into a dated calendar and downloadable report.

---

## ⚠️ Limitations

- US-only field analysis (USDA datasets).
- Crop water, cover and organic matter values are simplified reference estimates, and planting offsets are general rules of thumb.
- Economics use benchmark averages, not local prices.
- Public APIs can be slow or temporarily unavailable.

---

## 📄 License

Add your license here (e.g. MIT).

## 🙏 Acknowledgements

NASA POWER Project · USDA NASS · USDA NRCS · USDA ARS · Streamlit · Folium · Plotly
