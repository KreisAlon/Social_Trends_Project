import asyncio
import sys
import os
import httpx
from datetime import datetime

# --- System Path Setup ---
# This ensures Python can locate the 'database' and 'collectors' packages
# even when running the script from different directory levels.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Internal Imports ---
import config
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
    Executes a single data collection, storage, vector embedding generation,
    and normalization cycle.

    Args:
        cycle_num (int): The current iteration number of the scheduler.
        start_time (str): Timestamp string for logging.
    """
    print(f"\n" + "=" * 80)
    print(f"🕒 CYCLE #{cycle_num} STARTING | TIME: {start_time}")
    print("=" * 80)

    # Initialize Database Manager (DAL - Data Access Layer)
    # This now includes loading the Sentence-Transformers NLP model
    db_manager = TrendManager()

    # Initialize Data Collectors with the shared configuration
    collectors = [
        GitHubCollector(config.COLLECTORS_CONFIG),
        HackerNewsCollector(config.COLLECTORS_CONFIG),
        MastodonCollector(config.COLLECTORS_CONFIG),
        DevToCollector(config.COLLECTORS_CONFIG)
    ]

    all_posts = []

    try:
        # 1. Collect Data
        # Using a shared AsyncClient for better performance and connection pooling
        async with httpx.AsyncClient(timeout=30.0, headers={'User-Agent': 'TrendAnalyzer/5.0'}) as client:
            for collector in collectors:
                try:
                    # Polymorphic call: each collector implements .collect() differently
                    posts = await collector.collect(client)
                    all_posts.extend(posts)
                except Exception as e:
                    print(f"⚠️ Warning: Collector '{collector.platform_name}' failed: {e}")

        # 2. Process & Save to SQLite (Includes Semantic Embeddings generation)
        if all_posts:
            added_count = db_manager.save_posts(all_posts)
            print(f">>> 💾 Saved {added_count} new unique items to the database.")

        # 3. Normalization (Z-Score Algorithm)
        print(">>> 🧠 Triggering decentralized normalization logic...")
        for collector in collectors:
            collector.recalculate_platform_stats()

        print(f">>> ✅ Cycle #{cycle_num} Complete. Processed {len(all_posts)} total fetched items.")

        # 4. Display Live Leaderboard (Console Output)
        print("\n" + "-" * 100)
        print(f"    🏆 GLOBAL TREND RANKING (Cycle #{cycle_num})")
        print("-" * 100)
        print(f"{'Rank':<5} | {'Platform':<12} | {'Score':<6} | {'Title'}")

        # Fetch all posts and display the top 15 based on the normalized trend_score
        all_db_posts = db_manager.get_all_posts()
        top_posts = all_db_posts[:15] if all_db_posts else []

        for i, post in enumerate(top_posts, 1):
            title = post['title'] if post['title'] else "No Title"
            # Format the output to fit nicely in the console
            print(f"#{i:<4} | {post['source_platform']:<12} | {post['trend_score']:>6.1f} | {title[:60]}...")
        print("-" * 100)

    except Exception as e:
        print(f"❌ Critical Error during cycle execution: {e}")


async def start_scheduler():
    """
    Main loop that runs the collector indefinitely based on the configured interval.
    Acts as the always-on server engine.
    """
    print("\n" + "#" * 60)
    print(f"      TrendAnalyzer v5.0 - Semantic AI Edition")
    print(f"      🔄 Refresh Interval: {REFRESH_INTERVAL_MINUTES} Minutes")
    print("#" * 60)

    cycle_counter = 1

    while True:
        try:
            # Get current time formatted as HH:MM:SS
            current_time = datetime.now().strftime("%H:%M:%S")

            # Execute the cycle
            await run_cycle(cycle_counter, current_time)

            # Sleep until the next cycle
            print(
                f"\n[Scheduler] 💤 Cycle #{cycle_counter} finished. Sleeping for {REFRESH_INTERVAL_MINUTES} minutes...")
            cycle_counter += 1
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            # Allows clean exit via Ctrl+C without throwing a traceback
            print("\n🛑 Stopping Scheduler manually...")
            break
        except Exception as e:
            # Error resilience: If the loop crashes, wait 60s and retry instead of terminating the server
            print(f"Unexpected Scheduler Error: {e}")
            print("Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        # Start the async event loop
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print("\n👋 System Shutdown.")