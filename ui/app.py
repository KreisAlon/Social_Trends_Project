import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import json
import numpy as np
import time

# --- Google Generative AI SDK ---
import google.generativeai as genai

# --- Dynamic Path Resolution ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from graph_analyzer import GraphBuilder

DB_PATH = os.path.join(PROJECT_ROOT, "trends_project.db")

st.set_page_config(page_title="TrendAnalyzer Pro | AI Intelligence", page_icon="🧿", layout="wide")

# --- Custom UI Styles ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; color: #1a1a1a; }
    .stMetric { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; }
    .insight-card { background: #ffffff; border-left: 6px solid #4a90e2; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .inspector-card { background: #ffffff; border: 1px solid #dee2e6; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .ai-box { background-color: #f0f7ff; border: 1px dashed #0d6efd; padding: 15px; border-radius: 10px; color: #0d47a1; line-height: 1.6; }
    .source-detail-box {
        background-color: #ffffff; border: 1px solid #e9ecef;
        padding: 15px; border-radius: 10px; height: 100%;
        transition: transform 0.2s;
    }
    .source-detail-box:hover { border-color: #4a90e2; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# Strict Color Mapping
PLATFORM_COLORS = {
    "GitHub": "#2dba4e",
    "Hacker News": "#ff6600",
    "Mastodon": "#7c6ff7",
    "Dev.to": "#333333",
    "AI Ecosystem": "#0d6efd"
}


# ==========================================
# 🧠 AI ANALYST (LOGIC UNTOUCHED)
# ==========================================

@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_briefing(p1, t1, c1, p2, t2, c2, score):
    GEMINI_KEY = os.getenv("GEMINI_KEY")

    if not GEMINI_KEY:
        return "System Error: API key not found."

    time.sleep(3.0)

    try:
        genai.configure(api_key=GEMINI_KEY)

        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
        except Exception as e:
            print("Primary model failed:", e)
            model = genai.GenerativeModel("models/gemini-2.5-flash")

        prompt = f"""
        You are a senior AI industry analyst.

        Analyze the connection between the following two signals from different platforms.
        These signals have a semantic similarity score of {score:.1f}%.

        --- SOURCE A ({p1}) ---
        Title: {t1}
        Content: {c1}

        --- SOURCE B ({p2}) ---
        Title: {t2}
        Content: {c2}

        Your task:

        1. Explain the deeper connection between these two signals (not just surface similarity).
        2. Identify the underlying technological or industry trend.
        3. Explain WHY this trend is emerging now (market forces, technology shifts, developer behavior, etc).
        4. Provide a forward-looking prediction (what is likely to happen next in this space).
        5. Highlight any strategic insight or opportunity.

        Write a detailed, well-structured analysis (5–8 sentences).
        Use a professional, insightful tone (like a top-tier analyst report).
        Write ONLY in English.
        """
        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            return response.text.strip()

        return "AI could not generate insight."

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return "The AI service is currently at capacity. Please try again in 60 seconds."
        return f"AI Insight unavailable: {error_msg}"


# ==========================================
# 📊 DATA ACCESS LAYER
# ==========================================

@st.cache_data(ttl=300)
def fetch_balanced_trends():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    # Balanced representation
    df = pd.read_sql_query("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY source_platform ORDER BY trend_score DESC) as rn 
            FROM unified_posts
        ) WHERE rn <= 25 ORDER BY trend_score DESC
    """, conn)
    conn.close()
    return df


def safe_url_fetch(val):
    if isinstance(val, pd.Series):
        val = val.iloc[0]
    return str(val) if pd.notna(val) else "https://google.com"


# ==========================================
# 🚀 CORE DASHBOARD INTERFACE
# ==========================================

def main():
    st.title("🧿 AI Trends Intelligence System")
    st.markdown("### Cross-Platform Semantic Discovery Engine")

    df = fetch_balanced_trends()

    if df.empty:
        st.error("Database connection failed. Please ensure the data collectors are running.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Trends Scanned", len(df))
    m2.metric("Platforms Monitored", df['source_platform'].nunique())
    m3.metric("Analysis Engine", "Semantic Nexus")
    m4.metric("Last Data Refresh", df['collected_at'].max().split('T')[0] if 'collected_at' in df else "N/A")

    st.divider()

    tab_wheel, tab_ai = st.tabs(["🌀 Ecosystem Wheel", "🔬 Intelligence Briefing"])

    with tab_wheel:
        # --- BALANCED LAYOUT: 3.0 vs 1.5 ---
        col_main, col_ins = st.columns([3.0, 1.5])

        with col_main:
            df_plot = df.copy()
            df_plot['root'] = 'AI Ecosystem'
            df_plot['short_title'] = df_plot['title'].apply(
                lambda x: str(x)[:35] + '...' if len(str(x)) > 35 else str(x))

            # --- OPTIMIZED SUNBURST (Height 750) ---
            fig = px.sunburst(
                df_plot,
                path=['root', 'source_platform', 'short_title'],
                values='trend_score',
                color='source_platform',
                color_discrete_map=PLATFORM_COLORS,  # Enforce brand colors
                height=750
            )

            fig.update_traces(
                textinfo="label+percent parent",
                insidetextorientation='radial',
                hoverinfo='none',
                hovertemplate=None,
                # Ensures leaves inherit parent color properly
                marker=dict(line=dict(color='#ffffff', width=1))
            )

            fig.update_layout(margin=dict(t=10, l=10, r=10, b=10))

            selection_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun",
                                              key="sunburst_optimized")

        with col_ins:
            st.markdown("### 🔎 Trend Inspector")

            target_label = None
            if selection_event and selection_event.selection.points:
                target_label = selection_event.selection.points[0]["label"]

            title_list = df_plot['short_title'].unique().tolist()
            start_idx = title_list.index(target_label) if target_label in title_list else 0

            chosen_title = st.selectbox("Inspect Target:", title_list, index=start_idx)

            if chosen_title:
                row_data = df_plot[df_plot['short_title'] == chosen_title].iloc[0]

                # Visual Intensity Gauge
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=row_data['trend_score'],
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Intensity Score", 'font': {'size': 16}},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': PLATFORM_COLORS.get(row_data['source_platform'], "#0d6efd")},
                        'steps': [
                            {'range': [0, 50], 'color': "#f8f9fa"},
                            {'range': [50, 80], 'color': "#e9ecef"},
                            {'range': [80, 100], 'color': "#dee2e6"}
                        ]
                    }
                ))
                fig_gauge.update_layout(height=200, margin=dict(t=20, b=0, l=10, r=10))
                st.plotly_chart(fig_gauge, use_container_width=True)

                st.markdown(f"""
                <div class="inspector-card" style="border-top: 5px solid {PLATFORM_COLORS.get(row_data['source_platform'], '#333')};">
                    <p style="text-transform: uppercase; color: gray; font-size: 0.75em; margin:0;">{row_data['source_platform']}</p>
                    <h4 style="margin-top: 5px; line-height: 1.3;">{row_data['title']}</h4>
                    <p style="font-size: 0.95em; color: #444; background: #f8f9fa; padding: 12px; border-radius: 8px;">
                        "{str(row_data.get('content', ''))[:200]}..."
                    </p>
                </div>
                <br>
                """, unsafe_allow_html=True)

                st.link_button("🌐 Open Source URL", safe_url_fetch(row_data['url']), use_container_width=True)

    with tab_ai:
        st.subheader("Automated Semantic Nexus Discovery")
        st.write("Generating strategic insights based on cross-platform convergence.")

        builder = GraphBuilder()
        g_nx = builder.build_graph()

        semantic_bridges = sorted(
            [(u, v, d) for u, v, d in g_nx.edges(data=True) if d.get('is_cross')],
            key=lambda x: x[2].get('weight', 0),
            reverse=True
        )[:5]

        if not semantic_bridges:
            st.info("Searching for cross-platform semantic overlap...")
        else:
            for u, v, d in semantic_bridges:
                r1 = df[df['id'] == u].iloc[0]
                r2 = df[df['id'] == v].iloc[0]
                match_val = d['weight'] * 100

                with st.container():
                    st.markdown(f"<div class='insight-card'><h3>🔗 Semantic Nexus: {match_val:.1f}% Match</h3></div>",
                                unsafe_allow_html=True)

                    btn_key = f"ai_btn_{u}_{v}"
                    if st.button(f"🔍 Generate Strategic Briefing for this Nexus", key=btn_key):
                        with st.spinner("AI Analyst is synthesizing narrative..."):
                            thesis = get_ai_briefing(
                                r1['source_platform'], r1['title'], r1.get('content', ''),
                                r2['source_platform'], r2['title'], r2.get('content', ''),
                                match_val
                            )
                        st.markdown(f"<div class='ai-box'>🤖 <b>Strategic Report:</b><br>{thesis}</div>",
                                    unsafe_allow_html=True)
                    else:
                        st.info("Click the button above to request a deep analysis of this connection.")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"""<div class="source-detail-box">
                            <p style="color: {PLATFORM_COLORS.get(r1['source_platform'], 'gray')}; font-weight: bold; margin:0;">{r1['source_platform']}</p>
                            <h5 style="margin-top: 10px;">{r1['title']}</h5>
                            <p style="font-size: 0.85em; color: #666; font-style: italic;">{str(r1.get('content', ''))[:140]}...</p>
                        </div>""", unsafe_allow_html=True)
                        st.link_button(f"Visit {r1['source_platform']}", safe_url_fetch(r1['url']),
                                       use_container_width=True)

                    with c2:
                        st.markdown(f"""<div class="source-detail-box">
                            <p style="color: {PLATFORM_COLORS.get(r2['source_platform'], 'gray')}; font-weight: bold; margin:0;">{r2['source_platform']}</p>
                            <h5 style="margin-top: 10px;">{r2['title']}</h5>
                            <p style="font-size: 0.85em; color: #666; font-style: italic;">{str(r2.get('content', ''))[:140]}...</p>
                        </div>""", unsafe_allow_html=True)
                        st.link_button(f"Visit {r2['source_platform']}", safe_url_fetch(r2['url']),
                                       use_container_width=True)
                    st.divider()


if __name__ == "__main__":
    main()