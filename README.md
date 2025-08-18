# overland-tracks-safe

Privacy-safe web map of my overlanding GPX tracks. Raw GPX files go in a staging folder; a GitHub Action **sanitizes** them (geofence, delay, optional jitter) and publishes a simple Leaflet map via GitHub Pages.

**Live map:** https://dmparker1.github.io/overland-tracks-safe/
**Quick start & cheat sheet:** https://github.com/DMParker1/overland-tracks-safe/blob/main/docs/quick-start.md


---

## What this is

- Upload one or more `.gpx` files to `data/raw/`.
- Run the **Build sanitized map** GitHub Action.
- The Action writes a single GeoJSON at `docs/data/processed/tracks_safe.geojson`, and the site in `docs/` renders it.

> ⚠️ This repo is public. Only upload GPX you’re comfortable sharing, or keep raw GPX elsewhere and publish only the sanitized output here.

---

## How to use

1. **Add GPX**
   - Put files in `data/raw/` (create the folder in the web UI if it doesn’t exist).
2. **Run the Action**
   - Go to **Actions → Build sanitized map → Run workflow**.
   - Pick a privacy **mode** (see below).
3. **View the map**
   - Open the Live map URL above.
   - Ensure Pages is enabled: **Settings → Pages → Deploy from a branch → main /docs**.

**Repo layout**
```text
docs/                       # published site (GitHub Pages)
  index.html
  data/processed/tracks_safe.geojson
data/
  raw/                      # uploaded GPX files (public!)
scripts/
  gpx_sanitize.py           # sanitizer used by the Action
.github/workflows/
  build_map.yml             # GitHub Action (manual run with inputs)
```

---

## Action settings (picked at run time)

When you run **Build sanitized map** you’ll see these inputs:

- **mode**: `home` · `trip` · `custom`
  - `home` – stronger privacy near home:
    - jitter ≈ **300–800 m** on kept points
    - geofence (default **2 km**) hides points near home
    - delay (default **7 days**) hides recent points
  - `trip` – softer privacy when away:
    - small jitter ≈ **30–80 m**
    - same geofence / delay
    - if an entire segment stays **>30 km** from home, jitter auto-disables
  - `custom` – set your own numbers below
- **geofence_m**: drop points within this many meters of home (e.g., `2000`)
- **min_age_days**: include only points older than this many days (e.g., `7`)
- **jitter_min_m / jitter_max_m** *(custom mode)*:
  - set both to `0` to turn jitter **off**

These map to environment variables the script reads:
```text
HOME_LAT / HOME_LON        # set inside the workflow (edit once)
GEOFENCE_M                 # meters
MIN_AGE_DAYS               # days
JITTER                     # true/false
JITTER_MIN_M / JITTER_MAX_M
FAR_FROM_HOME_M            # meters; disables jitter for far segments
```

---

## Configure your home location (edit once)

Edit `.github/workflows/build_map.yml` → step **“Set parameters from inputs”** and set your approximate home:
```bash
echo "HOME_LAT=33.683"  >> $GITHUB_ENV   # ← change me
echo "HOME_LON=-117.826" >> $GITHUB_ENV  # ← change me
```

_Defaults in the workflow (can be changed at run time):_
```text
geofence_m:   2000
min_age_days: 7
home mode jitter:  300–800 m
trip mode jitter:   30–80 m + FAR_FROM_HOME_M=30000 (30 km)
```

---

## Notes

- The sanitizer keeps only segments with ≥2 points **after** filtering.
- Both **tracks** and **routes** in GPX are supported.
- You can adjust the map styling/zoom in `docs/index.html`.
- For sensitive trips, consider:
  - keeping raw GPX in a **private** repo and pushing only the sanitized GeoJSON here, or
  - keeping this repo private (Pages can publish from private repos on eligible plans).

---

## License

Code: **MIT**.  
Site content: you own your data; keep raw files out of the public repo if privacy is a concern.
