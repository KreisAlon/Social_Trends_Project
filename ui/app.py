import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pyvis.network import Network
import streamlit.components.v1 as components
import os

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
    query = """
    SELECT source_platform, title, trend_score, sentiment, raw_score, url, found_keywords
    FROM unified_posts
    ORDER BY trend_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# --- UI Header ---
st.title("🤖 AI Trends & Network Analysis")
st.markdown("### Real-time Cross-Platform Intelligence")
st.markdown("Aggregating: **GitHub**, **Hacker News**, **Mastodon**, **Dev.to**")

df = load_data()

if df.empty:
    st.error("⚠️ No data found. Please run 'python ui/main.py' first.")
else:
    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Posts", len(df))
    col2.metric("Highest Trend Score", f"{df['trend_score'].max():.1f}")
    col3.metric("Average Sentiment", f"{df['sentiment'].mean():.2f}")
    col4.metric("Dominant Platform", df['source_platform'].value_counts().idxmax())

    st.divider()

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard", "🕸️ Semantic Graph", "📊 Analytics"])

    # === TAB 1: Leaderboard ===
    with tab1:
        st.subheader("Global Trend Ranking")
        platforms = st.multiselect("Filter by Platform", df['source_platform'].unique(),
                                   default=df['source_platform'].unique())
        filtered_df = df[df['source_platform'].isin(platforms)]

        st.dataframe(
            filtered_df[['source_platform', 'title', 'trend_score', 'sentiment', 'url']],
            column_config={
                "url": st.column_config.LinkColumn("Direct Link"),
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
        col_graph, col_legend = st.columns([3, 1])
        with col_graph:
            st.subheader("Keyword Connection Network")
            if st.button("Generate Static Graph"):
                gb = GraphBuilder()
                G = gb.build_graph()

                if G.number_of_nodes() > 0:
                    net = Network(height="600px", width="100%", bgcolor="#1E1E1E", font_color="white")
                    net.from_nx(G)

                    # --- CRITICAL: FREEZE GRAPH ---
                    net.toggle_physics(False)  # Disable browser physics completely
                    # ------------------------------

                    path = os.path.join(CURRENT_DIR, "network.html")
                    net.save_graph(path)

                    with open(path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    components.html(source_code, height=620)
                else:
                    st.warning("Not enough strong connections found yet. Try collecting more data.")

        with col_legend:
            st.info("""
            **How to read this graph:**
            * **Nodes:** Trending Posts.
            * **Lines:** Shared keywords.
            * **Color:** Platform.
            * **Position:** Fixed by algorithm.
            """)

    # === TAB 3: Analytics ===
    with tab3:
        st.subheader("Sentiment & Volume Analysis")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.box(df, x="source_platform", y="sentiment", color="source_platform",
                         title="Sentiment Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df, x="source_platform", y="trend_score", title="Average Trend Score per Platform")
            st.plotly_chart(fig2, use_container_width=True)