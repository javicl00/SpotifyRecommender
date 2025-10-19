from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QGroupBox,
    QTabWidget,
)
from backend.recommender import get_recommendations, filter_by_genre
from backend.matcher import match_favs_with_features
from utils.fileloader import load_csv
import pandas as pd
import webbrowser


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recomendador Spotify")
        self.setStyleSheet("background-color: #222; color: #eee; font-size: 13px;")
        self.resize(1350, 800)
        self.user_favs = None
        self.tracks_ds = None
        self.merged_favs = None
        self.last_recs = None

        layout = QHBoxLayout()
        sidebar = QVBoxLayout()
        main_area = QVBoxLayout()

        self.lbl_info = QLabel(
            "Carga tu archivo de canciones gustadas y el dataset (CSV).\n"
            "Puedes filtrar por popularidad, año, género y obtener solo versiones únicas más populares."
        )
        self.lbl_info.setStyleSheet("font-weight: bold; border-bottom:1px solid white;")
        main_area.addWidget(self.lbl_info)

        self.btn_load_favs = QPushButton("Cargar My Spotify Library CSV")
        self.btn_load_favs.clicked.connect(self.load_fav_songs)
        sidebar.addWidget(self.btn_load_favs)

        self.btn_load_ds = QPushButton("Cargar Dataset de Tracks CSV")
        self.btn_load_ds.clicked.connect(self.load_dataset)
        sidebar.addWidget(self.btn_load_ds)

        self.popularity_in = QLineEdit()
        self.popularity_in.setPlaceholderText("Popularidad mínima [0-100]")
        sidebar.addWidget(self.popularity_in)

        self.year_min_in = QLineEdit()
        self.year_min_in.setPlaceholderText("Año mínimo (ej. 2000)")
        sidebar.addWidget(self.year_min_in)

        self.year_max_in = QLineEdit()
        self.year_max_in.setPlaceholderText("Año máximo (ej. 2022)")
        sidebar.addWidget(self.year_max_in)

        self.genre_in = QLineEdit()
        self.genre_in.setPlaceholderText("Filtrar por género (opcional)")
        sidebar.addWidget(self.genre_in)

        self.btn_match = QPushButton("Emparejar favoritas con atributos")
        self.btn_match.clicked.connect(self.match_attributes)
        sidebar.addWidget(self.btn_match)

        self.btn_recommend = QPushButton("Recomendar canciones únicas")
        self.btn_recommend.clicked.connect(self.recommend_songs)
        sidebar.addWidget(self.btn_recommend)

        self.btn_save = QPushButton("Guardar recomendaciones a CSV")
        self.btn_save.clicked.connect(self.save_recs)
        sidebar.addWidget(self.btn_save)

        sidebar.addStretch()
        layout.addLayout(sidebar)

        self.tabs = QTabWidget()
        self.tbl_result = QTableWidget()
        self.tbl_result.cellDoubleClicked.connect(self.open_spotify_link)
        self.tabs.addTab(self.tbl_result, "Recomendaciones")

        main_area.addWidget(self.tabs)
        layout.addLayout(main_area)
        self.setLayout(layout)

    def load_fav_songs(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Selecciona tu archivo de canciones gustadas (CSV)"
        )
        if fname:
            self.user_favs = load_csv(fname)
            QMessageBox.information(
                self, "Éxito", "Lista de favoritas cargada correctamente."
            )

    def load_dataset(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Selecciona el dataset tracks.csv")
        if fname:
            self.tracks_ds = load_csv(fname)
            QMessageBox.information(
                self, "Éxito", "Dataset de tracks cargado correctamente."
            )

    def match_attributes(self):
        if self.user_favs is not None and self.tracks_ds is not None:
            self.merged_favs = match_favs_with_features(self.user_favs, self.tracks_ds)
            count = len(self.merged_favs)
            if count == 0:
                QMessageBox.warning(
                    self, "Sin coincidencias", "No se encontraron coincidencias."
                )
            else:
                QMessageBox.information(
                    self, "Completado", f"Encontradas {count} favoritas en el dataset."
                )
        else:
            QMessageBox.warning(
                self, "Falta archivo", "Carga archivos antes de emparejar."
            )

    def recommend_songs(self):
        if self.merged_favs is None or self.tracks_ds is None:
            QMessageBox.warning(
                self, "Falta datos", "Busca primero los atributos de tus favoritas."
            )
            return

        attr_cols = [
            "danceability",
            "energy",
            "key",
            "loudness",
            "mode",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
            "valence",
            "tempo",
            "duration_ms",
        ]
        already_liked_ids = (
            set(self.user_favs["Spotify - id"])
            if "Spotify - id" in self.user_favs
            else set()
        )

        genre_filter = self.genre_in.text() or None
        filtered_tracks = self.tracks_ds.copy()
        if genre_filter:
            filtered_tracks = filter_by_genre(filtered_tracks, genre_filter)

        pop_min = self.popularity_in.text() or None
        year_min = self.year_min_in.text() or None
        year_max = self.year_max_in.text() or None
        recs = get_recommendations(
            self.merged_favs,
            filtered_tracks,
            attr_cols,
            topn=20,
            pop_min=pop_min,
            year_min=year_min,
            year_max=year_max,
            exclude_ids=already_liked_ids,
        )

        self.last_recs = recs
        cols = ["name", "artists", "sim", "popularity", "release_date", "id"]
        self.tbl_result.setRowCount(recs.shape[0])
        self.tbl_result.setColumnCount(len(cols))
        self.tbl_result.setHorizontalHeaderLabels(cols)
        for i, row in recs.iterrows():
            for j, col in enumerate(cols):
                self.tbl_result.setItem(i, j, QTableWidgetItem(str(row.get(col, ""))))
        self.tbl_result.resizeColumnsToContents()

    def save_recs(self):
        if self.last_recs is not None and not self.last_recs.empty:
            fname, _ = QFileDialog.getSaveFileName(
                self, "Guardar recomendaciones", "recs.csv"
            )
            if fname:
                self.last_recs.to_csv(fname, index=False)
                QMessageBox.information(
                    self, "Guardado", f"Recomendaciones guardadas en {fname}"
                )

    def open_spotify_link(self, row, col):
        rec = self.last_recs.iloc[row]
        if "id" in rec:
            url = f"https://open.spotify.com/track/{rec['id']}"
            webbrowser.open(url)
