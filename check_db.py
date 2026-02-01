import sqlite3
import pandas as pd
import os

# מציאת הנתיב לקובץ ה-DB בתיקייה הנוכחית
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

print(f"📂 Looking for DB at: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print("❌ Error: Database file not found!")
else:
    print("✅ Database found.")
    try:
        conn = sqlite3.connect(DB_PATH)
        # שליפת כל הפוסטים של מסטודון (בלי סינון של ציון)
        query = "SELECT title, raw_score, trend_score FROM unified_posts WHERE source_platform = 'Mastodon' ORDER BY trend_score DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            print(f"\n✅ Found {len(df)} Mastodon posts in DB:")
            print(df)
        else:
            print("\n⚠️  No Mastodon posts found in DB (maybe they were filtered out?).")

    except Exception as e:
        print(f"Error: {e}")