"""Static reference data: locations, farmer goals and the crop catalog."""

US_CITIES_COORDS = {
    "Alabama": {
        "Decatur (Morgan County)": (34.6059, -86.9833),
        "Dothan (Houston County)": (31.2232, -85.3905),
        "Huntsville (Madison County)": (34.7304, -86.5861),
    },
    "Arkansas": {
        "Stuttgart (Arkansas County)": (34.5004, -91.5526),
        "Jonesboro (Craighead County)": (35.8423, -90.7043),
        "Pine Bluff (Jefferson County)": (34.2284, -92.0032),
        "Blytheville (Mississippi County)": (35.9273, -89.9190),
    },
    "California": {
        "Fresno (Fresno County)": (36.7378, -119.7871),
        "Bakersfield (Kern County)": (35.3733, -119.0187),
        "Salinas (Monterey County)": (36.6777, -121.6555),
        "Modesto (Stanislaus County)": (37.6391, -120.9969),
        "Visalia (Tulare County)": (36.3302, -119.2921),
        "El Centro (Imperial County)": (32.7920, -115.5631),
    },
    "Colorado": {
        "Greeley (Weld County)": (40.4233, -104.7091),
        "Sterling (Logan County)": (40.6255, -103.2077),
        "Fort Morgan (Morgan County)": (40.2503, -103.8000),
        "Lamar (Prowers County)": (38.0872, -102.6207),
    },
    "Georgia": {
        "Albany (Dougherty County)": (31.5785, -84.1557),
        "Tifton (Tift County)": (31.4505, -83.5085),
        "Statesboro (Bulloch County)": (32.4488, -81.7832),
        "Moultrie (Colquitt County)": (31.1799, -83.7891),
    },
    "Idaho": {
        "Twin Falls (Twin Falls County)": (42.5558, -114.4701),
        "Idaho Falls (Bonneville County)": (43.4917, -112.0339),
        "Caldwell (Canyon County)": (43.6629, -116.6874),
        "Burley (Cassia County)": (42.5357, -113.7928),
    },
    "Illinois": {
        "Champaign (Champaign County)": (40.1164, -88.2434),
        "Peoria (Peoria County)": (40.6936, -89.5890),
        "Bloomington (McLean County)": (40.4842, -88.9937),
        "Decatur (Macon County)": (39.8403, -88.9548),
        "DeKalb (DeKalb County)": (41.9295, -88.7504),
        "Springfield (Sangamon County)": (39.7817, -89.6501),
    },
    "Indiana": {
        "Lafayette (Tippecanoe County)": (40.4167, -86.8753),
        "Fort Wayne (Allen County)": (41.0793, -85.1394),
        "Kokomo (Howard County)": (40.4864, -86.1336),
        "Vincennes (Knox County)": (38.6773, -87.5286),
        "Valparaiso (Porter County)": (41.4731, -87.0611),
    },
    "Iowa": {
        "Ames (Story County)": (42.0308, -93.6319),
        "Cedar Rapids (Linn County)": (41.9779, -91.6656),
        "Des Moines (Polk County)": (41.5868, -93.6250),
        "Sioux City (Woodbury County)": (42.4963, -96.4049),
        "Waterloo (Black Hawk County)": (42.4928, -92.3426),
        "Mason City (Cerro Gordo County)": (43.1536, -93.2010),
    },
    "Kansas": {
        "Garden City (Finney County)": (37.9717, -100.8727),
        "Dodge City (Ford County)": (37.7528, -100.0171),
        "Salina (Saline County)": (38.8403, -97.6114),
        "Hays (Ellis County)": (38.8792, -99.3268),
        "Colby (Thomas County)": (39.3958, -101.0524),
        "Hutchinson (Reno County)": (38.0608, -97.9298),
    },
    "Kentucky": {
        "Owensboro (Daviess County)": (37.7719, -87.1112),
        "Hopkinsville (Christian County)": (36.8656, -87.4886),
        "Bowling Green (Warren County)": (36.9685, -86.4808),
    },
    "Louisiana": {
        "Alexandria (Rapides Parish)": (31.3113, -92.4451),
        "Monroe (Ouachita Parish)": (32.5093, -92.1193),
        "Crowley (Acadia Parish)": (30.2141, -92.3746),
    },
    "Michigan": {
        "Saginaw (Saginaw County)": (43.4195, -83.9508),
        "Lansing (Ingham County)": (42.7325, -84.5555),
        "Kalamazoo (Kalamazoo County)": (42.2917, -85.5872),
        "Bad Axe (Huron County)": (43.8025, -83.0005),
    },
    "Minnesota": {
        "Mankato (Blue Earth County)": (44.1636, -93.9994),
        "Rochester (Olmsted County)": (44.0121, -92.4802),
        "Moorhead (Clay County)": (46.8738, -96.7678),
        "Willmar (Kandiyohi County)": (45.1219, -95.0433),
        "Marshall (Lyon County)": (44.4469, -95.7883),
    },
    "Mississippi": {
        "Greenville (Washington County)": (33.4101, -91.0618),
        "Clarksdale (Coahoma County)": (34.2001, -90.5709),
        "Tupelo (Lee County)": (34.2576, -88.7034),
    },
    "Missouri": {
        "Columbia (Boone County)": (38.9517, -92.3341),
        "Cape Girardeau (Cape Girardeau County)": (37.3059, -89.5181),
        "St. Joseph (Buchanan County)": (39.7675, -94.8467),
        "Sedalia (Pettis County)": (38.7045, -93.2283),
    },
    "Montana": {
        "Great Falls (Cascade County)": (47.5053, -111.3008),
        "Billings (Yellowstone County)": (45.7833, -108.5007),
        "Havre (Hill County)": (48.5500, -109.6841),
        "Bozeman (Gallatin County)": (45.6770, -111.0429),
    },
    "Nebraska": {
        "Kearney (Buffalo County)": (40.6993, -99.0817),
        "Grand Island (Hall County)": (40.9264, -98.3420),
        "North Platte (Lincoln County)": (41.1403, -100.7601),
        "Scottsbluff (Scotts Bluff County)": (41.8666, -103.6672),
        "Norfolk (Madison County)": (42.0329, -97.4170),
    },
    "New York": {
        "Batavia (Genesee County)": (42.9981, -78.1875),
        "Auburn (Cayuga County)": (42.9317, -76.5661),
        "Watertown (Jefferson County)": (43.9748, -75.9108),
    },
    "North Carolina": {
        "Greenville (Pitt County)": (35.6127, -77.3664),
        "Goldsboro (Wayne County)": (35.3849, -77.9928),
        "Lumberton (Robeson County)": (34.6182, -79.0086),
    },
    "North Dakota": {
        "Fargo (Cass County)": (46.8772, -96.7898),
        "Grand Forks (Grand Forks County)": (47.9253, -97.0329),
        "Minot (Ward County)": (48.2325, -101.2963),
        "Bismarck (Burleigh County)": (46.8083, -100.7837),
        "Jamestown (Stutsman County)": (46.9105, -98.7084),
    },
    "Ohio": {
        "Lima (Allen County)": (40.7426, -84.1052),
        "Wooster (Wayne County)": (40.8051, -81.9351),
        "Findlay (Hancock County)": (41.0442, -83.6499),
        "Chillicothe (Ross County)": (39.3331, -82.9824),
    },
    "Oklahoma": {
        "Enid (Garfield County)": (36.3956, -97.8784),
        "Altus (Jackson County)": (34.6381, -99.3340),
        "Lawton (Comanche County)": (34.6036, -98.3959),
        "Guymon (Texas County)": (36.6828, -101.4816),
    },
    "Oregon": {
        "Pendleton (Umatilla County)": (45.6721, -118.7886),
        "Ontario (Malheur County)": (44.0266, -116.9629),
        "Salem (Marion County)": (44.9429, -123.0351),
    },
    "Pennsylvania": {
        "Lancaster (Lancaster County)": (40.0379, -76.3055),
        "Chambersburg (Franklin County)": (39.9376, -77.6611),
        "State College (Centre County)": (40.7934, -77.8600),
    },
    "South Carolina": {
        "Orangeburg (Orangeburg County)": (33.4918, -80.8556),
        "Florence (Florence County)": (34.1954, -79.7626),
        "Sumter (Sumter County)": (33.9204, -80.3415),
    },
    "South Dakota": {
        "Sioux Falls (Minnehaha County)": (43.5460, -96.7313),
        "Aberdeen (Brown County)": (45.4647, -98.4865),
        "Brookings (Brookings County)": (44.3114, -96.7984),
        "Pierre (Hughes County)": (44.3683, -100.3510),
    },
    "Tennessee": {
        "Jackson (Madison County)": (35.6145, -88.8139),
        "Dyersburg (Dyer County)": (36.0345, -89.3856),
        "Clarksville (Montgomery County)": (36.5298, -87.3595),
    },
    "Texas": {
        "Lubbock (Lubbock County)": (33.5779, -101.8552),
        "Amarillo (Potter County)": (35.2220, -101.8313),
        "Waco (McLennan County)": (31.5493, -97.1467),
        "Corpus Christi (Nueces County)": (27.8006, -97.3964),
        "Plainview (Hale County)": (34.1848, -101.7068),
        "Dalhart (Dallam County)": (36.0595, -102.5133),
    },
    "Virginia": {
        "Harrisonburg (Rockingham County)": (38.4496, -78.8689),
        "Suffolk (Suffolk City)": (36.7282, -76.5836),
        "Winchester (Frederick County)": (39.1857, -78.1633),
    },
    "Washington": {
        "Yakima (Yakima County)": (46.6021, -120.5059),
        "Walla Walla (Walla Walla County)": (46.0646, -118.3430),
        "Moses Lake (Grant County)": (47.1301, -119.2781),
        "Pullman (Whitman County)": (46.7298, -117.1817),
    },
    "Wisconsin": {
        "Madison (Dane County)": (43.0731, -89.4012),
        "Green Bay (Brown County)": (44.5133, -88.0133),
        "Janesville (Rock County)": (42.6828, -89.0187),
        "Eau Claire (Eau Claire County)": (44.8113, -91.4985),
    },
}

