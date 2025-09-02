import psycopg2
import os
from tqdm import tqdm  # <-- NUEVO: Importamos la librería para la barra de progreso

# ==============================================================================
# --- CONFIGURACIÓN (MODIFICA ESTAS VARIABLES) ---
# ==============================================================================

# 1. DATOS DE TU BASE DE DATOS SUPABASE
DB_USER = "postgres.kbcwpzwhnlscogiglthk"
DB_PASSWORD = "cristianpixel01@"  # <-- ¡IMPORTANTE! REEMPLAZA ESTO
DB_HOST = "aws-0-sa-east-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"

# 2. RUTA A TU ARCHIVO .SQL
SQL_FILE_PATH = "/Users/pixel/Documents/PERSONAL/ANALISTA/terrenos/carga.sql"

# 3. RUTA PARA GUARDAR LAS LÍNEAS CON ERRORES
ERROR_FILE_PATH = "errores.sql"

# 4. TAMAÑO DEL LOTE (BATCH SIZE)
# Define cuántas inserciones exitosas se acumularán antes de guardarlas en la BD.
# Un valor entre 500 y 5000 suele funcionar bien.
BATCH_SIZE = 1000  # <-- NUEVO: Variable de configuración para el tamaño del lote

# ==============================================================================
# --- SCRIPT DE EJECUCIÓN (NO NECESITAS MODIFICAR DE AQUÍ EN ADELANTE) ---
# ==============================================================================

def execute_sql_optimizado():
    """
    Se conecta a la BD y ejecuta un archivo .sql por lotes con una barra de progreso.
    """
    print("Iniciando el script optimizado...")

    if not os.path.exists(SQL_FILE_PATH):
        print(f"❌ Error: No se encontró el archivo en la ruta: {SQL_FILE_PATH}")
        return
    
    # --- NUEVO: Contamos el total de líneas para la barra de progreso ---
    try:
        print("Calculando el tamaño del archivo...")
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for line in f)
        print(f"Archivo '{os.path.basename(SQL_FILE_PATH)}' tiene {total_lines} líneas.")
    except Exception as e:
        print(f"❌ Error al leer el archivo para contar líneas: {e}")
        return

    successful_lines = 0
    failed_lines = 0
    lines_since_commit = 0
    
    with open(ERROR_FILE_PATH, 'w', encoding='utf-8') as f_error:
        f_error.write("-- Comandos SQL que fallaron durante la carga --\n\n")

    conn = None
    try:
        print("Conectando a la base de datos...")
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        print("✅ Conexión exitosa.")

        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f_sql:
            # --- NUEVO: Envolvemos el bucle con tqdm para la barra de progreso ---
            progress_bar = tqdm(f_sql, total=total_lines, unit=" líneas", desc="Cargando SQL")
            
            for line in progress_bar:
                if not line.strip() or line.strip().startswith('--'):
                    continue
                
                try:
                    with conn.cursor() as cur:
                        cur.execute(line)
                    successful_lines += 1
                    lines_since_commit += 1

                    # --- NUEVO: Lógica de carga por lotes (batch) ---
                    # Si alcanzamos el tamaño del lote, hacemos commit.
                    if lines_since_commit >= BATCH_SIZE:
                        conn.commit()
                        lines_since_commit = 0 # Reiniciamos el contador del lote

                except psycopg2.Error as e:
                    conn.rollback()
                    failed_lines += 1
                    with open(ERROR_FILE_PATH, 'a', encoding='utf-8') as f_error:
                        f_error.write(line)

            # --- NUEVO: Commit final para el último lote ---
            # Asegurarse de que las últimas líneas que no completaron un lote se guarden.
            if lines_since_commit > 0:
                conn.commit()
                print("\n✅ Confirmando lote final de inserciones.")

        print("\n" + "="*50)
        print("🎉 ¡Proceso completado!")
        print(f"  -> Líneas exitosas: {successful_lines}")
        print(f"  -> Líneas fallidas: {failed_lines}")
        if failed_lines > 0:
            print(f"  -> Las líneas con errores se guardaron en: {ERROR_FILE_PATH}")
        print("="*50)

    except Exception as e:
        print(f"❌ Ocurrió un error general e inesperado: {e}")
        if conn: conn.rollback()
            
    finally:
        if conn:
            conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    execute_sql_optimizado()