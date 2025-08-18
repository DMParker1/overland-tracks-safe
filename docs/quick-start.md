# Overland Tracks — Action Quick Start & Cheat Sheet

This GitHub Action sanitizes your `.gpx` tracks and publishes a privacy-safe `docs/data/processed/tracks_safe.geojson` for the map.

---

## 1) Where to set your HOME location (required)

Edit the **“Set parameters from inputs”** step to your coordinates:

```bash
echo "HOME_LAT=33.6846"  >> $GITHUB_ENV   # <-- set yours
echo "HOME_LON=-117.8265" >> $GITHUB_ENV
```

These are used for **geofencing** (drop points within X meters of home) and for the **far-from-home** jitter rule in `trip` mode.

---

## 2) Inputs you choose in the Action UI

| Input          | Type      | Default | What it does                                                                                           |
|----------------|-----------|---------|---------------------------------------------------------------------------------------------------------|
| `mode`         | choice    | `home`  | Selects a **privacy profile** that sets jitter & far-from-home behavior (`home`, `trip`, or `custom`). |
| `geofence_m`   | string    | `10000` | **Drop** all points within this many **meters** of home.                                               |
| `min_age_days` | string    | `14`    | Only include points **older than** this many **days**.                                                 |
| `jitter_min_m` | string    | `300`   | (custom mode only) Min random offset in meters (set to **0** to disable jitter).                       |
| `jitter_max_m` | string    | `800`   | (custom mode only) Max random offset in meters.                                                         |

> Notes  
> • Inputs are strings in the UI; the workflow passes them as env vars to the Python sanitizer.  
> • `geofence_m` and `min_age_days` apply in **all** modes.

---

## 3) What each **mode** sets under the hood

The Action converts your selection into environment variables consumed by `scripts/gpx_sanitize.py`.

### `home` (default, high privacy near home)
```
JITTER=true
JITTER_MIN_M=300
JITTER_MAX_M=800
FAR_FROM_HOME_M=0
```
- Always jitter (300–800 m).
- No far-from-home override (jitter everywhere, outside the geofence & age filter).

### `trip` (share trips without revealing exact paths)
```
JITTER=true
JITTER_MIN_M=30
JITTER_MAX_M=80
FAR_FROM_HOME_M=30000
```
- Light jitter (30–80 m).  
- **Auto-disable jitter** when the entire segment is **> 30 km from home** (keeps remote tracks crisp while still protecting home vicinity).

### `custom` (full control)
- If `jitter_min_m == 0`:
  ```
  JITTER=false
  JITTER_MIN_M=0
  JITTER_MAX_M=0
  FAR_FROM_HOME_M=0
  ```
  (no jitter at all)
- Else:
  ```
  JITTER=true
  JITTER_MIN_M=<your value>
  JITTER_MAX_M=<your value>
  FAR_FROM_HOME_M=0
  ```

---

## 4) Typical recipes

- **Default “safe at home”**  
  - `mode = home`  
  - `geofence_m = 10000` (10 km)  
  - `min_age_days = 14`

- **Share a recent road trip map, but keep home private**  
  - `mode = trip`  
  - `geofence_m = 10000`  
  - `min_age_days = 7` (if you’re okay showing last week’s trip)  
  - Result: light jitter on most tracks, automatically **no jitter** when tracks are >30 km from home.

- **Absolutely no jitter, rely on geofence + age**  
  - `mode = custom`  
  - `jitter_min_m = 0` (disables jitter)  
  - `geofence_m = 15000` (increase)  
  - `min_age_days = 30` (older only)

---

## 5) What the Action does (pipeline)

1. **Check out code**  
2. **Install Python + `gpxpy`**  
3. **Export env vars** from your inputs & mode (see above)  
4. **Run** `python scripts/gpx_sanitize.py`  
   - Drops points within `GEOFENCE_M` of (`HOME_LAT`, `HOME_LON`)  
   - Excludes points newer than `MIN_AGE_DAYS`  
   - Applies jitter if `JITTER=true` (and not auto-disabled by FAR_FROM_HOME_M logic)  
   - Writes `docs/data/processed/tracks_safe.geojson`
5. **Commit & push** the updated GeoJSON (only if changed)

---

## 6) Quick troubleshooting

- **Map shows “No tracks yet.”**  
  - Check that your sanitizer created: `docs/data/processed/tracks_safe.geojson`  
  - Make sure your GPX files are in the expected raw folder and are parsable.

- **No visible lines but file exists**  
  - `min_age_days` may be too high → everything filtered out.  
  - `geofence_m` may be too large → long segments near home removed.  
  - Try `trip` mode to allow far-from-home de-jittering and confirm geometry exists.

- **Path/URL mismatch**  
  - The webpage fetches: `data/processed/tracks_safe.geojson` relative to `docs/`.  
  - Ensure the committed file is exactly `docs/data/processed/tracks_safe.geojson`.

- **Accidental leak concern**  
  - Increase `geofence_m`.  
  - Increase `min_age_days`.  
  - Use `home` mode (heavier jitter) or `custom` with larger jitter window.

---

## 7) Defaults (at a glance)

- `mode = home`  
- `geofence_m = 10000`  
- `min_age_days = 14`  
- `jitter_min_m = 300` (custom only)  
- `jitter_max_m = 800` (custom only)

You can change any of these at dispatch time in the Actions UI.

---

## 8) Files touched by the workflow

- **Reads** your `.gpx` files (wherever `gpx_sanitize.py` expects them; typically under `data/raw` or similar).  
- **Writes/commits**: `docs/data/processed/tracks_safe.geojson`  

> The map page (`docs/index.html`) loads that GeoJSON and builds the toggle list per base filename.

---

## 9) Safety reminders

- `HOME_LAT/HOME_LON` must be set correctly for **geofence** and **far-from-home** logic to work as intended.  
- Test first with `mode=trip` and a larger `min_age_days` to preview behavior safely.  
- Review the resulting `tracks_safe.geojson` (you can download it and inspect) before widely sharing the link.

---
