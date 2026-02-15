import sqlite3


def clean_database():
    """
    Utility script to clean low-quality data before presentation.
    """
    db_path = "trends_project.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"--- 🧹 Cleaning Database: {db_path} ---")

    # 1. Remove Mastodon spam (0 likes)
    cursor.execute("DELETE FROM unified_posts WHERE source_platform = 'Mastodon' AND raw_score < 1")
    print(f"✅ Removed {cursor.rowcount} low-quality Mastodon posts.")

    # 2. Remove very old data (keep only 2024-2026)
    cursor.execute("DELETE FROM unified_posts WHERE published_at < '2024-01-01'")
    print(f"✅ Removed {cursor.rowcount} outdated legacy posts.")

    conn.commit()
    conn.close()
    print("--- ✨ Database Optimized. ---")


if __name__ == "__main__":
    clean_database()