PRIMARY_GOALS = [
    "Maximize Cash Profit (Recommended)",
    "Conserve Irrigation Water (Recommended for Dry Regions)",
    "Build Soil Organic Matter & Carbon",
    "Reduce Soil Erosion Risk",
    "Boost Livestock Feed & Forage Potential",
    "Improve Crop Quality & Grain Protein",
    "Lower Fertilizer & Input Costs",
]

GOAL_PRESETS = {
    "Maximize Cash Profit (Recommended)": {
        "water": "Medium",
        "equip": "High",
        "forage": "Low",
    },
    "Conserve Irrigation Water (Recommended for Dry Regions)": {
        "water": "Low",
        "equip": "Medium",
        "forage": "Low",
    },
    "Build Soil Organic Matter & Carbon": {
        "water": "Medium",
        "equip": "Medium",
        "forage": "Medium",
    },
    "Reduce Soil Erosion Risk": {
        "water": "Low",
        "equip": "Low",
        "forage": "Medium",
    },
    "Boost Livestock Feed & Forage Potential": {
        "water": "Medium",
        "equip": "Medium",
        "forage": "High",
    },
    "Improve Crop Quality & Grain Protein": {
        "water": "Medium",
        "equip": "High",
        "forage": "Low",
    },
    "Lower Fertilizer & Input Costs": {
        "water": "Medium",
        "equip": "Low",
        "forage": "Medium",
    },
}

