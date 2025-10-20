import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from multiprocessing import Pool, cpu_count
import warnings

warnings.filterwarnings("ignore")


def compute_similarity_chunk(args):
    chunk, fav_mean = args
    return cosine_similarity(chunk, fav_mean).flatten()


def parallel_similarity_multicore(ds_scaled, fav_mean, n_workers=None):
    if n_workers is None:
        n_workers = min(cpu_count(), 8)

    chunk_size = max(1, int(np.ceil(ds_scaled.shape[0] / n_workers)))
    chunks = [
        ds_scaled[i : i + chunk_size] for i in range(0, ds_scaled.shape[0], chunk_size)
    ]

    with Pool(processes=n_workers) as pool:
        results = pool.map(
            compute_similarity_chunk, [(chunk, fav_mean) for chunk in chunks]
        )

    return np.concatenate(results)


def filter_by_genre(df, genre):
    if genre and "track_genre" in df.columns:
        return df[df["track_genre"].str.contains(genre, case=False, na=False)]
    return df


def calculate_diversity_score(recommendations, features):
    """Calcula puntuación de diversidad para evitar recomendaciones muy similares entre sí"""
    if len(recommendations) < 2:
        return np.ones(len(recommendations))

    rec_features = recommendations[features].values
    diversity_scores = []

    for i, track in enumerate(rec_features):
        others = np.delete(rec_features, i, axis=0)
        similarities = cosine_similarity([track], others).flatten()
        diversity = 1 - np.mean(similarities)
        diversity_scores.append(diversity)

    return np.array(diversity_scores)


def hybrid_recommendation_score(
    similarity_scores, popularity_scores, diversity_scores, novelty_scores, weights=None
):
    """Sistema híbrido que combina múltiples métricas"""
    if weights is None:
        weights = {
            "similarity": 0.4,
            "popularity": 0.2,
            "diversity": 0.25,
            "novelty": 0.15,
        }

    # Normalizar todas las puntuaciones a [0,1]
    norm_sim = (similarity_scores - similarity_scores.min()) / (
        similarity_scores.max() - similarity_scores.min() + 1e-8
    )
    norm_pop = (popularity_scores - popularity_scores.min()) / (
        popularity_scores.max() - popularity_scores.min() + 1e-8
    )
    norm_div = (diversity_scores - diversity_scores.min()) / (
        diversity_scores.max() - diversity_scores.min() + 1e-8
    )
    norm_nov = (novelty_scores - novelty_scores.min()) / (
        novelty_scores.max() - novelty_scores.min() + 1e-8
    )

    hybrid_score = (
        weights["similarity"] * norm_sim
        + weights["popularity"] * norm_pop
        + weights["diversity"] * norm_div
        + weights["novelty"] * norm_nov
    )

    return hybrid_score


