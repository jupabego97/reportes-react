"""
Servicio de integración con Google Maps API
Incluye Places API, Geocoding y Distance Matrix
"""

import os
import time
import googlemaps
from typing import List, Dict, Tuple, Optional
import json

class GoogleMapsService:
    """Servicio para interactuar con Google Maps API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el servicio de Google Maps
        
        Args:
            api_key: Clave API de Google Maps
        """
        self.gmaps = googlemaps.Client(key=api_key)
        self.api_key = api_key
        self._cache = {}
    
    def get_competitors(self, location: Tuple[float, float], radius: int = 5000, 
                       keyword: str = "tienda tecnología electrónica computadores") -> List[Dict]:
        """
        Obtiene tiendas de tecnología competidoras cercanas
        
        Args:
            location: Tupla (lat, lon) del punto central
            radius: Radio de búsqueda en metros (default 5000m = 5km)
            keyword: Palabras clave para la búsqueda
            
        Returns:
            Lista de diccionarios con información de competidores
        """
        cache_key = f"competitors_{location}_{radius}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Buscar lugares cercanos
            places_result = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                type='electronics_store',
                keyword=keyword
            )
            
            competitors = []
            for place in places_result.get('results', []):
                competitors.append({
                    'name': place.get('name', ''),
                    'place_id': place.get('place_id', ''),
                    'location': place.get('geometry', {}).get('location', {}),
                    'rating': place.get('rating', 0),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'vicinity': place.get('vicinity', ''),
                    'types': place.get('types', [])
                })
            
            # Obtener más resultados si hay página siguiente
            while 'next_page_token' in places_result:
                time.sleep(2)  # Esperar para el token
                places_result = self.gmaps.places_nearby(
                    location=location,
                    radius=radius,
                    type='electronics_store',
                    keyword=keyword,
                    page_token=places_result['next_page_token']
                )
                for place in places_result.get('results', []):
                    competitors.append({
                        'name': place.get('name', ''),
                        'place_id': place.get('place_id', ''),
                        'location': place.get('geometry', {}).get('location', {}),
                        'rating': place.get('rating', 0),
                        'user_ratings_total': place.get('user_ratings_total', 0),
                        'vicinity': place.get('vicinity', ''),
                        'types': place.get('types', [])
                    })
            
            self._cache[cache_key] = competitors
            return competitors
            
        except Exception as e:
            print(f"Error obteniendo competidores: {e}")
            return []
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Geocodifica una dirección a coordenadas
        
        Args:
            address: Dirección a geocodificar
            
        Returns:
            Diccionario con lat, lon y otros datos o None
        """
        cache_key = f"geocode_{address}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            geocode_result = self.gmaps.geocode(address)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                result = {
                    'lat': location['lat'],
                    'lon': location['lng'],
                    'formatted_address': geocode_result[0].get('formatted_address', ''),
                    'place_id': geocode_result[0].get('place_id', '')
                }
                self._cache[cache_key] = result
                return result
            return None
        except Exception as e:
            print(f"Error geocodificando dirección: {e}")
            return None
    
    def get_distance_matrix(self, origins: List[Tuple[float, float]], 
                          destinations: List[Tuple[float, float]],
                          mode: str = 'driving') -> Dict:
        """
        Calcula matriz de distancias y tiempos de viaje
        
        Args:
            origins: Lista de tuplas (lat, lon) de origen
            destinations: Lista de tuplas (lat, lon) de destino
            mode: Modo de transporte ('driving', 'walking', 'transit')
            
        Returns:
            Diccionario con distancias y tiempos
        """
        try:
            # Convertir tuplas a strings para la API
            origins_str = [f"{lat},{lon}" for lat, lon in origins]
            destinations_str = [f"{lat},{lon}" for lat, lon in destinations]
            
            matrix = self.gmaps.distance_matrix(
                origins=origins_str,
                destinations=destinations_str,
                mode=mode,
                language='es',
                units='metric'
            )
            
            return matrix
        except Exception as e:
            print(f"Error calculando matriz de distancias: {e}")
            return {}
    
    def get_place_details(self, place_id: str) -> Dict:
        """
        Obtiene detalles completos de un lugar
        
        Args:
            place_id: ID del lugar en Google Places
            
        Returns:
            Diccionario con detalles del lugar
        """
        cache_key = f"place_details_{place_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            place_details = self.gmaps.place(
                place_id=place_id,
                fields=['name', 'geometry', 'formatted_address', 'rating', 
                       'user_ratings_total', 'opening_hours', 'types']
            )
            result = place_details.get('result', {})
            self._cache[cache_key] = result
            return result
        except Exception as e:
            print(f"Error obteniendo detalles del lugar: {e}")
            return {}
    
    def search_commercial_areas(self, location: Tuple[float, float], 
                               radius: int = 3000) -> List[Dict]:
        """
        Busca zonas comerciales (centros comerciales, áreas comerciales)
        
        Args:
            location: Tupla (lat, lon) del punto central
            radius: Radio de búsqueda en metros
            
        Returns:
            Lista de zonas comerciales encontradas
        """
        cache_key = f"commercial_{location}_{radius}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Buscar centros comerciales
            shopping_malls = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                type='shopping_mall'
            )
            
            # Buscar áreas comerciales
            commercial_areas = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                keyword='zona comercial centro comercial'
            )
            
            results = []
            for place in shopping_malls.get('results', []):
                results.append({
                    'name': place.get('name', ''),
                    'location': place.get('geometry', {}).get('location', {}),
                    'place_id': place.get('place_id', ''),
                    'type': 'shopping_mall',
                    'rating': place.get('rating', 0)
                })
            
            for place in commercial_areas.get('results', []):
                if place.get('place_id') not in [r['place_id'] for r in results]:
                    results.append({
                        'name': place.get('name', ''),
                        'location': place.get('geometry', {}).get('location', {}),
                        'place_id': place.get('place_id', ''),
                        'type': 'commercial_area',
                        'rating': place.get('rating', 0)
                    })
            
            self._cache[cache_key] = results
            return results
            
        except Exception as e:
            print(f"Error buscando zonas comerciales: {e}")
            return []
    
    def estimate_traffic(self, origin: Tuple[float, float], 
                        destination: Tuple[float, float]) -> Dict:
        """
        Estima tráfico y tiempo de viaje entre dos puntos
        
        Args:
            origin: Tupla (lat, lon) de origen
            destination: Tupla (lat, lon) de destino
            
        Returns:
            Diccionario con tiempo de viaje y distancia
        """
        try:
            directions = self.gmaps.directions(
                origin=f"{origin[0]},{origin[1]}",
                destination=f"{destination[0]},{destination[1]}",
                mode='driving',
                departure_time='now',
                traffic_model='best_guess'
            )
            
            if directions:
                leg = directions[0]['legs'][0]
                return {
                    'distance_meters': leg['distance']['value'],
                    'duration_seconds': leg['duration']['value'],
                    'duration_in_traffic_seconds': leg.get('duration_in_traffic', {}).get('value', leg['duration']['value'])
                }
            return {}
        except Exception as e:
            print(f"Error estimando tráfico: {e}")
            return {}
























