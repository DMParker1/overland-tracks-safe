import os, glob, json, math, random
from datetime import datetime, timezone, timedelta
import gpxpy

# --- settings from env ---
HOME_LAT = float(os.getenv("HOME_LAT", "0"))
HOME_LON = float(os.getenv("HOME_LON", "0"))
GEOFENCE_M = int(os.getenv("GEOFENCE_M", "0"))
MIN_AGE_DAYS = int(os.getenv("MIN_AGE_DAYS", "0"))
JITTER = os.getenv("JITTER", "false").lower() == "true"
JITTER_MIN_M = int(os.getenv("JITTER_MIN_M", "0"))
JITTER_MAX_M = int(os.getenv("JITTER_MAX_M", "0"))

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

cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_AGE_DAYS)
features = []
file_count = 0
seg_count = 0
pt_in = pt_out = 0

for path in sorted(glob.glob(os.path.join(RAW_DIR, "*.gpx"))):
    with open(path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)
    file_count += 1
    tname = os.path.splitext(os.path.basename(path))[0]
    for track in gpx.tracks:
        for seg in track.segments:
            pts = []
            for p in seg.points:
                lat = p.latitude; lon = p.longitude
                when = p.time  # may be None
                pt_in += 1
                # delay filter
                if when is not None:
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    if when >= cutoff:
                        continue
                # geofence filter
                if GEOFENCE_M > 0 and haversine_m(lat, lon, HOME_LAT, HOME_LON) <= GEOFENCE_M:
                    continue
                # jitter
                if JITTER:
                    dist = random.uniform(JITTER_MIN_M, JITTER_MAX_M)
                    brg = random.uniform(0, 360)
                    lat, lon = dest_point(lat, lon, brg, dist)
                pts.append([lon, lat])

            if len(pts) >= 2:
                seg_count += 1
                pt_out += len(pts)
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": pts},
                    "properties": {"name": tname}
                })

geo = {"type": "FeatureCollection", "features": features}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geo, f)

print(f"Processed files: {file_count}, segments kept: {seg_count}, points in/out: {pt_in}/{pt_out}")
print(f"Wrote {OUT_PATH}")
