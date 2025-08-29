import psycopg2
import psycopg2.extras
import csv
import time
import os
from multiprocessing import Pool, cpu_count

# --- COPIA AQUÍ TUS CREDENCIALES DE LA BASE DE DATOS ---
db_host = "aws-0-sa-east-1.pooler.supabase.com"
db_name = "postgres"
db_user = "postgres.kbcwpzwhnlscogiglthk"
db_password = "cristianpixel01@"
db_port = "6543"

# --- CONFIGURACIÓN ---
CARPETA_CHUNKS = 'chunks_para_procesar'
# Usa casi todos los núcleos disponibles para dejar uno libre para el sistema
NUMERO_DE_PROCESOS = max(1, cpu_count() - 1) 

def procesar_chunk(nombre_archivo_chunk):
    """
    Esta es la función que ejecutará cada trabajador en paralelo.
    Se conecta a la BD, procesa su chunk asignado y solo inserta relaciones.
    """
    conn = None
    try:
        # Cada proceso debe tener su PROPIA conexión a la base de datos
        conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password, port=db_port)
        cursor = conn.cursor()

        # Obtenemos todos los IDs de matrícula en un caché para este proceso
        cursor.execute("SELECT no_matricula_inmobiliaria, id FROM Matriculas")
        matriculas_cache = dict(cursor.fetchall())
        
        relaciones_a_insertar = set()
        with open(nombre_archivo_chunk, mode='r', encoding='utf-8') as archivo_csv:
            lector_csv = csv.reader(archivo_csv, delimiter=';')
            next(lector_csv, None)  # Saltar encabezado

            for fila in lector_csv:
                no_matricula_actual = fila[0].strip()
                padres_str = fila[2].strip()
                hija_str = fila[3].strip()

                id_actual = matriculas_cache.get(no_matricula_actual)
                if not id_actual: continue

                if padres_str:
                    for padre in [p.strip() for p in padres_str.split(',')]:
                        id_padre = matriculas_cache.get(padre)
                        if id_padre:
                            relaciones_a_insertar.add((id_padre, id_actual))
                
                if hija_str:
                    id_hija = matriculas_cache.get(hija_str)
                    if id_hija:
                        relaciones_a_insertar.add((id_actual, id_hija))
        
        if relaciones_a_insertar:
            sql_insert_relaciones = "INSERT INTO RelacionesMatriculas (matricula_padre_id, matricula_hija_id) VALUES %s ON CONFLICT DO NOTHING"
            psycopg2.extras.execute_values(cursor, sql_insert_relaciones, list(relaciones_a_insertar))
            conn.commit()

        return f"Éxito: {os.path.basename(nombre_archivo_chunk)} procesado, {len(relaciones_a_insertar)} relaciones insertadas."
    except Exception as e:
        if conn: conn.rollback()
        return f"Error en {os.path.basename(nombre_archivo_chunk)}: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    archivos_chunk = [os.path.join(CARPETA_CHUNKS, f) for f in os.listdir(CARPETA_CHUNKS) if f.endswith('.csv')]
    
    if not archivos_chunk:
        print("No se encontraron archivos 'chunk' para procesar. Ejecuta primero 'preparar_y_dividir_csv.py'.")
    else:
        print(f"Iniciando procesamiento paralelo con {NUMERO_DE_PROCESOS} procesos para {len(archivos_chunk)} archivos.")
        start_time = time.time()
        
        # Pool es la magia del paralelismo: distribuye la lista de archivos entre los trabajadores
        with Pool(processes=NUMERO_DE_PROCESOS) as pool:
            resultados = pool.map(procesar_chunk, archivos_chunk)
            
            for res in resultados:
                print(res)

        print(f"\n✅ ¡Procesamiento paralelo completado en {time.time() - start_time:.2f} segundos!")