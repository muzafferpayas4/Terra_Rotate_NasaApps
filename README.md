# 🌱 TerraRotate: Crop Rotation Advisor

**🔗 Live demo:** [terrarotatenasaapps-1.streamlit.app](https://terrarotatenasaapps-1.streamlit.app/)

TerraRotate is a decision-support app that helps a farmer decide **what to plant next season**. You outline your field on a map; the app automatically pulls **NASA** and **USDA** data for that exact spot and ranks crop rotation plans based on your goal, water situation and machinery. For every plan it also estimates **how much seed you need, how much you can harvest and how much profit you could make**.

## Why TerraRotate?

Planting the same crop year after year builds up pests and disease and drains soil nitrogen. A good rotation breaks that cycle, but the answer to "which crop, in what order?" depends on the field's climate, soil, history and the farmer's resources. TerraRotate produces that answer for your specific field using satellite and soil data.

## How it works

### 1. Tell us about your farm
- **Pick your goal:** maximize profit, save water, build soil carbon, stop erosion, grow livestock feed, improve crop quality, or cut input costs.
- **Choose your machinery:** mark the equipment you own or can easily rent (row-crop planter, grain drill, combine harvester, roller-crimper / cover-crop termination rig, swather and hay baler, broadcast spreader and sprayer). Plans adapt to this: for example, if you have no grain drill, a plan with winter rye and winter wheat tells you to rent one.
- **Choose your location:** from the US state and city list, or from your browser location.
- Optionally enter your **2021–2025 crop history**; any year you skip is filled from satellite records.

### 2. Outline your field
Draw the field boundary on an interactive map. The area (acres) is calculated automatically, and satellite land cover is used to check that the land is farmable (it warns you about water, developed land and similar).

### 3. Get your plan
Results are organized into six tabs:

| Tab | What it shows |
|---|---|
| **Summary** | The recommended plan and why, plan score, and a quick snapshot of your field (details below) |
| **Compare plans** | Three rotation strategies with water efficiency and soil health scores, pros and cons, evidence, and how stable the ranking is |
| **Yield & Profit** | **Revenue, cost and profit estimates** (below) |
| **Next steps** | Season calendar based on your field's frost dates, questions for your advisor, PDF report / `.ics` calendar / JSON downloads |
| **Field data** | Your field's climate, soil and crop history |
| **Crop guide** | Needs, risks, required equipment and when to avoid each of 20 crops |

## 📋 The Summary tab

The Summary tab puts the whole analysis in one view:

- **Crop history and yield-loss warning:** your 2021–2025 history is analyzed. The app checks whether the same crop or the same plant family (legumes, cereals, broadleaf crops) was planted repeatedly; if there is a risk, it explains why and recommends a next crop to prevent yield loss.
- **Recommended plan:** the highest-scoring rotation for your goal, shown with its crop sequence. You can choose it with one click and move on to the next steps.
- **Plan score (out of 100):** how many points it leads the runner-up by, and how the score is weighted between water efficiency and soil protection for your goal.
- **"Why this plan?" panel:** the reasoning, the evidence behind it (with sources), what is uncertain, and what to check locally before planting.
- **Your field at a glance:** yearly rainfall, very hot days, drought risk and topsoil texture.
- **Coming up:** the first calendar steps for the selected plan.
- **"What if the weather changes?" test:** change yearly rain from −40% to +40% and warming up to +4 °C to see how plan scores and the ranking change.

## 💰 Yield and profit calculation

For the rotation plan you pick, and based on the area you drew on the map, it calculates **season by season**:

- plantable area (hectares),
- required **seed quantity (kg)**,
- climate-adjusted **estimated yield (t/ha)** and total harvest,
- **gross revenue, estimated cost and net profit** (annual average and total).

The calculation uses USDA NASS/ERS regional benchmarks (yield, seeding rate, price, cost). To fit your own conditions:

- **Plantable field share** (50–100%): excludes headlands, ditches and farm roads.
- **Local price adjustment** (−40% to +40%): shifts benchmark prices to match your local buying price.
- **Manual table editing:** double-click price, yield or cost cells and type your own numbers; results recalculate instantly.

> These are estimates based on reference averages, not guaranteed earnings.

## 📚 References

The system pulls live data for your field's coordinates directly from official NASA and USDA servers.

| Source | Used for |
|---|---|
| [NASA POWER](https://power.larc.nasa.gov/api/temporal/daily/point) (Daily Agroclimatology API) | 2021–2025 rainfall, temperature, root-zone soil moisture, evapotranspiration, humidity, wind, heat-stress days above 35 °C, drought index, median frost dates |
| [USDA NRCS SSURGO](https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest) (Soil Data Access) | Soil map unit, texture, organic matter, drainage, water erosion K factor, wind erodibility group, hydrologic group, available water capacity |
| [USDA NASS CDL](https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLValue) (CropScape) | Satellite crop history for years marked "Not sure", and monoculture analysis |
| [USGS The National Map (NAIP)](https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer) and OpenStreetMap | Map base layers (satellite imagery and streets) |
| [USDA NASS Quick Stats](https://quickstats.nass.usda.gov/) | Regional average yield benchmarks for 20 crops |
| [USDA ERS Commodity Costs and Returns](https://www.ers.usda.gov/data-products/commodity-costs-and-returns/) | Seeding rate, price and cost per hectare benchmarks |
| Geodesic area formula | Area in acres and hectares (1 acre = 0.404686 ha) from the map corners |
| [USDA ARS LTAR](https://ltar.ars.usda.gov/) and [SARE](https://www.sare.org/resources/crop-rotation-on-organic-farms/) | Monoculture-breaking rotation rules, legume–cereal–cover crop sequences |
| [USDA NRCS RUSLE2](https://www.nrcs.usda.gov/resources/tech-tools/rusle2) and WEQ | Water erosion (K), wind erosion (WEG) and runoff (HSG) exposure for the soil protection score |
| [FAO Irrigation and Drainage Paper No. 56](https://www.fao.org/3/x0490e/x0490e00.htm) | Seasonal crop water needs and the water efficiency score |
| Monte Carlo sensitivity analysis | Randomly perturbs weights (±30%) and scores to test how stable the ranking is |
| [USDA PLANTS](https://plants.usda.gov/) | Botanical family, nitrogen fixation, rooting depth and drought/salinity tolerance of the 20 crops |
| [SARE Managing Cover Crops Profitably](https://www.sare.org/resources/managing-cover-crops-profitably/) | Guidance on cover crops such as winter rye, hairy vetch, crimson clover, forage radish and buckwheat |
| State university extension services: [K-State](https://www.bookstore.ksre.ksu.edu/), [Iowa State](https://crops.extension.iastate.edu/), [NDSU](https://www.ndsu.edu/agriculture/extension), [UNL CropWatch](https://cropwatch.unl.edu/), [Texas A&M AgriLife](https://agrilifeextension.tamu.edu/) | Planting dates, nitrogen credits, nematode management, rotation intervals, irrigation planning, soil testing guides |
| US city/county coordinate database | State and city selection, and matching browser location to the nearest farming center |

USDA datasets cover the **United States**, so field analysis works for US locations.

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

TerraRotate is a decision-support tool. Results are estimates derived from NASA and USDA data; confirm plans with a local agronomist or agricultural advisor before acting on them.
