import asyncio
import sys
import os
import httpx
import textwrap
from datetime import datetime

# --- System Path Setup ---
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
REFRESH_INTERVAL_MINUTES = 10
REFRESH_INTERVAL_SECONDS = REFRESH_INTERVAL_MINUTES * 60


async def run_cycle(cycle_num, start_time):
    """
    Executes a single data collection cycle, including storage,
    AI embedding generation, and cross-platform normalization.
    """
    print(f"\n" + "=" * 80)
    print(f"🕒 CYCLE #{cycle_num} STARTING | TIME: {start_time}")
    print("=" * 80)

    # Initialize Database Manager
    db_manager = TrendManager()

    # Initialize Data Collectors
    collectors = [
        GitHubCollector(),
        HackerNewsCollector(),
        MastodonCollector(),
        DevToCollector()
    ]

    all_posts = []

    try:
        async with httpx.AsyncClient(timeout=30.0, headers={'User-Agent': 'TrendAnalyzer/5.0'}) as client:
            # 1. Ingest Data from all platforms
            for collector in collectors:
                platform_posts = await collector.collect(client)
                all_posts.extend(platform_posts)

            # 2. Save new unique items and generate semantic embeddings
            new_count = db_manager.save_posts(all_posts)
            print(f">>> 💾 Saved {new_count} new unique items to the database.")

            # 3. Trigger statistical normalization logic
            print(">>> 🧠 Triggering decentralized normalization logic...")
            for collector in collectors:
                collector.recalculate_platform_stats()

        # 4. Data Health Report
        db_manager.get_db_stats()

        # 5. Final Output - Reporting Results in a formatted table
        print(f">>> ✅ Cycle #{cycle_num} Complete. Total fetched items: {len(all_posts)}")

        print("\n" + "-" * 100)
        print(f"    🏆 GLOBAL TREND RANKING (Cycle #{cycle_num})")
        print("-" * 100)
        print(f"{'Rank':<5} | {'Platform':<12} | {'Score':<6} | {'Title'}")
        print("-" * 100)

        # Fetch top 15 trends from the database
        top_posts = db_manager.get_all_posts()[:15]

        for i, post in enumerate(top_posts, 1):
            title = post.get('title', 'No Title').replace('\n', ' ')

            # Use textwrap for smart shortening without breaking words
            display_title = textwrap.shorten(title, width=100, placeholder="...")

            print(f"#{i:<4} | {post['source_platform']:<12} | {post['trend_score']:>6.1f} | {display_title}")
            print("-" * 100)

    except Exception as e:
        print(f"❌ Critical Error during cycle execution: {e}")


async def start_scheduler():
    """
    Main scheduler loop that keeps the engine running in intervals.
    """
    print("\n" + "#" * 60)
    print(f"      TrendAnalyzer v5.0 - Semantic AI Edition")
    print(f"      🔄 Refresh Interval: {REFRESH_INTERVAL_MINUTES} Minutes")
    print("#" * 60)

    cycle_counter = 1

    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            await run_cycle(cycle_counter, current_time)

            print(
                f"\n[Scheduler] 💤 Cycle #{cycle_counter} finished. Sleeping for {REFRESH_INTERVAL_MINUTES} minutes...")
            cycle_counter += 1
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n🛑 Stopping Scheduler manually...")
            break
        except Exception as e:
            print(f"Unexpected Scheduler Error: {e}")
            print("Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print("\n👋 System Shutdown.")