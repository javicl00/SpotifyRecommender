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
from backend.spotify_auth import get_spotify_client, get_user_liked_tracks
from utils.dataset_loader import get_spotify_dataset
from backend.db_sqlite import init_db, save_user_profile, load_user_profile

st.set_page_config(page_title="🎧 Recomendador Spotify SSO", layout="wide")


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


init_db()

# -------------------------
#      LOGIN Y SSO
# -------------------------
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "spotify_user" not in st.session_state:
    st.session_state["spotify_user"] = None
if "favs_df" not in st.session_state:
    st.session_state["favs_df"] = None
if "liked_tracks" not in st.session_state:
    st.session_state["liked_tracks"] = []
if "disliked_tracks" not in st.session_state:
    st.session_state["disliked_tracks"] = []

st.markdown(
    """
<div style='text-align: center'>
    <h1>🎧 Spotify Music Recommender SSO</h1>
</div>
""",
    unsafe_allow_html=True,
)

st.sidebar.header("Inicio de sesión")
if not st.session_state["logged_in"]:
    if st.button("Iniciar sesión con Spotify"):
        sp = get_spotify_client()
        user_info = sp.current_user()
        st.session_state["spotify_user"] = {
            "id": user_info["id"],
            "email": user_info.get("email", ""),
            "name": user_info.get("display_name", ""),
        }
        st.session_state["user_id"] = user_info["id"]
        st.session_state["logged_in"] = True
        with st.spinner("Obteniendo tus canciones gustadas..."):
            liked_tracks = get_user_liked_tracks(sp, limit=200)
            st.session_state["favs_df"] = pd.DataFrame(liked_tracks)
        st.rerun()

else:
    st.sidebar.success(
        f"Sesión iniciada: {st.session_state['spotify_user']['name']} ({st.session_state['spotify_user']['email']})"
    )
    if st.sidebar.button("Cerrar sesión"):
        for k in [
            "user_id",
            "logged_in",
            "spotify_user",
            "favs_df",
            "liked_tracks",
            "disliked_tracks",
            "merged_favs",
            "recs",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

# -------------------------
#    CARGA DATASET NUBE
# -------------------------
tracks_df = get_spotify_dataset()
if tracks_df is None or tracks_df.empty:
    st.warning("No se pudo cargar el dataset de canciones.")
    st.stop()
else:
    st.success(f"Catálogo cargado: {len(tracks_df):,} canciones disponibles")

# -------------------------
#     LÓGICA RECOMENDADOR
# -------------------------
if st.session_state["logged_in"] and st.session_state["favs_df"] is not None:
    favs_df = st.session_state["favs_df"]

    # Recarga perfil likes/dislikes desde SQLite si existe
    profile = load_user_profile(st.session_state["user_id"])
    if profile:
        st.session_state["liked_tracks"] = profile["likes"]
        st.session_state["disliked_tracks"] = profile["dislikes"]

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

    # Emparejar favoritas automáticamente si no existe ya
    if "merged_favs" not in st.session_state:
        merged_favs = match_favs_with_features(favs_df, tracks_df)
        st.session_state["merged_favs"] = merged_favs
    merged_favs = st.session_state["merged_favs"]

    if not merged_favs.empty:
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

        # Estadísticas
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

        # Filtros de recomendación en sidebar
        with st.sidebar:
            st.header("🔍 Filtros personalizados")
            pop_min = st.slider("Popularidad mínima", 0, 100, 60)
            year_min = st.number_input("Año desde", 1950, 2025, 2000)
            year_max = st.number_input("Año hasta", 1950, 2025, 2025)
            genre_filter = st.text_input("Género (opcional)")
            if st.button("🎯 Obtener Recomendaciones", type="primary"):
                with st.spinner("Generando recomendaciones..."):
                    already_liked_ids = (
                        set(favs_df["Spotify - id"])
                        if "Spotify - id" in favs_df
                        else set()
                    )
                    filtered_tracks = tracks_df.copy()
                    if genre_filter:
                        filtered_tracks = filter_by_genre(filtered_tracks, genre_filter)

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
                    st.rerun()

        # Mostrar recomendaciones
        if "recs" in st.session_state:
            recs = st.session_state["recs"]
            st.header(f"🎵 Recomendaciones para ti ({len(recs)})")
            for idx, row in recs.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                    with col1:
                        cover_url = get_album_cover(row["id"])
                        if cover_url:
                            st.image(cover_url, width=100)
                    with col2:
                        st.markdown(f"**{row['name']}**")
                        st.caption(f"{row['artists']}")
                        st.markdown(
                            f"⭐ {row.get('popularity','')} • 📅 {row.get('release_date','')}"
                        )
                    with col3:
                        st.markdown(
                            f"[▶️ Escuchar](https://open.spotify.com/track/{row['id']})",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<iframe src="https://open.spotify.com/embed/track/{row["id"]}" width="140" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>',
                            unsafe_allow_html=True,
                        )
                    with col4:
                        col_like, col_dislike = st.columns(2)
                        with col_like:
                            if st.button("👍", key=f"like_{row['id']}"):
                                if row["id"] not in st.session_state["liked_tracks"]:
                                    st.session_state["liked_tracks"].append(row["id"])
                                    if row["id"] in st.session_state["disliked_tracks"]:
                                        st.session_state["disliked_tracks"].remove(
                                            row["id"]
                                        )
                                    st.rerun()
                        with col_dislike:
                            if st.button("👎", key=f"dislike_{row['id']}"):
                                if row["id"] not in st.session_state["disliked_tracks"]:
                                    st.session_state["disliked_tracks"].append(
                                        row["id"]
                                    )
                                    if row["id"] in st.session_state["liked_tracks"]:
                                        st.session_state["liked_tracks"].remove(
                                            row["id"]
                                        )
                                    st.rerun()
                    st.markdown("---")

            st.download_button(
                "📥 Descargar recomendaciones",
                recs.to_csv(index=False),
                "recomendaciones.csv",
                "text/csv",
            )

        # Guardar/recuperar preferencias multiusuario
        st.write("Likes actuales:", st.session_state.get("liked_tracks", []))
        st.write("Dislikes actuales:", st.session_state.get("disliked_tracks", []))
        if st.button("Guardar mi perfil ahora"):
            save_user_profile(
                st.session_state["user_id"],
                st.session_state["spotify_user"]["email"],
                st.session_state.get("liked_tracks", []),
                st.session_state.get("disliked_tracks", []),
            )
            st.success("Perfil guardado correctamente en SQLite.")

        if st.button("Recargar mi perfil guardado"):
            profile = load_user_profile(st.session_state["user_id"])
            if profile:
                st.session_state["liked_tracks"] = profile["likes"]
                st.session_state["disliked_tracks"] = profile["dislikes"]
                st.success("Perfil recargado!")
                st.rerun()
            else:
                st.warning("Todavía no tienes perfil guardado.")

else:
    st.info("Inicia sesión con Spotify para obtener recomendaciones personalizadas.")
