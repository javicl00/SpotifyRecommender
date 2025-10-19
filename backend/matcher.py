import pandas as pd


def match_favs_with_features(favs_df, tracks_df):
    # Merge con PyArrow habilitado internamente si los DataFrames son grandes
    merged = pd.merge(
        favs_df, tracks_df, left_on="Spotify - id", right_on="id", how="inner"
    )
    if merged.empty:
        merged = pd.merge(
            favs_df,
            tracks_df,
            left_on=["Track name", "Artist name"],
            right_on=["name", "artists"],
            how="inner",
        )
    return merged

