import re
import os
from tqdm import tqdm

# ==============================================================================
# --- CONFIGURACIÓN (MODIFICA ESTAS VARIABLES) ---
# ==============================================================================

# 1. RUTA A TU ARCHIVO .SQL DE ENTRADA
SQL_INPUT_PATH = "/Users/pixel/Documents/PERSONAL/ANALISTA/terrenos/carga.sql"

# 2. RUTA DONDE SE GUARDARÁ EL NUEVO ARCHIVO .CSV DE SALIDA
CSV_OUTPUT_PATH = "/Users/pixel/Documents/PERSONAL/ANALISTA/terrenos/carga_convertida.csv"

# ==============================================================================
# --- SCRIPT DE CONVERSIÓN (NO NECESITAS MODIFICAR DE AQUÍ EN ADELANTE) ---
# ==============================================================================

def clean_value(value):
    """Limpia un valor individual, quitando espacios y comillas/apóstrofes."""
    value = value.strip()
    # Quita apóstrofes al inicio/final: 'texto' -> texto
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    # Quita comillas al inicio/final: "texto" -> texto
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    # Maneja el valor NULL de SQL
    if value.upper() == 'NULL':
        return '' # CSV lo interpreta como nulo si el campo está vacío
    return value

def convert_sql_to_csv():
    """
    Lee un archivo .sql con sentencias INSERT y lo convierte a un archivo .csv.
    """
    print("Iniciando la conversión de .sql a .csv...")

    if not os.path.exists(SQL_INPUT_PATH):
        print(f"❌ Error: No se encontró el archivo de entrada: {SQL_INPUT_PATH}")
        return

    try:
        # Contamos las líneas para la barra de progreso
        with open(SQL_INPUT_PATH, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for line in f)
    except Exception as e:
        print(f"❌ Error al leer el archivo de entrada: {e}")
        return

    header_written = False
    lines_converted = 0

    # Abrimos el archivo de entrada para leer y el de salida para escribir
    with open(SQL_INPUT_PATH, 'r', encoding='utf-8') as f_sql, \
         open(CSV_OUTPUT_PATH, 'w', encoding='utf-8') as f_csv:
        
        progress_bar = tqdm(f_sql, total=total_lines, unit=" líneas", desc="Convirtiendo")

        for line in progress_bar:
            if not line.strip().upper().startswith('INSERT INTO'):
                continue
            
            # Extraemos las columnas y los valores con expresiones regulares
            match_cols = re.search(r'\((.*?)\)', line)
            match_vals = re.search(r'VALUES[ ]*\((.*)\);', line, re.IGNORECASE)

            if not match_cols or not match_vals:
                continue

            # --- Procesar el encabezado (solo una vez) ---
            if not header_written:
                column_str = match_cols.group(1)
                # Limpiamos y dividimos los nombres de las columnas
                columns = [clean_value(col) for col in column_str.split(',')]
                # Escribimos el encabezado en el archivo CSV
                f_csv.write(','.join(columns) + '\n')
                header_written = True

            # --- Procesar los valores de la fila ---
            values_str = match_vals.group(1)
            # Limpiamos y dividimos los valores
            values = [clean_value(val) for val in values_str.split(',')]
            # Escribimos la fila de datos en el archivo CSV
            f_csv.write(','.join(values) + '\n')
            lines_converted += 1

    print("\n" + "="*50)
    print("🎉 ¡Conversión completada!")
    print(f"  -> Se convirtieron {lines_converted} sentencias INSERT.")
    print(f"  -> Archivo de salida guardado en: {CSV_OUTPUT_PATH}")
    print("="*50)

if __name__ == "__main__":
    # Si no tienes tqdm, puedes instalarlo con: pip install tqdm
    convert_sql_to_csv()