# Crop catalog. 'sources' lists extension / SARE references checked for that crop's text.
EXPANDED_CROP_CATALOG = [
    {
        "name": "Corn (Maize)",
        "role": "High Revenue Cash Crop",
        "desc": "Delivers strong market liquidity; demands high water and nitrogen inputs for maximum grain yield.",
        "reqs": "Required Equipment: Precision planter, heavy cultivator, high-capacity combine harvester with corn head.",
        "watchouts": "Key Watchouts: Monitor rootworm pressure and ensure timely nitrogen side-dressing during vegetative growth.",
        "avoid_if": "Avoid if: Your water availability is low or irrigation pumping costs exceed local grain price margins.",
        "sources": [],
    },
    {
        "name": "Soybeans",
        "role": "Natural Nitrogen Fixer",
        "desc": "Fixes much of its own nitrogen through root nodules (up to 50-75% of its need), so it needs little nitrogen fertilizer.",
        "reqs": "Required Equipment: Standard grain drill or row crop planter, flexible cutter bar header for clean pod cutting.",
        "watchouts": "Key Watchouts: Inoculate seed if soybeans have not been grown in the field for 3-5 years; scout for white mold under a humid canopy.",
        "avoid_if": "Avoid if: Soil pH is below about 6.0 without lime, which reduces nodulation and nitrogen fixation.",
        "sources": [["Iowa State Univ. Extension", "https://crops.extension.iastate.edu/encyclopedia/seed-inoculation"], ["UW-Madison Extension", "https://ipcm.wisc.edu/blog/2016/04/do-crop-rotation-and-tillage-influence-seed-applied-inoculant-decisions"]],
    },
    {
        "name": "Grain Sorghum",
        "role": "Drought-Smart Grain",
        "desc": "Uses less water than corn. High Plains trials report roughly 30% lower crop water use and better water-use efficiency under dryland conditions, though yields are not always higher.",
        "reqs": "Required Equipment: Standard row-crop planter, grain combine with specialized sorghum concave settings.",
        "watchouts": "Key Watchouts: Control sorghum midge at flowering and verify local elevator market demand.",
        "avoid_if": "Avoid if: Local livestock feed or ethanol mills do not accept sorghum or offer discounted regional delivery rates.",
        "sources": [["Oklahoma State Univ. water study", "https://ojs.library.okstate.edu/osu/index.php/OWRC/article/view/6219/6811"], ["Univ. of Nebraska CropWatch", "https://cropwatch.unl.edu/crop-water-use-comparison-rainfed-corn-sorghum-and-soybean-2009-2011/"]],
    },
    {
        "name": "Winter Wheat",
        "role": "Cool-Season Cash Crop",
        "desc": "Protects winter soil cover and efficiently utilizes early spring moisture before intense summer heat arrives.",
        "reqs": "Required Equipment: Grain drill, combine harvester equipped with a standard grain platform.",
        "watchouts": "Key Watchouts: Monitor for fungal leaf spots in wet springs and apply timely top-dress nitrogen.",
        "avoid_if": "Avoid if: Your rotation already includes multiple small grains, increasing Fusarium head blight risks.",
        "sources": [],
    },
    {
        "name": "Winter Rye",
        "role": "Cover Crop & Erosion Shield",
        "desc": "Hardy cereal cover crop: its fibrous roots hold soil, it scavenges leftover nitrogen, adds organic matter and suppresses weeds.",
        "reqs": "Required Equipment: Broadcast spreader or grain drill, roller-crimp termination tool for organic no-till.",
        "watchouts": "Key Watchouts: End the rye before it gets tall; late termination can use up soil moisture and tie up nitrogen for the next crop.",
        "avoid_if": "Avoid if: You cannot terminate it on time (roll, crimp, till or herbicide) before the next crop.",
        "sources": [["SARE: Cereal Rye", "https://www.sare.org/publications/managing-cover-crops-profitably/nonlegume-cover-crops/cereal-rye/"], ["SARE: Cover crops and erosion", "https://www.sare.org/publications/cover-crops-ecosystem-services/cover-crops-at-work-covering-the-soil-to-prevent-erosion/"]],
    },
    {
        "name": "Alfalfa",
        "role": "High-Protein Forage",
        "desc": "Deep taproots aerate soil profile while supplying premium protein-rich livestock feed and fixing nitrogen.",
        "reqs": "Required Equipment: Alfalfa seeder, swather/mower-conditioner, heavy-duty baler or forage chopper.",
        "watchouts": "Key Watchouts: Maintain optimal soil pH above 6.5 and monitor closely for alfalfa weevil infestations.",
        "avoid_if": "Avoid if: You need a short 1-year cash rotation, as alfalfa is a multi-year perennial crop investment.",
        "sources": [],
    },
    {
        "name": "Sunflower",
        "role": "Industrial Oilseed",
        "desc": "Deep taproots extract subsoil moisture and residual nutrients efficiently from lower soil horizons.",
        "reqs": "Required Equipment: Row crop planter, combine fitted with specialized sunflower pan attachments.",
        "watchouts": "Key Watchouts: Manage bird predation risks during seed fill and scout for Sclerotinia head rot.",
        "avoid_if": "Avoid if: Local bird populations are exceptionally high or regional drying and storage facilities are missing.",
        "sources": [],
    },
    {
        "name": "Barley",
        "role": "Resilient Feed & Malt",
        "desc": "Features a short growth cycle and tolerates soil salinity and cooler temperatures better than wheat.",
        "reqs": "Required Equipment: Grain drill, standard grain combine harvester.",
        "watchouts": "Key Watchouts: Avoid excessive nitrogen fertilization to prevent lodging (stem collapse) before harvest.",
        "avoid_if": "Avoid if: Malting grade specifications cannot be met, forcing you to sell at lower feed-grade market prices.",
        "sources": [],
    },
    {
        "name": "Oats",
        "role": "Cool-Weather Cover & Grain",
        "desc": "Excellent for weed suppression, soil conditioning, and companion cropping in cooler northern zones.",
        "reqs": "Required Equipment: Grain drill, conventional combine harvester.",
        "watchouts": "Key Watchouts: Susceptible to crown rust; select disease-resistant certified seed varieties.",
        "avoid_if": "Avoid if: Grown in warm southern climates where high temperatures induce heat sterility and low test weights.",
        "sources": [],
    },
    {
        "name": "Canola",
        "role": "High-Value Oilseed",
        "desc": "Thrives in cooler spring temperatures as a profitable broadleaf rotation break for cereal crops.",
        "reqs": "Required Equipment: Precision air seeder or canola drill, swather or direct-cut header.",
        "watchouts": "Key Watchouts: Monitor flea beetles closely during seedling emergence and protect young stands.",
        "avoid_if": "Avoid if: Summer temperatures frequently exceed 35°C during flowering, causing severe pod abortion.",
        "sources": [],
    },
    {
        "name": "Cotton",
        "role": "Fiber Cash Crop",
        "desc": "High-value cash crop requiring warm temperatures, adequate sunshine, and targeted irrigation.",
        "reqs": "Required Equipment: Precision pneumatic planter, multi-row cotton stripper or picker.",
        "watchouts": "Key Watchouts: Manage bollworm pressure and ensure strict defoliation timing prior to harvest.",
        "avoid_if": "Avoid if: Your growing season frost-free days are fewer than 180 or regional ginning infrastructure is distant.",
        "sources": [],
    },
    {
        "name": "Sugar Beets",
        "role": "High-Sugar Root Crop",
        "desc": "Deep root structure breaks soil compaction layers while producing high sucrose content for processing.",
        "reqs": "Required Equipment: Specialized beet planter, multi-row beet harvester and defoliator.",
        "watchouts": "Key Watchouts: Requires deep, well-drained soils and careful Cercospora leaf spot management.",
        "avoid_if": "Avoid if: You do not have a guaranteed delivery contract with a regional sugar beet processing factory.",
        "sources": [],
    },
    {
        "name": "Dry Beans",
        "role": "Legume Protein Cash Crop",
        "desc": "Short-season legume that adds moderate nitrogen to soil while commanding strong food-grade market prices.",
        "reqs": "Required Equipment: Row crop planter, bean cutter/puller and pick-up combine header.",
        "watchouts": "Key Watchouts: Highly sensitive to root rot pathogens; avoid poorly drained fields.",
        "avoid_if": "Avoid if: Harvest weather is traditionally wet in your area, which stains beans and ruins food-grade quality.",
        "sources": [],
    },
    {
        "name": "Lentils",
        "role": "Arid-Adapted Pulse",
        "desc": "Thrives in low-moisture environments, fixing atmospheric nitrogen and reducing chemical fertilizer needs.",
        "reqs": "Required Equipment: Standard grain drill, flexible header or windrower.",
        "watchouts": "Key Watchouts: Vulnerable to Ascochyta blight in wet years; use certified disease-free seed.",
        "avoid_if": "Avoid if: Soil is heavy clay prone to waterlogging or crusting during seedling emergence.",
        "sources": [],
    },
    {
        "name": "Chickpeas",
        "role": "High-Value Pulse",
        "desc": "Deep-rooted pulse crop well-suited to dryland rotations with excellent export market demand.",
        "reqs": "Required Equipment: Precision planter or air seeder, combine with low cylinder speed.",
        "watchouts": "Key Watchouts: Ascochyta blight management is critical; fungicide seed treatments are recommended.",
        "avoid_if": "Avoid if: Regional rainfall during pod fill exceeds historical averages, triggering uncontrollable disease spread.",
        "sources": [],
    },
    {
        "name": "Potatoes",
        "role": "High-Yield Tuber Crop",
        "desc": "Intensive high-value tuber crop requiring loose, well-drained soils and rigorous irrigation management.",
        "reqs": "Required Equipment: Potato seed cutter, specialized multi-row planter, potato harvester and storage facility.",
        "watchouts": "Key Watchouts: Prevent late blight through rigorous scouting and timed fungicide applications.",
        "avoid_if": "Avoid if: You lack specialized cool-storage facilities or capital-intensive specialized machinery.",
        "sources": [],
    },
    {
        "name": "Flaxseed",
        "role": "Omega-3 Oilseed",
        "desc": "Drought-tolerant oilseed with fine roots that leaves a clean, easy-to-manage stubble for following crops.",
        "reqs": "Required Equipment: Grain drill, conventional combine with tight concave clearance.",
        "watchouts": "Key Watchouts: Tough fibrous stems can wrap around combine shafts if not completely dry.",
        "avoid_if": "Avoid if: Herbicide carryover from previous broadleaf chemistry persists in your soil profile.",
        "sources": [],
    },
    {
        "name": "Safflower",
        "role": "Deep-Rooted Oilseed",
        "desc": "Extremely deep taproot system extracts moisture from deep subsoil layers unreachable by other crops.",
        "reqs": "Required Equipment: Standard grain drill or row planter, grain combine.",
        "watchouts": "Key Watchouts: Susceptible to Alternaria leaf spot and root rot if soil remains waterlogged.",
        "avoid_if": "Avoid if: Irrigation or high rainfall is expected late in the season, which degrades oil quality.",
        "sources": [],
    },
    {
        "name": "Millet",
        "role": "Ultra-Short Season Grain",
        "desc": "Exceptional drought tolerance with a very short growing season; ideal as an emergency or catch crop.",
        "reqs": "Required Equipment: Grain drill, standard grain combine.",
        "watchouts": "Key Watchouts: Bird feeding pressure can be high on small fields; harvest promptly when ripe.",
        "avoid_if": "Avoid if: Primary cash crop opportunities with higher market premiums are viable in your region.",
        "sources": [],
    },
    {
        "name": "Field Peas",
        "role": "Nitrogen-Fixing Cover & Grain",
        "desc": "Builds soil health rapidly, suppresses weeds, and provides high-protein feed or cash grain.",
        "reqs": "Required Equipment: Grain drill, flexible cutter bar or pickup reel.",
        "watchouts": "Key Watchouts: Prone to lodging if vines grow excessively lush in high-nitrogen soils.",
        "avoid_if": "Avoid if: Soil compaction is severe, restricting the root penetration necessary for nitrogen fixation.",
        "sources": [],
    },
]

