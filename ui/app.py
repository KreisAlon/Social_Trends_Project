import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from collections import Counter
from bs4 import BeautifulSoup

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

# --- Page Configuration ---
st.set_page_config(page_title="AI Trend Hunter", page_icon="🚨", layout="wide")


# --- Helper Functions ---

def clean_html_content(raw_html):
    """
    Utility to strip HTML tags from raw content.
    Returns clean, readable plain text.
    """
    if not raw_html:
        return "No content available."
    try:
        soup = BeautifulSoup(str(raw_html), "html.parser")
        return soup.get_text().strip()
    except (AttributeError, TypeError):
        return str(raw_html)


def load_data():
    """
    Fetches the complete dataset from the SQLite database.
    """
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT source_platform, title, trend_score, sentiment, raw_score, url, found_keywords, content, author, published_at
    FROM unified_posts
    ORDER BY trend_score DESC
    """
    data_frame = pd.read_sql_query(query, conn)
    conn.close()
    return data_frame


def get_alerts(df, threshold=65.0):
    """Filters the dataset for high-priority items."""
    if df.empty:
        return pd.DataFrame()
    return df[df['trend_score'] >= threshold]


def prepare_sunburst_data(df):
    """
    Prepares data for the Galaxy (Sunburst) Chart.
    Strictly limits to Top 60 for visual clarity.
    """
    chart_df = df.head(60).copy()

    sunburst_keywords = []
    for ks in chart_df['found_keywords']:
        if ks:
            words = [w.strip().lower() for w in str(ks).split(',')]
            # NLP Stop-words filter
            stop_words = ['ai', 'the', 'to', 'of', 'in', 'for', 'new', 'model', 'data', 'using', 'app', 'tool', 'llm']
            words = [w for w in words if w not in stop_words]
            sunburst_keywords.extend(words)

    if not sunburst_keywords:
        return pd.DataFrame()

    top_topics = [t[0] for t in Counter(sunburst_keywords).most_common(8)]
    records = []

    for topic_name in top_topics:
        mask = chart_df['found_keywords'].str.contains(topic_name, case=False, na=False)
        topic_posts = chart_df[mask]

        for _, post_row in topic_posts.iterrows():
            clean_preview = clean_html_content(post_row['content'])
            records.append({
                "Topic": topic_name.upper(),
                "Platform": post_row['source_platform'],
                "Post Title": post_row['title'],
                "Score": post_row['trend_score'],
                "Url": post_row['url'],
                "Content": clean_preview
            })
    return pd.DataFrame(records)


def get_trend_stories(df):
    """Detects cross-platform narratives."""
    stories_keywords = []
    top_df = df.head(100)

    for ks in top_df['found_keywords']:
        if ks:
            words = [w.strip().lower() for w in str(ks).split(',')]
            stop_words = ['ai', 'the', 'to', 'of', 'in', 'for', 'new', 'model', 'data', 'using']
            words = [w for w in words if w not in stop_words]
            stories_keywords.extend(words)

    if not stories_keywords:
        return []

    common_topics = [word for word, count in Counter(stories_keywords).most_common(10) if count > 1]

    stories_list = []
    for story_topic in common_topics:
        mask = df['found_keywords'].str.contains(story_topic, case=False, na=False)
        topic_df = df[mask]

        if len(topic_df['source_platform'].unique()) < 2:
            continue

        # Renamed to avoid shadowing outer scope
        s_gh = topic_df[topic_df['source_platform'] == 'GitHub'].head(1)
        s_hn = topic_df[topic_df['source_platform'] == 'Hacker News'].head(1)
        s_so = topic_df[topic_df['source_platform'].isin(['Mastodon', 'Dev.to'])].head(1)

        stories_list.append({
            "topic": story_topic.upper(),
            "github": s_gh.iloc[0] if not s_gh.empty else None,
            "hackernews": s_hn.iloc[0] if not s_hn.empty else None,
            "social": s_so.iloc[0] if not s_so.empty else None
        })
    return stories_list


# --- UI EXECUTION ---

# 1. SIDEBAR: ALERTS
with st.sidebar:
    st.header("🔔 Notification Center")
    main_df = load_data()

    if not main_df.empty:
        alert_df = get_alerts(main_df, 60.0)
        if not alert_df.empty:
            st.error(f"CRITICAL: {len(alert_df)} Trends Detected!")
            for _, alert_row in alert_df.head(5).iterrows():
                st.markdown(f"**🚨 {alert_row['title'][:40]}**")
                st.caption(f"Score: {alert_row['trend_score']:.1f}")
                st.divider()
        else:
            st.success("System Normal.")

# 2. MAIN HEADER
st.title("🚨 AI Trend Hunter: Command Center")

if not main_df.empty:
    # Breaking News logic
    super_critical = main_df[main_df['trend_score'] > 70]
    if not super_critical.empty:
        top_trend = super_critical.iloc[0]
        st.error(f"🔥 BREAKING NEWS: '{top_trend['title']}' is exploding on {top_trend['source_platform']}")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Intel", len(main_df))
    m2.metric("Max Score", f"{main_df['trend_score'].max():.1f}")
    m3.metric("Avg Sentiment", f"{main_df['sentiment'].mean():.2f}")
    m4.metric("Sources", len(main_df['source_platform'].unique()))

    st.divider()

    t1, t2, t3 = st.tabs(["🏆 Leaderboard", "🌌 Trend Galaxy", "🧩 Stories"])

    with t1:
        st.dataframe(main_df[['source_platform', 'title', 'trend_score', 'sentiment', 'url']], use_container_width=True)

    with t2:
        sunburst_df = prepare_sunburst_data(main_df)
        if not sunburst_df.empty:
            col_graph, col_ins = st.columns([2, 1])
            with col_graph:
                fig = px.sunburst(
                    sunburst_df, path=['Topic', 'Platform', 'Post Title'], values='Score',
                    color='Platform',
                    color_discrete_map={'GitHub': '#2dba4e', 'Hacker News': '#ff6600', 'Mastodon': '#6364ff',
                                        'Dev.to': '#000000'},
                    hover_data=['Content'], height=700
                )
                fig.update_traces(
                    hovertemplate="<b>%{label}</b><br>Score: %{value:.1f}<br><br>%{customdata[0]}<extra></extra>")
                st.plotly_chart(fig, use_container_width=True)

            with col_ins:
                st.markdown("### 🔎 Quick Inspector")
                ui_topics = sunburst_df['Topic'].unique()
                sel_topic = st.selectbox("Select Topic:", ui_topics)
                if sel_topic:
                    # Using .loc makes it explicitly clear to PyCharm that the result is a DataFrame
                    filtered_df = sunburst_df.loc[sunburst_df['Topic'] == sel_topic].copy()

                    # Ensure the variable is treated as a DataFrame for the sort_values method
                    if isinstance(filtered_df, pd.DataFrame):
                        sorted_rows = filtered_df.sort_values(by='Score', ascending=False)

                        for _, r in sorted_rows.iterrows():
                            with st.expander(f"[{r['Platform']}] {r['Post Title']}"):
                                st.write(f"Score: {r['Score']:.1f}")
                                st.text(r['Content'])
        else:
            st.warning("No data for galaxy.")

    with t3:
        stories = get_trend_stories(main_df)
        for s in stories:
            st.markdown(f"### 🔥 Topic: {s['topic']}")
            c_gh, c_hn, c_so = st.columns(3)
            if s['github'] is not None: c_gh.info(s['github']['title'])
            if s['hackernews'] is not None: c_hn.warning(s['hackernews']['title'])
            if s['social'] is not None: c_so.success(s['social']['title'])
            st.divider()
else:
    st.error("No database found.")