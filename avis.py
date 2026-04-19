import logging
import math
from supabase import create_client, Client

# --- LOGGING CONFIGURATION ---
# Logs to both 'avis_system.log' and your terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AVIS-ENGINE] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("avis_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points 
    on the Earth's surface in meters.
    """
    R = 6371000  # Earth radius in meters
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi_1) * math.cos(phi_2) * \
        math.sin(delta_lambda / 2.0) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AvisDataExtractor:
    def __init__(self, url: str, key: str):
        """Initializes connection to Supabase World Database."""
        try:
            self.supabase: Client = create_client(url, key)
            logger.info("✅ Supabase Engine Connection Established.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise

    def get_local_world_data(self, user_lat: float, user_lon: float, radius_m: float = 2000):
        """
        1. Fetches all locations and lore stories.
        2. Merges them based on location IDs.
        3. Filters based on the user's current GPS position.
        """
        logger.info(f"🛰️ Scanning world objects within {radius_m}m of ({user_lat}, {user_lon})")
        
        try:
            # Fetch raw data from your Supabase tables
            loc_res = self.supabase.table("locations").select("*").execute()
            story_res = self.supabase.table("stories").select("*").execute()

            locations = loc_res.data
            stories = story_res.data

            # Create an efficient lookup for stories indexed by loc_id
            story_lookup = {}
            for s in stories:
                l_id = s.get("loc_id")
                if l_id not in story_lookup:
                    story_lookup[l_id] = []
                story_lookup[l_id].append(s)

            processed_world = []

            for loc in locations:
                # Support both 'lat/lon' and 'latitude/longitude' naming conventions
                t_lat = loc.get("lat") or loc.get("latitude")
                t_lon = loc.get("lon") or loc.get("longitude")

                if t_lat is None or t_lon is None:
                    continue

                # Distance calculation
                dist_m = calculate_haversine(user_lat, user_lon, t_lat, t_lon)

                # Only include objects within the active "loading" radius
                if dist_m <= radius_m:
                    loc_id = loc.get("id")
                    
                    # Merge story lore into the location object
                    loc_stories = story_lookup.get(loc_id, [])
                    
                    node = {
                        "id": loc_id,
                        "name": loc.get("name", "Unknown Landmark"),
                        "lat": t_lat,
                        "lon": t_lon,
                        "category": loc.get("category", "point_of_interest"),
                        "reward": loc.get("reward_per_visit", 100),
                        "icon": loc.get("icon", "treasure"),
                        "stories": loc_stories,
                        "distance_meters": round(dist_m, 2),
                        "is_legend": any(s.get("is_resident_legend") for s in loc_stories)
                    }
                    processed_world.append(node)

            logger.info(f"🎯 Extraction Success: {len(processed_world)} objects synced to AR view.")
            return processed_world

        except Exception as e:
            logger.error(f"🔥 Critical Data Extraction Failure: {e}")
            return []

# --- INTEGRATION HOOK ---
# Used by main.py to quickly boot the system
def load_avis_system():
    URL = "https://ihdllispdbwvwcwxlvhr.supabase.co"
    KEY = "sb_publishable_TbC7C4Gf277RzfQtBd3CTw_M68nRP2P"
    return AvisDataExtractor(URL, KEY)
