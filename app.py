import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os
import json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# --- FUNCIONES DE BASE DE DATOS (sin cambios) ---
def obtener_info_catastral_batch(matriculas, db_params):
    if not matriculas: return {}
    matriculas_limpias = [str(m).strip() for m in matriculas]
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT TRIM("Matricula") as "Matricula", numero_predial, area_terreno, area_construida, nombre
                FROM public.informacioncatastral
                WHERE TRIM("Matricula") = ANY(%(matriculas)s);
            """
            df = pd.read_sql_query(query, conn, params={'matriculas': matriculas_limpias})
            info_catastral = {}
            for matricula, group in df.groupby('Matricula'):
                info_catastral[matricula] = {
                    "numero_predial": group['numero_predial'].iloc[0],
                    "area_terreno": group['area_terreno'].iloc[0],
                    "area_construida": group['area_construida'].iloc[0],
                    "propietarios": [p.strip() for p in group['nombre'].tolist()]
                }
            return info_catastral
    except Exception as e:
        st.error(f"Error al obtener datos catastrales: {e}")
        return {}

# --- FUNCIÓN DEL GRAFO (sin cambios) ---
def generar_grafo_interactivo(no_matricula_inicial, db_params):
    try:
        with psycopg2.connect(**db_params) as conn:
            query_recursiva = """
            WITH RECURSIVE familia_grafo AS (
                SELECT id, no_matricula_inmobiliaria FROM public.matriculas WHERE TRIM(no_matricula_inmobiliaria) = %(start_node)s
                UNION
                SELECT
                    CASE WHEN r.matricula_padre_id = fg.id THEN m_hija.id ELSE m_padre.id END,
                    CASE WHEN r.matricula_padre_id = fg.id THEN m_hija.no_matricula_inmobiliaria ELSE m_padre.no_matricula_inmobiliaria END
                FROM public.relacionesmatriculas r
                JOIN familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id
                JOIN public.matriculas m_padre ON r.matricula_padre_id = m_padre.id
                JOIN public.matriculas m_hija ON r.matricula_hija_id = m_hija.id
            )
            SELECT DISTINCT
                TRIM(padre.no_matricula_inmobiliaria) AS padre,
                TRIM(hija.no_matricula_inmobiliaria) AS hija
            FROM public.relacionesmatriculas rel
            JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id
            JOIN public.matriculas hija ON rel.matricula_hija_id = hija.id
            WHERE padre.id IN (SELECT id FROM familia_grafo)
              AND hija.id IN (SELECT id FROM familia_grafo);
            """
            df_relaciones = pd.read_sql_query(query_recursiva, conn, params={'start_node': str(no_matricula_inicial).strip()})

        if df_relaciones.empty:
            return None, f"⚠️ No se encontraron relaciones para '{no_matricula_inicial}'."

        nodos_del_grafo = set(df_relaciones['padre']).union(set(df_relaciones['hija']))
        info_catastral_nodos = obtener_info_catastral_batch(nodos_del_grafo, db_params)

        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')

        for node_id in g.nodes():
            info_nodo = info_catastral_nodos.get(str(node_id))

            if info_nodo:
                title = f"Matrícula: {node_id}\nEstado: Se encuentra en la base catastral."
                color = "#28a745"
            else:
                title = f"Matrícula: {node_id}\nEstado: No se encuentra en la base catastral."
                color = "#ffc107"

            if str(node_id) == str(no_matricula_inicial).strip():
                color = "#dc3545"
                size = 40
            else:
                size = 25

            net.add_node(str(node_id), label=str(node_id), title=title, color=color, size=size)

        net.add_edges(g.edges())

        options = {"layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}}, "physics": {"enabled": False}}
        net.set_options(json.dumps(options))

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Grafo interactivo generado con {len(g.nodes())} nodos."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"

def mostrar_tarjeta_info(info_dict):
    st.success("✅ ¡Encontrada en la Base Catastral!")
    st.metric(label="Número Predial", value=info_dict['numero_predial'])
    col1, col2 = st.columns(2)
    col1.metric(label="Área Terreno (m²)", value=info_dict['area_terreno'])
    col2.metric(label="Área Construida (m²)", value=info_dict['area_construida'])
    with st.expander(f"Propietarios ({len(info_dict['propietarios'])})"):
        for propietario in info_dict['propietarios']:
            st.write(f"- {propietario}")

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---
st.title("Panel de Análisis de Matrículas 🕸️")

# Inicializar el estado de la sesión para mantener los valores
if 'matricula_grafo' not in st.session_state:
    st.session_state.matricula_grafo = ""
if 'matricula_analisis' not in st.session_state:
    st.session_state.matricula_analisis = ""
if 'mostrar_analisis' not in st.session_state:
    st.session_state.mostrar_analisis = False

# Layout de dos columnas principales
col_grafo, col_analisis = st.columns([2, 1])

# --- Columna Izquierda: Controles del Grafo y Visualización ---
with col_grafo:
    st.subheader("Visualizador de Grafo de Relaciones")
    
    matricula_input_grafo = st.text_input(
        "Introduce la matrícula para generar el grafo:",
        key="input_grafo",
        placeholder="Ej: 1037473"
    )

    if st.button("Generar Grafo Interactivo", type="primary"):
        if matricula_input_grafo:
            st.session_state.matricula_grafo = matricula_input_grafo
            # Sincroniza el análisis con la nueva búsqueda del grafo
            st.session_state.matricula_analisis = matricula_input_grafo
            st.session_state.mostrar_analisis = True
        else:
            st.warning("Por favor, introduce una matrícula para generar el grafo.")

    # Mostrar el grafo si se ha buscado una matrícula
    if st.session_state.matricula_grafo:
        db_credentials = st.secrets["db_credentials"]
        with st.spinner("Generando grafo con códigos de color..."):
            nombre_archivo_html, mensaje = generar_grafo_interactivo(st.session_state.matricula_grafo, db_credentials)
        
        st.info(mensaje)

        if nombre_archivo_html:
            # Leyenda de colores
            st.markdown("""
                **Leyenda:** <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#dc3545; vertical-align:middle;"></span> Matrícula Buscada &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#28a745; vertical-align:middle;"></span> En Base Catastral &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#ffc107; vertical-align:middle;"></span> No en Base Catastral
            """, unsafe_allow_html=True)
            
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=800, scrolling=True)
            os.remove(nombre_archivo_html)

# --- Columna Derecha: Análisis Catastral ---
with col_analisis:
    st.subheader("Análisis Catastral Individual")
    
    # El valor por defecto del input de análisis es la última matrícula analizada
    matricula_input_analisis = st.text_input(
        "Matrícula a analizar:",
        value=st.session_state.matricula_analisis,
        key="input_analisis"
    )
    
    if st.button("Analizar"):
        if matricula_input_analisis:
            st.session_state.matricula_analisis = matricula_input_analisis
            st.session_state.mostrar_analisis = True
        else:
            st.warning("Introduce una matrícula para analizar.")
            st.session_state.mostrar_analisis = False
            
    # Mostrar la tarjeta de análisis si corresponde
    if st.session_state.mostrar_analisis and st.session_state.matricula_analisis:
        st.markdown("---")
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral_batch([st.session_state.matricula_analisis], db_credentials)
        resultado_individual = info.get(st.session_state.matricula_analisis.strip())
        
        if resultado_individual:
            mostrar_tarjeta_info(resultado_individual)
        else:
            st.error(f"❌ No se encontró la matrícula '{st.session_state.matricula_analisis}' en la base catastral.")
    else:
        st.info("Introduce una matrícula y presiona 'Analizar' para ver sus detalles.")