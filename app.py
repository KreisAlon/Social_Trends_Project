import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

# ייבוא בונה הגרפים שלנו
from graph_analyzer import GraphBuilder

# הגדרת עמוד בסיסית
st.set_page_config(
    page_title="AI Trend Hunter",
    page_icon="🤖",
    layout="wide"
)

DB_PATH = "trends_project.db"


def load_data():
    """שליפת הנתונים מהדאטה-בייס לתוך DataFrame"""
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


# --- כותרת ראשית ---
st.title("🤖 AI Trends & Network Analysis")
st.markdown("מערכת לניתוח מגמות חוצות-פלטפורמות בזמן אמת (GitHub, Mastodon, HackerNews, DevTo)")

# טעינת נתונים
df = load_data()

if df.empty:
    st.warning("עדיין אין נתונים במערכת. אנא הרץ את main.py לאיסוף מידע.")
else:
    # --- Metrics Row (מדדים מרכזיים) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Posts Tracked", len(df))
    col2.metric("Top Trend Score", f"{df['trend_score'].max():.1f}")
    col3.metric("Avg Sentiment", f"{df['sentiment'].mean():.2f}")

    # הפלטפורמה הכי פעילה
    top_platform = df['source_platform'].value_counts().idxmax()
    col4.metric("Dominant Platform", top_platform)

    st.divider()

    # --- Tabs Layout ---
    tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "🕸️ Network Graph", "📈 Sentiment Analysis"])

    with tab1:
        st.subheader("🔥 Top Trending Topics")

        # פילטרים בצד
        platforms = st.multiselect("Filter by Platform", df['source_platform'].unique(),
                                   default=df['source_platform'].unique())
        filtered_df = df[df['source_platform'].isin(platforms)]

        # הצגת הטבלה עם עיצוב
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

    with tab2:
        st.subheader("🔍 Keyword Connection Graph")
        st.caption("Visualizing connections between posts based on shared keywords.")

        # כפתור לרענון הגרף
        if st.button("Generate Network Graph"):
            gb = GraphBuilder()
            G = gb.build_graph()

            if G.number_of_nodes() > 0:
                # יצירת ויזואליזציה עם PyVis
                net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")
                net.from_nx(G)

                # שמירה זמנית לקובץ HTML
                path = "tmp_network.html"
                net.save_graph(path)

                # טעינת ה-HTML לתוך Streamlit
                HtmlFile = open(path, 'r', encoding='utf-8')
                source_code = HtmlFile.read()
                components.html(source_code, height=500)
            else:
                st.info("Not enough connections found yet to build a graph.")

    with tab3:
        st.subheader("💡 Sentiment & Distribution")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Sentiment by Platform**")
            fig_sent = px.box(df, x="source_platform", y="sentiment", color="source_platform", points="all")
            st.plotly_chart(fig_sent, use_container_width=True)

        with col_b:
            st.markdown("**Trend Score Distribution**")
            fig_hist = px.histogram(df, x="trend_score", nbins=20, title="Trend Score Spread")
            st.plotly_chart(fig_hist, use_container_width=True)