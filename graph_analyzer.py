import networkx as nx
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

PLATFORM_COLORS = {
    "GitHub": "#2dba4e",
    "Hacker News": "#ff6600",
    "Mastodon": "#6364ff",
    "Dev.to": "#000000"
}

GENERIC_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'genai', 'generative ai',
    'llm', 'gpt', 'tool', 'code', 'data', 'model', 'new', 'app', 'python', 'project',
    'using', 'via', 'show', 'hn'
}


class GraphBuilder:
    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # --- שינוי 1: הוספנו את 'content' לשליפה ---
        cursor.execute('''
            SELECT id, title, source_platform, found_keywords, trend_score, content
            FROM unified_posts 
            WHERE trend_score > 15
        ''')
        rows = cursor.fetchall()
        conn.close()

        print(f"[Graph] Processing {len(rows)} nodes...")

        for row in rows:
            # --- שינוי 2: פורקים גם את ה-content ---
            post_id, title, platform, keywords_str, score, content = row

            keywords = [k.strip().lower() for k in keywords_str.split(',')] if keywords_str else []
            strong_keywords_set = set(keywords) - GENERIC_KEYWORDS

            node_color = PLATFORM_COLORS.get(platform, "#808080")
            short_label = title[:20] + "..." if len(title) > 20 else title

            # --- שינוי 3: יצירת תקציר תוכן ---
            # אם יש תוכן, ניקח 350 תווים ראשונים. אם אין, נכתוב שאין.
            if content:
                # מנקים ירידות שורה כדי שהטולטיפ יראה יפה
                clean_content = content.replace('\n', ' ').replace('\r', '')
                preview_text = clean_content[:350] + "..." if len(clean_content) > 350 else clean_content
            else:
                preview_text = "No content preview available."

            # --- שינוי 4: הוספת התוכן לטולטיפ (HTML) ---
            hover_text = (f"<b>{title}</b><br>"
                          f"<span style='color: gray;'>{platform} | Score: {score:.1f}</span><br><br>"
                          f"<b>Summary:</b><br><i>{preview_text}</i><br><br>"
                          f"<b>Keywords:</b> {', '.join(list(strong_keywords_set)[:5])}")

            # הוספת הצומת
            self.graph.add_node(post_id,
                                label=short_label,
                                title=hover_text,  # כאן נכנס כל הטקסט העשיר
                                color=node_color,
                                value=score,
                                group=platform,
                                strong_keys=list(strong_keywords_set))

            # הוספת קשתות (אותו לוגיקה כמו מקודם)
        nodes = list(self.graph.nodes(data=True))

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                id1, data1 = nodes[i]
                id2, data2 = nodes[j]

                set1 = set(data1['strong_keys'])
                set2 = set(data2['strong_keys'])

                shared = set1 & set2
                MIN_COMMON_WORDS = 1

                if len(shared) >= MIN_COMMON_WORDS:
                    weight = len(shared)
                    self.graph.add_edge(id1, id2,
                                        value=weight,
                                        title=f"Shared Topics: {', '.join(list(shared))}")

        return self.graph