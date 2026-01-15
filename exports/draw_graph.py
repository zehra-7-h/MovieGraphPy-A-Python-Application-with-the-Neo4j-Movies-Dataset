import json
import networkx as nx
import matplotlib.pyplot as plt

# graph.json dosyasını oku
with open("exports/graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

G = nx.Graph()

# Node'ları ekle
for node in data["nodes"]:
    G.add_node(node["id"], **node)

# Link'leri ekle
for link in data["links"]:
    G.add_edge(link["source"], link["target"], type=link["type"])

# Etiketleri hazırla (Film adı ve Kişi adı görünsün)
labels = {}
for node in data["nodes"]:
    if node["label"] == "Movie":
        labels[node["id"]] = node["title"]
    else:
        labels[node["id"]] = node["name"]

# Yerleşim
pos = nx.spring_layout(G, k=0.8)

# Grafı çiz
plt.figure(figsize=(10,8))
nx.draw(G, pos, with_labels=True, labels=labels, node_size=2000, font_size=8)

# Kenar etiketleri
edge_labels = nx.get_edge_attributes(G, 'type')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

plt.title("Film - Kişi Graf Görselleştirme")
plt.axis("off")
plt.show()
