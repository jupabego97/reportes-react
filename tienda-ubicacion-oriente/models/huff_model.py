"""
Modelo de Huff para análisis de áreas de influencia comercial
Calcula probabilidad de atracción de clientes
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from math import sqrt

class HuffModel:
    """
    Modelo de Huff: Estándar de la industria para análisis 
    de áreas comerciales y probabilidad de atracción
    
    P(ij) = (Sj^α / Dij^β) / Σ(Sk^α / Dik^β)
    
    Donde:
    - P(ij): Probabilidad de que consumidor i visite tienda j
    - Sj: Tamaño/atractivo de la tienda j
    - Dij: Distancia entre consumidor i y tienda j
    - α: Factor de atractivo (default: 1)
    - β: Factor de decaimiento por distancia (default: 2)
    """
    
    def __init__(self, attractiveness_factor: float = 1.0, 
                 distance_decay: float = 2.0):
        """
        Inicializa el modelo de Huff
        
        Args:
            attractiveness_factor: Factor α de atractivo (default: 1.0)
            distance_decay: Factor β de decaimiento por distancia (default: 2.0)
        """
        self.alpha = attractiveness_factor
        self.beta = distance_decay
    
    def calculate_probability(self, store_size: float, distance: float,
                             competitors: List[Dict]) -> float:
        """
        Calcula la probabilidad de que un consumidor visite una tienda
        
        Args:
            store_size: Tamaño/atractivo de la tienda (normalizado 0-1)
            distance: Distancia en kilómetros
            competitors: Lista de competidores con formato:
                [{'size': float, 'distance': float}, ...]
        
        Returns:
            Probabilidad de atracción (0-1)
        """
        # Evitar división por cero
        if distance == 0:
            distance = 0.001
        
        # Calcular atractivo de la tienda
        attractiveness = (store_size ** self.alpha) / (distance ** self.beta)
        
        # Calcular atractivo total (tienda + competidores)
        total_attractiveness = attractiveness
        for competitor in competitors:
            comp_distance = competitor.get('distance', 999)
            if comp_distance == 0:
                comp_distance = 0.001
            comp_size = competitor.get('size', 0.5)
            total_attractiveness += (comp_size ** self.alpha) / (comp_distance ** self.beta)
        
        # Probabilidad = atractivo de la tienda / atractivo total
        if total_attractiveness == 0:
            return 0.0
        
        return attractiveness / total_attractiveness
    
    def calculate_market_share(self, location: Tuple[float, float],
                              store_size: float,
                              demand_points: np.ndarray,
                              demand_weights: np.ndarray,
                              competitors: List[Dict]) -> float:
        """
        Calcula participación de mercado para una ubicación
        
        Args:
            location: Tupla (lat, lon) de la ubicación
            store_size: Tamaño/atractivo de la tienda
            demand_points: Array numpy de puntos de demanda (n, 2)
            demand_weights: Array numpy de pesos de demanda (población)
            competitors: Lista de competidores con ubicaciones
        
        Returns:
            Participación de mercado estimada (población)
        """
        total_market_share = 0.0
        
        for i, demand_point in enumerate(demand_points):
            # Calcular distancia desde punto de demanda a la tienda
            distance = self._haversine_distance(
                (demand_point[0], demand_point[1]),
                location
            )
            
            # Calcular distancias a competidores
            competitor_distances = []
            for comp in competitors:
                comp_location = comp.get('location', {})
                if isinstance(comp_location, dict):
                    comp_lat = comp_location.get('lat')
                    comp_lon = comp_location.get('lng')
                elif isinstance(comp_location, tuple):
                    comp_lat, comp_lon = comp_location
                else:
                    continue
                
                comp_distance = self._haversine_distance(
                    (demand_point[0], demand_point[1]),
                    (comp_lat, comp_lon)
                )
                competitor_distances.append({
                    'distance': comp_distance,
                    'size': comp.get('size', 0.5)
                })
            
            # Calcular probabilidad de atracción
            probability = self.calculate_probability(
                store_size,
                distance,
                competitor_distances
            )
            
            # Acumular participación de mercado ponderada
            total_market_share += probability * demand_weights[i]
        
        return total_market_share
    
    def analyze_location(self, location: Tuple[float, float],
                        store_size: float,
                        demand_points: np.ndarray,
                        demand_weights: np.ndarray,
                        competitors: List[Dict]) -> Dict:
        """
        Analiza una ubicación usando el modelo de Huff
        
        Args:
            location: Tupla (lat, lon) de la ubicación
            store_size: Tamaño/atractivo de la tienda
            demand_points: Puntos de demanda
            demand_weights: Pesos de demanda
            competitors: Lista de competidores
        
        Returns:
            Diccionario con métricas del análisis
        """
        market_share = self.calculate_market_share(
            location,
            store_size,
            demand_points,
            demand_weights,
            competitors
        )
        
        # Calcular población alcanzable (dentro de 10km)
        reachable_population = 0.0
        for i, demand_point in enumerate(demand_points):
            distance = self._haversine_distance(
                (demand_point[0], demand_point[1]),
                location
            )
            if distance <= 10.0:  # 10km de radio
                reachable_population += demand_weights[i]
        
        # Calcular competencia promedio cercana
        avg_competitor_distance = 999.0
        if competitors:
            distances = []
            for comp in competitors:
                comp_location = comp.get('location', {})
                if isinstance(comp_location, dict):
                    comp_lat = comp_location.get('lat')
                    comp_lon = comp_location.get('lng')
                elif isinstance(comp_location, tuple):
                    comp_lat, comp_lon = comp_location
                else:
                    continue
                
                dist = self._haversine_distance(location, (comp_lat, comp_lon))
                distances.append(dist)
            
            if distances:
                avg_competitor_distance = np.mean(distances)
        
        return {
            'market_share': market_share,
            'reachable_population': reachable_population,
            'avg_competitor_distance': avg_competitor_distance,
            'huff_score': market_share / max(reachable_population, 1) * 100
        }
    
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
























