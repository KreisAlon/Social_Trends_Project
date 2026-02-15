import networkx as nx
import sqlite3
import os

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")

# Platform Color Coding for Visualization
PLATFORM_COLORS = {
    "GitHub": "#2dba4e",  # Green
    "Hacker News": "#ff6600",  # Orange
    "Mastodon": "#6364ff",  # Purple
    "Dev.to": "#000000"  # Black
}

# Stop-words to filter out generic connections
GENERIC_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'genai', 'generative ai',
    'llm', 'gpt', 'tool', 'code', 'data', 'model', 'new', 'app', 'python', 'project',
    'using', 'via', 'show', 'hn', 'launch', 'release', 'agent', 'agents',
    'source', 'open', 'web', 'chat', 'bot', 'system', 'learning'
}


class GraphBuilder:
    """
    Constructs a semantic network graph from trending posts.
    Nodes represent posts, and edges represent shared topics/keywords.
    """

    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(self):
        """
        Fetches top trends from the database and builds the NetworkX graph.
        Returns:
            nx.Graph: The constructed graph object with metadata.
        """
        if not os.path.exists(DB_PATH):
            return self.graph

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # --- VIP Filter: Top 40 Only ---
        # limiting to top 40 items ensures the graph remains readable and performant.
        cursor.execute('''
            SELECT id, title, source_platform, found_keywords, trend_score, content
            FROM unified_posts 
            ORDER BY trend_score DESC
            LIMIT 40
        ''')
        rows = cursor.fetchall()
        conn.close()

        # Step 1: Add Nodes (Vertices)
        for row in rows:
            post_id, title, platform, keywords_str, score, content = row

            # Parse and filter keywords
            keywords = [k.strip().lower() for k in keywords_str.split(',')] if keywords_str else []
            strong_keywords_list = [k for k in keywords if k not in GENERIC_KEYWORDS]

            node_color = PLATFORM_COLORS.get(platform, "#808080")

            # Truncate title for display label
            short_label = title[:15] + "..." if len(title) > 15 else title

            # Create rich HTML tooltip
            hover_text = (f"<b>{title}</b><br>"
                          f"<span style='color: gray;'>{platform} | Score: {score:.1f}</span><br>"
                          f"Keywords: {', '.join(strong_keywords_list[:3])}")

            # Dynamic node sizing based on Trend Score (Visual Hierarchy)
            node_size = score * 0.8

            self.graph.add_node(post_id,
                                label=short_label,
                                title=hover_text,
                                color=node_color,
                                value=node_size,
                                group=platform,
                                strong_keys=strong_keywords_list)

            # Step 2: Add Edges (Semantic Connections)
        nodes = list(self.graph.nodes(data=True))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                id1, data1 = nodes[i]
                id2, data2 = nodes[j]

                # Calculate intersection of keywords
                shared = set(data1['strong_keys']) & set(data2['strong_keys'])

                # Create an edge only if a strong semantic link exists
                if len(shared) >= 1:
                    width = len(shared) * 2  # Edge thickness indicates connection strength
                    self.graph.add_edge(id1, id2, value=width, title=f"Shared: {list(shared)}")

        # --- Static Layout Algorithm ---
        # Pre-calculating positions to prevent graph jittering in the UI
        if self.graph.number_of_nodes() > 0:
            # Spring layout simulation
            pos = nx.spring_layout(self.graph, seed=42, k=1.5, iterations=100)

            for node, cords in pos.items():
                # Scale coordinates for PyVis visualization
                self.graph.nodes[node]['x'] = cords[0] * 1000
                self.graph.nodes[node]['y'] = cords[1] * 1000
                self.graph.nodes[node]['physics'] = False  # Lock positions

        return self.graph