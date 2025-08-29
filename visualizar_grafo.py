import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import sys

def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo para una matrícula específica y sus familiares.
    """
    print(f"🔎 Buscando familiares para la matrícula: {no_matricula_inicial}...")

    # --- 1. Consulta SQL Recursiva (VERSIÓN FINAL) ---
    # Esta versión cumple la regla de "una sola referencia recursiva".
    query_recursiva = """
    WITH RECURSIVE familia_grafo (id, path) AS (
        -- Starting point: the matricula we are interested in
        SELECT m.id,
            ARRAY[m.id] AS path
        FROM public.matriculas m
        WHERE m.no_matricula_inmobiliaria = %(start_node)s

        UNION ALL

        -- Recursive step: follow relationships in either direction, but avoid cycles
        SELECT
            CASE
                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                ELSE r.matricula_padre_id
            END AS id,
            fg.path || CASE
                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                ELSE r.matricula_padre_id
            END
        FROM public.relacionesmatriculas r
        JOIN familia_grafo fg
        ON r.matricula_padre_id = fg.id
        OR r.matricula_hija_id = fg.id
        WHERE NOT (
            CASE
                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                ELSE r.matricula_padre_id
            END) = ANY (fg.path)
        -- Optional safety guard (uncomment if needed)
        -- AND array_length(fg.path, 1) < 1000
    )

    SELECT
        padre.no_matricula_inmobiliaria AS padre,
        hija.no_matricula_inmobiliaria  AS hija
    FROM public.relacionesmatriculas rel
    JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id
    JOIN public.matriculas hija  ON rel.matricula_hija_id = hija.id
    WHERE rel.matricula_padre_id IN (SELECT id FROM familia_grafo)
    AND rel.matricula_hija_id  IN (SELECT id FROM familia_grafo);
    """

    try:
        with psycopg2.connect(**db_params) as conn:
            # Usamos pandas para ejecutar la consulta y obtener los resultados
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df.empty:
            print(f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'.")
            return

        print(f"✅ Se encontraron {len(df)} relaciones.")

        # --- 2. Construcción y Visualización del Grafo ---
        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if node["id"] == no_matricula_inicial:
                node["color"] = "#FF0000"
                node["size"] = 40

                net.set_options("""
        var options = {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 150,
              "nodeSpacing": 100
            }
          },
          "physics": {
            "enabled": false
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df)} relaciones."

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

# --- Zona de Ejecución ---
if __name__ == "__main__":
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES DE SUPABASE
    db_credenciales = {
        "host": "aws-0-sa-east-1.pooler.supabase.com",
        "dbname": "postgres",
        "user": "postgres.kbcwpzwhnlscogiglthk",
        "password": "cristianpixel01@", # ¡Reemplázame!
        "port": "6543"
    }

    # Obtenemos el número de matrícula desde los argumentos de la línea de comandos
    if len(sys.argv) > 1:
        matricula_a_buscar = sys.argv[1]
        generar_grafo_matricula(matricula_a_buscar, db_credenciales)
    else:
        print("🔴 Uso: python visualizar_grafo.py <numero_de_matricula>")
        print("   Ejemplo: python visualizar_grafo.py 1037472")