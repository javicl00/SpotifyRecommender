import warnings
import logging

warnings.filterwarnings("ignore")
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(
    logging.ERROR
)

import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt
from backend.recommender import get_recommendations, filter_by_genre
from backend.matcher import match_favs_with_features
from utils.fileloader import load_csv
import streamlit as st
from backend.db_sqlite import init_db, save_user_profile, load_user_profile

st.set_page_config(page_title="🎧 Recomendador Spotify", layout="wide")


def get_album_cover(track_id):
    url = (
        f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    )
    try:
        resp = requests.get(url, timeout=5)
        if resp.ok:
            return resp.json().get("thumbnail_url", "")
    except:
        return ""
    return ""


st.title("🎧 Recomendador Avanzado de Spotify con Feedback Dinámico")
st.markdown(
    """
Importa tus canciones gustadas y el dataset, filtra por popularidad, año o género y obtén recomendaciones únicas.
**Nuevo:** Dale 👍 o 👎 a las recomendaciones para mejorar dinámicamente tu perfil musical.
"""
)

# Inicializar estado de likes/dislikes
if "liked_tracks" not in st.session_state:
    st.session_state["liked_tracks"] = []
if "disliked_tracks" not in st.session_state:
    st.session_state["disliked_tracks"] = []

uploaded_favs = st.file_uploader("Archivo de canciones gustadas (CSV)", type="csv")
uploaded_tracks = st.file_uploader("Dataset de tracks Spotify (CSV)", type="csv")


@st.cache_data
def load_data(file):
    return pd.read_csv(file, engine="pyarrow")


if uploaded_favs:
    st.session_state["favs_df"] = load_data(uploaded_favs)
if uploaded_tracks:
    st.session_state["tracks_df"] = load_data(uploaded_tracks)

