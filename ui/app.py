import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) if "ui" in CURRENT_DIR else CURRENT_DIR
DB_PATH = os.path.join(PROJECT_ROOT, "trends_project.db")

st.set_page_config(page_title="AI Trend Intelligence", page_icon="🧿", layout="wide")

# --- UI Styling ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; color: #1e1e1e; }
    .stMetric { background: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .insight-card { 
        background: #ffffff; border-left: 6px solid #4a90e2; 
        padding: 20px; border-radius: 8px; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .inspector-card {
        background: #ffffff; border: 1px solid #dee2e6;
        padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

PLATFORM_COLORS = {
    "GitHub": "#2dba4e",
    "Hacker News": "#ff6600",
    "Mastodon": "#7c6ff7",
    "Dev.to": "#3b49df",
    "AI Ecosystem": "#0d6efd"
}


@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    # Balanced data extraction
    df = pd.read_sql_query("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY source_platform ORDER BY trend_score DESC) as rn
            FROM unified_posts
        ) WHERE rn <= 25 ORDER BY trend_score DESC
    """, conn)
    conn.close()
    return df


def get_valid_embeddings(df):
    """Safely decodes embeddings from the DB, dropping invalid ones (Fixes the 0% bug)"""
    valid_indices = []
    embeddings = []

    for idx, row in df.iterrows():
        emb_data = row['embedding']
        try:
            if isinstance(emb_data, bytes):
                emb_data = emb_data.decode('utf-8')
            emb = json.loads(emb_data)

            if isinstance(emb, list) and len(emb) > 0:
                embeddings.append(emb)
                valid_indices.append(idx)
        except Exception:
            continue

    return df.iloc[valid_indices].reset_index(drop=True), np.array(embeddings)


def find_semantic_connections(df, threshold=0.55):
    valid_df, emb_matrix = get_valid_embeddings(df)

    if len(emb_matrix) < 2: return []

    sim_matrix = cosine_similarity(emb_matrix)
    connections = []

    for i in range(len(valid_df)):
        for j in range(i + 1, len(valid_df)):
            score = float(sim_matrix[i][j])
            p1, p2 = valid_df.iloc[i]['source_platform'], valid_df.iloc[j]['source_platform']

            if p1 != p2 and score >= threshold:
                connections.append({
                    'score': score,
                    'p1': p1, 'title1': valid_df.iloc[i]['title'], 'url1': valid_df.iloc[i]['url'],
                    'content1': valid_df.iloc[i].get('content', ''),
                    'p2': p2, 'title2': valid_df.iloc[j]['title'], 'url2': valid_df.iloc[j]['url'],
                    'content2': valid_df.iloc[j].get('content', '')
                })

    return sorted(connections, key=lambda x: x['score'], reverse=True)[:10]


def safe_url(url_val):
    if isinstance(url_val, pd.Series): return str(url_val.iloc[0])
    return str(url_val) if pd.notna(url_val) else "https://google.com"


def run_app():
    st.title("🧿 AI Trend Intelligence Dashboard")
    df = load_data()

    if df.empty:
        st.error("Database empty. Please run main.py first.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Monitored Items", len(df))
    m2.metric("Active Platforms", df['source_platform'].nunique())
    m3.metric("Semantic Engine", "Online 🟢")
    m4.metric("Last Update", df['collected_at'].max().split('T')[0] if 'collected_at' in df else "N/A")

    st.divider()

    tab_wheel, tab_insights, tab_raw = st.tabs(["🌀 The Trend Wheel", "🔬 Intelligence Briefing", "📊 Raw Data"])

    with tab_wheel:
        st.subheader("Interactive Sunburst Graph")
        st.write(
            "Explore the ecosystem. **Click any slice on the wheel** to automatically load its full details in the inspector on the right.")

        col_graph, col_inspector = st.columns([2.5, 1.2])

        # --- THE WHEEL (Left Side) ---
        with col_graph:
            df_sun = df.copy()
            df_sun['root'] = 'AI Ecosystem'

            # Create a truncated title for better graph display while preserving the original
            df_sun['short_title'] = df_sun['title'].apply(lambda x: str(x)[:40] + '...' if len(str(x)) > 40 else str(x))

            fig = px.sunburst(
                df_sun,
                path=['root', 'source_platform', 'short_title'],
                values='trend_score',
                color='source_platform',
                color_discrete_map=PLATFORM_COLORS,
                height=650
            )
            fig.update_traces(textinfo="label+percent parent", insidetextorientation='radial')
            fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)')

            # Capture the user's click event on the Plotly chart
            chart_event = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",  # Triggers a script rerun on selection
                key="sunburst_click"
            )

        # --- THE INSPECTOR (Right Side) ---
        with col_inspector:
            st.markdown("### 🔎 Trend Inspector")

            selected_short_title = None

            # Check if the user clicked an element on the graph
            if chart_event and len(chart_event.selection.points) > 0:
                clicked_label = chart_event.selection.points[0]["label"]
                # Ensure the click targets a specific post rather than the parent platform category
                if clicked_label in df_sun['short_title'].values:
                    selected_short_title = clicked_label

            titles_list = df_sun['short_title'].dropna().unique().tolist()

            # Set the default selectbox index based on the graph click, falling back to 0
            default_index = titles_list.index(selected_short_title) if selected_short_title in titles_list else 0

            # Dropdown menu acts as a fallback and synchronizes with graph clicks
            selected_from_box = st.selectbox("Selected Target:", titles_list, index=default_index)

            if selected_from_box:
                row = df_sun[df_sun['short_title'] == selected_from_box].iloc[0]

                # Safely extract a preview of the content if available
                content_preview = row.get('content', '')
                if pd.isna(content_preview) or not str(content_preview).strip():
                    content_preview = "No detailed content extracted for this item."
                else:
                    content_preview = str(content_preview)[:150] + "..."

                platform_color = PLATFORM_COLORS.get(row['source_platform'], '#000')

                # Render a rich, styled HTML information card
                st.markdown(f"""
                <div class="inspector-card" style="border-top: 4px solid {platform_color};">
                    <span style="background-color: {platform_color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; text-transform: uppercase;">
                        {row['source_platform']}
                    </span>
                    <h3 style="margin-top: 15px; margin-bottom: 10px; font-size: 1.25em; line-height: 1.3;">
                        {row['title']}
                    </h3>
                    <p style="color: #555; font-size: 0.95em; line-height: 1.5; background: #f8f9fa; padding: 10px; border-radius: 6px;">
                        <i>"{content_preview}"</i>
                    </p>
                    <div style="margin-top: 15px;">
                        <p style="margin-bottom: 5px;"><b>🔥 Trend Score:</b> <span style="color: #0d6efd; font-weight: bold;">{row['trend_score']:.1f}</span></p>
                        <p style="margin-bottom: 5px;"><b>🔑 Keywords:</b> {row.get('found_keywords', 'None identified')}</p>
                    </div>
                </div>
                <br>
                """, unsafe_allow_html=True)

                # Render a prominent button linking to the original source
                st.link_button("🌐 Read Full Source", safe_url(row['url']), use_container_width=True)


    with tab_insights:
        st.subheader("Deep AI Analysis: Cross-Platform Connections")
        st.write(
            "The AI scans the vector database to find strong narrative bridges between entirely different platforms.")

        with st.spinner("Analyzing semantic bridges..."):
            connections = find_semantic_connections(df, threshold=0.55)

        if not connections:
            st.info(
                "Searching for stronger cross-platform vectors... Ensure the collector gathers enough diverse data.")
        else:
            for idx, conn in enumerate(connections, 1):
                match_pct = conn['score'] * 100

                # Dynamic Analyst Note based on the real percentage!
                analyst_note = ""
                if match_pct > 80:
                    analyst_note = "🔥 **Critical Convergence:** The exact same concept is dominating both platforms simultaneously."
                elif match_pct > 65:
                    analyst_note = "📈 **Strong Signal:** A solid bridge is forming. A narrative is transitioning across audiences."
                else:
                    analyst_note = "🌱 **Emerging Ripple:** Early signs of a shared methodology spreading to a new ecosystem."

                with st.container():
                    st.markdown(f"""<div class="insight-card">
                        <h3>🔗 Semantic Nexus #{idx} | <span style="color: #0d6efd;">{match_pct:.1f}% Match</span></h3>
                        <p>{analyst_note}</p>
                    </div>""", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption(f"SOURCE A: {conn['p1']}")
                        st.write(f"**{conn['title1']}**")
                        st.link_button(f"View on {conn['p1']}", safe_url(conn['url1']))
                    with c2:
                        st.caption(f"SOURCE B: {conn['p2']}")
                        st.write(f"**{conn['title2']}**")
                        st.link_button(f"View on {conn['p2']}", safe_url(conn['url2']))
                    st.divider()

    with tab_raw:
        st.subheader("Balanced Dataset")
        st.dataframe(df[['source_platform', 'title', 'trend_score', 'url']].head(100), use_container_width=True)


if __name__ == "__main__":
    run_app()