def get_advanced_recommendations(
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
    use_clustering=True,
    diversity_weight=0.3,
    novelty_boost=True,
):
    """
    Sistema de recomendación avanzado con múltiples técnicas de ML:
    - Clustering para encontrar micro-géneros
    - Análisis de componentes principales (PCA)
    - Filtrado colaborativo híbrido
    - Detección de outliers para novedad
    - Balanceado de diversidad vs similitud
    """

    df = tracks_df.copy()

    # ===== FILTROS BÁSICOS =====
    if pop_min is not None and "popularity" in df.columns:
        df = df[df["popularity"] >= int(pop_min)]

    if year_min or year_max:
        if "release_date" in df.columns:
            df["release_year"] = pd.to_datetime(
                df["release_date"], errors="coerce"
            ).dt.year
        elif "album_name" in df.columns:
            # Extraer año del nombre del álbum si está disponible
            df["release_year"] = df["album_name"].str.extract(r"(\d{4})").astype(float)

        if year_min and "release_year" in df.columns:
            df = df[df["release_year"] >= int(year_min)]
        if year_max and "release_year" in df.columns:
            df = df[df["release_year"] <= int(year_max)]

    if exclude_ids is not None:
        df = df[~df["track_id"].isin(exclude_ids)]

    # Mantener solo la más popular de cada canción única
    if "popularity" in df.columns:
        df = df.sort_values("popularity", ascending=False)
    df = df.drop_duplicates(subset=["track_name", "artists"], keep="first")

    if df.empty:
        return df

    # ===== PREPARACIÓN DE DATOS =====
    # Escalado robusto de características
    scaler = StandardScaler()
    ds_scaled = scaler.fit_transform(df[attr_cols])
    fav_scaled = scaler.transform(user_favs_df[attr_cols])

    # ===== PERFIL DINÁMICO DEL USUARIO =====
    base_profile = fav_scaled.mean(axis=0)

    # Ajustar perfil con feedback de likes/dislikes
    if liked_tracks is not None and not liked_tracks.empty:
        liked_scaled = scaler.transform(liked_tracks[attr_cols])
        liked_profile = liked_scaled.mean(axis=0)
        # Aumentar peso de características de likes
        base_profile = 0.6 * base_profile + 0.4 * liked_profile

    if disliked_tracks is not None and not disliked_tracks.empty:
        disliked_scaled = scaler.transform(disliked_tracks[attr_cols])
        disliked_profile = disliked_scaled.mean(axis=0)
        # Alejar perfil de características de dislikes
        base_profile = base_profile + 0.3 * (base_profile - disliked_profile)

    user_profile = base_profile.reshape(1, -1)

    # ===== CLUSTERING PARA MICRO-GÉNEROS =====
    if use_clustering and len(df) > 100:
        # K-means para encontrar grupos musicales naturales
        n_clusters = min(20, len(df) // 100)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster"] = kmeans.fit_predict(ds_scaled)

        # Encontrar el cluster más similar al perfil del usuario
        cluster_centers = kmeans.cluster_centers_
        user_cluster_similarities = cosine_similarity(
            user_profile, cluster_centers
        ).flatten()
        preferred_clusters = np.argsort(user_cluster_similarities)[
            -3:
        ]  # Top 3 clusters

        # Filtrar a canciones de clusters preferidos
        cluster_mask = df["cluster"].isin(preferred_clusters)
        df_filtered = df[cluster_mask].copy()
        ds_scaled = ds_scaled[cluster_mask]
    else:
        df_filtered = df.copy()

    # ===== CÁLCULO DE SIMILITUDES =====
    sim_scores = parallel_similarity_multicore(
        ds_scaled, user_profile, n_workers=cpu_count()
    )
    df_filtered["similarity"] = sim_scores

    # ===== ANÁLISIS DE NOVEDAD =====
    if novelty_boost:
        # Usar Isolation Forest para encontrar canciones "únicas"
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        novelty_scores = iso_forest.decision_function(ds_scaled)
        # Convertir a puntuación positiva (más alto = más novedoso)
        novelty_scores = (novelty_scores - novelty_scores.min()) / (
            novelty_scores.max() - novelty_scores.min()
        )
        df_filtered["novelty"] = novelty_scores
    else:
        df_filtered["novelty"] = 0.5

    # ===== SELECCIÓN INICIAL DE CANDIDATOS =====
    # Tomar top candidates (más que topn para luego re-rankear)
    initial_candidates = min(topn * 3, len(df_filtered))
    top_candidates = df_filtered.nlargest(initial_candidates, "similarity")

    # ===== CÁLCULO DE DIVERSIDAD =====
    diversity_scores = calculate_diversity_score(top_candidates, attr_cols)
    top_candidates["diversity"] = diversity_scores

    # ===== PUNTUACIÓN HÍBRIDA FINAL =====
    similarity_scores = top_candidates["similarity"].values
    popularity_scores = (
        top_candidates["popularity"].values / 100.0
    )  # Normalizar a [0,1]
    diversity_scores = top_candidates["diversity"].values
    novelty_scores = top_candidates["novelty"].values

    # Pesos adaptativos basados en el tamaño de la biblioteca del usuario
    user_library_size = len(user_favs_df)
    if user_library_size < 20:
        # Usuario nuevo: priorizar popularidad y similitud
        weights = {
            "similarity": 0.5,
            "popularity": 0.3,
            "diversity": 0.1,
            "novelty": 0.1,
        }
    elif user_library_size < 100:
        # Usuario intermedio: balance
        weights = {
            "similarity": 0.4,
            "popularity": 0.2,
            "diversity": 0.25,
            "novelty": 0.15,
        }
    else:
        # Usuario avanzado: priorizar diversidad y novedad
        weights = {
            "similarity": 0.35,
            "popularity": 0.15,
            "diversity": 0.3,
            "novelty": 0.2,
        }

    hybrid_scores = hybrid_recommendation_score(
        similarity_scores, popularity_scores, diversity_scores, novelty_scores, weights
    )

    top_candidates["hybrid_score"] = hybrid_scores

    # ===== RECOMENDACIONES FINALES =====
    final_recommendations = top_candidates.nlargest(topn, "hybrid_score")

    # Asegurar diversidad de géneros en el resultado final
    if (
        "track_genre" in final_recommendations.columns
        and len(final_recommendations) > 5
    ):
        genre_counts = final_recommendations["track_genre"].value_counts()
        max_per_genre = max(2, topn // 4)  # Máximo 25% de un género

        diverse_recs = []
        genre_counter = {}

        for _, row in final_recommendations.iterrows():
            genre = row["track_genre"]
            if genre_counter.get(genre, 0) < max_per_genre:
                diverse_recs.append(row)
                genre_counter[genre] = genre_counter.get(genre, 0) + 1
                if len(diverse_recs) >= topn:
                    break

        final_recommendations = pd.DataFrame(diverse_recs)

    # Limpiar columnas auxiliares
    cols_to_drop = ["cluster", "similarity", "novelty", "diversity", "hybrid_score"]
    final_recommendations = final_recommendations.drop(
        columns=[col for col in cols_to_drop if col in final_recommendations.columns]
    )

    return final_recommendations


# Alias para compatibilidad con código existente
def get_recommendations(*args, **kwargs):
    return get_advanced_recommendations(*args, **kwargs)
