"""
Servicio de insights - Generación automática de insights de negocio.
"""
from datetime import date, timedelta
from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InsightsService:
    """Servicio para generar insights automáticos."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_insights_dashboard(self) -> List[Dict[str, Any]]:
        """Genera insights para el dashboard ejecutivo."""
        insights = []
        
        # 1. Insight: Mejor día de la semana
        mejor_dia = await self._get_mejor_dia_semana()
        if mejor_dia:
            insights.append(mejor_dia)
        
        # 2. Insight: Productos en crecimiento
        crecimiento = await self._get_productos_crecimiento()
        if crecimiento:
            insights.append(crecimiento)
        
        # 3. Insight: Productos en declive
        declive = await self._get_productos_declive()
        if declive:
            insights.append(declive)
        
        # 4. Insight: Productos sin movimiento
        sin_mov = await self._get_productos_sin_movimiento()
        if sin_mov:
            insights.append(sin_mov)
        
        # 5. Insight: Mejor vendedor
        mejor_vendedor = await self._get_mejor_vendedor()
        if mejor_vendedor:
            insights.append(mejor_vendedor)
        
        # 6. Insight: Familia más rentable
        familia_rentable = await self._get_familia_mas_rentable()
        if familia_rentable:
            insights.append(familia_rentable)
        
        return insights
    
    async def _get_mejor_dia_semana(self) -> Dict[str, Any] | None:
        """Encuentra el mejor día de la semana para ventas."""
        query = """
            SELECT 
                EXTRACT(DOW FROM fecha_venta) as dia_semana,
                SUM(precio * cantidad) as total_venta,
                COUNT(*) as transacciones
            FROM reportes_ventas_30dias
            GROUP BY EXTRACT(DOW FROM fecha_venta)
            ORDER BY total_venta DESC
            LIMIT 1
        """
        try:
            result = await self.db.execute(text(query))
            row = result.fetchone()
            
            if row:
                dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
                dia_nombre = dias[int(row[0])]
                total = float(row[1])
                
                # Calcular diferencia con promedio
                avg_query = """
                    SELECT AVG(total_dia) FROM (
                        SELECT fecha_venta, SUM(precio * cantidad) as total_dia
                        FROM reportes_ventas_30dias
                        GROUP BY fecha_venta
                    ) t
                """
                avg_result = await self.db.execute(text(avg_query))
                promedio = float(avg_result.scalar() or 0)
                
                if promedio > 0:
                    diferencia = ((total / 7 * 30 / 4) / promedio - 1) * 100  # Aproximación semanal
                    
                    return {
                        "tipo": "positive",
                        "icono": "📅",
                        "titulo": f"{dia_nombre} es tu mejor día",
                        "descripcion": f"Vendes un {abs(diferencia):.0f}% más que el promedio. Considera reforzar personal ese día.",
                    }
        except Exception:
            pass
        return None
    
    async def _get_productos_crecimiento(self) -> Dict[str, Any] | None:
        """Encuentra productos con tendencia positiva."""
        query = """
            WITH semana_actual AS (
                SELECT nombre, SUM(cantidad) as cantidad
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY nombre
            ),
            semana_anterior AS (
                SELECT nombre, SUM(cantidad) as cantidad
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '14 days'
                  AND fecha_venta < CURRENT_DATE - INTERVAL '7 days'
                GROUP BY nombre
            )
            SELECT 
                sa.nombre,
                sa.cantidad as actual,
                COALESCE(sp.cantidad, 0) as anterior,
                CASE WHEN COALESCE(sp.cantidad, 0) > 0 
                    THEN ((sa.cantidad::float - sp.cantidad) / sp.cantidad * 100)
                    ELSE 100
                END as crecimiento
            FROM semana_actual sa
            LEFT JOIN semana_anterior sp ON sa.nombre = sp.nombre
            WHERE sa.cantidad > COALESCE(sp.cantidad, 0)
            ORDER BY crecimiento DESC
            LIMIT 5
        """
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            if rows:
                productos = [row[0] for row in rows[:3]]
                return {
                    "tipo": "positive",
                    "icono": "📈",
                    "titulo": f"{len(rows)} productos en crecimiento",
                    "descripcion": f"Destacados: {', '.join(productos)}. Considera aumentar stock.",
                }
        except Exception:
            pass
        return None
    
    async def _get_productos_declive(self) -> Dict[str, Any] | None:
        """Encuentra productos con tendencia negativa."""
        query = """
            WITH semana_actual AS (
                SELECT nombre, SUM(cantidad) as cantidad
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY nombre
            ),
            semana_anterior AS (
                SELECT nombre, SUM(cantidad) as cantidad
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '14 days'
                  AND fecha_venta < CURRENT_DATE - INTERVAL '7 days'
                GROUP BY nombre
            )
            SELECT 
                sp.nombre,
                COALESCE(sa.cantidad, 0) as actual,
                sp.cantidad as anterior,
                ((COALESCE(sa.cantidad, 0)::float - sp.cantidad) / sp.cantidad * 100) as cambio
            FROM semana_anterior sp
            LEFT JOIN semana_actual sa ON sa.nombre = sp.nombre
            WHERE COALESCE(sa.cantidad, 0) < sp.cantidad
            ORDER BY cambio ASC
            LIMIT 5
        """
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            if rows:
                productos = [row[0] for row in rows[:3]]
                return {
                    "tipo": "warning",
                    "icono": "📉",
                    "titulo": f"{len(rows)} productos en declive",
                    "descripcion": f"Atención: {', '.join(productos)}. Revisar precios o promociones.",
                }
        except Exception:
            pass
        return None
    
    async def _get_productos_sin_movimiento(self) -> Dict[str, Any] | None:
        """Encuentra productos sin ventas recientes."""
        query = """
            SELECT i.nombre, i.cantidad_disponible, i.precio
            FROM items i
            WHERE i.cantidad_disponible > 0
            AND i.nombre NOT IN (
                SELECT DISTINCT nombre 
                FROM reportes_ventas_30dias
            )
            ORDER BY i.cantidad_disponible * i.precio DESC
            LIMIT 10
        """
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            if rows:
                valor_total = sum(float(row[1] or 0) * float(row[2] or 0) for row in rows)
                return {
                    "tipo": "warning",
                    "icono": "💤",
                    "titulo": f"{len(rows)} productos sin movimiento",
                    "descripcion": f"Capital inmovilizado: ${valor_total:,.0f}. Considera promociones o devolución.",
                }
        except Exception:
            pass
        return None
    
    async def _get_mejor_vendedor(self) -> Dict[str, Any] | None:
        """Encuentra el vendedor con mejor desempeño."""
        query = """
            SELECT 
                vendedor,
                SUM(precio * cantidad) as total_venta,
                COUNT(*) as transacciones
            FROM reportes_ventas_30dias
            WHERE vendedor IS NOT NULL
            GROUP BY vendedor
            ORDER BY total_venta DESC
            LIMIT 1
        """
        try:
            result = await self.db.execute(text(query))
            row = result.fetchone()
            
            if row:
                return {
                    "tipo": "positive",
                    "icono": "🏆",
                    "titulo": f"{row[0]} lidera las ventas",
                    "descripcion": f"${float(row[1]):,.0f} en ventas con {row[2]} transacciones este mes.",
                }
        except Exception:
            pass
        return None
    
    async def _get_familia_mas_rentable(self) -> Dict[str, Any] | None:
        """Encuentra la familia de productos más rentable."""
        query = """
            SELECT 
                familia,
                SUM(precio * cantidad) as total_venta,
                AVG(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN ((precio - precio_promedio_compra) / NULLIF(precio, 0)) * 100 
                    ELSE NULL END) as margen_promedio
            FROM reportes_ventas_30dias
            WHERE familia IS NOT NULL AND precio_promedio_compra IS NOT NULL
            GROUP BY familia
            HAVING AVG(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN ((precio - precio_promedio_compra) / NULLIF(precio, 0)) * 100 
                    ELSE NULL END) IS NOT NULL
            ORDER BY margen_promedio DESC
            LIMIT 1
        """
        try:
            result = await self.db.execute(text(query))
            row = result.fetchone()
            
            if row and row[2]:
                return {
                    "tipo": "positive",
                    "icono": "💰",
                    "titulo": f"{row[0]} es tu categoría más rentable",
                    "descripcion": f"Margen promedio del {float(row[2]):.1f}%. Prioriza stock de esta familia.",
                }
        except Exception:
            pass
        return None
    
    async def get_kpis_ejecutivo(self) -> Dict[str, Any]:
        """Obtiene KPIs para el dashboard ejecutivo."""
        
        # Ventas del día
        ventas_hoy_query = """
            SELECT 
                COALESCE(SUM(precio * cantidad), 0) as total_hoy,
                COUNT(*) as transacciones_hoy
            FROM reportes_ventas_30dias
            WHERE fecha_venta = CURRENT_DATE
        """
        
        # Ventas ayer para comparación
        ventas_ayer_query = """
            SELECT COALESCE(SUM(precio * cantidad), 0) as total_ayer
            FROM reportes_ventas_30dias
            WHERE fecha_venta = CURRENT_DATE - INTERVAL '1 day'
        """
        
        # Total del mes
        ventas_mes_query = """
            SELECT 
                COALESCE(SUM(precio * cantidad), 0) as total_mes,
                COUNT(*) as transacciones_mes,
                COUNT(DISTINCT nombre) as productos_vendidos,
                AVG(precio * cantidad) as ticket_promedio
            FROM reportes_ventas_30dias
        """
        
        # Margen total
        margen_query = """
            SELECT 
                COALESCE(SUM(
                    CASE WHEN precio_promedio_compra IS NOT NULL 
                        THEN (precio - precio_promedio_compra) * cantidad
                        ELSE 0
                    END
                ), 0) as margen_total
            FROM reportes_ventas_30dias
        """
        
        try:
            hoy_result = await self.db.execute(text(ventas_hoy_query))
            hoy = hoy_result.fetchone()
            
            ayer_result = await self.db.execute(text(ventas_ayer_query))
            ayer = ayer_result.fetchone()
            
            mes_result = await self.db.execute(text(ventas_mes_query))
            mes = mes_result.fetchone()
            
            margen_result = await self.db.execute(text(margen_query))
            margen = margen_result.fetchone()
            
            total_hoy = float(hoy[0]) if hoy else 0
            total_ayer = float(ayer[0]) if ayer else 0
            delta_hoy = ((total_hoy - total_ayer) / total_ayer * 100) if total_ayer > 0 else 0
            
            return {
                "ventas_hoy": round(total_hoy, 2),
                "transacciones_hoy": hoy[1] if hoy else 0,
                "delta_vs_ayer": round(delta_hoy, 1),
                "ventas_mes": round(float(mes[0]) if mes else 0, 2),
                "transacciones_mes": mes[1] if mes else 0,
                "productos_vendidos": mes[2] if mes else 0,
                "ticket_promedio": round(float(mes[3]) if mes and mes[3] else 0, 2),
                "margen_total": round(float(margen[0]) if margen else 0, 2),
            }
        except Exception:
            return {
                "ventas_hoy": 0,
                "transacciones_hoy": 0,
                "delta_vs_ayer": 0,
                "ventas_mes": 0,
                "transacciones_mes": 0,
                "productos_vendidos": 0,
                "ticket_promedio": 0,
                "margen_total": 0,
            }
