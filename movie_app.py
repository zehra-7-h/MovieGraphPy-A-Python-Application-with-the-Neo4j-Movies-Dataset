from neo4j import GraphDatabase
import json
import os

class MovieGraphApp:
    def __init__(self, uri, user, password):
        self.driver = None
        self.selected_movie_title = None
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("✅ Neo4j bağlantisi basarili!")
        except Exception as e:
            print("❌ Neo4j'e baglanilamadi.")
            print("Detay:", e)
            print("Ana menüye dönülüyor...")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    # ---------------- Film Arama ----------------
    def search_movie(self):
        if not self.driver:
            print("⚠️ Veritabani bağlantisi yok.")
            return

        term = input("\n🔎 Aranacak film adi: ").strip()
        if not term:
            print("⚠️ Lütfen boş giriş yapmayiniz.")
            return

        query = """
        MATCH (m:Movie)
        WHERE toLower(m.title) CONTAINS toLower($term)
        RETURN m.title AS title, m.released AS released
        ORDER BY m.title
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, term=term)
                movies = list(result)

                # --- SONUÇ YOKSA EKLEME TEKLİFİ ---
                if not movies:
                    print("❌ Sonuç bulunamadi.")
                    add_choice = input("Bu filmi veritabanina eklemek ister misiniz? (E/H): ").strip().lower()
                    if add_choice == "e":
                        self.add_movie_direct(term)
                    return

                print("\n--- Arama Sonuçlari ---")
                for i, record in enumerate(movies, 1):
                    print(f"{i}) {record['title']} ({record['released']})")

                self.select_movie_from_list(movies)

        except Exception as e:
            print("⚠️ Arama sirasinda hata oluştu:", e)

    # ---------------- Gelişmiş Film Ekleme ----------------
    def add_movie_direct(self, title):
        print("\n🎬 Yeni Film Bilgilerini Giriniz")

        year = input("Çikiş yili: ").strip()
        if not year.isdigit():
            print("⚠️ Geçerli yil girilmedi. Ekleme iptal edildi.")
            return

        tagline = input("Tagline (boş birakilabilir): ").strip()
        director = input("Yönetmen adi: ").strip()

        actors_input = input("Oyuncular (virgülle ayiriniz): ").strip()
        actor_list = [a.strip() for a in actors_input.split(",") if a.strip()]

        query = """
        CREATE (m:Movie {title:$title, released:$year, tagline:$tagline})
        WITH m
        MERGE (d:Person {name:$director})
        MERGE (d)-[:DIRECTED]->(m)
        WITH m
        UNWIND $actors AS actorName
        MERGE (p:Person {name:actorName})
        MERGE (p)-[:ACTED_IN]->(m)
        """

        try:
            with self.driver.session() as session:
                session.run(query,
                            title=title,
                            year=int(year),
                            tagline=tagline,
                            director=director,
                            actors=actor_list)

            print(f"✅ '{title}' filmi tüm bilgileriyle veritabanina eklendi.")
            print("🔎 Şimdi tekrar film aramasi yapabilirsiniz.")

        except Exception as e:
            print("⚠️ Film ekleme sirasinda hata:", e)

    # ---------------- Film Seçimi ----------------
    def select_movie_from_list(self, movies_list):
        while True:
            choice = input("\nSeçmek istediğiniz filmin numarasi (İptal: 0): ")

            if not choice.isdigit():
                print("⚠️ Lütfen geçerli bir sayı giriniz.")
                continue

            choice = int(choice)

            if choice == 0:
                return

            if 1 <= choice <= len(movies_list):
                self.selected_movie_title = movies_list[choice - 1]['title']
                print(f"✅ Seçilen Film: {self.selected_movie_title}")
                return
            else:
                print("⚠️ Geçersiz numara. Tekrar deneyiniz.")

    # ---------------- Film Detayı ----------------
    def show_details(self):
        if not self.driver:
            print("⚠️ Veritabani bağlantisi yok.")
            return

        if not self.selected_movie_title:
            print("⚠️ Önce film arayip seçmelisiniz.")
            return

        query = """
        MATCH (m:Movie {title:$title})
        OPTIONAL MATCH (p:Person)-[:ACTED_IN]->(m)
        OPTIONAL MATCH (d:Person)-[:DIRECTED]->(m)
        RETURN m.title AS title,
               m.released AS released,
               m.tagline AS tagline,
               collect(DISTINCT p.name)[..5] AS actors,
               collect(DISTINCT d.name) AS directors
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, title=self.selected_movie_title)
                record = result.single()

                if not record:
                    print("❌ Film bulunamadi.")
                    return

                print("\n🎬 FİLM DETAYI")
                print("Ad:", record["title"])
                print("Yil:", record["released"])
                print("Tagline:", record["tagline"] if record["tagline"] else "Yok")

                print("\n🎥 Yönetmen(ler):")
                if record["directors"]:
                    for d in record["directors"]:
                        print(" -", d)
                else:
                    print(" - Bilgi yok")

                print("\n🎭 Oyuncular (İlk 5):")
                if record["actors"]:
                    for a in record["actors"]:
                        print(" -", a)
                else:
                    print(" - Bilgi yok")

        except Exception as e:
            print("⚠️ Detay gösterme sirasinda hata:", e)

    # ---------------- Graph JSON ----------------
    def create_graph_json(self):
        if not self.driver:
            print("⚠️ Veritabani bağlantisi yok.")
            return

        if not self.selected_movie_title:
            print("⚠️ Önce film seçmelisiniz.")
            return

        if not os.path.exists("exports"):
            os.makedirs("exports")

        query = """
        MATCH (m:Movie {title:$title})
        OPTIONAL MATCH (p:Person)-[r:ACTED_IN|DIRECTED]->(m)
        RETURN m, p, type(r) AS rel_type
        """

        nodes = []
        links = []
        node_id_map = {}
        node_counter = 0

        try:
            with self.driver.session() as session:
                result = session.run(query, title=self.selected_movie_title)

                for record in result:
                    movie_node = record["m"]
                    person_node = record["p"]
                    rel_type = record["rel_type"]

                    m_key = "Movie:" + movie_node["title"]
                    if m_key not in node_id_map:
                        node_counter += 1
                        node_id_map[m_key] = node_counter
                        nodes.append({
                            "id": node_counter,
                            "label": "Movie",
                            "title": movie_node["title"],
                            "released": movie_node["released"]
                        })

                    if person_node:
                        p_key = "Person:" + person_node["name"]
                        if p_key not in node_id_map:
                            node_counter += 1
                            node_id_map[p_key] = node_counter
                            nodes.append({
                                "id": node_counter,
                                "label": "Person",
                                "name": person_node["name"]
                            })

                        links.append({
                            "source": node_id_map[p_key],
                            "target": node_id_map[m_key],
                            "type": rel_type
                        })

            output = {"nodes": nodes, "links": links}

            file_path = "exports/graph.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, ensure_ascii=False)

            print(f"✅ graph.json oluşturuldu → {file_path}")
            print(f"📊 {len(nodes)} düğüm, {len(links)} ilişki yazildi.")

        except Exception as e:
            print("⚠️ JSON oluşturma sirasinda hata:", e)

    # ---------------- Menü ----------------
    def run(self):
        while True:
            print("\n==============================")
            print("Seçili Film:", self.selected_movie_title if self.selected_movie_title else "YOK")
            print("==============================")
            print("1) Film Ara")
            print("2) Film Detayi Göster")
            print("3) Seçili Film için graph.json Oluştur")
            print("4) Çikiş")

            choice = input("Seçiminiz: ")

            if choice == "1":
                self.search_movie()
            elif choice == "2":
                self.show_details()
            elif choice == "3":
                self.create_graph_json()
            elif choice == "4":
                print("👋 Program sonlandirildi.")
                self.close()
                break
            else:
                print("⚠️ Geçersiz seçim, tekrar deneyiniz.")


# ---------------- Program Başlangıç ----------------
if __name__ == "__main__":
    URI = "neo4j://localhost:7687"
    USER = "neo4j"
    PASSWORD = "zehrareyhan1"

    app = MovieGraphApp(URI, USER, PASSWORD)
    app.run()
