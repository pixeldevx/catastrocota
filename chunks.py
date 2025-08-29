import psycopg2
import psycopg2.extras
import csv
import time
import os

# --- COPIA AQUÍ TUS CREDENCIALES DE LA BASE DE DATOS ---
db_host = "aws-0-sa-east-1.pooler.supabase.com"
db_name = "postgres"
db_user = "postgres.kbcwpzwhnlscogiglthk"
db_password = "cristianpixel01@"
db_port = "6543"

# --- CONFIGURACIÓN ---
NOMBRE_ARCHIVO_ORIGINAL = 'Libro4.csv'
CARPETA_CHUNKS = 'chunks_para_procesar'
LINEAS_POR_CHUNK = 5000  # Ajusta este número según el tamaño de tu archivo y tu memoria

def sincronizar_todas_las_matriculas(nombre_archivo, db_connection):
    """
    Esta función es una adaptación del script anterior. Lee el CSV completo
    y se asegura de que todas las matrículas existan y estén actualizadas en la BD.
    No inserta relaciones, solo prepara el terreno.
    """
    # (El código de esta función es el mismo que el del Paso 1 y 2 de la respuesta anterior)
    # Lo he copiado aquí para tu comodidad.
    cursor = db_connection.cursor()
    print("Iniciando Fase de Preparación: Sincronizando todas las matrículas...")
    start_time = time.time()

    matricula_data = {}
    with open(nombre_archivo, mode='r', encoding='utf-8') as archivo_csv:
        lector_csv = csv.reader(archivo_csv, delimiter=';')
        header = next(lector_csv, None)
        for fila in lector_csv:
            no_matricula_actual = fila[0].strip()
            if not no_matricula_actual: continue
            estado_folio = fila[1].strip() or "No especificado"
            if (no_matricula_actual not in matricula_data or 
                    matricula_data[no_matricula_actual]['estado_folio'] == "No especificado"):
                matricula_data[no_matricula_actual] = {'estado_folio': estado_folio}
            padres_str = fila[2].strip()
            if padres_str:
                for padre in [p.strip() for p in padres_str.split(',')]:
                    if padre and padre not in matricula_data:
                        matricula_data[padre] = {'estado_folio': 'No especificado'}
            hija_str = fila[3].strip()
            if hija_str and hija_str not in matricula_data:
                matricula_data[hija_str] = {'estado_folio': 'No especificado'}

    todas_las_matriculas_nombres = list(matricula_data.keys())
    cursor.execute(
        "SELECT no_matricula_inmobiliaria, id, estado_folio FROM Matriculas WHERE no_matricula_inmobiliaria = ANY(%s)",
        (todas_las_matriculas_nombres,)
    )
    matriculas_en_db = {row[0]: {'id': row[1], 'estado_folio': str(row[2])} for row in cursor.fetchall()}
    matriculas_a_insertar = []
    matriculas_a_actualizar = []
    for nombre, data_csv in matricula_data.items():
        estado_csv = data_csv['estado_folio']
        if nombre not in matriculas_en_db:
            matriculas_a_insertar.append((nombre, estado_csv))
        else:
            info_db = matriculas_en_db[nombre]
            if info_db['estado_folio'] != estado_csv and estado_csv != "No especificado":
                matriculas_a_actualizar.append((estado_csv, info_db['id']))

    if matriculas_a_actualizar:
        psycopg2.extras.execute_batch(cursor, "UPDATE Matriculas SET estado_folio = %s WHERE id = %s", matriculas_a_actualizar)
    if matriculas_a_insertar:
        psycopg2.extras.execute_values(cursor, "INSERT INTO Matriculas (no_matricula_inmobiliaria, estado_folio) VALUES %s", matriculas_a_insertar)
    
    db_connection.commit()
    cursor.close()
    print(f"Sincronización de matrículas completada en {time.time() - start_time:.2f} segundos.")
    return header

def dividir_csv(nombre_archivo, header):
    """Divide el archivo CSV grande en archivos más pequeños (chunks)."""
    print(f"Dividiendo '{nombre_archivo}' en chunks de {LINEAS_POR_CHUNK} líneas...")
    if not os.path.exists(CARPETA_CHUNKS):
        os.makedirs(CARPETA_CHUNKS)
    
    file_count = 0
    with open(nombre_archivo, 'r', encoding='utf-8') as f_in:
        # Saltar la cabecera del archivo original que ya leímos
        next(f_in)
        
        while True:
            chunk_path = os.path.join(CARPETA_CHUNKS, f'chunk_{file_count}.csv')
            with open(chunk_path, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.writer(f_out, delimiter=';')
                writer.writerow(header)
                
                lines_written = 0
                for line in f_in:
                    # Escribimos la línea como una lista de campos
                    writer.writerow(line.strip().split(';'))
                    lines_written += 1
                    if lines_written >= LINEAS_POR_CHUNK:
                        break
                
                if lines_written == 0:
                    # Si no se escribió ninguna línea, es que terminamos. Borramos el archivo vacío.
                    os.remove(chunk_path)
                    break
            
            print(f"Creado: {chunk_path}")
            file_count += 1
    print("División completada.")


if __name__ == '__main__':
    conn = None
    try:
        conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password, port=db_port)
        # 1. Sincronizar todas las matrículas primero
        header = sincronizar_todas_las_matriculas(NOMBRE_ARCHIVO_ORIGINAL, conn)
        # 2. Dividir el archivo para el procesamiento paralelo
        dividir_csv(NOMBRE_ARCHIVO_ORIGINAL, header)
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        if conn:
            conn.close()