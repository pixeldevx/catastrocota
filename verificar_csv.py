import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import multiprocessing
import glob
import time
import os

# --- TUS CREDENCIALES DE BASE DE DATOS ---
DB_CREDS = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "dbname": "postgres",
    "user": "postgres.kbcwpzwhnlscogiglthk",
    "password": "cristianpixel01@", # ¡Reemplázame!
    "port": "6543"
}

def procesar_chunk_para_recolectar(ruta_archivo_csv):
    """
    Fase 1 (Paralela): Lee un CSV y devuelve las matrículas y relaciones encontradas.
    NO se conecta a la base de datos.
    """
    try:
        df = pd.read_csv(ruta_archivo_csv, sep=';', dtype=str).fillna('')
        
        relaciones_potenciales = set()
        matriculas_con_estado = {} # Usamos un diccionario para guardar matrícula -> estado

        for index, row in df.iterrows():
            matricula_actual = row['no_matricula_inmobiliaria'].strip()
            if not matricula_actual:
                continue

            matriculas_con_estado[matricula_actual] = row['estado_folio'].strip()

            matriculas_matriz_str = row['matriculas_matriz']
            if matriculas_matriz_str:
                padres = [p.strip() for p in matriculas_matriz_str.split(',') if p.strip()]
                for padre in padres:
                    # Guardamos el padre sin estado específico, se le asignará uno por defecto si no es principal
                    if padre not in matriculas_con_estado:
                        matriculas_con_estado[padre] = 'ACTIVO' # Valor por defecto
                    relaciones_potenciales.add((padre, matricula_actual))

            matriculas_derivadas_str = row['matriculas_derivadas']
            if matriculas_derivadas_str:
                hijas = [h.strip() for h in matriculas_derivadas_str.split(',') if h.strip()]
                for hija in hijas:
                    # Guardamos la hija sin estado específico
                    if hija not in matriculas_con_estado:
                        matriculas_con_estado[hija] = 'ACTIVO' # Valor por defecto
                    relaciones_potenciales.add((matricula_actual, hija))

        return (matriculas_con_estado, relaciones_potenciales)
    except Exception as e:
        print(f"Error leyendo {os.path.basename(ruta_archivo_csv)}: {e}")
        return ({}, set())


if __name__ == '__main__':
    directorio_chunks = 'chunks_para_procesar'
    archivos_csv = glob.glob(f'{directorio_chunks}/*.csv')

    if not archivos_csv:
        print("🔴 No se encontraron archivos .csv en la carpeta 'chunks'.")
    else:
        num_procesos = min(os.cpu_count(), len(archivos_csv))
        print(f"🚀 Fase 1: Recolectando datos en paralelo con {num_procesos} procesos...")
        
        inicio = time.time()
        with multiprocessing.Pool(processes=num_procesos) as pool:
            resultados = pool.map(procesar_chunk_para_recolectar, archivos_csv)
        
        # --- Fase 2: Agregando todos los resultados en un solo lugar ---
        master_matriculas = {}
        master_relaciones = set()
        for matriculas_con_estado, relaciones in resultados:
            master_matriculas.update(matriculas_con_estado)
            master_relaciones.update(relaciones)
            
        print(f"✅ Recolección completada en {time.time() - inicio:.2f} segundos.")
        print(f"   - Se encontraron {len(master_matriculas)} matrículas únicas en total.")
        print(f"   - Se encontraron {len(master_relaciones)} relaciones únicas en total.")

        if not master_matriculas:
            print("No se encontraron matrículas para procesar. Finalizando.")
        else:
            # --- Fase 3: Escribiendo en la base de datos de forma secuencial ---
            print("\n🚀 Fase 2: Escribiendo en la base de datos...")
            try:
                with psycopg2.connect(**DB_CREDS) as conn:
                    with conn.cursor() as cur:
                        # Paso A: Insertar todas las matrículas únicas
                        print("   - Insertando matrículas...")
                        matriculas_a_insertar = list(master_matriculas.items())
                        execute_batch(
                            cur,
                            "INSERT INTO public.matriculas (no_matricula_inmobiliaria, estado_folio) VALUES (%s, %s) ON CONFLICT (no_matricula_inmobiliaria) DO NOTHING",
                            matriculas_a_insertar
                        )
                        print(f"     ... {cur.rowcount} matrículas nuevas insertadas/verificadas.")

                        if master_relaciones:
                            # Paso B: Obtener los IDs de TODAS las matrículas necesarias
                            print("   - Obteniendo IDs para crear relaciones...")
                            todas_las_matriculas_para_relacion = {m for rel in master_relaciones for m in rel}
                            cur.execute(
                                "SELECT no_matricula_inmobiliaria, id FROM public.matriculas WHERE no_matricula_inmobiliaria = ANY(%s)",
                                (list(todas_las_matriculas_para_relacion),)
                            )
                            id_map = dict(cur.fetchall())

                            # Paso C: Insertar todas las relaciones
                            print("   - Insertando relaciones...")
                            relaciones_con_id = []
                            for padre, hija in master_relaciones:
                                padre_id = id_map.get(padre)
                                hija_id = id_map.get(hija)
                                if padre_id and hija_id:
                                    relaciones_con_id.append((padre_id, hija_id))
                            
                            execute_batch(
                                cur,
                                "INSERT INTO public.relacionesmatriculas (matricula_padre_id, matricula_hija_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                relaciones_con_id
                            )
                            print(f"     ... {cur.rowcount} relaciones nuevas insertadas/verificadas.")
                        
                        conn.commit()
                print("✅ Escritura en la base de datos completada.")

            except Exception as e:
                print(f"❌ Ocurrió un error durante la escritura en la base de datos: {e}")

        fin = time.time()
        print(f"\n✅ ¡Procesamiento total completado en {fin - inicio:.2f} segundos!")