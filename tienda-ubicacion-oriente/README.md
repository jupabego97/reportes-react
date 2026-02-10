# Análisis de Ubicación Óptima para Tiendas de Tecnología - Oriente Antioqueño

Aplicación de análisis geoespacial para determinar las mejores ubicaciones para tiendas de tecnología en el Oriente Antioqueño, Colombia.

## 🎯 Objetivo

Identificar ubicaciones óptimas para tiendas de tecnología en los municipios del Oriente Antioqueño utilizando:
- Datos de Google Maps API
- Información poblacional del DANE
- Algoritmos estándar de la industria (P-Median, Modelo de Huff)
- Sistema de scoring multi-criterio

## 🏘️ Municipios Analizados

- Rionegro
- La Ceja
- Marinilla
- El Carmen de Viboral
- Santuario
- El Retiro
- Guarne

## 🛠️ Tecnologías Utilizadas

- **Streamlit**: Interfaz web interactiva
- **Google Maps API**: Places, Geocoding, Distance Matrix
- **DANE**: Datos poblacionales y socioeconómicos
- **Scikit-learn**: Algoritmo P-Median (K-Means)
- **Folium**: Visualización de mapas interactivos
- **Pandas/NumPy**: Procesamiento de datos

## 📊 Algoritmos Implementados

### 1. P-Median (Location-Allocation)
Encuentra ubicaciones que minimizan la distancia total ponderada a la población objetivo.

### 2. Modelo de Huff
Calcula la probabilidad de atracción de clientes considerando:
- Tamaño/atractivo del local
- Distancia desde centros poblados
- Competencia existente

### 3. Sistema de Scoring Multi-Criterio
Evalúa ubicaciones usando criterios ponderados:
- **Población (35%)**: Población total y alcanzable
- **Tráfico (30%)**: Tráfico peatonal y vehicular
- **Competencia/Zona Comercial (15%)**: Proximidad y competencia
- **Nivel Socioeconómico (12%)**: Indicadores del DANE
- **Densidad Comercial (8%)**: Densidad de establecimientos

## 🚀 Instalación

1. Clonar o descargar el proyecto

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar API Key de Google Maps:
   - Obtener una API key de Google Cloud Platform
   - Habilitar las siguientes APIs:
     - Places API
     - Geocoding API
     - Distance Matrix API
   - La API key se puede ingresar en la interfaz de Streamlit

## 💻 Uso

1. Ejecutar la aplicación:
```bash
streamlit run app.py
```

2. En la barra lateral:
   - Ingresar la API key de Google Maps
   - Seleccionar municipios a analizar
   - Ajustar parámetros de análisis (tamaño de grilla, número de ubicaciones, etc.)
   - Ajustar pesos del scoring si es necesario

3. Hacer clic en "Ejecutar Análisis"

4. Visualizar resultados:
   - Mapa interactivo con mejores ubicaciones
   - Tabla de resultados rankeados
   - Métricas resumen

## 📁 Estructura del Proyecto

```
tienda-ubicacion-oriente/
├── app.py                    # Aplicación principal Streamlit
├── services/
│   ├── google_maps.py        # Integración con Google Maps API
│   ├── dane_scraper.py       # Recolección de datos del DANE
│   └── data_processor.py     # Procesamiento de datos
├── models/
│   ├── location_analysis.py  # Algoritmo P-Median
│   ├── huff_model.py         # Modelo de Huff
│   └── scoring.py            # Sistema de scoring
├── data/
│   └── municipios.json       # Coordenadas de municipios
├── requirements.txt
└── README.md
```

## 📝 Notas

- Los datos del DANE incluyen proyecciones poblacionales 2024
- El análisis se centra en zonas urbanas de cada municipio
- Los resultados incluyen caché para optimizar llamadas a la API
- Los pesos del scoring son ajustables desde la interfaz

## 🔒 Seguridad

- La API key de Google Maps se maneja de forma segura en la aplicación
- Se recomienda usar variables de entorno para producción
- No compartir la API key públicamente

## 📄 Licencia

Este proyecto es de uso educativo y comercial.

## 👨‍💻 Autor

Desarrollado para análisis de ubicación de tiendas de tecnología en Colombia.
























