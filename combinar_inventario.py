"""
Script para combinar múltiples archivos Excel de inventario en uno solo
"""
import pandas as pd
from pathlib import Path

# Carpeta con los archivos de inventario
carpeta_inventario = Path(r"d:\Desktop\inventario")

# Lista para almacenar todos los DataFrames
todos_los_datos = []

# Obtener todos los archivos xlsx en la carpeta
archivos_excel = sorted(carpeta_inventario.glob("*.xlsx"))

print(f"Archivos encontrados: {len(archivos_excel)}")
print("-" * 50)

for archivo in archivos_excel:
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo)
        
        # Agregar columna con el nombre del archivo origen (opcional)
        df['Archivo_Origen'] = archivo.name
        
        todos_los_datos.append(df)
        print(f"[OK] Procesado: {archivo.name} ({len(df)} filas)")
    except Exception as e:
        print(f"[ERROR] Error en {archivo.name}: {e}")

print("-" * 50)

if todos_los_datos:
    # Combinar todos los DataFrames
    df_combinado = pd.concat(todos_los_datos, ignore_index=True)
    
    # Guardar el archivo combinado
    archivo_salida = carpeta_inventario / "Inventario_Combinado.xlsx"
    df_combinado.to_excel(archivo_salida, index=False)
    
    print(f"\n[OK] Archivo combinado guardado exitosamente!")
    print(f"  Ubicación: {archivo_salida}")
    print(f"  Total de filas: {len(df_combinado)}")
    print(f"  Columnas: {list(df_combinado.columns)}")
else:
    print("No se encontraron datos para combinar.")
