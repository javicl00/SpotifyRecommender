import pandas as pd


def match_favs_with_features(favs_df, tracks_df):
    # Une por Spotify ID (track_id en HuggingFace dataset)
    merged = pd.merge(
        favs_df, tracks_df, left_on="Spotify - id", right_on="track_id", how="inner"
    )
    if merged.empty:
        merged = pd.merge(
            favs_df,
            tracks_df,
            left_on=["Track name", "Artist name"],
            right_on=["track_name", "artists"],
            how="inner",
        )
    return merged
