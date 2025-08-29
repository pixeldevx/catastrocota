import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os

# --- FUNCIÓN DE VERIFICACIÓN (CORREGIDA) ---
def verificar_informacion_catastral(no_matricula, db_params):
    """
    Verifica si una matrícula tiene al menos un registro en la tabla InformacionCatastral.
    """
    try:
        with psycopg2.connect(**db_params) as conn:
            # CORRECCIÓN: Se usa "Matricula" con comillas dobles para respetar mayúsculas/minúsculas.
            query = 'SELECT EXISTS (SELECT 1 FROM public.informacioncatastral WHERE "Matricula" = %(matricula)s);'
            df = pd.read_sql_query(query, conn, params={'matricula': no_matricula})
            return df.iloc[0]['exists']
    except Exception as e:
        return f"Error al verificar en catastro: {e}"


def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo y devuelve el nombre del archivo HTML.
    """
    try:
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
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df.empty:
            return None, f"⚠️ No se encontraron relaciones de parentesco para la matrícula '{no_matricula_inicial}'."

        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if str(node["id"]) == str(no_matricula_inicial):
                node["color"] = "#FF0000"
                node["size"] = 40
        
        net.set_options("""
        var options = { "layout": { "hierarchical": { "enabled": true, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 100 }}, "physics": { "enabled": false }}
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df)} relaciones de parentesco."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"

# --- INTERFAZ GRÁFICA CON STREAMLIT ---

st.set_page_config(layout="wide") # Hacemos la página más ancha para las columnas

st.title("Visor de Grafos de Matrículas 🕸️")
st.write("Esta herramienta visualiza las relaciones jerárquicas y verifica la información catastral.")

matricula_input = st.text_input("Introduce el número de matrícula inmobiliaria:", placeholder="Ej: 1037472")

if st.button("Consultar y Generar Grafo"):
    if matricula_input:
        db_credentials = st.secrets["db_credentials"]
        
        # --- SECCIÓN MODIFICADA: DISEÑO EN COLUMNAS ---
        col1, col2 = st.columns([3, 1]) # Columna 1 (izquierda) es 3 veces más ancha que la Columna 2 (derecha)

        # Contenido de la Columna Derecha (Tarjeta de Información)
        with col2:
            st.subheader("Info Rápida")
            existe_en_catastro = verificar_informacion_catastral(matricula_input, db_credentials)
            
            if isinstance(existe_en_catastro, bool):
                resultado_texto = "Sí ✅" if existe_en_catastro else "No ❌"
                st.metric(label="R1: En Base Catastral", value=resultado_texto)
            else:
                st.error(existe_en_catastro)

        # Contenido de la Columna Izquierda (Grafo)
        with col1:
            with st.spinner(f"🔎 Generando grafo de relaciones para {matricula_input}..."):
                nombre_archivo_html, mensaje = generar_grafo_matricula(matricula_input, db_credentials)
            
            st.info(mensaje)

            if nombre_archivo_html:
                with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                    st.components.v1.html(source_code, height=820, scrolling=True)
                
                os.remove(nombre_archivo_html)
    else:
        st.warning("Por favor, introduce un número de matrícula.")