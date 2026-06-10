import sqlite3
import os

db_path = "c:/Pyfinalfusion/db/local_dev.db"
if not os.path.exists(db_path):
    print("Database does not exist at:", db_path)
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check products table model_name count
        cursor.execute("SELECT DISTINCT model_name, COUNT(*) FROM products GROUP BY model_name ORDER BY model_name")
        rows = cursor.fetchall()
        print("--- DISTINCT model_name in products ---")
        for name, count in rows:
            print(f"{name}: {count} products")
        
        # Check mappings table
        cursor.execute("SELECT id, raw_name, mapped_name FROM model_mappings ORDER BY raw_name")
        mappings = cursor.fetchall()
        print("\n--- MAPPINGS in model_mappings ---")
        for mid, raw, mapped in mappings:
            print(f"ID {mid}: '{raw}' -> '{mapped}'")
            
    except Exception as e:
        print("Error reading database:", e)
    finally:
        conn.close()
