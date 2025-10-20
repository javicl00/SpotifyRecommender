import pandas as pd
import streamlit as st
import requests
from io import BytesIO


@st.cache_data(ttl=86400)
def load_remote_dataset(url, ext="csv"):
    response = requests.get(url)
    if ext == "csv":
        return pd.read_csv(BytesIO(response.content))
    elif ext == "parquet":
        return pd.read_parquet(BytesIO(response.content))
    else:
        raise ValueError("Formato no soportado")


def get_spotify_dataset():
    # Para CSV completo de Hugging Face (descarga directa):
    url = "hf://datasets/maharshipandya/spotify-tracks-dataset/dataset.csv"
    # Si usas parquet: url = "hf://datasets/maharshipandya/spotify-tracks-dataset/dataset.parquet"
    return load_remote_dataset(url, ext="csv")
