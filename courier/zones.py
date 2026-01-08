import pandas as pd
import json
import os
import logging

# Configure module logger
logger = logging.getLogger('courier')

# --- 1. CONFIGURATION LOADING ---
def load_config(filename):
    path = os.path.join(os.path.dirname(__file__), "config", filename)
    with open(path, "r") as f:
        return json.load(f)

# Load configurations
METRO_CITIES = load_config("metro_cities.json")
ZONE_E_STATES = load_config("special_states.json")
ALIAS_MAP = load_config("alias_map.json")


# --- 2. DATABASE INITIALIZATION ---
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "pincode_master.csv")

def initialize_pincode_lookup():
    if not os.path.exists(DATA_PATH):
        logger.critical(f"Database not found at {DATA_PATH}")
        return {}

    try:
        temp_df = pd.read_csv(
            DATA_PATH, usecols=["pincode", "office", "state", "district"]
        )
        temp_df.columns = temp_df.columns.str.strip()
        temp_df = temp_df.drop_duplicates(subset=["pincode"], keep="first")
        return temp_df.set_index("pincode").to_dict("index")
    except Exception as e:
        logger.critical(f"Failed to initialize pincode lookup: {e}")
        return {}

PINCODE_LOOKUP = initialize_pincode_lookup()


# --- 3. REFACTORED HELPERS ---
def normalize_name(name: str, type: str = 'state') -> str:
    """
    Normalizes City/State names using alias_map.json.
    Ex: 'Gujarat' -> 'gujrat' (if mapped)
    """
    cleaned = str(name).lower().replace("&", "and").strip()
    
    # Check alias map
    # Handle plural mapping keys
    map_key = type
    if type == "city": map_key = "cities"
    elif type == "state": map_key = "states"
    elif not type.endswith("s"): map_key = type + "s"
    
    section = ALIAS_MAP.get(map_key, {})

    # Invert the map for easier lookup? 
    # Or just iterate. Since list is small, iteration is fine.
    # But for O(1), we should probably index this differently or just loop.
    # For now, simplistic loop check is robust enough for small maps.
    
    # Check if cleaned name matches a key (standard name)
    if cleaned in section:
        return cleaned # It's already standard (or at least a key)
        
    # Check if it's in values
    for standard, aliases in section.items():
        if cleaned == standard or cleaned in aliases:
            return standard
            
    return cleaned

def get_location_details(pincode: int):
    data = PINCODE_LOOKUP.get(pincode)
    if data:
        return {
            "city": normalize_name(data["office"], "city"),
            "state": normalize_name(data["state"], "state"),
            "district": normalize_name(data["district"], "city"), # Approximate district as city type
            "original_city": str(data["office"]).lower().strip(),
            "original_state": str(data["state"]).lower().strip()
        }
    return None

def is_metro(location_dict):
    city = location_dict["city"]
    district = location_dict["district"]
    # METRO_CITIES are assumed to be normalized or lowercase in config
    return any(metro in city or metro in district for metro in METRO_CITIES)



# --- 5. CSV REGION LOGIC (Generic) ---
CSV_CACHE = {}

def get_csv_region_details(pincode: int, csv_filename: str = "BlueDart_Serviceable Pincodes.csv"):
    global CSV_CACHE
    
    # Key by filename
    if csv_filename not in CSV_CACHE:
        path = os.path.join(os.path.dirname(__file__), "data", csv_filename)
        
        # Fallback to base dir if not found (for robustness)
        if not os.path.exists(path):
             # Try assuming path is relative to project root if needed, but let's stick to courier/data
             pass

        if not os.path.exists(path):
             logger.error(f"CSV not found at {path}")
             CSV_CACHE[csv_filename] = {}
        else:
            try:
                 df = pd.read_csv(path)
                 # Strip whitespace
                 df.columns = df.columns.str.strip()
                 df_obj = df.select_dtypes(['object'])
                 df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())
                 # Cache valid pincodes
                 # Pincode column might be "Pincode" or "PINCODE" - standardize?
                 # Example CSV has "PINCODE". 
                 if "PINCODE" in df.columns:
                    CSV_CACHE[csv_filename] = df.set_index("PINCODE").to_dict("index")
                 elif "Pincode" in df.columns:
                    CSV_CACHE[csv_filename] = df.set_index("Pincode").to_dict("index")
                 else:
                     # Fallback to first column?
                     CSV_CACHE[csv_filename] = df.set_index(df.columns[0]).to_dict("index")
                     
            except Exception as e:
                 logger.error(f"Error loading CSV {path}: {e}")
                 CSV_CACHE[csv_filename] = {}

    return CSV_CACHE[csv_filename].get(pincode)