if "favs_df" in st.session_state and "tracks_df" in st.session_state:
    favs_df = st.session_state["favs_df"]
    tracks_df = st.session_state["tracks_df"]

    st.success(f"Cargados {len(favs_df)} favoritos y {len(tracks_df)} tracks.")

    # Mostrar estadísticas de feedback
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        st.metric("👍 Likes", len(st.session_state["liked_tracks"]))
    with col_stats2:
        st.metric("👎 Dislikes", len(st.session_state["disliked_tracks"]))

    with st.expander("Ver muestra de tus canciones gustadas"):
        st.dataframe(favs_df.head())

    if "merged_favs" not in st.session_state:
        if st.button("Emparejar favoritas con atributos"):
            with st.spinner("Emparejando..."):
                merged_favs = match_favs_with_features(favs_df, tracks_df)
                st.session_state["merged_favs"] = merged_favs
                st.info(f"{len(merged_favs)} favoritas emparejadas.")
    else:
        merged_favs = st.session_state["merged_favs"]

    if "merged_favs" in st.session_state and not merged_favs.empty:
        st.header("🎼 Tu perfil musical extraído")

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

        perfil_media = merged_favs[attr_cols].mean()
        norm_perfil = perfil_media.copy()
        norm_perfil["duration_ms"] = perfil_media["duration_ms"] / 60000
        for col in [
            "danceability",
            "energy",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
            "valence",
        ]:
            norm_perfil[col] = perfil_media[col] * 10
        norm_perfil["tempo"] = perfil_media["tempo"] * 10 / 200
        norm_perfil["key"] = perfil_media["key"] * 10 / 11
        norm_perfil["loudness"] = (perfil_media["loudness"] + 60) * 10 / 60
        norm_perfil["mode"] = perfil_media["mode"] * 10

        rename_map = {
            "danceability": "Bailabilidad",
            "energy": "Energía",
            "key": "Tono",
            "loudness": "Volumen",
            "mode": "Modo",
            "speechiness": "Habla",
            "acousticness": "Acústico",
            "instrumentalness": "Instrumentalidad",
            "liveness": "Directo",
            "valence": "Positividad",
            "tempo": "Tempo",
            "duration_ms": "Duración (min)",
        }
        radar_data = pd.DataFrame(
            {
                "attribute": [rename_map.get(col, col) for col in norm_perfil.index],
                "score": norm_perfil.values,
            }
        )

        chart = (
            alt.Chart(radar_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("attribute:N", sort=list(rename_map.values())),
                y=alt.Y("score:Q", scale=alt.Scale(domain=[0, 10])),
            )
            .properties(width=700, height=380)
        )
        st.altair_chart(chart, use_container_width=True)

        colA, colB = st.columns(2)
        with colA:
            if "genre" in merged_favs and not merged_favs["genre"].isna().all():
                genre_counts = merged_favs["genre"].value_counts().head(10)
                if not genre_counts.empty:
                    st.subheader("Tus géneros favoritos")
                    genre_chart = (
                        alt.Chart(genre_counts.reset_index())
                        .mark_bar()
                        .encode(
                            x=alt.X("genre:N", title="Género"),
                            y=alt.Y("count:Q", title="Cantidad"),
                        )
                        .properties(width=300, height=250)
                    )
                    st.altair_chart(genre_chart, use_container_width=True)
        with colB:
            if "release_date" in merged_favs:
                years = pd.to_datetime(
                    merged_favs["release_date"], errors="coerce"
                ).dt.year
                years_counts = years.value_counts().sort_index()
                if not years_counts.empty:
                    st.subheader("Distribución por años")
                    years_df = years_counts.reset_index()
                    years_df.columns = ["year", "count"]
                    years_chart = (
                        alt.Chart(years_df)
                        .mark_bar()
                        .encode(
                            x=alt.X("year:Q", title="Año"),
                            y=alt.Y("count:Q", title="Cantidad"),
                        )
                        .properties(width=300, height=250)
                    )
                    st.altair_chart(years_chart, use_container_width=True)

        st.header("🔍 Filtros de recomendación")
        pop_min = st.slider("Popularidad mínima", 0, 100, 60)
        year_min = st.number_input("Año mínimo", 1900, 2025, 2000)
        year_max = st.number_input("Año máximo", 1900, 2025, 2025)
        genre_filter = st.text_input("Género (opcional)")

        already_liked_ids = (
            set(favs_df["Spotify - id"]) if "Spotify - id" in favs_df else set()
        )
        filtered_tracks = tracks_df.copy()
        if genre_filter:
            filtered_tracks = filter_by_genre(filtered_tracks, genre_filter)

        if st.button("Obtener recomendaciones únicas"):
            with st.spinner("Calculando recomendaciones con feedback dinámico..."):
                # Construir DataFrames de likes/dislikes
                liked_df = pd.DataFrame()
                disliked_df = pd.DataFrame()

                if st.session_state["liked_tracks"]:
                    liked_df = tracks_df[
                        tracks_df["id"].isin(st.session_state["liked_tracks"])
                    ]
                if st.session_state["disliked_tracks"]:
                    disliked_df = tracks_df[
                        tracks_df["id"].isin(st.session_state["disliked_tracks"])
                    ]

                recs = get_recommendations(
                    merged_favs,
                    filtered_tracks,
                    attr_cols,
                    topn=20,
                    pop_min=pop_min,
                    year_min=year_min,
                    year_max=year_max,
                    exclude_ids=already_liked_ids,
                    liked_tracks=liked_df if not liked_df.empty else None,
                    disliked_tracks=disliked_df if not disliked_df.empty else None,
                )
                st.session_state["recs"] = recs

        if "recs" in st.session_state:
            recs = st.session_state["recs"]
            st.subheader(f"🎵 Top {len(recs)} recomendaciones")
            for idx, row in recs.iterrows():
                col1, col2, col3, col4 = st.columns([2, 4, 2, 1])
                with col1:
                    cover_url = get_album_cover(row["id"])
                    if cover_url:
                        st.image(cover_url, width=120)
                with col2:
                    st.markdown(f"**{row['name']}**")
                    st.markdown(f"*{row['artists']}*")
                    st.markdown(
                        f":star: Popularidad: {row.get('popularity','')}, Año: {row.get('release_date','')}"
                    )
                    st.markdown(
                        f"[Escuchar en Spotify](https://open.spotify.com/track/{row['id']})"
                    )
                with col3:
                    st.markdown(
                        f'<iframe src="https://open.spotify.com/embed/track/{row["id"]}" width="140" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>',
                        unsafe_allow_html=True,
                    )
                with col4:
                    # Botones de feedback
                    if st.button("👍", key=f"like_{row['id']}"):
                        if row["id"] not in st.session_state["liked_tracks"]:
                            st.session_state["liked_tracks"].append(row["id"])
                            if row["id"] in st.session_state["disliked_tracks"]:
                                st.session_state["disliked_tracks"].remove(row["id"])
                            st.rerun()

                    if st.button("👎", key=f"dislike_{row['id']}"):
                        if row["id"] not in st.session_state["disliked_tracks"]:
                            st.session_state["disliked_tracks"].append(row["id"])
                            if row["id"] in st.session_state["liked_tracks"]:
                                st.session_state["liked_tracks"].remove(row["id"])
                            st.rerun()

            st.write("---")
            st.dataframe(
                recs[["name", "artists", "sim", "popularity", "release_date", "id"]]
            )
            st.download_button(
                "Descargar CSV",
                recs.to_csv(index=False),
                file_name="recs.csv",
                mime="text/csv",
            )

            # Botón para reiniciar feedback
            if st.button("🔄 Reiniciar likes/dislikes"):
                st.session_state["liked_tracks"] = []
                st.session_state["disliked_tracks"] = []
                st.rerun()
    else:
        st.warning("Debes emparejar tus favoritas con atributos para continuar.")

