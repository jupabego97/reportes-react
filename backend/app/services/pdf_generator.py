"""
Generador de reportes PDF.
"""
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class PDFReportGenerator:
    """Generador de reportes PDF para ventas."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos personalizados."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceBefore=20,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#1e40af'),
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
    
    def generate_sales_report(
        self,
        metricas: Dict[str, Any],
        top_productos: List[Dict],
        top_vendedores: List[Dict],
        ventas_por_familia: List[Dict],
        alertas: List[Dict],
        fecha_inicio: str = None,
        fecha_fin: str = None
    ) -> bytes:
        """Genera un reporte PDF completo de ventas."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        elements = []
        
        # Título
        elements.append(Paragraph("Reporte de Ventas", self.styles['CustomTitle']))
        
        # Período
        periodo = "Últimos 30 días"
        if fecha_inicio and fecha_fin:
            periodo = f"{fecha_inicio} - {fecha_fin}"
        elements.append(Paragraph(
            f"Período: {periodo}",
            self.styles['Normal']
        ))
        elements.append(Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 20))
        
        # Métricas principales
        elements.append(Paragraph("Resumen Ejecutivo", self.styles['SectionTitle']))
        elements.append(self._create_metrics_table(metricas))
        elements.append(Spacer(1, 20))
        
        # Alertas (si hay)
        if alertas:
            elements.append(Paragraph("⚠️ Alertas Activas", self.styles['SectionTitle']))
            elements.append(self._create_alerts_table(alertas[:5]))
            elements.append(Spacer(1, 20))
        
        # Top Productos
        if top_productos:
            elements.append(Paragraph("Top 10 Productos", self.styles['SectionTitle']))
            elements.append(self._create_products_table(top_productos[:10]))
            elements.append(Spacer(1, 20))
        
        # Top Vendedores
        if top_vendedores:
            elements.append(Paragraph("Ranking de Vendedores", self.styles['SectionTitle']))
            elements.append(self._create_sellers_table(top_vendedores[:10]))
            elements.append(Spacer(1, 20))
        
        # Ventas por Familia
        if ventas_por_familia:
            elements.append(Paragraph("Ventas por Familia", self.styles['SectionTitle']))
            elements.append(self._create_family_table(ventas_por_familia[:10]))
        
        # Construir PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _create_metrics_table(self, metricas: Dict[str, Any]) -> Table:
        """Crea tabla de métricas."""
        data = [
            [
                Paragraph("Total Ingresos", self.styles['MetricLabel']),
                Paragraph("Total Ventas", self.styles['MetricLabel']),
                Paragraph("Ticket Promedio", self.styles['MetricLabel']),
            ],
            [
                Paragraph(f"${metricas.get('total_ingresos', 0):,.0f}", self.styles['MetricValue']),
                Paragraph(f"{metricas.get('total_ventas', 0):,}", self.styles['MetricValue']),
                Paragraph(f"${metricas.get('ticket_promedio', 0):,.0f}", self.styles['MetricValue']),
            ],
            [
                Paragraph("Productos Únicos", self.styles['MetricLabel']),
                Paragraph("Margen Promedio", self.styles['MetricLabel']),
                Paragraph("Total Margen", self.styles['MetricLabel']),
            ],
            [
                Paragraph(f"{metricas.get('productos_unicos', 0):,}", self.styles['MetricValue']),
                Paragraph(f"{metricas.get('margen_promedio', 0):.1f}%", self.styles['MetricValue']),
                Paragraph(f"${metricas.get('total_margen', 0):,.0f}", self.styles['MetricValue']),
            ],
        ]
        
        table = Table(data, colWidths=[150, 150, 150])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f3f4f6')),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        return table
    
    def _create_alerts_table(self, alertas: List[Dict]) -> Table:
        """Crea tabla de alertas."""
        data = [['Tipo', 'Título', 'Mensaje']]
        
        for alerta in alertas:
            data.append([
                alerta.get('tipo', ''),
                alerta.get('titulo', ''),
                alerta.get('mensaje', '')[:50] + '...' if len(alerta.get('mensaje', '')) > 50 else alerta.get('mensaje', '')
            ])
        
        table = Table(data, colWidths=[60, 120, 270])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fee2e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#991b1b')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_products_table(self, productos: List[Dict]) -> Table:
        """Crea tabla de productos."""
        data = [['#', 'Producto', 'Cantidad', 'Total Ventas', 'Margen %']]
        
        for i, prod in enumerate(productos, 1):
            data.append([
                str(i),
                prod.get('nombre', '')[:30],
                f"{prod.get('cantidad', 0):,}",
                f"${prod.get('total_venta', 0):,.0f}",
                f"{prod.get('margen_porcentaje', 0):.1f}%" if prod.get('margen_porcentaje') else '-'
            ])
        
        table = Table(data, colWidths=[30, 200, 70, 100, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        
        return table
    
    def _create_sellers_table(self, vendedores: List[Dict]) -> Table:
        """Crea tabla de vendedores."""
        data = [['#', 'Vendedor', 'Transacciones', 'Total Ventas', 'Ticket Prom.']]
        
        for i, vend in enumerate(vendedores, 1):
            data.append([
                str(i),
                vend.get('vendedor', 'Sin nombre')[:25],
                f"{vend.get('cantidad', 0):,}",
                f"${vend.get('total_venta', 0):,.0f}",
                f"${vend.get('ticket_promedio', 0):,.0f}"
            ])
        
        table = Table(data, colWidths=[30, 150, 90, 100, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        
        return table
    
    def _create_family_table(self, familias: List[Dict]) -> Table:
        """Crea tabla de familias."""
        data = [['Familia', 'Cantidad', 'Total Ventas', '% del Total']]
        
        total_general = sum(f.get('total_venta', 0) for f in familias)
        
        for fam in familias:
            porcentaje = (fam.get('total_venta', 0) / total_general * 100) if total_general > 0 else 0
            data.append([
                fam.get('familia', 'Sin familia')[:25],
                f"{fam.get('cantidad', 0):,}",
                f"${fam.get('total_venta', 0):,.0f}",
                f"{porcentaje:.1f}%"
            ])
        
        table = Table(data, colWidths=[150, 100, 120, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        
        return table

