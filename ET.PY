import psycopg2
import csv # ---> NUEVO: Importamos la librería para manejar archivos CSV

def procesar_csv(nombre_archivo, db_connection):
    """
    Lee un archivo CSV con información registral y lo inserta en la base de datos.

    Args:
        nombre_archivo (str): La ruta al archivo CSV.
        db_connection: Una conexión activa a la base de datos PostgreSQL.
    """
    try:

        cursor = db_connection.cursor()

        # La función auxiliar no necesita cambios, ¡sigue siendo perfecta para su trabajo!
        def obtener_o_crear_matricula_id(no_matricula, estado_folio=""):
            # Asegurarnos de que no procesamos un número vacío
            if not no_matricula or not no_matricula.strip():
                return None
            
            no_matricula = no_matricula.strip()
            
            cursor.execute("SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %s", (no_matricula,))
            resultado = cursor.fetchone()

            if resultado:
                return resultado[0]
            else:
                # Si el estado no se proporciona, usamos 'No especificado'
                estado_actual = estado_folio if estado_folio else "No especificado"
                cursor.execute(
                    "INSERT INTO Matriculas (no_matricula_inmobiliaria, estado_folio) VALUES (%s, %s) RETURNING id",
                    (no_matricula, estado_actual)
                )
                nuevo_id = cursor.fetchone()[0]
                return nuevo_id

        # ---> NUEVO: Abrimos y leemos el archivo CSV
        with open(nombre_archivo, mode='r', encoding='utf-8') as archivo_csv:
            lector_csv = csv.reader(archivo_csv, delimiter=';')
            next(lector_csv, None)  # Saltamos la fila del encabezado

            print("Iniciando procesamiento del archivo CSV...")
            # Procesamos cada fila del archivo
            for i, fila in enumerate(lector_csv):
                # Asignamos las columnas a variables para mayor claridad
                no_matricula_actual = fila[0]
                estado_folio_actual = fila[1]
                matriculas_padre_str = fila[2]
                matricula_hija_str = fila[3]

                # --- Lógica de procesamiento para cada fila ---

                # 1. Obtenemos/creamos la matrícula principal de esta fila
                id_actual = obtener_o_crear_matricula_id(no_matricula_actual, estado_folio_actual)

                # 2. Procesamos sus padres (relación hacia arriba)
                if matriculas_padre_str:
                    lista_padres = [padre.strip() for padre in matriculas_padre_str.split(',')]
                    for no_matricula_padre in lista_padres:
                        id_padre = obtener_o_crear_matricula_id(no_matricula_padre)
                        if id_padre and id_actual:
                            cursor.execute(
                                """
                                INSERT INTO RelacionesMatriculas (matricula_padre_id, matricula_hija_id) 
                                VALUES (%s, %s) ON CONFLICT DO NOTHING
                                """,
                                (id_padre, id_actual)
                            )
                
                # 3. Procesamos su hija (relación hacia abajo)
                if matricula_hija_str:
                    id_hija = obtener_o_crear_matricula_id(matricula_hija_str)
                    if id_actual and id_hija:
                        cursor.execute(
                            """
                            INSERT INTO RelacionesMatriculas (matricula_padre_id, matricula_hija_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                            """,
                            (id_actual, id_hija) # ¡Nota el orden: actual es el padre, derivada es la hija!
                        )
                
                # Imprimimos un progreso para no pensar que se ha colgado
                if (i + 1) % 100 == 0:
                    print(f"Procesadas {i + 1} filas...")

        db_connection.commit()
        print(f"✅ ¡Éxito! Se procesaron {i + 1} filas del archivo CSV y se guardaron en Supabase.")

    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{nombre_archivo}'. Asegúrate de que esté en la misma carpeta que el script.")
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")
        db_connection.rollback()
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()

# --- Zona de Ejecución ---

# REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES DE SUPABASE
db_host = "aws-0-sa-east-1.pooler.supabase.com" 
db_name = "postgres"
db_user = "postgres.kbcwpzwhnlscogiglthk"
db_password = "cristianpixel01@" 
db_port = "6543"

conn = None
try:
    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password, port=db_port)
    
    # ---> CAMBIO: Llamamos a la nueva función pasándole el nombre del archivo
    procesar_csv('matriculas_input.csv', conn)

except psycopg2.OperationalError as e:
    print(f"❌ Error de conexión: No se pudo conectar a la base de datos de Supabase. Revisa tus credenciales.")
    print(e)
finally:
    if conn:
        conn.close()