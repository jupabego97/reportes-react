"""
Sistema de puntuación multi-criterio para evaluar ubicaciones
Usa pesos ajustados priorizando población y tráfico
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from sklearn.preprocessing import MinMaxScaler

class SiteSelectionScoring:
    """
    Sistema de puntuación multi-criterio para evaluar ubicaciones
    Pesos ajustados según importancia:
    - Población: 35%
    - Tráfico: 30%
    - Competencia/Zonas comerciales: 15%
    - Nivel socioeconómico: 12%
    - Densidad comercial: 8%
    """
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Inicializa el sistema de scoring
        
        Args:
            custom_weights: Pesos personalizados (opcional)
        """
        # Pesos por defecto según el plan
        self.weights = custom_weights or {
            'poblacion': 0.35,              # Mayor peso - factor principal
            'trafico': 0.30,                # Segundo factor más importante
            'competencia_zona_comercial': 0.15,  # Zonas comerciales y competencia
            'nivel_socioeconomico': 0.12,   # Nivel socioeconómico
            'densidad_comercial': 0.08      # Densidad comercial existente
        }
        
        # Verificar que los pesos sumen 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            # Normalizar si no suman 1.0
            self.weights = {k: v/total_weight for k, v in self.weights.items()}
        
        self.scaler = MinMaxScaler()
    
    def calculate_score(self, location_data: Dict) -> float:
        """
        Calcula el score total de una ubicación
        
        Args:
            location_data: Diccionario con datos de la ubicación:
                - poblacion_total: Población total del municipio
                - poblacion_alcanzable: Población dentro del radio de influencia
                - trafico_peatonal: Score de tráfico peatonal (0-100)
                - trafico_vehicular: Score de tráfico vehicular (0-100)
                - competidores_cercanos: Número de competidores cercanos
                - distancia_zona_comercial: Distancia a zona comercial (km)
                - nivel_socioeconomico: Score de nivel socioeconómico (0-100)
                - densidad_comercial: Densidad de comercio en el área
        
        Returns:
            Score total (0-100)
        """
        # Normalizar y calcular score de población
        poblacion_score = self._calculate_poblacion_score(location_data)
        
        # Normalizar y calcular score de tráfico
        trafico_score = self._calculate_trafico_score(location_data)
        
        # Normalizar y calcular score de competencia/zona comercial
        competencia_score = self._calculate_competencia_score(location_data)
        
        # Normalizar y calcular score de nivel socioeconómico
        socioeconomico_score = self._calculate_socioeconomico_score(location_data)
        
        # Normalizar y calcular score de densidad comercial
        densidad_score = self._calculate_densidad_score(location_data)
        
        # Calcular score ponderado total
        total_score = (
            poblacion_score * self.weights['poblacion'] +
            trafico_score * self.weights['trafico'] +
            competencia_score * self.weights['competencia_zona_comercial'] +
            socioeconomico_score * self.weights['nivel_socioeconomico'] +
            densidad_score * self.weights['densidad_comercial']
        )
        
        return min(100, max(0, total_score))
    
    def _calculate_poblacion_score(self, data: Dict) -> float:
        """
        Calcula score de población (0-100)
        Considera población total y población alcanzable
        """
        poblacion_total = data.get('poblacion_total', 0)
        poblacion_alcanzable = data.get('poblacion_alcanzable', 0)
        
        # Score basado en población alcanzable (más relevante)
        # Normalizar a escala 0-100
        # Asumimos máximo de 200,000 habitantes alcanzables
        max_poblacion = 200000
        poblacion_norm = min(100, (poblacion_alcanzable / max_poblacion) * 100)
        
        # Bonus por población total del municipio (indica potencial)
        poblacion_total_norm = min(50, (poblacion_total / 200000) * 50)
        
        return (poblacion_norm * 0.7) + (poblacion_total_norm * 0.3)
    
    def _calculate_trafico_score(self, data: Dict) -> float:
        """
        Calcula score de tráfico (0-100)
        Considera tráfico peatonal y vehicular
        """
        trafico_peatonal = data.get('trafico_peatonal', 0)
        trafico_vehicular = data.get('trafico_vehicular', 0)
        
        # Si no hay datos específicos, usar proxies
        if trafico_peatonal == 0 and trafico_vehicular == 0:
            # Usar distancia a zona comercial como proxy
            distancia_comercial = data.get('distancia_zona_comercial', 999)
            if distancia_comercial < 1.0:
                trafico_peatonal = 80
                trafico_vehicular = 70
            elif distancia_comercial < 2.0:
                trafico_peatonal = 60
                trafico_vehicular = 60
            else:
                trafico_peatonal = 40
                trafico_vehicular = 50
        
        # Promedio ponderado (tráfico peatonal más importante para tiendas)
        return (trafico_peatonal * 0.6) + (trafico_vehicular * 0.4)
    
    def _calculate_competencia_score(self, data: Dict) -> float:
        """
        Calcula score de competencia/zona comercial (0-100)
        Menos competencia y más cerca de zona comercial = mejor
        """
        competidores = data.get('competidores_cercanos', 0)
        distancia_comercial = data.get('distancia_zona_comercial', 999)
        
        # Score de competencia (menos competidores = mejor)
        # 0 competidores = 100, 5+ competidores = 0
        competencia_norm = max(0, 100 - (competidores * 20))
        
        # Score de zona comercial (más cerca = mejor)
        # 0km = 100, 5km+ = 0
        if distancia_comercial >= 5.0:
            zona_norm = 0
        else:
            zona_norm = max(0, 100 - (distancia_comercial * 20))
        
        # Balance: queremos estar cerca de zonas comerciales pero no demasiada competencia
        # Si hay zona comercial cerca pero poca competencia = excelente
        if distancia_comercial < 1.0 and competidores < 2:
            return 100
        elif distancia_comercial < 2.0 and competidores < 3:
            return 80
        else:
            return (competencia_norm * 0.6) + (zona_norm * 0.4)
    
    def _calculate_socioeconomico_score(self, data: Dict) -> float:
        """
        Calcula score de nivel socioeconómico (0-100)
        """
        nivel_socioeconomico = data.get('nivel_socioeconomico', 50)
        
        # Si viene como score directo, usarlo
        if isinstance(nivel_socioeconomico, (int, float)):
            return min(100, max(0, nivel_socioeconomico))
        
        # Si viene como estrato promedio, convertir
        estrato_promedio = data.get('estrato_promedio', 3.0)
        return (estrato_promedio / 6.0) * 100
    
    def _calculate_densidad_score(self, data: Dict) -> float:
        """
        Calcula score de densidad comercial (0-100)
        Mayor densidad comercial = mejor (indica zona activa)
        """
        densidad_comercial = data.get('densidad_comercial', 0)
        
        # Normalizar densidad comercial
        # Asumimos máximo de 50 establecimientos comerciales por km²
        max_densidad = 50
        if densidad_comercial == 0:
            # Usar competidores como proxy
            competidores = data.get('competidores_cercanos', 0)
            densidad_comercial = competidores * 5
        
        densidad_norm = min(100, (densidad_comercial / max_densidad) * 100)
        return densidad_norm
    
    def rank_locations(self, locations_df: pd.DataFrame) -> pd.DataFrame:
        """
        Rankea todas las ubicaciones candidatas según su score
        
        Args:
            locations_df: DataFrame con datos de ubicaciones candidatas
        
        Returns:
            DataFrame ordenado por score descendente
        """
        df = locations_df.copy()
        
        # Calcular score para cada ubicación
        df['score'] = df.apply(
            lambda row: self.calculate_score(row.to_dict()),
            axis=1
        )
        
        # Ordenar por score descendente
        df = df.sort_values('score', ascending=False).reset_index(drop=True)
        
        # Agregar ranking
        df['ranking'] = range(1, len(df) + 1)
        
        return df
    
    def get_score_breakdown(self, location_data: Dict) -> Dict:
        """
        Obtiene desglose detallado del score
        
        Args:
            location_data: Datos de la ubicación
        
        Returns:
            Diccionario con scores individuales y total
        """
        return {
            'poblacion_score': self._calculate_poblacion_score(location_data),
            'trafico_score': self._calculate_trafico_score(location_data),
            'competencia_score': self._calculate_competencia_score(location_data),
            'socioeconomico_score': self._calculate_socioeconomico_score(location_data),
            'densidad_score': self._calculate_densidad_score(location_data),
            'total_score': self.calculate_score(location_data),
            'weights': self.weights.copy()
        }
























