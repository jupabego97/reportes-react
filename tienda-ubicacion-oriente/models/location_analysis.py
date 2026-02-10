"""
Algoritmo P-Median para análisis de ubicación óptima
Encuentra ubicaciones que minimizan la distancia total ponderada
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from typing import List, Tuple, Dict
from scipy.spatial.distance import cdist

class LocationAllocationAnalysis:
    """
    Implementación del algoritmo P-Median para encontrar 
    ubicaciones óptimas minimizando la distancia total ponderada
    """
    
    def __init__(self, n_facilities: int = 3):
        """
        Inicializa el análisis de ubicación
        
        Args:
            n_facilities: Número de instalaciones a ubicar
        """
        self.n_facilities = n_facilities
    
    def p_median_optimization(self, demand_points: np.ndarray,
                             weights: np.ndarray = None) -> np.ndarray:
        """
        Encuentra las p ubicaciones que minimizan la distancia 
        ponderada total a todos los puntos de demanda
        
        Args:
            demand_points: Array numpy de puntos de demanda (n, 2) con (lat, lon)
            weights: Array numpy de pesos para cada punto de demanda
            
        Returns:
            Array numpy con las ubicaciones óptimas (p, 2)
        """
        if weights is None:
            weights = np.ones(len(demand_points))
        
        # Normalizar pesos
        weights = weights / weights.sum()
        
        # Usar K-Means ponderado para encontrar centros iniciales
        kmeans = KMeans(
            n_clusters=self.n_facilities,
            random_state=42,
            n_init=10,
            max_iter=300
        )
        
        # Aplicar K-Means con pesos
        kmeans.fit(demand_points, sample_weight=weights)
        initial_centers = kmeans.cluster_centers_
        
        # Refinar usando algoritmo P-Median iterativo
        optimal_locations = self._refine_p_median(
            demand_points,
            weights,
            initial_centers
        )
        
        return optimal_locations
    
    def _refine_p_median(self, demand_points: np.ndarray,
                        weights: np.ndarray,
                        initial_centers: np.ndarray) -> np.ndarray:
        """
        Refina las ubicaciones usando algoritmo P-Median iterativo
        
        Args:
            demand_points: Puntos de demanda
            weights: Pesos de demanda
            initial_centers: Centros iniciales
            
        Returns:
            Ubicaciones optimizadas
        """
        current_centers = initial_centers.copy()
        max_iterations = 50
        tolerance = 1e-6
        
        for iteration in range(max_iterations):
            # Asignar cada punto de demanda a la instalación más cercana
            distances = cdist(demand_points, current_centers, metric='euclidean')
            assignments = np.argmin(distances, axis=1)
            
            # Calcular nuevos centros como centroides ponderados
            new_centers = np.zeros_like(current_centers)
            
            for i in range(self.n_facilities):
                mask = assignments == i
                if mask.sum() > 0:
                    # Centroide ponderado
                    weighted_points = demand_points[mask] * weights[mask, np.newaxis]
                    new_centers[i] = weighted_points.sum(axis=0) / weights[mask].sum()
                else:
                    # Si no hay puntos asignados, mantener el centro actual
                    new_centers[i] = current_centers[i]
            
            # Verificar convergencia
            if np.allclose(current_centers, new_centers, atol=tolerance):
                break
            
            current_centers = new_centers
        
        return current_centers
    
    def calculate_total_weighted_distance(self, facilities: np.ndarray,
                                         demand_points: np.ndarray,
                                         weights: np.ndarray) -> float:
        """
        Calcula la distancia total ponderada
        
        Args:
            facilities: Ubicaciones de instalaciones (p, 2)
            demand_points: Puntos de demanda (n, 2)
            weights: Pesos de demanda (n,)
            
        Returns:
            Distancia total ponderada
        """
        distances = cdist(demand_points, facilities, metric='euclidean')
        min_distances = distances.min(axis=1)
        total_distance = (min_distances * weights).sum()
        
        return total_distance
    
    def analyze_candidate_locations(self, candidate_locations: pd.DataFrame,
                                   demand_points: np.ndarray,
                                   weights: np.ndarray) -> pd.DataFrame:
        """
        Analiza ubicaciones candidatas y calcula métricas
        
        Args:
            candidate_locations: DataFrame con ubicaciones candidatas
            demand_points: Puntos de demanda
            weights: Pesos de demanda
            
        Returns:
            DataFrame enriquecido con métricas de análisis
        """
        df = candidate_locations.copy()
        
        # Convertir coordenadas a array numpy
        locations = df[['lat', 'lon']].values
        
        # Calcular distancia total ponderada para cada candidato
        df['weighted_distance'] = df.apply(
            lambda row: self._calculate_weighted_distance_for_location(
                (row['lat'], row['lon']),
                demand_points,
                weights
            ),
            axis=1
        )
        
        # Calcular población alcanzable (dentro de 5km)
        df['poblacion_alcanzable'] = df.apply(
            lambda row: self._calculate_reachable_population(
                (row['lat'], row['lon']),
                demand_points,
                weights,
                radius_km=5.0
            ),
            axis=1
        )
        
        return df
    
    def _calculate_weighted_distance_for_location(self, location: Tuple[float, float],
                                                  demand_points: np.ndarray,
                                                  weights: np.ndarray) -> float:
        """Calcula distancia ponderada para una ubicación"""
        location_array = np.array([[location[0], location[1]]])
        distances = cdist(location_array, demand_points, metric='euclidean')[0]
        return (distances * weights).sum()
    
    def _calculate_reachable_population(self, location: Tuple[float, float],
                                       demand_points: np.ndarray,
                                       weights: np.ndarray,
                                       radius_km: float = 5.0) -> float:
        """
        Calcula población alcanzable dentro de un radio
        
        Args:
            location: Tupla (lat, lon)
            demand_points: Puntos de demanda
            weights: Pesos (población)
            radius_km: Radio en kilómetros
            
        Returns:
            Población alcanzable
        """
        # Convertir radio a grados (aproximado: 1 grado ≈ 111km)
        radius_deg = radius_km / 111.0
        
        location_array = np.array([[location[0], location[1]]])
        distances = cdist(location_array, demand_points, metric='euclidean')[0]
        
        # Distancias en grados, convertir a km
        distances_km = distances * 111.0
        
        # Sumar pesos de puntos dentro del radio
        mask = distances_km <= radius_km
        return weights[mask].sum()
























