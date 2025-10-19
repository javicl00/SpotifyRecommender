import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from multiprocessing import Pool, cpu_count


def compute_similarity_chunk(args):
    chunk, fav_mean = args
    return cosine_similarity(chunk, fav_mean).flatten()


def parallel_similarity_multicore(ds_scaled, fav_mean, n_workers=None):
    if n_workers is None:
        n_workers = cpu_count()

    chunk_size = int(np.ceil(ds_scaled.shape[0] / n_workers))
    chunks = [
        ds_scaled[i : i + chunk_size] for i in range(0, ds_scaled.shape[0], chunk_size)
    ]

    with Pool(processes=n_workers) as pool:
        results = pool.map(
            compute_similarity_chunk, [(chunk, fav_mean) for chunk in chunks]
        )

    return np.concatenate(results)


def filter_by_genre(df, genre):
    if genre and "genre" in df.columns:
        return df[df["genre"].str.contains(genre, case=False, na=False)]
    return df


def get_recommendations(
    user_favs_df,
    tracks_df,
    attr_cols,
    topn=20,
    pop_min=None,
    year_min=None,
    year_max=None,
    exclude_ids=None,
    liked_tracks=None,
    disliked_tracks=None,
):
    df = tracks_df.copy()

    # Filtrar por popularidad
    if pop_min is not None and "popularity" in df.columns:
        df = df[df["popularity"] >= int(pop_min)]

    # Filtrar por año
    if year_min or year_max:
        if "release_date" in df.columns:
            df["release_year"] = pd.to_datetime(
                df["release_date"], errors="coerce"
            ).dt.year
            if year_min:
                df = df[df["release_year"] >= int(year_min)]
            if year_max:
                df = df[df["release_year"] <= int(year_max)]

    # Eliminar canciones ya gustadas y dislikes
    if exclude_ids is not None:
        df = df[~df["id"].isin(exclude_ids)]

    # Mantener solo la más popular de cada canción
    if "popularity" in df.columns:
        df = df.sort_values("popularity", ascending=False)
    df = df.drop_duplicates(subset=["name", "artists"], keep="first")

    if df.empty:
        return df

    # Ajustar perfil con feedback dinámico
    combined_favs = user_favs_df.copy()

    # Añadir likes con peso aumentado
    if liked_tracks is not None and not liked_tracks.empty:
        # Duplicar las canciones con like para aumentar su peso
        combined_favs = pd.concat(
            [combined_favs, liked_tracks, liked_tracks], ignore_index=True
        )

    # Restar influencia de dislikes
    if disliked_tracks is not None and not disliked_tracks.empty:
        # Crear un perfil "negativo" y restarlo del promedio
        pass  # Se implementa abajo en el cálculo

    scaler = StandardScaler()
    ds_scaled = scaler.fit_transform(df[attr_cols])
    fav_scaled = scaler.transform(combined_favs[attr_cols])
    fav_mean = fav_scaled.mean(axis=0).reshape(1, -1)

    # Si hay dislikes, restar su influencia
    if disliked_tracks is not None and not disliked_tracks.empty:
        dislike_scaled = scaler.transform(disliked_tracks[attr_cols])
        dislike_mean = dislike_scaled.mean(axis=0).reshape(1, -1)
        # Ajustar el perfil alejándolo de los dislikes
        fav_mean = fav_mean + 0.5 * (fav_mean - dislike_mean)

    # Cálculo paralelo de similitud
    sim_scores = parallel_similarity_multicore(
        ds_scaled, fav_mean, n_workers=cpu_count()
    )
    df["sim"] = sim_scores

    recs = df.sort_values("sim", ascending=False).head(topn)
    return recs
