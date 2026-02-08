# 📊 Dashboard de Ventas

Dashboard moderno y completo para análisis de ventas, construido con React + FastAPI.

![Dashboard Preview](https://via.placeholder.com/800x400?text=Dashboard+de+Ventas)

## ✨ Características

### 🔐 Autenticación y Seguridad
- Sistema JWT con roles (admin, vendedor, viewer)
- Protección de rutas según permisos
- Sesión persistente con localStorage

### 📈 Dashboard Principal
- Métricas en tiempo real con comparativa vs período anterior
- Sistema de alertas inteligente (márgenes negativos, stock bajo, etc.)
- Gráficos interactivos con Nivo Charts
- Heatmap de ventas semanal

### 🔍 Filtros Avanzados
- Multi-select para productos, vendedores, familias, etc.
- Slider de rango de precios
- Filtros persistentes en localStorage
- Sincronización con URL params

### 📊 Análisis
- **Márgenes**: Análisis de rentabilidad por producto y familia
- **Predicciones**: Proyecciones basadas en tendencias históricas
- **ABC/Pareto**: Clasificación de productos por contribución
- **Vendedores**: Ranking y métricas de desempeño
- **Compras**: Sugerencias de reposición por prioridad

### 🎨 UI/UX
- Tema claro/oscuro con persistencia
- Sidebar colapsable
- Breadcrumbs de navegación
- Animaciones fluidas con Framer Motion
- Notificaciones toast con Sonner
- Diseño responsive

### 📤 Exportación
- CSV
- Excel (múltiples hojas)
- PDF (reporte completo)

## 🚀 Instalación

### Requisitos
- Node.js 18+
- Python 3.11+
- PostgreSQL 14+

### Backend

```bash
cd ventas-dashboard/backend

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL

# Ejecutar servidor
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd ventas-dashboard/frontend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev
```

## 🔑 Credenciales

Las credenciales de acceso son gestionadas por el administrador del sistema.
Contacta al administrador para obtener tus credenciales.

## 📁 Estructura del Proyecto

```
ventas-dashboard/
├── backend/
│   ├── app/
│   │   ├── auth/           # Sistema de autenticación
│   │   ├── models/         # Schemas Pydantic
│   │   ├── routes/         # Endpoints API
│   │   └── services/       # Lógica de negocio
│   ├── requirements.txt
│   └── .env
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── auth/       # Componentes de auth
    │   │   ├── charts/     # Gráficos Nivo
    │   │   ├── dashboard/  # Métricas y alertas
    │   │   ├── data/       # Tabla de datos
    │   │   ├── filters/    # Panel de filtros
    │   │   ├── layout/     # Sidebar, Header
    │   │   └── ui/         # Componentes base
    │   ├── hooks/          # React Query hooks
    │   ├── pages/          # Páginas principales
    │   ├── services/       # API client
    │   └── stores/         # Zustand stores
    └── package.json
```

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI** - Framework web async
- **SQLAlchemy** - ORM async
- **Pydantic** - Validación de datos
- **python-jose** - JWT tokens
- **ReportLab** - Generación PDF

### Frontend
- **React 18** - UI Library
- **TypeScript** - Type safety
- **TanStack Query** - Server state
- **Zustand** - Client state
- **Nivo** - Visualizaciones
- **shadcn/ui** - Componentes
- **Tailwind CSS** - Estilos
- **Framer Motion** - Animaciones

## 📝 API Endpoints

### Autenticación
- `POST /api/auth/login` - Login OAuth2
- `POST /api/auth/login/json` - Login JSON
- `GET /api/auth/me` - Usuario actual

### Dashboard
- `GET /api/dashboard` - Datos completos
- `GET /api/dashboard/metricas` - Métricas
- `GET /api/dashboard/alertas` - Alertas

### Ventas
- `GET /api/ventas` - Ventas paginadas
- `GET /api/ventas/all` - Todas las ventas
- `GET /api/ventas/por-dia` - Por día
- `GET /api/ventas/por-vendedor` - Por vendedor
- `GET /api/ventas/por-familia` - Por familia
- `GET /api/ventas/por-metodo` - Por método

### Análisis
- `GET /api/margenes` - Análisis de márgenes
- `GET /api/predicciones` - Predicciones
- `GET /api/abc` - Análisis ABC
- `GET /api/vendedores/ranking` - Ranking

### Exportación
- `GET /api/export/csv` - Exportar CSV
- `GET /api/export/excel` - Exportar Excel
- `GET /api/export/pdf` - Exportar PDF

## 🎯 Próximas Mejoras

- [ ] Integración con sistema de inventario
- [ ] Notificaciones push
- [ ] Dashboard personalizable (drag & drop)
- [ ] Comparativa multi-período
- [ ] Exportación programada
- [ ] API de webhooks

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.
