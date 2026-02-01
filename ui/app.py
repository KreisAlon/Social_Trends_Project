import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pyvis.network import Network
import streamlit.components.v1 as components
import os

# Import the GraphBuilder logic
from graph_analyzer import GraphBuilder

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Trend Hunter",
    page_icon="🤖",
    layout="wide"
)

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


def load_data():
    """
    Fetches the latest data from the SQLite database into a Pandas DataFrame.
    """
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT source_platform, title, trend_score, sentiment, raw_score, published_at, url, found_keywords
    FROM unified_posts
    ORDER BY trend_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# --- Main Dashboard Layout ---

st.title("🤖 AI Trends & Network Analysis")
st.markdown("Real-time cross-platform trend analysis engine (GitHub, Mastodon, HackerNews, Dev.to)")

# Load Data
df = load_data()

if df.empty:
    st.warning("⚠️ No data found. Please run 'main.py' to start the data collection cycle.")
else:
    # --- Top Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Posts Tracked", len(df))
    col2.metric("Top Trend Score", f"{df['trend_score'].max():.1f}")
    col3.metric("Avg Sentiment", f"{df['sentiment'].mean():.2f}")

    # Identify the most active platform
    top_platform = df['source_platform'].value_counts().idxmax()
    col4.metric("Dominant Platform", top_platform)

    st.divider()

    # --- Tabs Interface ---
    tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "🕸️ Network Graph", "📈 Sentiment Analysis"])

    # === Tab 1: Leaderboard ===
    with tab1:
        st.subheader("🔥 Top Trending Topics")

        platforms = st.multiselect("Filter by Platform", df['source_platform'].unique(),
                                   default=df['source_platform'].unique())
        filtered_df = df[df['source_platform'].isin(platforms)]

        st.dataframe(
            filtered_df[['source_platform', 'title', 'trend_score', 'sentiment', 'raw_score', 'url']],
            column_config={
                "url": st.column_config.LinkColumn("Link"),
                "trend_score": st.column_config.ProgressColumn(
                    "Trend Score", format="%.1f", min_value=0, max_value=100
                ),
                "sentiment": st.column_config.NumberColumn(
                    "Sentiment", format="%.2f"
                )
            },
            hide_index=True,
            use_container_width=True
        )

    # === Tab 2: Network Graph ===
    with tab2:
        st.subheader("🔍 Keyword Connection Graph")
        st.caption("Visualizing semantic connections between posts based on shared keywords.")

        if st.button("Generate Network Graph"):
            gb = GraphBuilder()
            G = gb.build_graph()

            if G.number_of_nodes() > 0:
                # Initialize PyVis Network
                net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
                net.from_nx(G)

                # --- PHYSICS STABILIZATION FIX ---
                # This configuration stops the "dancing" effect.
                # 1. 'stabilization': Pre-calculates layout before rendering.
                # 2. 'damping': Adds resistance to movement.
                # 3. 'minVelocity': Stops animation when movement is small.
                net.set_options("""
                var options = {
                  "physics": {
                    "barnesHut": {
                      "gravitationalConstant": -4000,
                      "centralGravity": 0.3,
                      "springLength": 95,
                      "springConstant": 0.04,
                      "damping": 0.09,
                      "avoidOverlap": 0.2
                    },
                    "stabilization": {
                      "enabled": true,
                      "iterations": 1000,
                      "updateInterval": 100,
                      "onlyDynamicEdges": false,
                      "fit": true
                    },
                    "minVelocity": 0.75,
                    "solver": "barnesHut"
                  }
                }
                """)

                # Save and Render
                path = os.path.join(CURRENT_DIR, "tmp_network.html")
                net.save_graph(path)

                with open(path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                components.html(source_code, height=600)
            else:
                st.info("Not enough connections found yet to build a graph. Try collecting more data.")

    # === Tab 3: Sentiment & Statistics ===
    with tab3:
        st.subheader("💡 Sentiment & Distribution Analysis")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Sentiment Distribution by Platform**")
            # Using Box Plot to show sentiment spread (Min, Max, Median)
            fig_sent = px.box(df, x="source_platform", y="sentiment", color="source_platform", points="all")
            st.plotly_chart(fig_sent, use_container_width=True)

        with col_b:
            st.markdown("**Trend Score Distribution**")
            fig_hist = px.histogram(df, x="trend_score", nbins=20, title="Trend Score Spread",
                                    color_discrete_sequence=['#3366cc'])
            st.plotly_chart(fig_hist, use_container_width=True)