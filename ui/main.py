import asyncio
import sys
import os
from datetime import datetime  # Imported for timestamp logging

# --- CRITICAL PATH FIX ---
# This ensures Python can locate the 'database' and 'collectors' packages
# even when running the script from inside the 'ui' directory.
current_dir = os.path.dirname(os.path.abspath(__file__))  # ui/
project_root = os.path.dirname(current_dir)  # Social_Trends_Project/
sys.path.append(project_root)
# -------------------------

from database.manager import TrendManager
from collectors.github import GitHubCollector
from collectors.hacker_news import HackerNewsCollector
from collectors.mastodon import MastodonCollector
from collectors.devto import DevToCollector

# --- Configuration ---
# Set the time interval between data collection cycles (in minutes)
REFRESH_INTERVAL_MINUTES = 10
REFRESH_INTERVAL_SECONDS = REFRESH_INTERVAL_MINUTES * 60


async def run_cycle(cycle_num, start_time):
    """
    Executes a single data collection, storage, and normalization cycle.

    Args:
        cycle_num (int): The current iteration number of the scheduler.
        start_time (str): Timestamp string for logging.
    """
    print(f"\n" + "=" * 80)
    print(f"🕒 CYCLE #{cycle_num} STARTING | TIME: {start_time}")
    print("=" * 80)

    # Initialize Database Manager (DAL)
    db_manager = TrendManager()

    # Initialize Data Collectors
    collectors = [
        GitHubCollector(),
        HackerNewsCollector(),
        MastodonCollector(),
        DevToCollector()
    ]

    # 1. Collect Data (Concurrent Execution)
    import httpx
    all_posts = []

    try:
        # Using a shared AsyncClient for better performance and connection pooling
        async with httpx.AsyncClient(timeout=20.0, headers={'User-Agent': 'TrendAnalyzer/5.0'}) as client:
            for collector in collectors:
                try:
                    # Polymorphic call: each collector implements .collect() differently
                    posts = await collector.collect(client)
                    all_posts.extend(posts)
                except Exception as e:
                    print(f"⚠️ Warning: Collector '{collector.platform_name}' failed: {e}")

        # 2. Save Raw Data to SQLite
        if all_posts:
            db_manager.save_posts(all_posts)

        # 3. Normalization (Z-Score Algorithm)
        print(">>> 🧠 Triggering decentralized normalization logic...")
        for collector in collectors:
            collector.recalculate_platform_stats()

        print(f">>> ✅ Cycle #{cycle_num} Complete. {len(all_posts)} new items processed.")

        # 4. Display Live Leaderboard (Console Output)
        print("\n" + "-" * 100)
        print(f"    🏆 GLOBAL TREND RANKING (Cycle #{cycle_num})")
        print("-" * 100)
        print(f"{'Rank':<5} | {'Platform':<12} | {'Score':<6} | {'Title'}")

        top_posts = db_manager.get_top_trends(limit=15)
        for i, post in enumerate(top_posts, 1):
            # Handle potential empty titles safely
            title = post['title'] if post['title'] else "No Title"
            print(f"#{i:<4} | {post['source_platform']:<12} | {post['trend_score']:>6.1f} | {title[:60]}")
        print("-" * 100)

    except Exception as e:
        print(f"❌ Critical Error during cycle execution: {e}")


async def start_scheduler():
    """
    Main loop that runs the collector indefinitely based on the configured interval.
    """
    print("\n" + "#" * 60)
    print(f"      TrendAnalyzer v5.0 - Always-On Server Mode")
    print(f"      🔄 Refresh Interval: {REFRESH_INTERVAL_MINUTES} Minutes")
    print("#" * 60)

    cycle_counter = 1  # Initialize cycle counter

    while True:
        try:
            # Get current time formatted as HH:MM:SS
            current_time = datetime.now().strftime("%H:%M:%S")

            # Execute the cycle
            await run_cycle(cycle_counter, current_time)

            # Calculate next run time for log display
            print(
                f"\n[Scheduler] 💤 Cycle #{cycle_counter} finished. Sleeping for {REFRESH_INTERVAL_MINUTES} minutes...")

            cycle_counter += 1  # Increment counter for next run

            # Sleep until next cycle
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            # Allows clean exit via Ctrl+C
            print("\n🛑 Stopping Scheduler manually...")
            break
        except Exception as e:
            # Error resilience: If the loop crashes, wait 60s and retry instead of terminating
            print(f"Unexpected Scheduler Error: {e}")
            print("Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        # Start the async event loop
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print("\n👋 System Shutdown.")