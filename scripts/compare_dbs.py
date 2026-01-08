import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def check_db(path):
    print(f"Checking {path}...")
    if not os.path.exists(path):
        print("  - File not found.")
        return
        
    size = os.path.getsize(path)
    print(f"  - Size: {size} bytes")
    
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        
        # Check Couriers
        try:
            cur.execute("SELECT count(*) FROM couriers")
            courier_count = cur.fetchone()[0]
            print(f"  - Couriers: {courier_count}")
        except sqlite3.OperationalError:
            print("  - Couriers table missing")

        # Check Orders
        try:
            cur.execute("SELECT count(*) FROM orders")
            order_count = cur.fetchone()[0]
            print(f"  - Orders: {order_count}")
        except sqlite3.OperationalError:
            print("  - Orders table missing")
            
        conn.close()
    except Exception as e:
        print(f"  - Error opening DB: {e}")

def main():
    root_db = BASE_DIR / "logistics.db"
    data_db = BASE_DIR / "data" / "logistics.db"
    
    check_db(root_db)
    check_db(data_db)

if __name__ == "__main__":
    main()
