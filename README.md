# overland-tracks-safe

**Privacy-safe web map** of my overlanding GPX tracks. Raw GPX files go in a staging folder; a GitHub Action sanitizes them (geofence, delay, optional jitter) and publishes a simple Leaflet map via GitHub Pages.

**Live map:** https://dmparker1.github.io/overland-tracks-safe/

---

## What this is
- Upload one or more `.gpx` files to `data/raw/`.
- Run the **Build sanitized map** action.
- The action writes a single GeoJSON (`docs/data/processed/tracks_safe.geojson`) and the site at `/docs` renders it.

**Important:** This repo is public. Only upload GPX you’re comfortable sharing, or keep raw GPX elsewhere and publish only the sanitized output here.

---

## How to use

1. **Add GPX**
   - Put files in `data/raw/` (you can create the folder in the web UI).
2. **Run the Action**
   - Go to **Actions → Build sanitized map → Run workflow**.
   - Pick a privacy **mode** (see below).
3. **View the map**
   - Open the Live map URL above.
   - Pages must be enabled: **Settings → Pages → Deploy from a branch → main /docs**.

Repo layout:
