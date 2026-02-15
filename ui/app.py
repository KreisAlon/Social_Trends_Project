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

# --- Topic Intelligence Dictionary ---
TOPIC_INFO = {
    "AGENTS": "Autonomous systems leveraging LLMs to execute multi-step workflows independently. Unlike simple chatbots, Agents can use external tools, browse the web, and correct their own mistakes to reach a goal.",
    "DEEPSEEK": "A disruptive suite of open-weights models developed in China. They have shifted the industry focus toward high-efficiency training (Mixture-of-Experts) and provide top-tier performance at a fraction of the cost of GPT-4.",
    "LLM": "Large Language Models; massive transformer-based neural networks trained on vast datasets. They serve as the foundational logic layer for modern AI, capable of advanced linguistic synthesis, coding, and mathematical reasoning.",
    "VISION": "Computer Vision and Multimodal AI. These systems bridge the gap between pixels and language, enabling capabilities like OCR, object detection, and the ability for AI to 'reason' about the content of images and videos.",
    "NLP": "Natural Language Processing; the engineering field focused on making human language machine-readable. It covers everything from basic tokenization to complex sentiment analysis and semantic entity recognition.",
    "RAG": "Retrieval-Augmented Generation; a sophisticated architecture that anchors LLM responses in verified, external data. It solves the 'hallucination' problem by forcing the model to cite specific documents before generating an answer.",
    "GPU": "Graphics Processing Units; the specialized silicon hardware (primarily from Nvidia) designed for massive parallel processing. They are the 'fuel' of the AI revolution, essential for both model training and high-speed inference.",
    "CLAUDE": "Anthropic's flagship AI models, widely regarded for their superior performance in coding and complex reasoning. They emphasize 'Constitutional AI' to ensure outputs are safe, honest, and follow human values.",
    "GENAI": "Generative Artificial Intelligence; a broad category of AI capable of creating new content (text, images, audio) that mimics human creativity, rather than just classifying existing data."
}

# --- Page Configuration ---
st.set_page_config(page_title="AI Trend Hunter", page_icon="🚨", layout="wide")


# --- Helper Functions ---

def clean_html_content(raw_html):
    """Strips HTML tags and ensures clean text display."""
    if not raw_html: return "No content available."
    try:
        soup = BeautifulSoup(str(raw_html), "html.parser")
        return soup.get_text().strip()
    except (AttributeError, TypeError):
        return str(raw_html)


def load_data():
    """Fetches the complete dataset from SQLite."""
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM unified_posts ORDER BY trend_score DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def prepare_sunburst_data(df):
    """Prepares hierarchical data for the Trend Galaxy visualization."""
    chart_df = df.head(60).copy()
    sunburst_keywords = []
    for ks in chart_df['found_keywords']:
        if ks:
            words = [w.strip().lower() for w in str(ks).split(',')]
            stop_words = ['ai', 'the', 'to', 'of', 'in', 'for', 'new', 'model', 'data', 'using', 'app', 'tool', 'llm']
            words = [w for w in words if w not in stop_words]
            sunburst_keywords.extend(words)

    if not sunburst_keywords: return pd.DataFrame()
    top_topics = [t[0] for t in Counter(sunburst_keywords).most_common(8)]

    records = []
    for topic_name in top_topics:
        mask = chart_df['found_keywords'].str.contains(topic_name, case=False, na=False)
        topic_posts = chart_df[mask]
        for _, post in topic_posts.iterrows():
            records.append({
                "Topic": topic_name.upper(),
                "Platform": post['source_platform'],
                "Post Title": post['title'],
                "Score": post['trend_score'],
                "Url": post['url'],
                "Content": clean_html_content(post['content'])
            })
    return pd.DataFrame(records)


def get_trend_stories(df):
    """Detects cross-platform narratives (The Story Engine)."""
    stories_keywords = []
    top_df = df.head(100)
    for ks in top_df['found_keywords']:
        if ks:
            words = [w.strip().lower() for w in str(ks).split(',')]
            stop_words = ['ai', 'the', 'to', 'of', 'in', 'for', 'new', 'model', 'data', 'using']
            words = [w for w in words if w not in stop_words]
            stories_keywords.extend(words)

    if not stories_keywords: return []
    common_topics = [word for word, count in Counter(stories_keywords).most_common(10) if count > 1]

    stories_list = []
    for story_topic in common_topics:
        mask = df['found_keywords'].str.contains(story_topic, case=False, na=False)
        topic_df = df[mask]
        if len(topic_df['source_platform'].unique()) < 2: continue
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


# --- UI START ---

