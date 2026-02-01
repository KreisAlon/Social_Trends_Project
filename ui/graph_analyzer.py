import networkx as nx
import sqlite3
import os

# --- Path Configuration ---
# Since this file is inside the 'ui/' folder, we need to navigate up one level
# to locate the 'trends_project.db' database file.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

# Platform Color Schema for Visualization
PLATFORM_COLORS = {
    "GitHub": "#2dba4e",  # GitHub Green
    "Hacker News": "#ff6600",  # HN Orange
    "Mastodon": "#6364ff",  # Mastodon Purple
    "Dev.to": "#000000"  # Dev.to Black
}

# Stop-words list: Generic terms to ignore during connection building.
# We only want connections based on specific, meaningful topics.
GENERIC_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'genai', 'generative ai',
    'llm', 'gpt', 'tool', 'code', 'data', 'model', 'new', 'app', 'python', 'project',
    'using', 'via', 'show', 'hn'
}


class GraphBuilder:
    """
    Builds a semantic network graph connecting posts from different platforms.
    Nodes = Posts
    Edges = Shared meaningful keywords
    """

    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(self):
        """
        Fetches high-trending posts from the DB and constructs the graph.
        """
        if not os.path.exists(DB_PATH):
            print(f"[Graph] Error: Database not found at {DB_PATH}")
            return self.graph

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Fetch high-scoring posts (Trend Score > 15) to reduce noise
        # We also fetch 'content' to display a summary in the tooltip
        cursor.execute('''
            SELECT id, title, source_platform, found_keywords, trend_score, content
            FROM unified_posts 
            WHERE trend_score > 15
        ''')
        rows = cursor.fetchall()
        conn.close()

        print(f"[Graph] Processing {len(rows)} nodes...")

        # --- Step 1: Add Nodes ---
        for row in rows:
            post_id, title, platform, keywords_str, score, content = row

            # Process keywords
            keywords = [k.strip().lower() for k in keywords_str.split(',')] if keywords_str else []
            strong_keywords_set = set(keywords) - GENERIC_KEYWORDS

            # Visual styling
            node_color = PLATFORM_COLORS.get(platform, "#808080")
            short_label = title[:20] + "..." if len(title) > 20 else title

            # Content Summary for Tooltip
            if content:
                # Clean newlines for cleaner HTML display
                clean_content = content.replace('\n', ' ').replace('\r', '')
                preview_text = clean_content[:350] + "..." if len(clean_content) > 350 else clean_content
            else:
                preview_text = "No content preview available."

            # Construct HTML Tooltip
            hover_text = (f"<b>{title}</b><br>"
                          f"<span style='color: gray;'>{platform} | Score: {score:.1f}</span><br><br>"
                          f"<b>Summary:</b><br><i>{preview_text}</i><br><br>"
                          f"<b>Keywords:</b> {', '.join(list(strong_keywords_set)[:5])}")

            # Add Node to Graph
            # Note: We convert strong_keys to a list because sets are not JSON serializable by PyVis
            self.graph.add_node(post_id,
                                label=short_label,
                                title=hover_text,
                                color=node_color,
                                value=score,
                                group=platform,
                                strong_keys=list(strong_keywords_set))

            # --- Step 2: Add Edges (Connections) ---
        nodes = list(self.graph.nodes(data=True))

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                id1, data1 = nodes[i]
                id2, data2 = nodes[j]

                # Retrieve keywords (convert back to set for intersection)
                set1 = set(data1['strong_keys'])
                set2 = set(data2['strong_keys'])

                # Find shared topics
                shared = set1 & set2

                # Connection Threshold: At least 1 meaningful keyword shared
                MIN_COMMON_WORDS = 1

                if len(shared) >= MIN_COMMON_WORDS:
                    weight = len(shared)
                    # Edge thickness depends on how many words they share
                    self.graph.add_edge(id1, id2,
                                        value=weight,
                                        title=f"Shared Topics: {', '.join(list(shared))}")

        return self.graph