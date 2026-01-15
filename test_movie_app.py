import unittest
from unittest.mock import patch, MagicMock
from movie_app import MovieGraphApp


class TestMovieGraphApp(unittest.TestCase):

    # --- Başlangıçta bağlantı testi ---
    @patch("movie_app.GraphDatabase.driver")
    def test_connection_success(self, mock_driver):
        mock_driver_instance = MagicMock()
        mock_driver_instance.verify_connectivity.return_value = True
        mock_driver.return_value = mock_driver_instance
        
        with patch("builtins.print") as mock_print:
            app = MovieGraphApp("bolt://localhost:7687", "neo4j", "1234")
            
            # Başarılı bağlantı mesajını kontrol et
            mock_print.assert_any_call("✅ Neo4j bağlantisi basarili!")
            self.assertIsNotNone(app.driver)
            app.close()

    # --- Bağlantı hatası testi ---
    @patch("movie_app.GraphDatabase.driver")
    def test_connection_failure(self, mock_driver):
        mock_driver.side_effect = Exception("Connection failed")
        
        with patch("builtins.print") as mock_print:
            app = MovieGraphApp("bolt://localhost:7687", "neo4j", "1234")
            
            mock_print.assert_any_call("❌ Neo4j'e baglanilamadi.")
            mock_print.assert_any_call("Ana menüye dönülüyor...")
            self.assertIsNone(app.driver)

    # --- Boş film araması testi (driver yok) ---
    @patch("builtins.input", return_value="")
    def test_search_movie_no_driver(self, mock_input):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        app.driver = None
        
        with patch("builtins.print") as mock_print:
            app.search_movie()
            mock_print.assert_any_call("⚠️ Veritabani bağlantisi yok.")

    # --- Film seçimi testi ---
    @patch("builtins.input", side_effect=["1"])
    def test_select_movie(self, mock_input):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        
        fake_movies = [
            {'title': 'The Matrix', 'released': 1999}
        ]
        
        app.select_movie_from_list(fake_movies)
        self.assertEqual(app.selected_movie_title, "The Matrix")

    # --- Geçersiz seçim testi ---
    @patch("builtins.input", side_effect=["10", "0"])  # Geçersiz, sonra iptal
    def test_select_movie_invalid_choice(self, mock_input):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        
        fake_movies = [
            {'title': 'The Matrix', 'released': 1999}
        ]
        
        app.select_movie_from_list(fake_movies)
        self.assertIsNone(app.selected_movie_title)  # Seçilmiş film olmamalı

    # --- JSON üretme testi ---
    @patch("movie_app.os.makedirs")
    @patch("movie_app.os.path.exists", return_value=False)
    @patch("movie_app.GraphDatabase.driver")
    def test_create_graph_json(self, mock_driver, mock_exists, mock_makedirs):
        # Sahte session ve query sonucu
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
        
        # Sahte Neo4j record
        fake_movie = MagicMock()
        fake_movie.__getitem__.side_effect = lambda key: {"title": "Matrix", "released": 1999}[key]
        
        fake_person = MagicMock()
        fake_person.__getitem__.side_effect = lambda key: {"name": "Keanu Reeves"}[key]
        
        mock_record = MagicMock()
        mock_record.__getitem__.side_effect = lambda key: {
            "m": fake_movie,
            "p": fake_person,
            "rel_type": "ACTED_IN"
        }[key]
        
        mock_session.run.return_value = [mock_record]

        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        app.driver = mock_driver.return_value
        app.selected_movie_title = "Matrix"

        # JSON dosyası yazmayı engellemek için open mock
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            with patch("json.dump") as mock_json_dump:
                with patch("builtins.print") as mock_print:
                    app.create_graph_json()
                    
                    # Kontroller
                    mock_file.assert_called_once_with("exports/graph.json", "w", encoding="utf-8")
                    mock_print.assert_any_call("✅ graph.json oluşturuldu → exports/graph.json")

    # --- Detay gösterme testi (seçili film yok) ---
    def test_show_details_no_movie_selected(self):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        app.selected_movie_title = None
        app.driver = MagicMock()  # Driver var ama film seçili değil
        
        with patch("builtins.print") as mock_print:
            app.show_details()
            # NOT: Türkçe karakterlere dikkat! "ç" kullanılıyor
            mock_print.assert_any_call("⚠️ Önce film arayip seçmelisiniz.")

    # --- Detay gösterme testi (driver yok) ---
    def test_show_details_no_driver(self):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        app.driver = None
        app.selected_movie_title = "The Matrix"
        
        with patch("builtins.print") as mock_print:
            app.show_details()
            mock_print.assert_any_call("⚠️ Veritabani bağlantisi yok.")

    # --- Arama sonucu yoksa ekleme teklifi testi ---
    @patch("builtins.input", side_effect=["H"])  # Hayır diyor
    @patch("movie_app.GraphDatabase.driver")
    def test_search_movie_no_results(self, mock_driver, mock_input):
        app = MovieGraphApp("bolt://test:7687", "neo4j", "1234")
        
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []  # Boş sonuç
        
        app.driver = mock_driver.return_value
        
        with patch("builtins.print") as mock_print:
            # İlk input arama terimi, ikincisi ekleme teklifi için "H"
            with patch("builtins.input", side_effect=["Varolmayan Film", "H"]):
                app.search_movie()
                
            mock_print.assert_any_call("❌ Sonuç bulunamadi.")


if __name__ == "__main__":
    unittest.main()
    