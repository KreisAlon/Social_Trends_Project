import networkx as nx
import sqlite3
import os

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

PLATFORM_COLORS = {
    "GitHub": "#2dba4e",  # Green
    "Hacker News": "#ff6600",  # Orange
    "Mastodon": "#6364ff",  # Purple
    "Dev.to": "#000000"  # Black
}

# Stop words to ignore in graph connections
GENERIC_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'genai', 'generative ai',
    'llm', 'gpt', 'tool', 'code', 'data', 'model', 'new', 'app', 'python', 'project',
    'using', 'via', 'show', 'hn', 'launch', 'release', 'agent', 'agents'
}


class GraphBuilder:
    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(self):
        if not os.path.exists(DB_PATH):
            return self.graph

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Fetch high-quality nodes only (>15 score)
        cursor.execute('''
            SELECT id, title, source_platform, found_keywords, trend_score, content
            FROM unified_posts 
            WHERE trend_score > 15
        ''')
        rows = cursor.fetchall()
        conn.close()

        # Step 1: Add Nodes
        for row in rows:
            post_id, title, platform, keywords_str, score, content = row

            keywords = [k.strip().lower() for k in keywords_str.split(',')] if keywords_str else []
            strong_keywords_set = set(keywords) - GENERIC_KEYWORDS
            strong_keywords_list = list(strong_keywords_set)

            node_color = PLATFORM_COLORS.get(platform, "#808080")
            short_label = title[:20] + "..." if len(title) > 20 else title

            # Create rich HTML tooltip
            if content:
                clean_content = content.replace('\n', ' ').replace('\r', '')
                preview_text = clean_content[:300] + "..." if len(clean_content) > 300 else clean_content
            else:
                preview_text = "No content preview."

            hover_text = (f"<b>{title}</b><br>"
                          f"<span style='color: gray;'>{platform} | Score: {score:.1f}</span><br><br>"
                          f"<b>Summary:</b><br><i>{preview_text}</i><br><br>"
                          f"<b>Keywords:</b> {', '.join(strong_keywords_list[:5])}")

            self.graph.add_node(post_id,
                                label=short_label,
                                title=hover_text,
                                color=node_color,
                                value=score,
                                group=platform,
                                strong_keys=strong_keywords_list)

            # Step 2: Add Edges (Connections based on shared keywords)
        nodes = list(self.graph.nodes(data=True))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                id1, data1 = nodes[i]
                id2, data2 = nodes[j]

                shared = set(data1['strong_keys']) & set(data2['strong_keys'])

                if len(shared) >= 1:
                    self.graph.add_edge(id1, id2, value=len(shared), title=f"Shared: {list(shared)}")

        # --- STATIC LAYOUT FIX (Anti-Dance) ---
        # We calculate positions HERE, in Python.
        if self.graph.number_of_nodes() > 0:
            # spring_layout calculates the X,Y coordinates
            pos = nx.spring_layout(self.graph, seed=42, k=0.8, iterations=100)

            for node, cords in pos.items():
                # Scale coordinates for PyVis
                self.graph.nodes[node]['x'] = cords[0] * 1000
                self.graph.nodes[node]['y'] = cords[1] * 1000
                self.graph.nodes[node]['physics'] = False  # Lock node in place

        return self.graph