ALL_CROP_NAMES = [c["name"] for c in EXPANDED_CROP_CATALOG]
HISTORY_YEARS = [2021, 2022, 2023, 2024, 2025]

# Short, farmer-facing labels for each goal. Keys must stay identical to
# PRIMARY_GOALS because nasa.py matches keywords inside them.
GOAL_INFO = {
    "Maximize Cash Profit (Recommended)": (
        "Maximize profit (high-value cash crops)",
        "Favors high-value cash crops when water and equipment allow.",
    ),
    "Conserve Irrigation Water (Recommended for Dry Regions)": (
        "Save water (drought-tolerant crops)",
        "Favors drought-tolerant crops and residue that keeps moisture in.",
    ),
    "Build Soil Organic Matter & Carbon": (
        "Build soil carbon (cover crops & deep roots)",
        "Favors cover crops and deep roots that add organic matter.",
    ),
    "Reduce Soil Erosion Risk": (
        "Stop erosion (living winter cover)",
        "Favors living cover through winter and high-residue crops.",
    ),
    "Boost Livestock Feed & Forage Potential": (
        "Grow more feed (forage & hay)",
        "Favors forage crops, grazing covers and hay.",
    ),
    "Improve Crop Quality & Grain Protein": (
        "Improve quality (legume-cereal balance)",
        "Favors legume-cereal sequences that lift grain protein.",
    ),
    "Lower Fertilizer & Input Costs": (
        "Cut input costs (nitrogen-fixing legumes)",
        "Favors nitrogen-fixing legumes and lower-input crops.",
    ),
}

