from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
import math
import os

# -----------------------------
# 🌐 SUPABASE CONFIG
# -----------------------------
SUPABASE_URL = "https://ihdllispdbwvwcwxlvhr.supabase.co"
SUPABASE_KEY = "sb_publishable_TbC7C4Gf277RzfQtBd3CTw_M68nRP2P"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# 🚀 APP INIT
# -----------------------------
app = FastAPI(title="AVIS Tactical AR OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# 📁 SERVE FRONTEND (avis.html)
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def serve_ui():
    with open(os.path.join(BASE_DIR, "avis.html"), "r", encoding="utf-8") as f:
        return f.read()


# -----------------------------
# 🧠 DISTANCE ENGINE
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# -----------------------------
# 📡 AR FEED (USED BY FRONTEND)
# -----------------------------
@app.get("/api/avis/ar/feed")
def ar_feed(lat: float = Query(...), lon: float = Query(...), limit: int = 25):
    try:
        res = supabase.table("locations").select("*").execute()
        data = res.data or []

        results = []

        for item in data:
            dist = haversine(lat, lon, item["lat"], item["lon"])

            # 5KM VISIBILITY RADIUS
            if dist <= 5:
                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "type": item.get("type", "poi"),
                    "tag": item.get("tag", "DEFAULT"),
                    "lat": item["lat"],
                    "lon": item["lon"],
                    "distance": dist,
                    "rating": item.get("rating", 0),
                    "reviews": item.get("reviews", 0)
                })

        results = sorted(results, key=lambda x: x["distance"])[:limit]

        return {
            "status": "success",
            "count": len(results),
            "data": results
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -----------------------------
# 🧭 GLOBAL MAP DUMP (TEST MODE)
# -----------------------------
@app.get("/api/avis/ar/global")
def global_map():
    try:
        res = supabase.table("locations").select("*").execute()

        return {
            "status": "success",
            "total": len(res.data),
            "data": res.data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}