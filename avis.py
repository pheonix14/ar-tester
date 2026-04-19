import logging
import math
from supabase import create_client, Client

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AVIS-CORE] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("avis_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in meters between two GPS points using Haversine."""
    R = 6371000  # Radius of Earth in meters
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
        try:
            self.supabase: Client = create_client(url, key)
            logger.info("Supabase Engine Initialized.")
        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            raise

    def get_local_world_data(self, user_lat: float, user_lon: float, radius_m: float = 2000):
        """
        Fetches locations, merges stories, and filters out objects beyond the radius.
        """
        logger.info(f"Extracting local data for coordinates: {user_lat}, {user_lon} (Radius: {radius_m}m)")
        
        try:
            # Fetch base data (If DB gets massive, this should migrate to a Supabase PostGIS RPC call)
            loc_res = self.supabase.table("locations").select("*").execute()
            story_res = self.supabase.table("stories").select("*").execute()

            locations = loc_res.data
            stories = story_res.data

            # Story mapping for O(1) lookup
            story_lookup = {}
            for s in stories:
                l_id = s.get("loc_id")
                if l_id not in story_lookup:
                    story_lookup[l_id] = []
                story_lookup[l_id].append(s)

            final_map_data = []
            for loc in locations:
                target_lat = loc.get("lat")
                target_lon = loc.get("lon")

                # Skip if coordinates are missing
                if target_lat is None or target_lon is None:
                    continue

                # Filter by distance
                distance = calculate_distance(user_lat, user_lon, target_lat, target_lon)
                if distance <= radius_m:
                    loc_id = loc.get("id")
                    loc["lore"] = story_lookup.get(loc_id, [])
                    
                    processed_node = {
                        "id": loc_id,
                        "name": loc.get("name"),
                        "lat": target_lat,
                        "lon": target_lon,
                        "category": loc.get("category"),
                        "reward": loc.get("reward_per_visit"),
                        "icon": loc.get("icon", "treasure"),
                        "stories": loc["lore"],
                        "distance_m": round(distance, 2),
                        "is_legend": any(s.get("is_resident_legend") for s in loc["lore"])
                    }
                    
                    # Ready for location encryption API processing here if needed
                    final_map_data.append(processed_node)

            logger.info(f"Extraction Complete. Yielding {len(final_map_data)} local nodes.")
            return final_map_data

        except Exception as e:
            logger.error(f"Critical Extraction Error: {e}")
            return []