# --- 4. UNIFIED ZONE LOGIC (UPDATED) ---
def get_zone(source_pincode: int, dest_pincode: int, carrier_config: dict):
    """
    Determines the Zone Identifier based on Carrier Logic.
    Returns: (zone_id, description, logic_type)
    """
    s_loc = get_location_details(source_pincode)
    d_loc = get_location_details(dest_pincode)

    routing = carrier_config.get("routing_logic", {})
    logic_type = routing.get("type")

    # --- LOGIC 4: CSV REGION (Blue Dart / Others) ---
    if logic_type == "pincode_region_csv":
         csv_file = routing.get("csv_file", "BlueDart_Serviceable Pincodes.csv")
         details = get_csv_region_details(dest_pincode, csv_file)
         if not details:
              return None, "Pincode Not Found in Carrier DB", logic_type
         
         if details.get("Embargo") == "Y":
              return None, "Embargo (Not Servicable)", logic_type

         # Return the Region as Zone ID (e.g., "NORTH", "SOUTH")
         # And include the full details for the engine to use (EDL, etc.)
         # We cheat a bit and return the details dict as part of the zone_id or handle it in engine?
         # Standard signature returns: zone_id, zone_desc, logic_type.
         # The engine calls this. We will return the Region String, but we need to pass EDL info provided by this lookup.
         # BUT `get_zone` returns simple strings usually. 
         # We can return a tuple or dict as zone_id? Or let engine re-fetch?
         # Engine calls `zones.get_zone`. 
         # Let's return the Region string, but also attach the metadata to the carrier_data in the engine? 
         # No, `get_zone` is clean. 
         # We'll modify `engine.py` to call `get_bluedart_details` if needed, OR we return the details in the ID.
         # Let's return the details dict as the ID? No, that breaks simple logic.
         # We will return the Region Name.
         # The Engine will have to do a specific check or we return a rich object.
         # Let's return (RegionName, DetailsDict) as zone_id? 
         # Engine expects zone_id to lookup rates. Rates key is "NORTH". 
         # So zone_id MUST be "NORTH".
         
         # We will make the Engine responsible for fetching extra details if logic_type is csv, 
         # OR we pass it in description? No.
         
         # Let's trust the engine update step to call `get_bluedart_details` again? 
         # Iterate implementation: Engine calls `zones.get_zone`. 
         # If `logic_type` is `pincode_region_csv`, we assume we need to re-fetch details in engine for EDL? 
         # Or we optimize and cache. Since we cache the DF, it's fast.
         
         return details.get("REGION"), f"Region: {details.get('REGION')}", logic_type

    if not s_loc or not d_loc:
        return None, "Invalid Pincode", None
    
    # --- LOGIC 1: CITY-TO-CITY via CSV (e.g., ACPL) ---
    # ACPL routes are bidirectional: Bhiwandi <-> Serviceable City
    # Uses ACPL_Serviceable_Pincodes.csv for pincode-to-city mapping
    if routing.get("is_city_specific"):
        csv_file = routing.get("pincode_csv", "ACPL_Serviceable_Pincodes.csv")
        hub_city = routing.get("hub_city", "bhiwandi")
        
        # Look up both pincodes in the CSV
        source_details = get_csv_region_details(source_pincode, csv_file)
        dest_details = get_csv_region_details(dest_pincode, csv_file)
        
        # Get city names from CSV (column is 'CITY')
        source_city = source_details.get("CITY", "").lower() if source_details else None
        dest_city = dest_details.get("CITY", "").lower() if dest_details else None
        
        source_is_hub = source_city == hub_city if source_city else False
        dest_is_hub = dest_city == hub_city if dest_city else False
        
        # Validate that we can identify both cities AND one of them is the hub
        if source_city and dest_city and (source_is_hub or dest_is_hub):
            # Return the NON-HUB city as zone_id for rate card lookup
            # Rate card is keyed by serviceable cities (e.g., 'gandhidham'), not the hub
            # This enables bidirectional routing: both Bhiwandi->Gandhidham and Gandhidham->Bhiwandi
            # will return 'gandhidham' as the zone_id
            serviceable_city = dest_city if source_is_hub else source_city
            return serviceable_city, f"City Route: {source_city} <-> {dest_city}", "city_specific"
        
        return None, "Cities not identified in service list", "city_specific"

    # --- LOGIC 2: CARRIER SPECIFIC ZONE MATRIX (e.g., V-Trans) ---
    zone_map = carrier_config.get("zone_mapping")
    if zone_map:
        # 1. Map Source State/City to Origin Zone
        
        def find_mapped_zone(loc_details, mapping):
            # Check State
            state = loc_details["state"]
            # We need to find if 'state' matches a key in 'mapping' considering case-insensitivity
            # mapping keys might be "Maharashtra" (Title Case).
            for key, code in mapping.items():
                if normalize_name(key, "state") == state:
                    return code
            return None

        origin_zone = find_mapped_zone(s_loc, zone_map)
        dest_zone = find_mapped_zone(d_loc, zone_map)

        if origin_zone and dest_zone:
            # We return the tuple (Origin, Dest) to be looked up in matrix by engine
            return (origin_zone, dest_zone), f"Matrix: {origin_zone}->{dest_zone}", "matrix"
            
        return "z_d", "Zone Mapping Failed (Defaulting)", "matrix" # Fallback or Error?

    # --- LOGIC 3: STANDARD ZONAL (Shadowfax/Courier) ---
    # Existing Logic
    if s_loc["state"] in ZONE_E_STATES or d_loc["state"] in ZONE_E_STATES:
         return "z_f", "Zone E (North-East & J&K)", "standard"
    
    if is_metro(s_loc) and is_metro(d_loc):
        return "z_a", "Zone A (Metropolitan)", "standard"
        
    if s_loc["state"] == d_loc["state"]:
        return "z_b", "Zone B (Regional)", "standard"
        
    if s_loc["city"] != d_loc["city"]:
        return "z_c", "Zone C (Intercity)", "standard" # Note: logic check might need tuning vs z_d
        
    return "z_d", "Zone D (Pan-India)", "standard"

# --- 5. LEGACY WRAPPER (For Backward Compatibility) ---
def get_zone_column(source_pincode: int, dest_pincode: int):
    """
    Legacy wrapper for existing views that expect a simple (zone_id, description) tuple.
    Uses 'Standard' logic by default.
    """
    # Dummy config to trigger Standard Zonal Logic
    dummy_config = {
        "routing_logic": {
            "is_city_specific": False
            # No zone_mapping implies standard logic fallback
        }
    }
    
    zone_id, desc, logic = get_zone(source_pincode, dest_pincode, dummy_config)
    return zone_id, desc

