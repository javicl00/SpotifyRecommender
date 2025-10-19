# 🎧 Spotify Music Recommender with Dynamic Feedback

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red?style=for-the-badge&logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Un recomendador de música de Spotify inteligente y visual con aprendizaje dinámico basado en feedback del usuario.**

[🚀 Demo](#demo) • [⚡ Características](#características) • [📦 Instalación](#instalación) • [🎯 Uso](#uso) • [🤝 Contribuir](#contribuir)

</div>

---

## 🌟 Descripción

**Spotify Music Recommender** es un sistema de recomendación avanzado que analiza tus canciones favoritas y sugiere nuevas canciones que podrían gustarte, basándose en atributos musicales como bailabilidad, energía, positividad y más.

### ¿Qué lo hace especial?

- 🎯 **Recomendaciones personalizadas** basadas en similitud de atributos musicales
- 👍👎 **Feedback dinámico**: Dale like o dislike a las recomendaciones para mejorar tu perfil musical en tiempo real
- 📊 **Dashboard visual interactivo**: Visualiza tu perfil musical con gráficos y estadísticas
- 🎵 **Preview de canciones**: Escucha directamente en Spotify desde la app
- 🚀 **Optimizado para datasets masivos**: Usa PyArrow, Numba y Multiprocessing
- 🎨 **Interfaz moderna**: Construida con Streamlit para una experiencia fluida

---

## ✨ Características

### 🔍 Análisis y Filtrado Avanzado

- Filtra recomendaciones por **popularidad**, **año de lanzamiento** y **género**
- Excluye automáticamente canciones que ya tienes en tu biblioteca
- Encuentra solo versiones únicas (elimina duplicados, manteniendo la más popular)

### 📈 Visualización de tu Perfil Musical

- **Gráfico de radar** con tus atributos musicales favoritos normalizados (0-10)
- **Distribución de géneros** favoritos
- **Histograma de años** de tus canciones preferidas
- Métricas en tiempo real de likes y dislikes

### 🎓 Aprendizaje Interactivo

- Sistema de **feedback con 👍 y 👎** para ajustar recomendaciones dinámicamente
- Las canciones con like **aumentan su peso** en el perfil musical
- Las canciones con dislike **alejan** el perfil de esos atributos

### ⚡ Alto Rendimiento

- **PyArrow** para carga ultra-rápida de CSVs masivos (hasta 10x más rápido)
- **Multiprocessing** para cálculos paralelos de similitud
- **Numba** para optimización de operaciones numéricas

---

## 🖼️ Demo

### Dashboard Principal

![Dashboard](https://via.placeholder.com/800x400?text=Dashboard+Screenshot)

### Sistema de Feedback

![Feedback](https://via.placeholder.com/800x400?text=Feedback+System+Screenshot)

---

## 📦 Instalación

### Requisitos previos

- Python 3.9 o superior
- pip

### Clonar el repositorio

git clone <https://github.com/tu-usuario/spotify-recommender.git>
cd spotify-recommender

### Instalar dependencias

pip install -r requirements.txt

---

## 🎯 Uso

### 1. Preparar tus datos

Necesitarás dos archivos CSV:

#### a) **Tu lista de canciones gustadas** (`my_spotify_library.csv`)

Puedes exportarla desde Spotify usando herramientas como:

- [TuneMyMusic](https://www.tunemymusic.com/)
- [Exportify](https://exportify.net/)

**Columnas necesarias:**

- `Track name`
- `Artist name`
- `Spotify - id`

#### b) **Dataset de canciones de Spotify** (`tracks.csv`)

Descarga un dataset público de Spotify con atributos:

- [Kaggle: Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/spotify-tracks-dataset)

**Columnas necesarias:**

- `id`, `name`, `artists`, `popularity`, `release_date`
- Atributos: `danceability`, `energy`, `key`, `loudness`, `mode`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence`, `tempo`, `duration_ms`

### 2. Ejecutar la aplicación

streamlit run app.py

La app se abrirá automáticamente en tu navegador en `http://localhost:8501`

### 3. ¡Empieza a explorar

1. **Carga tus archivos** usando los botones de upload
2. **Empareja tus favoritas** con el dataset para extraer atributos
3. **Visualiza tu perfil musical** en el dashboard interactivo
4. **Ajusta filtros** (popularidad, año, género)
5. **Obtén recomendaciones únicas**
6. **Dale 👍 o 👎** para mejorar las sugerencias
7. **Escucha previews** y descarga resultados en CSV

---

## 🏗️ Estructura del Proyecto

spotify_recommender/
│
├── backend/
│ ├── init.py
│ ├── recommender.py # Motor de recomendación optimizado
│ └── matcher.py # Emparejamiento de favoritas con dataset
│
├── utils/
│ ├── init.py
│ └── fileloader.py # Carga optimizada de CSV con PyArrow
│
├── app.py # Aplicación Streamlit principal
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE

---

## 🧠 Cómo Funciona

### Algoritmo de Recomendación

1. **Extracción de perfil**: Calcula el promedio de atributos musicales de tus canciones favoritas
2. **Normalización**: Escala todos los atributos para comparación justa
3. **Similitud coseno**: Compara cada canción del dataset con tu perfil
4. **Feedback dinámico**:
   - Likes → Duplica el peso de esas canciones en tu perfil
   - Dislikes → Aleja el perfil de esos atributos
5. **Ranking**: Ordena por similitud y filtra según tus criterios

### Atributos Musicales Utilizados

- **Bailabilidad**: Qué tan adecuada es para bailar
- **Energía**: Intensidad y actividad
- **Positividad**: Alegría/tristeza transmitida
- **Acústico**: Nivel de instrumentos acústicos
- **Instrumentalidad**: Cantidad de voz vs instrumental
- **Habla**: Presencia de palabras habladas
- **Directo**: Probabilidad de grabación en vivo
- **Tempo**: Velocidad (BPM)
- **Volumen**: Nivel de decibelios
- **Duración**: Longitud de la canción

---

## 🛠️ Tecnologías

- **[Streamlit](https://streamlit.io/)**: Framework web para apps de ML
- **[Pandas](https://pandas.pydata.org/)**: Manipulación de datos
- **[Scikit-learn](https://scikit-learn.org/)**: Algoritmos de ML (similitud coseno, normalización)
- **[Altair](https://altair-viz.github.io/)**: Visualizaciones interactivas
- **[PyArrow](https://arrow.apache.org/docs/python/)**: Carga rápida de datos
- **[Numba](https://numba.pydata.org/)**: Compilación JIT para optimización
- **Multiprocessing**: Paralelización de cálculos

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Si tienes ideas para mejorar el proyecto:

1. Haz un Fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Roadmap

- [ ] Integración completa con Spotify API para obtener datos en tiempo real
- [ ] Sistema de playlists automáticas
- [ ] Comparativa de gustos musicales entre usuarios
- [ ] Exportar perfil musical como imagen/infografía
- [ ] Clustering para descubrir subgéneros ocultos en tu biblioteca
- [ ] Modo "explorador" para descubrir música radicalmente diferente

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 🙏 Agradecimientos

- Datasets públicos de Spotify en Kaggle
- Comunidad de Streamlit por la increíble herramienta
- Todos los contribuidores y usuarios que mejoran el proyecto

---

<div align="center">

**Si este proyecto te resultó útil, dale una ⭐ en GitHub!**

Made with ❤️ and 🎵

</div>
