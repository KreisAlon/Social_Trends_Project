import networkx as nx
import sqlite3
import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --- Path Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) if "ui" in CURRENT_DIR else CURRENT_DIR
DB_PATH = os.path.join(PROJECT_ROOT, "trends_project.db")

# Platform UI Branding Colors
PLATFORM_COLORS = {
    "GitHub": "#2dba4e",
    "Hacker News": "#ff6600",
    "Mastodon": "#7c6ff7",
    "Dev.to": "#333333"
}


class GraphBuilder:
    """
    Constructs a semantic knowledge graph from database embeddings.
    Designed for circular/spiral visualizations and cross-platform discovery.
    """

    def __init__(self, cross_threshold=0.55, same_platform_threshold=0.85):
        self.cross_threshold = cross_threshold
        self.same_threshold = same_platform_threshold
        self.graph = nx.Graph()

    def build_graph(self):
        """Builds the network graph by calculating semantic similarity between posts."""
        if not os.path.exists(DB_PATH):
            return self.graph

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Balanced Sampling: Fetching top trends per platform to avoid bias
        platforms = ["GitHub", "Hacker News", "Dev.to", "Mastodon"]
        all_rows = []
        for p in platforms:
            cursor.execute('''
                SELECT id, title, source_platform, trend_score, embedding, url
                FROM unified_posts 
                WHERE source_platform = ? AND embedding IS NOT NULL
                ORDER BY trend_score DESC LIMIT 15
            ''', (p,))
            all_rows.extend(cursor.fetchall())
        conn.close()

        if not all_rows: return self.graph

        nodes_info, embeddings = [], []

        # --- Step 1: Intelligent Node Creation ---
        for row in all_rows:
            p_id, title, platform, score, emb_str, url = row
            try:
                emb = json.loads(emb_str)
                nodes_info.append({'id': p_id, 'platform': platform, 'title': title, 'url': url})
                embeddings.append(emb)

                self.graph.add_node(
                    p_id,
                    label=(title[:20] + '...') if len(title) > 20 else title,
                    title=f"<b>{title}</b><br>Source: {platform}<br>Trend: {score:.1f}",
                    color=PLATFORM_COLORS.get(platform, "#888"),
                    value=max(score * 0.8, 12),
                    group=platform
                )
            except (json.JSONDecodeError, TypeError, Exception):
                continue

        # --- Step 2: Semantic Bridge Linking ---
        if len(embeddings) > 1:
            emb_matrix = np.array(embeddings)
            sim_matrix = cosine_similarity(emb_matrix)

            for i in range(len(nodes_info)):
                for j in range(i + 1, len(nodes_info)):
                    sim_score = float(sim_matrix[i][j])
                    p1, p2 = nodes_info[i]['platform'], nodes_info[j]['platform']
                    is_cross = p1 != p2

                    threshold = self.cross_threshold if is_cross else self.same_threshold

                    if sim_score >= threshold:
                        # Storing 'weight' is critical for the sorting logic in app.py
                        self.graph.add_edge(
                            nodes_info[i]['id'], nodes_info[j]['id'],
                            weight=sim_score,
                            value=(sim_score - threshold + 0.1) * 15,
                            color="#4a90e2" if is_cross else "#d3d3d3",
                            title=f"Match: {sim_score * 100:.1f}%",
                            is_cross=is_cross
                        )

        # --- Step 3: Layout Configuration ---
        if self.graph.number_of_nodes() > 0:
            pos = nx.circular_layout(self.graph, scale=1000)
            for node, coords in pos.items():
                self.graph.nodes[node]['x'], self.graph.nodes[node]['y'] = coords[0], coords[1]
                self.graph.nodes[node]['physics'] = False

        return self.graph