with st.sidebar:
    st.header("🔔 Live Intel Feed")
    main_df = load_data()
    if not main_df.empty:
        alert_df = main_df[main_df['trend_score'] >= 60.0]
        if not alert_df.empty:
            st.error(f"ALERTS: {len(alert_df)} High-Trend Items")
            for _, alert_row in alert_df.head(3).iterrows():
                st.markdown(f"**{alert_row['title'][:35]}**")
                st.caption(f"Score: {alert_row['trend_score']:.1f}")
                st.divider()

st.title("🚨 AI Trend Hunter: Command Center")

if not main_df.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Intel Records", len(main_df))
    m2.metric("Peak Score", f"{main_df['trend_score'].max():.1f}")
    m3.metric("Avg Sentiment", f"{main_df['sentiment'].mean():.2f}")
    m4.metric("Active Sources", len(main_df['source_platform'].unique()))

    st.divider()

    t1, t2, t3 = st.tabs(["🏆 Leaderboard", "🌌 Trend Galaxy", "🧩 Narrative Stories"])

    # === TAB 1: LEADERBOARD (UPDATED WITH CLICKABLE LINKS) ===
    with t1:
        st.dataframe(
            main_df[['source_platform', 'title', 'trend_score', 'sentiment', 'url']],
            column_config={
                # Makes the URL clickable and shows a nice icon/text
                "url": st.column_config.LinkColumn("Source Link", display_text="🔗 Open"),
                # Adds a visual progress bar to the score
                "trend_score": st.column_config.ProgressColumn("Trend Intensity", format="%.1f", min_value=0,
                                                               max_value=100),
                "source_platform": "Platform",
                "title": "Post Title",
                "sentiment": st.column_config.NumberColumn("Sentiment", format="%.2f")
            },
            use_container_width=True,
            height=600,
            hide_index=True
        )

    # === TAB 2: GALAXY ===
    with t2:
        sunburst_df = prepare_sunburst_data(main_df)
        if not sunburst_df.empty:
            col_graph, col_ins = st.columns([2, 1])
            with col_graph:
                st.subheader("Interactive Intelligence Galaxy")
                fig = px.sunburst(
                    sunburst_df, path=['Topic', 'Platform', 'Post Title'], values='Score',
                    color='Platform',
                    color_discrete_map={'GitHub': '#2dba4e', 'Hacker News': '#ff6600', 'Mastodon': '#6364ff',
                                        'Dev.to': '#000000'},
                    hover_data=['Content'], height=750
                )
                fig.update_traces(
                    hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br><extra>Score: %{value:.1f}</extra>",
                    textinfo="label+percent entry")
                fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

            with col_ins:
                st.markdown("### 🔎 Quick Inspector")
                ui_topics = sunburst_df['Topic'].unique()
                sel_topic = st.selectbox("Select Trend Cluster:", ui_topics)
                if sel_topic:
                    st.info(f"**Background:** {TOPIC_INFO.get(sel_topic, 'Emerging AI trend.')}")
                    f_df = sunburst_df.loc[sunburst_df['Topic'] == sel_topic].copy()
                    if isinstance(f_df, pd.DataFrame):
                        s_rows = f_df.sort_values(by='Score', ascending=False)
                        with st.container(height=450):
                            for _, r in s_rows.iterrows():
                                with st.expander(f"[{r['Platform']}] {r['Post Title'][:45]}..."):
                                    st.write(f"**Score:** {r['Score']:.1f}")
                                    st.link_button("🔗 View Source", str(r['Url']))
                                    st.text(r['Content'])

    # === TAB 3: NARRATIVE STORIES ===
    with t3:
        st.subheader("🧩 Cross-Platform Narrative Detection")
        stories = get_trend_stories(main_df)
        if not stories:
            st.warning("Analyzing data... Not enough cross-platform connections found yet.")
        else:
            for s in stories:
                with st.container():
                    st.markdown(f"### 🔥 Narrative: {s['topic']}")
                    st.markdown(f"**Context:** {TOPIC_INFO.get(s['topic'], 'Cross-platform trend.')}")
                    cols = st.columns(3)
                    gh, hn, so = s['github'], s['hackernews'], s['social']
                    with cols[0]:
                        st.markdown("**🛠️ Code (GitHub)**")
                        if gh is not None:
                            st.info(f"**{gh['title']}**")
                            st.link_button("View Repo", str(gh['url']))
                    with cols[1]:
                        st.markdown("**📰 Discussion (HN)**")
                        if hn is not None:
                            st.warning(f"**{hn['title']}**")
                            st.link_button("Read Thread", str(hn['url']))
                    with cols[2]:
                        st.markdown("**🗣️ Opinion (Social)**")
                        if so is not None:
                            st.success(f"**{so['title']}**")
                            st.link_button("Join Chat", str(so['url']))
                    st.divider()
else:
    st.error("No database found. Run 'ui/main.py' first.")