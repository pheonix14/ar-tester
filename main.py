import uvicorn
import logging
import os
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from avis import AvisDataExtractor

# --- LOGGING CONFIGURATION ---
# Appends to the exact same file as avis.py so you have one master log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AVIS-SERVER] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("avis_system.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="AVIS AR World Server", version="2.5")

# Allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HTTP TRAFFIC LOGGER ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Intercepts and logs every single request coming to the server."""
    logger.info(f"[HTTP] Incoming: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"[HTTP] Outgoing Status: {response.status_code}")
    return response

# Initialize the Data Engine
URL = "https://ihdllispdbwvwcwxlvhr.supabase.co"
KEY = "sb_publishable_TbC7C4Gf277RzfQtBd3CTw_M68nRP2P"

try:
    logger.info("[STARTUP] Booting AVIS Data Extractor...")
    extractor = AvisDataExtractor(URL, KEY)
    
    # 💥 THE TRIGGER: Load everything from Supabase instantly on startup
    extractor.preload_world_data()
    
except Exception as e:
    logger.error(f"[FATAL] Could not initialize AVIS Engine: {e}")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the avis.html interface."""
    logger.info("[UI] Client requested AR Frontend.")
    index_path = os.path.join(os.path.dirname(__file__), "avis.html")
    
    if not os.path.exists(index_path):
        logger.error(f"[ERROR] Frontend file missing at: {index_path}")
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
    logger.info(f"[API] GPS Scan Triggered | Target: {lat}, {lon} | Radius: {radius}m")
    
    # Query the engine
    nodes = extractor.get_local_world_data(user_lat=lat, user_lon=lon, radius_m=radius)
    
    logger.info(f"[API] Sending {len(nodes)} location nodes to client device.")
    
    return {
        "status": "success",
        "objects_found": len(nodes),
        "data": nodes
    }

# This makes it run properly on Windows when double-clicking or using 'python main.py'
if __name__ == "__main__":
    logger.info("🚀 Uvicorn Server spinning up on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)