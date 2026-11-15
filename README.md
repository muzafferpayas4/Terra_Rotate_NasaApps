# 🌱 TerraRotate: Crop Rotation Advisor

**🔗 Live demo:** [terrarotatenasaapps-1.streamlit.app](https://terrarotatenasaapps-1.streamlit.app/)

TerraRotate helps a farmer decide **what to plant next**. Outline your field on a map, and the app pulls **NASA** and **USDA** data for that exact spot, then ranks crop rotation plans against your goals.

## What it does

1. **Tell us about your farm:** pick a goal (profit, save water, build soil carbon, stop erosion, grow feed, improve quality, cut input costs), water availability, equipment, and optionally your 2021–2025 crop history.
2. **Outline your field:** draw the field on an interactive map. Acreage is calculated automatically, and the app checks that the land is farmable.
3. **Get your plan:**
   - **Summary:** best plan, plus a what-if weather test (yearly rain −40% to +40%, warming up to +4 °C)
   - **Compare plans:** three rotation strategies scored on water efficiency and soil health
   - **Yield & Profit:** per-hectare yield, seed, price and cost estimates
   - **Next steps:** season calendar based on your field's frost dates, questions for your advisor, and downloads (PDF report, `.ics` calendar, JSON data)
   - **Field data:** climate, soil and crop history for your field
   - **Crop guide:** searchable notes for 20 crops

## Run locally

```bash
git clone https://github.com/muzafferpayas4/Terra_Rotate_NasaApps.git
cd Terra_Rotate_NasaApps
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py              # Streamlit UI (3-step flow, tabs, map, exports)
nasa.py             # NASA/USDA data fetching and scoring engine
action_plan.py      # Frost-based calendar, advisor questions, PDF and .ics export
catalog.py          # Locations, goals, crop catalog, equipment, economics
page_transition.py  # Tractor loading-bar transition
requirements.txt
```

## Disclaimer

TerraRotate is a decision-support tool. Results are estimates from NASA and USDA data; confirm plans with a local agronomist or county extension office.
