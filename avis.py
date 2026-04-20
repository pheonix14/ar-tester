import logging
import math
from supabase import create_client, Client

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AVIS-ENGINE] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("avis_system.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
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
            logger.info("[SUCCESS] Supabase Engine Connection Established.")
            # Data caches for the pre-loader
            self.global_locations = []
            self.global_stories = []
        except Exception as e:
            logger.error(f"[ERROR] Failed to connect to Supabase: {e}")
            raise

    def preload_world_data(self):
        """
        Runs automatically on server boot. 
        Extracts EVERYTHING from Supabase so it's ready before users even connect.
        """
        logger.info("[BOOT SEQUENCE] Initiating Global World Extraction...")
        
        try:
            # --- 1. EXTRACT LOCATIONS ---
            logger.info("[PROCESS] Extracting locations table...")
            loc_res = self.supabase.table("locations").select("*").execute()
            self.global_locations = loc_res.data
            logger.info(f"[DATABASE] Successfully pulled {len(self.global_locations)} raw locations.")

            # --- 2. EXTRACT STORIES ---
            logger.info("[PROCESS] Extracting stories table...")
            story_res = self.supabase.table("stories").select("*").execute()
            self.global_stories = story_res.data
            logger.info(f"[DATABASE] Successfully pulled {len(self.global_stories)} lore entries.")

            logger.info("[PROCESS] Beginning coordinate validation and global mapping...")

            # --- 3. PROCESS & EXPLICIT LOGGING OF EACH LOCATION ---
            for loc in self.global_locations:
                loc_id = loc.get("id", "UNKNOWN_ID")
                name = loc.get("name", "Unnamed Node")
                
                # Support both 'lat/lon' and 'latitude/longitude' naming conventions
                t_lat = loc.get("lat") or loc.get("latitude")
                t_lon = loc.get("lon") or loc.get("longitude")

                # Check for missing data
                if t_lat is None or t_lon is None:
                    logger.warning(f"[ERROR] Could not extract coordinates for {name} | Loc ID: {loc_id}")
                else:
                    logger.info(f"[SUCCESS] Extracted: {name} | Loc ID: {loc_id} | Coordinates: {t_lat}, {t_lon}")
            
            logger.info("[BOOT SEQUENCE] Global Extraction Complete. System is primed.")

        except Exception as e:
            logger.error(f"[CRITICAL] Global Data Pre-load Failure: {e}")

    def get_local_world_data(self, user_lat: float, user_lon: float, radius_m: float = 2000):
        """Filters the pre-loaded global data based on user GPS."""
        logger.info(f"[PROCESS] Initiating local scan for user at {user_lat}, {user_lon} (Radius: {radius_m}m)")
        
        try:
            # Create an efficient lookup for stories indexed by loc_id
            story_lookup = {}
            for s in self.global_stories:
                l_id = s.get("loc_id")
                if l_id not in story_lookup:
                    story_lookup[l_id] = []
                story_lookup[l_id].append(s)

            processed_world = []

            # --- 4. FILTER CACHED LOCATIONS BY DISTANCE ---
            for loc in self.global_locations:
                loc_id = loc.get("id", "UNKNOWN_ID")
                name = loc.get("name", "Unnamed Node")
                
                t_lat = loc.get("lat") or loc.get("latitude")
                t_lon = loc.get("lon") or loc.get("longitude")

                if t_lat is None or t_lon is None:
                    continue

                # Distance calculation using your Haversine formula
                dist_m = calculate_haversine(user_lat, user_lon, t_lat, t_lon)

                # Filter by active "loading" radius
                if dist_m <= radius_m:
                    loc_stories = story_lookup.get(loc_id, [])
                    
                    node = {
                        "id": loc_id,
                        "name": name,
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

            logger.info(f"[COMPLETED] Filtered down to {len(processed_world)} objects within {radius_m}m radius.")
            
            # --- 5. EXPLICIT LOGGING FOR USER SYNC ---
            logger.info(f"📍 [USER LOCATION SYNC] Active Player Coordinates Locked At: Lat {user_lat}, Lon {user_lon}")
            if processed_world:
                logger.info("📦 [PAYLOAD DELIVERY] Beaming the following location nodes to client:")
                for obj in processed_world:
                    logger.info(f"   -> [TARGET] {obj['name']} | Coords: {obj['lat']}, {obj['lon']} | Distance: {obj['distance_meters']}m")
            else:
                logger.info("⚠️ [PAYLOAD DELIVERY] No objects found within scan radius.")

            return processed_world

        except Exception as e:
            logger.error(f"[CRITICAL] Local Data Extraction Failure: {e}")
            return []

# --- INTEGRATION HOOK ---
def load_avis_system():
    URL = "https://ihdllispdbwvwcwxlvhr.supabase.co"
    KEY = "sb_publishable_TbC7C4Gf277RzfQtBd3CTw_M68nRP2P"
    return AvisDataExtractor(URL, KEY)
