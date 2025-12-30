import pandas as pd
import json
import os

# --- 1. CONFIGURATION LOADING ---
def load_config(filename):
    path = os.path.join(os.path.dirname(__file__), "config", filename)
    with open(path, "r") as f:
        return json.load(f)

METRO_CITIES = load_config("metro_cities.json")
ZONE_E_STATES = load_config("special_states.json")

# --- 2. OPTIMIZED DATABASE INITIALIZATION ---
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "pincode_master.csv")

def initialize_pincode_lookup():
    """
    Loads the CSV into a dictionary.
    Added .drop_duplicates() to ensure the index is unique.
    """
    if not os.path.exists(DATA_PATH):
        print(f"CRITICAL ERROR: Database not found at {DATA_PATH}")
        return {}

    try:
        # 1. Load data
        temp_df = pd.read_csv(DATA_PATH, usecols=['pincode', 'office', 'state', 'district'])
        temp_df.columns = temp_df.columns.str.strip()

        # 2. Industry-Grade Data Cleaning
        # Remove duplicates based on the 'pincode' column, keeping the first occurrence
        initial_count = len(temp_df)
        temp_df = temp_df.drop_duplicates(subset=['pincode'], keep='first')
        final_count = len(temp_df)

        if initial_count > final_count:
            print(f"INFO: Removed {initial_count - final_count} duplicate pincodes from database.")

        # 3. Convert to dictionary
        return temp_df.set_index('pincode').to_dict('index')

    except FileNotFoundError:
        print(f"CRITICAL ERROR: Pincode database missing at {DATA_PATH}")
        raise RuntimeError(f"Required database file not found: {DATA_PATH}")
    except pd.errors.ParserError as e:
        print(f"CRITICAL ERROR: Corrupted CSV file: {e}")
        raise RuntimeError(f"Failed to parse pincode database: {e}")
    except KeyError as e:
        print(f"CRITICAL ERROR: Missing required column in CSV: {e}")
        raise RuntimeError(f"Database schema error - missing column: {e}")
    except Exception as e:
        print(f"CRITICAL ERROR: Unexpected error loading pincode database: {e}")
        raise RuntimeError(f"Failed to initialize pincode lookup: {e}")

# Initialize the global lookup table
PINCODE_LOOKUP = initialize_pincode_lookup()

# --- 3. REFACTORED HELPERS ---
def normalize_state(state: str):
    return str(state).lower().replace("&", "and").strip()

def get_location_details(pincode: int):
    """
    Replaces slow Pandas filtering with a dictionary hash-map lookup.
    """
    data = PINCODE_LOOKUP.get(pincode)
    if data:
        return {
            "city": str(data['office']).lower().strip(),
            "state": normalize_state(data['state']),
            "district": str(data['district']).lower().strip()
        }
    return None

def is_metro(location_dict):
    # Ensure we are comparing lowercase to lowercase
    city_name = location_dict['city'].lower()
    district_name = location_dict['district'].lower()
    # METRO_CITIES in your config should already be lowercase
    return any(metro in city_name or metro in district_name for metro in METRO_CITIES)

# --- 4. ZONE ASSIGNMENT LOGIC ---
def get_zone_column(source_pincode: int, dest_pincode: int):
    s_loc = get_location_details(source_pincode)
    d_loc = get_location_details(dest_pincode)

    if not s_loc or not d_loc:
        return "z_d", "Zone D (National - Pincode Not Found)"

    # Priority 1: Zone E (Special States)
    if s_loc['state'] in ZONE_E_STATES or d_loc['state'] in ZONE_E_STATES:
        return "z_f", "Zone E (Special/NE/J&K)"

    # Priority 2: Zone A (Local)
    if s_loc['city'] == d_loc['city']:
        return "z_a", "Zone A (Local)"

    # Priority 3: Zone B (Regional)
    if s_loc['state'] == d_loc['state']:
        return "z_b", "Zone B (Regional/Same State)"

    # Priority 4: Zone C (Metro to Metro)
    if is_metro(s_loc) and is_metro(d_loc):
        return "z_c", "Zone C (Metro to Metro)"

    # Priority 5: Zone D Fallback
    return "z_d", "Zone D (National/Rest of India)"