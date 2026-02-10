"""
Aplicación Streamlit para análisis de ubicación de tiendas de tecnología
en el Oriente Antioqueño
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import json
import os
from typing import List, Dict, Tuple

# Imports locales
from services.google_maps import GoogleMapsService
from services.dane_scraper import DANEScraper
from services.data_processor import DataProcessor
from models.location_analysis import LocationAllocationAnalysis
from models.huff_model import HuffModel
from models.scoring import SiteSelectionScoring

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Ubicación - Tiendas Tecnología",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("📍 Análisis de Ubicación Óptima para Tiendas de Tecnología")
st.markdown("**Oriente Antioqueño - Colombia**")
st.markdown("---")

# Cargar datos de municipios
@st.cache_data
def load_municipios():
    """Carga datos de municipios"""
    with open('data/municipios.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Inicializar servicios
@st.cache_resource
def init_services(api_key: str):
    """Inicializa servicios con caché"""
    return {
        'google_maps': GoogleMapsService(api_key),
        'dane': DANEScraper(),
        'processor': DataProcessor()
    }

# Sidebar - Configuración
st.sidebar.header("⚙️ Configuración")

# API Key de Google Maps
api_key = st.sidebar.text_input(
    "Google Maps API Key",
    value="AIzaSyCZpB4HZ90MguFOPuSOtjr7XnhZpl6c8DU",
    type="password"
)

# Selección de municipios
municipios_data = load_municipios()
municipios_nombres = [m['nombre'] for m in municipios_data['municipios']]

municipios_seleccionados = st.sidebar.multiselect(
    "Municipios a analizar",
    options=municipios_nombres,
    default=municipios_nombres[:3]  # Por defecto primeros 3
)

# Parámetros de análisis
st.sidebar.subheader("📊 Parámetros de Análisis")
grid_size = st.sidebar.slider("Tamaño de grilla", 5, 20, 10)
n_facilities = st.sidebar.slider("Número de ubicaciones a encontrar", 1, 5, 3)
radius_km = st.sidebar.slider("Radio de búsqueda (km)", 2, 10, 5)

# Pesos del scoring (ajustables)
st.sidebar.subheader("⚖️ Pesos del Scoring")
peso_poblacion = st.sidebar.slider("Población", 0.0, 1.0, 0.35)
peso_trafico = st.sidebar.slider("Tráfico", 0.0, 1.0, 0.30)
peso_competencia = st.sidebar.slider("Competencia/Zona Comercial", 0.0, 1.0, 0.15)
peso_socioeconomico = st.sidebar.slider("Nivel Socioeconómico", 0.0, 1.0, 0.12)
peso_densidad = st.sidebar.slider("Densidad Comercial", 0.0, 1.0, 0.08)

# Normalizar pesos
total_peso = peso_poblacion + peso_trafico + peso_competencia + peso_socioeconomico + peso_densidad
if total_peso > 0:
    peso_poblacion /= total_peso
    peso_trafico /= total_peso
    peso_competencia /= total_peso
    peso_socioeconomico /= total_peso
    peso_densidad /= total_peso

custom_weights = {
    'poblacion': peso_poblacion,
    'trafico': peso_trafico,
    'competencia_zona_comercial': peso_competencia,
    'nivel_socioeconomico': peso_socioeconomico,
    'densidad_comercial': peso_densidad
}

# Botón para ejecutar análisis
ejecutar_analisis = st.sidebar.button("🚀 Ejecutar Análisis", type="primary")

# Contenido principal
if ejecutar_analisis and api_key and municipios_seleccionados:
    # Inicializar servicios
    with st.spinner("Inicializando servicios..."):
        services = init_services(api_key)
        google_maps = services['google_maps']
        dane = services['dane']
        processor = services['processor']
    
    # Contenedor para resultados
    resultados_completos = []
    
    # Procesar cada municipio
    for municipio in municipios_seleccionados:
        st.subheader(f"🏘️ Analizando: {municipio}")
        
        # Obtener datos del municipio
        municipio_info = next(m for m in municipios_data['municipios'] if m['nombre'] == municipio)
        centro_municipio = (municipio_info['lat'], municipio_info['lon'])
        
        # Obtener datos poblacionales del DANE
        with st.spinner(f"Obteniendo datos poblacionales de {municipio}..."):
            poblacion_data = dane.get_poblacion_municipio(municipio)
            poblacion_objetivo = dane.calculate_poblacion_objetivo(municipio)
            densidad = dane.get_densidad_poblacional(municipio)
            nivel_socioeconomico = dane.get_nivel_socioeconomico_score(municipio)
        
        # Obtener competidores de Google Maps
        with st.spinner(f"Buscando competidores en {municipio}..."):
            competitors = google_maps.get_competitors(
                centro_municipio,
                radius=radius_km * 1000
            )
        
        # Buscar zonas comerciales
        with st.spinner(f"Buscando zonas comerciales en {municipio}..."):
            commercial_areas = google_maps.search_commercial_areas(
                centro_municipio,
                radius=radius_km * 1000
            )
        
        # Crear grilla de ubicaciones candidatas
        with st.spinner(f"Generando ubicaciones candidatas para {municipio}..."):
            candidate_locations = processor.create_candidate_locations(
                municipio,
                grid_size=grid_size
            )
        
        # Enriquecer datos de ubicaciones
        poblacion_data['densidad'] = densidad
        poblacion_data['centro'] = centro_municipio
        poblacion_data['nivel_socioeconomico'] = nivel_socioeconomico
        
        enriched_locations = processor.combine_location_data(
            candidate_locations,
            competitors,
            poblacion_data,
            commercial_areas
        )
        
        # Agregar datos de tráfico estimado (usando proxies)
        enriched_locations['trafico_peatonal'] = enriched_locations.apply(
            lambda row: 80 if row['distancia_zona_comercial'] < 1.0 else 
                       60 if row['distancia_zona_comercial'] < 2.0 else 40,
            axis=1
        )
        enriched_locations['trafico_vehicular'] = enriched_locations['trafico_peatonal'] * 0.9
        
        # Calcular población alcanzable
        # Crear puntos de demanda basados en la grilla de ubicaciones
        demand_points = enriched_locations[['lat', 'lon']].values
        # Distribuir población objetivo entre los puntos de demanda
        demand_weights = np.full(len(demand_points), poblacion_objetivo / len(demand_points))
        
        location_analysis = LocationAllocationAnalysis(n_facilities=n_facilities)
        enriched_locations = location_analysis.analyze_candidate_locations(
            enriched_locations,
            demand_points,
            demand_weights
        )
        
        # Aplicar modelo de Huff
        huff_model = HuffModel()
        enriched_locations['huff_market_share'] = enriched_locations.apply(
            lambda row: huff_model.calculate_market_share(
                (row['lat'], row['lon']),
                store_size=1.0,
                demand_points=demand_points,
                demand_weights=demand_weights,
                competitors=competitors
            ),
            axis=1
        )
        
        # Calcular scores
        scoring_system = SiteSelectionScoring(custom_weights=custom_weights)
        
        # Preparar datos para scoring
        for idx, row in enriched_locations.iterrows():
            location_dict = {
                'poblacion_total': row['poblacion_total'],
                'poblacion_alcanzable': row.get('poblacion_alcanzable', row['poblacion_total'] * 0.3),
                'trafico_peatonal': row['trafico_peatonal'],
                'trafico_vehicular': row['trafico_vehicular'],
                'competidores_cercanos': row['competidores_cercanos'],
                'distancia_zona_comercial': row['distancia_zona_comercial'],
                'nivel_socioeconomico': nivel_socioeconomico,
                'densidad_comercial': row['competidores_cercanos'] * 5
            }
            enriched_locations.at[idx, 'score'] = scoring_system.calculate_score(location_dict)
        
        # Rankear ubicaciones
        ranked_locations = scoring_system.rank_locations(enriched_locations)
        
        # Agregar municipio a los resultados
        ranked_locations['municipio'] = municipio
        resultados_completos.append(ranked_locations)
        
        # Mostrar top 5 ubicaciones del municipio
        st.success(f"✅ Análisis completado para {municipio}")
        top_5 = ranked_locations.head(5)
        st.dataframe(
            top_5[['ranking', 'score', 'poblacion_alcanzable', 'competidores_cercanos', 
                   'distancia_zona_comercial', 'lat', 'lon']].style.format({
                'score': '{:.2f}',
                'poblacion_alcanzable': '{:.0f}',
                'distancia_zona_comercial': '{:.2f}'
            }),
            use_container_width=True
        )
    
    # Combinar todos los resultados
    if resultados_completos:
        todos_resultados = pd.concat(resultados_completos, ignore_index=True)
        todos_resultados = scoring_system.rank_locations(todos_resultados)
        
        st.markdown("---")
        st.subheader("🗺️ Mapa Interactivo - Mejores Ubicaciones")
        
        # Crear mapa
        center_lat = todos_resultados['lat'].mean()
        center_lon = todos_resultados['lon'].mean()
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='cartodbpositron'
        )
        
        # Agregar marcadores de mejores ubicaciones
        for idx, row in todos_resultados.head(20).iterrows():
            color = 'green' if row['ranking'] <= 3 else 'blue' if row['ranking'] <= 10 else 'gray'
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=8,
                popup=f"""
                <b>{row['municipio']}</b><br>
                Ranking: {row['ranking']}<br>
                Score: {row['score']:.2f}<br>
                Población Alcanzable: {row.get('poblacion_alcanzable', 0):.0f}<br>
                Competidores: {row['competidores_cercanos']}
                """,
                color=color,
                fill=True,
                fillColor=color
            ).add_to(m)
        
        # Agregar heatmap
        from folium.plugins import HeatMap
        heat_data = [[row['lat'], row['lon'], row['score']] 
                     for _, row in todos_resultados.iterrows()]
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
        
        # Mostrar mapa
        st_folium(m, width=1200, height=600)
        
        # Tabla de resultados completos
        st.subheader("📊 Tabla de Resultados Completos")
        st.dataframe(
            todos_resultados[['ranking', 'municipio', 'score', 'poblacion_alcanzable',
                             'competidores_cercanos', 'distancia_zona_comercial', 
                             'lat', 'lon']].head(30).style.format({
                'score': '{:.2f}',
                'poblacion_alcanzable': '{:.0f}',
                'distancia_zona_comercial': '{:.2f}'
            }),
            use_container_width=True
        )
        
        # Métricas resumen
        st.subheader("📈 Métricas Resumen")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Ubicaciones Analizadas", len(todos_resultados))
        with col2:
            st.metric("Score Promedio", f"{todos_resultados['score'].mean():.2f}")
        with col3:
            st.metric("Mejor Score", f"{todos_resultados['score'].max():.2f}")
        with col4:
            st.metric("Municipios Analizados", len(municipios_seleccionados))

else:
    # Pantalla inicial
    st.info("👈 Configura los parámetros en la barra lateral y haz clic en 'Ejecutar Análisis' para comenzar.")
    
    st.markdown("""
    ### 📋 Información de la Aplicación
    
    Esta aplicación utiliza:
    - **Google Maps API** para identificar competidores y zonas comerciales
    - **Datos del DANE** para información poblacional y socioeconómica
    - **Algoritmo P-Median** para encontrar ubicaciones óptimas
    - **Modelo de Huff** para calcular áreas de influencia
    - **Sistema de Scoring Multi-Criterio** para rankear ubicaciones
    
    ### 🎯 Criterios de Evaluación
    
    Los criterios están ponderados según importancia:
    - **Población (35%)**: Población total y población alcanzable
    - **Tráfico (30%)**: Tráfico peatonal y vehicular
    - **Competencia/Zona Comercial (15%)**: Proximidad a zonas comerciales y competencia
    - **Nivel Socioeconómico (12%)**: Indicadores del DANE
    - **Densidad Comercial (8%)**: Densidad de establecimientos comerciales
    
    ### 🏘️ Municipios Analizados
    
    - Rionegro
    - La Ceja
    - Marinilla
    - El Carmen de Viboral
    - Santuario
    - El Retiro
    - Guarne
    """)

