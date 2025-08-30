import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# --- FUNCIONES DE BASE DE DATOS ---

def obtener_info_catastral_batch(matriculas, db_params):
    """
    Función optimizada: Busca detalles para una LISTA de matrículas en una sola consulta.
    Devuelve un diccionario mapeando cada matrícula a sus datos.
    """
    if not matriculas:
        return {}
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT "Matricula", numero_predial, area_terreno, area_construida, nombre 
                FROM public.informacioncatastral 
                WHERE "Matricula" = ANY(%(matriculas)s);
            """
            df = pd.read_sql_query(query, conn, params={'matriculas': list(matriculas)})

            # Procesamos los resultados para agrupar por matrícula
            info_catastral = {}
            for matricula, group in df.groupby('Matricula'):
                info_catastral[matricula] = {
                    "numero_predial": group['numero_predial'].iloc[0],
                    "area_terreno": group['area_terreno'].iloc[0],
                    "area_construida": group['area_construida'].iloc[0],
                    "propietarios": group['nombre'].tolist()
                }
            return info_catastral
            
    except Exception as e:
        st.error(f"Error al obtener datos catastrales en lote: {e}")
        return {}


def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo donde los tooltips de los nodos contienen la información catastral.
    """
    try:
        # 1. Obtenemos la estructura del grafo (las relaciones)
        with psycopg2.connect(**db_params) as conn:
            query_recursiva = """
            WITH RECURSIVE familia_grafo AS (
                SELECT id FROM public.matriculas WHERE no_matricula_inmobiliaria = %(start_node)s
                UNION
                SELECT
                    CASE
                        WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                        ELSE r.matricula_padre_id
                    END
                FROM public.relacionesmatriculas r
                JOIN familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id
            )
            SELECT
                padre.no_matricula_inmobiliaria AS padre,
                hija.no_matricula_inmobiliaria AS hija
            FROM public.relacionesmatriculas rel
            JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id
            JOIN public.matriculas hija ON rel.matricula_hija_id = hija.id
            WHERE rel.matricula_padre_id IN (SELECT id FROM familia_grafo)
            AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);
            """
            df_relaciones = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df_relaciones.empty:
            return None, f"⚠️ No se encontraron relaciones de parentesco para '{no_matricula_inicial}'."

        # 2. Recolectamos TODOS los nodos únicos que aparecerán en el grafo
        nodos_del_grafo = set(df_relaciones['padre']).union(set(df_relaciones['hija']))

        # 3. Obtenemos la información catastral para todos esos nodos EN UN SOLO VIAJE a la BD
        info_catastral_nodos = obtener_info_catastral_batch(nodos_del_grafo, db_params)

        # 4. Construimos el grafo y los tooltips dinámicos
        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            node_id = str(node["id"])
            
            # --- LÓGICA DE TOOLTIPS INTELIGENTES ---
            info_nodo = info_catastral_nodos.get(node_id)
            if info_nodo:
                # Usamos \n para saltos de línea en el tooltip
                propietarios_str = '\n- '.join(info_nodo['propietarios'])
                tooltip_text = (
                    f"--- Info Catastral ---\n"
                    f"Matrícula: {node_id}\n"
                    f"Predial: {info_nodo['numero_predial']}\n"
                    f"Á. Terreno: {info_nodo['area_terreno']} m²\n"
                    f"Á. Construida: {info_nodo['area_construida']} m²\n"
                    f"Propietarios:\n- {propietarios_str}"
                )
                node["title"] = tooltip_text
            else:
                node["title"] = f"Matrícula: {node_id}\n(Sin datos en base catastral)"

            if node_id == str(no_matricula_inicial):
                node["color"] = "#FF0000"
                node["size"] = 40
        
        net.set_options("""
        var options = { "layout": { "hierarchical": { "enabled": true, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 100 }}, "physics": { "enabled": false }}
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df_relaciones)} relaciones de parentesco."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---

st.title("Visor Interactivo de Matrículas 🕸️")

matricula_input = st.text_input(
    "Introduce el número de matrícula para generar el grafo:",
    placeholder="Ej: 1037472"
)

if st.button("Generar Grafo"):
    if matricula_input:
        # El grafo se muestra ocupando todo el espacio principal
        st.subheader(f"Grafo de Relaciones para: {matricula_input}")
        db_credentials = st.secrets["db_credentials"]
        
        with st.spinner("Buscando relaciones y datos catastrales..."):
            nombre_archivo_html, mensaje = generar_grafo_matricula(matricula_input, db_credentials)
        
        st.info(mensaje)

        if nombre_archivo_html:
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=820, scrolling=True)
            os.remove(nombre_archivo_html)
    else:
        st.warning("Por favor, introduce un número de matrícula.")