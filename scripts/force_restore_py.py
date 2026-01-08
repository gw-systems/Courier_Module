import os
import sys
import shutil
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def count_orders(db_path):
    if not os.path.exists(db_path):
        return -1
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM orders")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"Error checking {db_path}: {e}")
        return -2

def restore_db():
    root_db = BASE_DIR / "logistics.db"
    dest_db = BASE_DIR / "data" / "logistics.db"
    
    print(f"Checking Root DB: {root_db}")
    root_count = count_orders(root_db)
    print(f"  - Orders: {root_count}")
    
    if root_count > 10: # Threshold to verify it's the 'good' one
        print("Root DB appears to be the correct backup.")
        print(f"Copying to {dest_db}...")
        try:
            shutil.copy2(root_db, dest_db)
            print("Copy successful.")
            
            dest_count = count_orders(dest_db)
            print(f"Destination Orders now: {dest_count}")
        except Exception as e:
            print(f"Copy FAILED: {e}")
    else:
        print("Root DB does NOT have enough orders (expected ~34). Aborting overwrite.")
        print(f"Current Destination Orders: {count_orders(dest_db)}")

if __name__ == "__main__":
    restore_db()
