import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st


def get_spotify_client():
    scope = "user-read-email user-library-read"
    sp_oauth = SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
        scope=scope,
        show_dialog=True,
    )
    token_info = sp_oauth.get_access_token(as_dict=True)
    access_token = token_info["access_token"]
    sp = spotipy.Spotify(auth=access_token)
    return sp


def get_user_liked_tracks(sp, limit=200):
    tracks = []
    results = sp.current_user_saved_tracks(limit=limit)
    while results:
        for item in results["items"]:
            track = item["track"]
            tracks.append(
                {
                    "Track name": track["name"],
                    "Artist name": ", ".join(
                        [artist["name"] for artist in track["artists"]]
                    ),
                    "Spotify - id": track["id"],
                }
            )
        results = sp.next(results) if results["next"] else None
    return tracks
