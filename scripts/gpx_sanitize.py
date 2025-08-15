import os, glob, json, math, random
from datetime import datetime, timezone, timedelta
import gpxpy

"""
Sanitize GAIA/GPX tracks for public maps:
- Drops points within a geofence radius of HOME
- Excludes points newer than MIN_AGE_DAYS
- Optionally jitters remaining points (random offset)
- Optionally disables jitter when an entire segment is far from HOME
- Outputs a single GeoJSON with LineString features

Env vars (set in workflow YAML):
  HOME_LAT, HOME_LON         : floats (required for geofence/jitter distance checks)
  GEOFENCE_M                 : int meters (drop points within this radius)
  MIN_AGE_DAYS               : int days (omit newer points)
  JITTER                     : "true"/"false" (apply random offset)
  JITTER_MIN_M, JITTER_MAX_M : int meters (jitter range)
  FAR_FROM_HOME_M            : int meters; if >0 and a segment’s closest point
                               to home is beyond this, jitter is disabled
Paths:
  RAW_DIR  : data/raw/*.gpx (input)
  OUT_PATH : docs/data/processed/tracks_safe.geojson (output)
"""

# --- settings from env ---
HOME_LAT = float(os.getenv("HOME_LAT", "0"))
HOME_LON = float(os.getenv("HOME_LON", "0"))
GEOFENCE_M = int(os.getenv("GEOFENCE_M", "0"))
MIN_AGE_DAYS = int(os.getenv("MIN_AGE_DAYS", "0"))
JITTER = os.getenv("JITTER", "false").lower() == "true"
JITTER_MIN_M = int(os.getenv("JITTER_MIN_M", "0"))
JITTER_MAX_M = int(os.getenv("JITTER_MAX_M", "0"))
FAR_FROM_HOME_M = int(os.getenv("FAR_FROM_HOME_M", "0"))  # NEW

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
    lat2 = math.asin(math.sin(lat1)*cos(dR) + math.cos(lat1)*math.sin(dR)*math.cos(brg))
    lon2 = lon1 + math.atan2(math.sin(brg)*math.sin(dR)*math.cos(lat1), math.cos(dR) - math.sin(lat1)*math.sin(lat2))
    return (math.degrees(lat2), (math.degrees(lon2)+540)%360 - 180)

def norm_time(dt):
    if dt is None:
        return None
    # Treat naive timestamps as UTC
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_AGE_DAYS)
features = []
file_count = 0
seg_count = 0
pt_in = pt_out = 0

def process_point_list(points, name):
    """points: list of objects with .latitude, .longitude, .time"""
    global seg_count, pt_in, pt_out
    # First pass: min distance to home for this segment/route
    min_dist = float("inf")
    for p in points:
        if p.latitude is None or p.longitude is None:
            continue
        d = haversine_m(p.latitude, p.longitude, HOME_LAT, HOME_LON)
        if d < min_dist:
            min_dist = d

    # Decide local jitter policy for this segment
    local_jitter = JITTER
    local_jmin = JITTER_MIN_M
    local_jmax = JITTER_MAX_M
    if FAR_FROM_HOME_M > 0 and min_dist > FAR_FROM_HOME_M:
        # Disable jitter entirely when comfortably far from home
        local_jitter = False

    # Second pass: apply filters + optional jitter
    pts = []
    for p in points:
        if p.latitude is None or p.longitude is None:
            continue
        lat = p.latitude; lon = p.longitude
        when = norm_time(getattr(p, "time", None))
        pt_in += 1

        # Delay filter
        if when is not None and when >= cutoff:
            continue

        # Geofence filter
        if GEOFENCE_M > 0 and haversine_m(lat, lon, HOME_LAT, HOME_LON) <= GEOFENCE_M:
            continue

        # Jitter (local policy)
        if local_jitter and (local_jmax > 0):
            dist = random.uniform(max(0, local_jmin), max(local_jmin, local_jmax))
            brg  = random.uniform(0, 360)
            lat, lon = dest_point(lat, lon, brg, dist)

        pts.append([lon, lat])

    if len(pts) >= 2:
        seg_count += 1
        pt_out += len(pts)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": pts},
            "properties": {"name": name}
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
            process_point_list(seg.points, name)

    # Routes (some GPX use these)
    for i, route in enumerate(getattr(gpx, "routes", [])):
        name = f"{base}_r{i+1}" if len(gpx.routes) > 1 else f"{base}_r"
        process_point_list(route.points, name)

# Write GeoJSON
geo = {"type": "FeatureCollection", "features": features}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geo, f)

print(f"Processed files: {file_count}, segments kept: {seg_count}, points in/out: {pt_in}/{pt_out}")
print(f"Wrote {OUT_PATH}")
