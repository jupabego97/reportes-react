"""
Procesador de datos que combina información de Google Maps y DANE
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import json
import os

class DataProcessor:
    """Procesa y combina datos de múltiples fuentes"""
    
    def __init__(self, municipios_file: str = None):
        """
        Inicializa el procesador de datos
        
        Args:
            municipios_file: Ruta al archivo JSON con datos de municipios
        """
        if municipios_file is None:
            municipios_file = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'data', 
                'municipios.json'
            )
        
        with open(municipios_file, 'r', encoding='utf-8') as f:
            self.municipios_data = json.load(f)
    
    def create_candidate_locations(self, municipio: str, 
                                   grid_size: int = 10) -> pd.DataFrame:
        """
        Crea una grilla de ubicaciones candidatas para un municipio
        
        Args:
            municipio: Nombre del municipio
            grid_size: Tamaño de la grilla (grid_size x grid_size puntos)
            
        Returns:
            DataFrame con ubicaciones candidatas
        """
        # Encontrar datos del municipio
        municipio_info = None
        for m in self.municipios_data['municipios']:
            if m['nombre'] == municipio:
                municipio_info = m
                break
        
        if not municipio_info:
            return pd.DataFrame()
        
        # Crear grilla alrededor del centro del municipio
        center_lat = municipio_info['lat']
        center_lon = municipio_info['lon']
        
        # Radio aproximado de ~5km en grados (1 grado ≈ 111km)
        radius_deg = 0.045  # ~5km
        
        # Generar puntos de la grilla
        locations = []
        lat_step = (radius_deg * 2) / grid_size
        lon_step = (radius_deg * 2) / grid_size
        
        start_lat = center_lat - radius_deg
        start_lon = center_lon - radius_deg
        
        for i in range(grid_size):
            for j in range(grid_size):
                lat = start_lat + (i * lat_step)
                lon = start_lon + (j * lon_step)
                
                locations.append({
                    'municipio': municipio,
                    'lat': lat,
                    'lon': lon,
                    'candidate_id': f"{municipio}_{i}_{j}"
                })
        
        return pd.DataFrame(locations)
    
    def combine_location_data(self, locations_df: pd.DataFrame,
                             competitors_data: List[Dict],
                             poblacion_data: Dict,
                             commercial_areas: List[Dict],
                             traffic_data: Dict = None) -> pd.DataFrame:
        """
        Combina todos los datos para cada ubicación candidata
        
        Args:
            locations_df: DataFrame con ubicaciones candidatas
            competitors_data: Lista de competidores encontrados
            poblacion_data: Datos poblacionales del municipio
            commercial_areas: Zonas comerciales encontradas
            traffic_data: Datos de tráfico (opcional)
            
        Returns:
            DataFrame enriquecido con todos los datos
        """
        df = locations_df.copy()
        
        # Calcular distancia a competidores más cercanos
        df['competidores_cercanos'] = df.apply(
            lambda row: self._count_nearby_competitors(
                (row['lat'], row['lon']), 
                competitors_data, 
                radius_km=2.0
            ), 
            axis=1
        )
        
        # Calcular distancia a zonas comerciales
        df['distancia_zona_comercial'] = df.apply(
            lambda row: self._min_distance_to_commercial(
                (row['lat'], row['lon']), 
                commercial_areas
            ), 
            axis=1
        )
        
        # Agregar datos poblacionales
        df['poblacion_total'] = poblacion_data.get('poblacion_2024', 0)
        df['poblacion_urbana'] = poblacion_data.get('poblacion_urbana', 0)
        df['densidad_poblacional'] = poblacion_data.get('densidad', 0)
        
        # Calcular accesibilidad (inversa de distancia a centro)
        df['accesibilidad'] = df.apply(
            lambda row: self._calculate_accessibility(
                (row['lat'], row['lon']),
                poblacion_data.get('centro', (row['lat'], row['lon']))
            ),
            axis=1
        )
        
        return df
    
    def _count_nearby_competitors(self, location: Tuple[float, float],
                                  competitors: List[Dict],
                                  radius_km: float = 2.0) -> int:
        """
        Cuenta competidores dentro de un radio
        
        Args:
            location: Tupla (lat, lon)
            competitors: Lista de competidores
            radius_km: Radio en kilómetros
            
        Returns:
            Número de competidores cercanos
        """
        count = 0
        for comp in competitors:
            comp_loc = comp.get('location', {})
            if 'lat' in comp_loc and 'lng' in comp_loc:
                distance = self._haversine_distance(
                    location,
                    (comp_loc['lat'], comp_loc['lng'])
                )
                if distance <= radius_km:
                    count += 1
        return count
    
    def _min_distance_to_commercial(self, location: Tuple[float, float],
                                    commercial_areas: List[Dict]) -> float:
        """
        Calcula distancia mínima a zona comercial
        
        Args:
            location: Tupla (lat, lon)
            commercial_areas: Lista de zonas comerciales
            
        Returns:
            Distancia mínima en kilómetros (999 si no hay zonas)
        """
        if not commercial_areas:
            return 999.0
        
        min_distance = float('inf')
        for area in commercial_areas:
            area_loc = area.get('location', {})
            if 'lat' in area_loc and 'lng' in area_loc:
                distance = self._haversine_distance(
                    location,
                    (area_loc['lat'], area_loc['lng'])
                )
                min_distance = min(min_distance, distance)
        
        return min_distance if min_distance != float('inf') else 999.0
    
    def _haversine_distance(self, point1: Tuple[float, float],
                           point2: Tuple[float, float]) -> float:
        """
        Calcula distancia entre dos puntos usando fórmula de Haversine
        
        Args:
            point1: Tupla (lat, lon) del primer punto
            point2: Tupla (lat, lon) del segundo punto
            
        Returns:
            Distancia en kilómetros
        """
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1 = radians(point1[0]), radians(point1[1])
        lat2, lon2 = radians(point2[0]), radians(point2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radio de la Tierra en kilómetros
        r = 6371
        
        return c * r
    
    def _calculate_accessibility(self, location: Tuple[float, float],
                                center: Tuple[float, float]) -> float:
        """
        Calcula score de accesibilidad (mayor = más accesible)
        
        Args:
            location: Tupla (lat, lon) de la ubicación
            center: Tupla (lat, lon) del centro del municipio
            
        Returns:
            Score de accesibilidad (0-100)
        """
        distance = self._haversine_distance(location, center)
        
        # Score inversamente proporcional a la distancia
        # Máximo score a 0km, mínimo a 10km+
        if distance == 0:
            return 100.0
        elif distance >= 10:
            return 0.0
        else:
            return max(0, 100 - (distance * 10))
    
    def normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza características para el scoring
        
        Args:
            df: DataFrame con datos de ubicaciones
            
        Returns:
            DataFrame con características normalizadas
        """
        df_norm = df.copy()
        
        # Normalizar población (0-100)
        if df_norm['poblacion_total'].max() > 0:
            df_norm['poblacion_norm'] = (
                (df_norm['poblacion_total'] - df_norm['poblacion_total'].min()) /
                (df_norm['poblacion_total'].max() - df_norm['poblacion_total'].min())
            ) * 100
        else:
            df_norm['poblacion_norm'] = 0
        
        # Normalizar competidores (inverso: menos competidores = mejor)
        if df_norm['competidores_cercanos'].max() > 0:
            df_norm['competencia_norm'] = (
                1 - (df_norm['competidores_cercanos'] / df_norm['competidores_cercanos'].max())
            ) * 100
        else:
            df_norm['competencia_norm'] = 100
        
        # Normalizar distancia a zona comercial (menor distancia = mejor)
        max_dist = df_norm['distancia_zona_comercial'].max()
        if max_dist > 0:
            df_norm['zona_comercial_norm'] = (
                1 - (df_norm['distancia_zona_comercial'] / max_dist)
            ) * 100
        else:
            df_norm['zona_comercial_norm'] = 100
        
        return df_norm
























