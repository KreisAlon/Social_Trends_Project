import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pyvis.network import Network
import streamlit.components.v1 as components
import os
from collections import Counter

# Custom Import
from graph_analyzer import GraphBuilder

# Page Config
st.set_page_config(page_title="AI Trend Hunter", page_icon="🤖", layout="wide")

# Path Config
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    # We load found_keywords to find the common stories
    query = """
    SELECT source_platform, title, trend_score, sentiment, raw_score, url, found_keywords, content
    FROM unified_posts
    ORDER BY trend_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_trend_stories(df):
    """
    Identifies major topics and groups posts from different platforms under them.
    """
    # 1. Collect all keywords from top posts
    all_keywords = []
    top_df = df.head(50)  # Analyze top 50 posts for trends

    for ks in top_df['found_keywords']:
        if ks:
            # Clean and split
            words = [w.strip().lower() for w in ks.split(',')]
            # Filter generic words
            words = [w for w in words if w not in ['ai', 'the', 'to', 'a', 'of', 'in', 'for', 'new', 'model', 'data']]
            all_keywords.extend(words)

    # 2. Find most common topics
    common_topics = [word for word, count in Counter(all_keywords).most_common(10) if count > 1]

    stories = []
    for topic in common_topics:
        # Find best post for this topic per platform
        topic_cluster = {
            "topic": topic.upper(),
            "GitHub": None,
            "Hacker News": None,
            "Mastodon": None,
            "Dev.to": None
        }

        # Filter dataframe for this topic
        mask = df['found_keywords'].str.contains(topic, case=False, na=False)
        topic_df = df[mask]

        # Check if we have at least 2 different platforms (Real Cross-Platform)
        unique_platforms = topic_df['source_platform'].unique()
        if len(unique_platforms) < 2:
            continue

            # Pick the highest scoring post for each platform
        for platform in unique_platforms:
            best_post = topic_df[topic_df['source_platform'] == platform].iloc[0]
            topic_cluster[platform] = best_post

        stories.append(topic_cluster)

    return stories


# --- UI Header ---
st.title("🤖 AI Trend Hunter")
st.markdown("### 🚀 Cross-Platform Intelligence Engine")

df = load_data()

if df.empty:
    st.error("⚠️ No data found. Please run 'python ui/main.py' first.")
else:
    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Posts Analyzed", len(df))
    col2.metric("Top Trend Score", f"{df['trend_score'].max():.1f}")
    col3.metric("Global Sentiment", f"{df['sentiment'].mean():.2f}")
    col4.metric("Active Platforms", len(df['source_platform'].unique()))

    st.divider()

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard", "🕸️ Network Graph", "🧩 Trend Stories (NEW)"])

    # === TAB 1: Leaderboard ===
    with tab1:
        st.subheader("Global Trend Ranking (Z-Score Normalized)")
        st.caption("Comparing 'Apples to Oranges' using statistical normalization.")

        st.dataframe(
            df[['source_platform', 'title', 'trend_score', 'sentiment', 'url']],
            column_config={
                "url": st.column_config.LinkColumn("Link"),
                "trend_score": st.column_config.ProgressColumn("Trend Score", format="%.1f", min_value=0,
                                                               max_value=100),
                "sentiment": st.column_config.NumberColumn("Sentiment", format="%.2f")
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )

    # === TAB 2: Network Graph ===
    with tab2:
        col_graph, col_analyze = st.columns([3, 1])

        if 'graph_obj' not in st.session_state:
            st.session_state['graph_obj'] = None

        with col_graph:
            if st.button("Generate Semantic Graph"):
                gb = GraphBuilder()
                G = gb.build_graph()
                st.session_state['graph_obj'] = G

                if G.number_of_nodes() > 0:
                    net = Network(height="500px", width="100%", bgcolor="#1E1E1E", font_color="white")
                    net.from_nx(G)
                    net.toggle_physics(False)  # Static layout
                    path = os.path.join(CURRENT_DIR, "network.html")
                    net.save_graph(path)
                    with open(path, 'r', encoding='utf-8') as f:
                        components.html(f.read(), height=520)
                else:
                    st.warning("Not enough data for graph.")

        with col_analyze:
            st.markdown("### 🕵️ Connection Inspector")
            G = st.session_state['graph_obj']
            if G and G.number_of_nodes() > 0:
                node_map = {data['label']: node_id for node_id, data in G.nodes(data=True)}
                selected = st.selectbox("Select Node:", list(node_map.keys()))
                if selected:
                    nid = node_map[selected]
                    neighbors = list(G.neighbors(nid))
                    if neighbors:
                        st.write(f"Connected to **{len(neighbors)}** items via keywords:")
                        for n in neighbors:
                            data = G.nodes[n]
                            edge = G.get_edge_data(nid, n)
                            kw = edge['title'].replace("Shared: ", "")
                            st.caption(f"🔗 {data['group']}: {kw}")
            else:
                st.info("Generate graph to inspect specific connections.")

    # === TAB 3: TREND STORIES
    with tab3:
        st.subheader("🧩 Cross-Platform Storyboard")
        st.markdown("""
        This engine automatically detects **topics** that are being discussed simultaneously across different platforms.
        It proves that a trend is not isolated to one community.
        """)

        stories = get_trend_stories(df)

        if not stories:
            st.info("No strong cross-platform stories detected yet. Try collecting more data.")

        for story in stories:
            with st.container():
                st.markdown(f"### 🔥 Topic: {story['topic']}")

                # Dynamic columns based on what we found
                cols = st.columns(3)

                # Column 1: The Code (GitHub)
                with cols[0]:
                    st.markdown("**🛠️ The Code (GitHub)**")
                    post = story.get('GitHub')
                    if post is not None:
                        st.info(f"[{post['title']}]({post['url']})\n\n⭐ Stars: {post['raw_score']}")
                    else:
                        st.markdown("*(No specific repo found)*")

                # Column 2: The News (Hacker News)
                with cols[1]:
                    st.markdown("**📰 The News (Hacker News)**")
                    post = story.get('Hacker News')
                    if post is not None:
                        st.warning(f"[{post['title']}]({post['url']})\n\n💬 Score: {post['raw_score']}")
                    else:
                        st.markdown("*(No major discussion)*")

                # Column 3: The Community (Mastodon/Dev.to)
                with cols[2]:
                    st.markdown("**🗣️ The Community (Social)**")
                    post_m = story.get('Mastodon')
                    post_d = story.get('Dev.to')

                    if post_m is not None:
                        st.success(f"**Mastodon:** [{post_m['title']}]({post_m['url']})")
                    if post_d is not None:
                        st.success(f"**Dev.to:** [{post_d['title']}]({post_d['url']})")

                    if post_m is None and post_d is None:
                        st.markdown("*(No social chatter)*")

                st.divider()