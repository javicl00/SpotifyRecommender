import pandas as pd


def load_csv(path):
    """Carga CSV usando PyArrow engine para máxima velocidad."""
    return pd.read_csv(path, engine="pyarrow")
