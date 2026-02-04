import folium
from folium import IFrame
from PIL import Image
import base64
import os
import io

# Colorado area photos with their GPS coordinates
photos = [
    {"file": "20240707-130838_Mini3Pro_DJI_0374.JPG", "lat": 38 + 19/60 + 49.57/3600, "lon": -(108 + 58/60 + 56.96/3600), "alt": 2015.5},
    {"file": "20240707-130844_Mini3Pro_DJI_0375.JPG", "lat": 38 + 19/60 + 49.57/3600, "lon": -(108 + 58/60 + 56.97/3600), "alt": 2015.5},
    {"file": "20240707-131030_Mini3Pro_DJI_0376.JPG", "lat": 38 + 19/60 + 49.57/3600, "lon": -(108 + 58/60 + 56.96/3600), "alt": 2015.5},
    {"file": "20240707-131310_Mini3Pro_DJI_0377.JPG", "lat": 38 + 19/60 + 47.72/3600, "lon": -(108 + 59/60 + 8.42/3600), "alt": 2042.3},
    {"file": "20240707-131316_Mini3Pro_DJI_0378.JPG", "lat": 38 + 19/60 + 47.72/3600, "lon": -(108 + 59/60 + 8.42/3600), "alt": 2042.9},
    {"file": "20240707-131330_Mini3Pro_DJI_0379.JPG", "lat": 38 + 19/60 + 47.72/3600, "lon": -(108 + 59/60 + 8.41/3600), "alt": 2043.1},
]

base_dir = "/Users/ariessunfeld/Documents/projects/georef"

def make_thumbnail_b64(img_path, max_size=300):
    """Create a small JPEG thumbnail and return as base64."""
    img = Image.open(img_path)
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return base64.b64encode(buf.getvalue()).decode()

# Offset overlapping markers slightly so all 6 are visible
# Group by approximate location and fan out
from collections import defaultdict

def round_coord(lat, lon, precision=4):
    return (round(lat, precision), round(lon, precision))

groups = defaultdict(list)
for p in photos:
    key = round_coord(p["lat"], p["lon"])
    groups[key].append(p)

import math

offset_photos = []
for key, group in groups.items():
    n = len(group)
    for i, p in enumerate(group):
        if n > 1:
            angle = 2 * math.pi * i / n
            # ~15 meter offset so pins don't stack
            dlat = 0.00013 * math.sin(angle)
            dlon = 0.00013 * math.cos(angle)
        else:
            dlat = dlon = 0
        offset_photos.append({**p, "display_lat": p["lat"] + dlat, "display_lon": p["lon"] + dlon})

# Center map on the midpoint
avg_lat = sum(p["lat"] for p in photos) / len(photos)
avg_lon = sum(p["lon"] for p in photos) / len(photos)

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=15, tiles="OpenStreetMap")

# Also add satellite tile layer
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite",
).add_to(m)

folium.LayerControl().add_to(m)

for p in offset_photos:
    img_path = os.path.join(base_dir, p["file"])
    thumb_b64 = make_thumbnail_b64(img_path)

    html = f"""
    <div style="text-align:center">
        <b>{p['file']}</b><br>
        <img src="data:image/jpeg;base64,{thumb_b64}" style="max-width:280px"><br>
        <small>Lat: {p['lat']:.6f}, Lon: {p['lon']:.6f}<br>Alt: {p['alt']} m</small>
    </div>
    """

    iframe = IFrame(html, width=320, height=340)
    popup = folium.Popup(iframe, max_width=330)

    folium.Marker(
        location=[p["display_lat"], p["display_lon"]],
        popup=popup,
        tooltip=p["file"],
        icon=folium.Icon(color="red", icon="camera", prefix="fa"),
    ).add_to(m)

output = os.path.join(base_dir, "colorado_photos_map.html")
m.save(output)
print(f"Map saved to {output}")