CONSTRAINTS = [
    ("slider_water", "Water available", "Irrigation or reliable rainfall you can count on."),
    ("slider_equip", "Equipment", "Automatically set by your selected goal."),
    ("slider_forage", "Livestock feed need", "How much hay or grazing your farm needs."),
]

EQUIPMENT_OPTIONS = [
    "Row-crop planter (Corn, Soybeans, Sorghum, Sunflower)",
    "Grain drill / air seeder (Wheat, Rye, Barley, Oats, Canola)",
    "Combine harvester with grain/corn head",
    "Roller-crimper or cover-crop termination rig",
    "Swather / mower-conditioner & hay baler (Alfalfa/Forage)",
    "Broadcast spreader & sprayer",
]


# USDA NASS / ERS baseline agronomic & economic benchmarks per hectare (metric)
# yield_t_ha: average yield in metric tons per hectare
# seed_kg_ha: recommended seeding rate in kg per hectare
# price_usd_t: benchmark farm-gate price in USD per metric ton
# cost_usd_ha: typical variable production cost (seed, fertilizer, fuel, chemicals) in USD per hectare
CROP_ECONOMICS = {
    "Corn (Maize)":      {"yield_t_ha": 11.2, "seed_kg_ha": 24.0, "price_usd_t": 185.0, "cost_usd_ha": 1180.0},
    "Soybeans":          {"yield_t_ha": 3.5,  "seed_kg_ha": 65.0, "price_usd_t": 410.0, "cost_usd_ha": 690.0},
    "Grain Sorghum":     {"yield_t_ha": 5.1,  "seed_kg_ha": 8.0,  "price_usd_t": 175.0, "cost_usd_ha": 560.0},
    "Winter Wheat":      {"yield_t_ha": 3.6,  "seed_kg_ha": 95.0, "price_usd_t": 215.0, "cost_usd_ha": 510.0},
    "Winter Rye":        {"yield_t_ha": 2.4,  "seed_kg_ha": 90.0, "price_usd_t": 190.0, "cost_usd_ha": 320.0},
    "Alfalfa":           {"yield_t_ha": 9.5,  "seed_kg_ha": 18.0, "price_usd_t": 210.0, "cost_usd_ha": 780.0},
    "Sunflower":         {"yield_t_ha": 2.1,  "seed_kg_ha": 5.5,  "price_usd_t": 480.0, "cost_usd_ha": 540.0},
    "Barley":            {"yield_t_ha": 4.2,  "seed_kg_ha": 100.0,"price_usd_t": 205.0, "cost_usd_ha": 490.0},
    "Oats":              {"yield_t_ha": 2.8,  "seed_kg_ha": 95.0, "price_usd_t": 220.0, "cost_usd_ha": 420.0},
    "Canola":            {"yield_t_ha": 2.3,  "seed_kg_ha": 5.5,  "price_usd_t": 460.0, "cost_usd_ha": 590.0},
    "Cotton":            {"yield_t_ha": 1.1,  "seed_kg_ha": 14.0, "price_usd_t": 1650.0,"cost_usd_ha": 1250.0},
    "Sugar Beets":       {"yield_t_ha": 68.0, "seed_kg_ha": 2.2,  "price_usd_t": 48.0,  "cost_usd_ha": 1850.0},
    "Dry Beans":         {"yield_t_ha": 2.2,  "seed_kg_ha": 75.0, "price_usd_t": 780.0, "cost_usd_ha": 790.0},
    "Lentils":           {"yield_t_ha": 1.5,  "seed_kg_ha": 45.0, "price_usd_t": 680.0, "cost_usd_ha": 460.0},
    "Chickpeas":         {"yield_t_ha": 1.7,  "seed_kg_ha": 110.0,"price_usd_t": 740.0, "cost_usd_ha": 550.0},
    "Potatoes":          {"yield_t_ha": 48.0, "seed_kg_ha": 2200.0,"price_usd_t": 230.0,"cost_usd_ha": 4900.0},
    "Flaxseed":          {"yield_t_ha": 1.5,  "seed_kg_ha": 45.0, "price_usd_t": 540.0, "cost_usd_ha": 410.0},
    "Safflower":         {"yield_t_ha": 1.6,  "seed_kg_ha": 28.0, "price_usd_t": 520.0, "cost_usd_ha": 430.0},
    "Millet":            {"yield_t_ha": 2.2,  "seed_kg_ha": 18.0, "price_usd_t": 240.0, "cost_usd_ha": 350.0},
    "Field Peas":        {"yield_t_ha": 2.5,  "seed_kg_ha": 140.0,"price_usd_t": 310.0, "cost_usd_ha": 470.0},
}
