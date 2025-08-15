import os, glob, json, math, random
from datetime import datetime, timezone, timedelta
import gpxpy

"""
Sanitize GAIA/GPX tracks for public maps:
- Drops points within a soft geofence radius of HOME (point-level filtering)
- Optionally drops ENTIRE segments that come within a hard geofence of HOME
- Excludes points newer than MIN_AGE_DAYS
- Optionally jitters remaining points (random offset)
- Optionally disables jitter when an entire segment is far from HOME
- Outputs a single GeoJSON with LineString features

Env vars (set in workflow YAML):
  HOME_LAT, HOME_LON           : floats (required for distance checks)
  GEOFENCE_M                   : int meters (drop individual points within this radius)
  GEOFENCE_HARD_M              : int meters (if any point in a segment is ≤ this distance from HOME, drop the whole segment)
  MIN_AGE_DAYS                 : int days (omit newer points)
  JITTER                       : "true"/"false" (apply random offset)
  JITTER_MIN_M, JITTER_MAX_M   : int meters (jitter range; set both 0 to disable)
  FAR_FROM_HOME_M              : int meters; if >0 and a segment’s closest point to HOME exceeds this, jitter is disabled

Paths:
  RAW_DIR  : data/raw/*.gpx (input)
  OUT_PATH : docs/data/processed/tracks_safe.geojson (output)
"""

# --- settings from env ---
HOME_LAT = float(os.getenv("HOME_LAT", "0"))
HOME_LON = float(os.getenv("HOME_LON", "0"))
GEOFENCE_M = int(os.getenv("GEOFENCE_M", "0"))
GEOFENCE_HARD_M = int(os.getenv("GEOFENCE_HARD_M", "0"))
MIN_AGE_DAYS = int(os.getenv("MIN_AGE_DAYS", "0"))
JITTER = os.getenv("JITTER", "false").lower() == "true"
JITTER_MIN_M = int(os.getenv("JITTER_MIN_M", "0"))
JITTER_MAX_M = int(os.getenv("JITTER_MAX_M", "0"))
FAR_FROM_HOME_M = int(os.getenv("FAR_FROM_HOME_M", "0"))

RAW_DIR = "data/raw"
OUT_PATH = "docs/data/processed/tracks_safe.geojson"

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def dest_point(lat, lon, bearing_deg, dist_m):
    R = 6371000.0
    brg = math.radians(bearing_deg)
    lat1 = math.radians(lat); lon1 = math.radians(lon)
    dR = dist_m / R
    lat2 = math.asin(math.sin(lat1)*math.cos(dR) + math.cos(lat1)*math.sin(dR)*math.cos(brg))
    lon2 = lon1 + math.atan2(math.sin(brg)*math.sin(dR)*math.cos(lat1), math.cos(dR) - math.sin(lat1)*math.sin(lat2))
    return (math.degrees(lat2), (math.degrees(lon2)+540)%360 - 180)

def norm_time(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_AGE_DAYS)
features = []
file_count = 0
seg_count = 0
pt_in = pt_out = 0

def process_point_list(points, name, source_base, kind):
    """points: list of objects with .latitude, .longitude, .time"""
    global seg_count, pt_in, pt_out

    # First pass: min distance to HOME for this segment/route
    min_dist = float("inf")
    any_valid = False
    for p in points:
        lat = getattr(p, "latitude", None)
        lon = getattr(p, "longitude", None)
        if lat is None or lon is None:
            continue
        any_valid = True
        d = haversine_m(lat, lon, HOME_LAT, HOME_LON)
        if d < min_dist:
            min_dist = d

    if not any_valid:
        return  # nothing usable

    # Hard geofence: drop ENTIRE segment if it ever comes too close to HOME
    if GEOFENCE_HARD_M > 0 and min_dist <= GEOFENCE_HARD_M:
        return

    # Decide local jitter policy for this segment
    local_jitter = JITTER
    local_jmin = max(0, JITTER_MIN_M)
    local_jmax = max(local_jmin, JITTER_MAX_M)
    if FAR_FROM_HOME_M > 0 and min_dist > FAR_FROM_HOME_M:
        # Disable jitter when comfortably far from home
        local_jitter = False

    # Second pass: apply point-level filters + optional jitter
    coords = []
    for p in points:
        lat = getattr(p, "latitude", None)
        lon = getattr(p, "longitude", None)
        if lat is None or lon is None:
            continue
        when = norm_time(getattr(p, "time", None))
        pt_in += 1

        # Delay filter
        if when is not None and when >= cutoff:
            continue

        # Soft geofence filter (drop points close to HOME)
        if GEOFENCE_M > 0 and haversine_m(lat, lon, HOME_LAT, HOME_LON) <= GEOFENCE_M:
            continue

        # Jitter (local policy)
        if local_jitter and local_jmax > 0:
            dist = random.uniform(local_jmin, local_jmax)
            brg  = random.uniform(0, 360)
            lat, lon = dest_point(lat, lon, brg, dist)

        coords.append([lon, lat])

    if len(coords) >= 2:
        seg_count += 1
        pt_out += len(coords)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "name": name,            # e.g., base_t1_s2 or base_r
                "source": source_base,   # base filename (for coloring/toggles)
                "kind": kind             # "track" or "route"
            }
        })

# Process each GPX
gpx_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.gpx")))
for path in gpx_files:
    with open(path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)
    file_count += 1
    base = os.path.splitext(os.path.basename(path))[0]

    # Tracks (segments)
    for i, track in enumerate(gpx.tracks):
        for j, seg in enumerate(track.segments):
            name = f"{base}"
            if len(gpx.tracks) > 1:
                name += f"_t{i+1}"
            if len(track.segments) > 1:
                name += f"_s{j+1}"
            process_point_list(seg.points, name, base, "track")

    # Routes (some GPX use these)
    routes = getattr(gpx, "routes", [])
    for i, route in enumerate(routes):
        name = f"{base}_r{i+1}" if len(routes) > 1 else f"{base}_r"
        process_point_list(route.points, name, base, "route")

# Write GeoJSON
geo = {"type": "FeatureCollection", "features": features}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geo, f)

print(f"Processed files: {file_count}, segments kept: {seg_count}, points in/out: {pt_in}/{pt_out}")
print(f"Wrote {OUT_PATH}")
