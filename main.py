import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from avis import AvisDataExtractor
import os

# Initialize FastAPI
app = FastAPI(title="AVIS AR World Server", version="2.0")

# Allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Data Engine
URL = "https://ihdllispdbwvwcwxlvhr.supabase.co"
KEY = "sb_publishable_TbC7C4Gf277RzfQtBd3CTw_M68nRP2P"
extractor = AvisDataExtractor(URL, KEY)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the avis.html interface."""
    index_path = os.path.join(os.path.dirname(__file__), "avis.html")
    if not os.path.exists(index_path):
        return HTMLResponse(content="<h1>avis.html not found in directory</h1>", status_code=404)
    
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

@app.get("/api/v1/scan")
async def scan_local_area(
    lat: float = Query(..., description="User current latitude"),
    lon: float = Query(..., description="User current longitude"),
    radius: float = Query(1000, description="Scan radius in meters")
):
    """
    API Endpoint for the frontend to fetch nearby AR nodes.
    """
    nodes = extractor.get_local_world_data(user_lat=lat, user_lon=lon, radius_m=radius)
    
    return {
        "status": "success",
        "objects_found": len(nodes),
        "data": nodes
    }

# This makes it run properly on Windows when double-clicking or using 'python main.py'
if __name__ == "__main__":
    print("🚀 AVIS Engine Starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