else:
    st.warning("Sube ambos archivos para empezar.")

import streamlit as st
from backend.db_sqlite import init_db, save_user_profile, load_user_profile
import pandas as pd

init_db()

st.set_page_config(page_title="Spotify Recommender Multiusuario", layout="wide")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🎧 Spotify Recommender (Login)")
    st.session_state["user_id"] = st.text_input(
        "Introduce tu usuario/alias/correo único", key="usuario_login"
    )
    if st.button("Empezar sesión"):
        if st.session_state["user_id"]:
            st.session_state["logged_in"] = True
            st.success(f"¡Bienvenido/a {st.session_state['user_id']}!")
            st.rerun()
        else:
            st.warning("Debes introducir un usuario/alias único.")

else:
    st.sidebar.success(f"Usuario: {st.session_state['user_id']}")

    # Cargar perfil si existe (likes/dislikes)
    profile = load_user_profile(st.session_state["user_id"])
    if profile:
        if "liked_tracks" not in st.session_state:
            st.session_state["liked_tracks"] = profile["likes"]
        if "disliked_tracks" not in st.session_state:
            st.session_state["disliked_tracks"] = profile["dislikes"]

    # --- Aquí iría el resto de tu app (filtros, recomendaciones, etc) ---
    st.write("Aquí va tu dashboard y recomendaciones...")

    st.write("Likes actuales:", st.session_state.get("liked_tracks", []))
    st.write("Dislikes actuales:", st.session_state.get("disliked_tracks", []))

    # Guardar
    if st.button("Guardar mi perfil ahora"):
        save_user_profile(
            st.session_state["user_id"],
            st.session_state["user_id"],
            st.session_state.get("liked_tracks", []),
            st.session_state.get("disliked_tracks", []),
        )
        st.success("Perfil guardado correctamente en SQLite.")

    # Recargar
    if st.button("Recargar mi perfil guardado"):
        profile = load_user_profile(st.session_state["user_id"])
        if profile:
            st.session_state["liked_tracks"] = profile["likes"]
            st.session_state["disliked_tracks"] = profile["dislikes"]
            st.success("Perfil recargado!")
        else:
            st.warning("Todavía no tienes perfil guardado.")

    if st.button("Cerrar sesión"):
        for k in ["user_id", "logged_in", "liked_tracks", "disliked_tracks"]:
            st.session_state.pop(k, None)
        st.rerun()
