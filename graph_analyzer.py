import networkx as nx
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "trends_project.db")


class GraphBuilder:
    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(self):
        """
        בונה גרף שבו כל צומת הוא פוסט, וכל קשת מייצגת מילות מפתח משותפות.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # שולפים פוסטים חזקים בלבד (כדי לא להעמיס על הגרף)
        cursor.execute('''
            SELECT id, title, source_platform, found_keywords, trend_score 
            FROM unified_posts 
            WHERE trend_score > 50
        ''')
        rows = cursor.fetchall()
        conn.close()

        print(f"[Graph] Processing {len(rows)} nodes for connections...")

        # 1. הוספת צמתים (Nodes)
        for row in rows:
            post_id, title, platform, keywords_str, score = row
            keywords = keywords_str.split(',') if keywords_str else []

            # מוסיפים את הפוסט כצומת בגרף
            self.graph.add_node(post_id,
                                title=title,
                                platform=platform,
                                score=score,
                                keywords=keywords)

        # 2. הוספת קשתות (Edges) - החלק "הכבד"
        # אנחנו בודקים למי יש מילים משותפות
        nodes = list(self.graph.nodes(data=True))

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                id1, data1 = nodes[i]
                id2, data2 = nodes[j]

                # חישוב חיתוך (Intersection) בין מילות המפתח
                shared_keywords = set(data1['keywords']) & set(data2['keywords'])

                # אם יש לפחות מילה אחת משותפת - יוצרים קשר
                if len(shared_keywords) > 0:
                    weight = len(shared_keywords)
                    self.graph.add_edge(id1, id2, weight=weight, common=list(shared_keywords))

        print(
            f"[Graph] Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        return self.graph

    def get_centrality(self):
        """
        מחזיר את הפוסטים הכי 'מקושרים' ברשת (Degree Centrality)
        """
        if not self.graph.number_of_nodes():
            return {}
        return nx.degree_centrality(self.graph)


if __name__ == "__main__":
    # בדיקה ידנית
    gb = GraphBuilder()
    G = gb.build_graph()
    print("Top Connections:", sorted(G.degree, key=lambda x: x[1], reverse=True)[:5])