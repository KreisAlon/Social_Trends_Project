import asyncio
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.manager import TrendManager, DB_PATH

# Instantiate the OOP Manager
manager = TrendManager()


def print_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("\n" + "=" * 100)
    print(f"   🏆 GLOBAL TREND RANKING (Live OOP Stats)")
    print("=" * 100)
    print(f"{'Rank':<4} | {'Platform':<12} | {'Score':<6} | {'Title'}")
    print("-" * 100)

    c.execute('''SELECT source_platform, trend_score, title FROM unified_posts 
                 ORDER BY trend_score DESC LIMIT 15''')

    for i, row in enumerate(c.fetchall(), 1):
        prefix = "🔥" if row[1] > 80 else "  "
        title = row[2][:60] + "..." if len(row[2]) > 60 else row[2]
        print(f"#{i:<3} | {row[0]:<12} | {prefix}{row[1]:<4.1f} | {title}")

    print("=" * 100 + "\n")
    conn.close()


async def job_wrapper():
    await manager.run_collection_cycle()
    print_dashboard()


async def start_system():
    print("\n" + "#" * 60)
    print("      TrendAnalyzer v5.0 - Final OOP Architecture")
    print("#" * 60)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_wrapper, 'interval', minutes=5)
    scheduler.add_job(job_wrapper)
    scheduler.start()

    print(f"--- 🚀 System Running. Collectors: {len(manager.collectors)} ---")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    asyncio.run(start_system())