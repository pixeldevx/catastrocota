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

# --- FUNCIÓN DEL GRAFO (MODIFICADA PARA COMUNICACIÓN EXTERNA) ---
def generar_grafo_para_streamlit(no_matricula_inicial, db_params):
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

        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        
        for node in g.nodes():
            node_id = str(node)
            color = "#FF0000" if node_id == str(no_matricula_inicial).strip() else "#97C2FC"
            size = 40 if node_id == str(no_matricula_inicial).strip() else 25
            title = f"Click para ver detalles de {node_id}"
            click_handler = f"window.top.location.href = '?matricula_buscada={no_matricula_inicial}&matricula_seleccionada={node_id}';"
            net.add_node(node_id, label=node_id, title=title, color=color, size=size, **{"onclick": click_handler})

        net.add_edges(g.edges())
        
        options = {"layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}}, "physics": {"enabled": False}}
        net.set_options(json.dumps(options))

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"

# --- FUNCIÓN PARA MOSTRAR LA TARJETA (sin cambios) ---
def mostrar_tarjeta_info(info_dict):
    st.success("✅ ¡Encontrada en la Base Catastral!")
    st.markdown("---")
    st.metric(label="Número Predial", value=info_dict['numero_predial'])
    col1, col2 = st.columns(2)
    col1.metric(label="Área Terreno (m²)", value=info_dict['area_terreno'])
    col2.metric(label="Área Construida (m²)", value=info_dict['area_construida'])
    with st.expander(f"Propietarios ({len(info_dict['propietarios'])})"):
        for propietario in info_dict['propietarios']:
            st.write(f"- {propietario}")

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL (CORREGIDA) ---
st.title("Visor Interactivo de Matrículas 🕸️")

# 1. Leer los parámetros de la URL al inicio
params = st.query_params
matricula_buscada_url = params.get("matricula_buscada", "")
matricula_seleccionada_url = params.get("matricula_seleccionada", "")

# 2. Inicializar el estado de la sesión si es la primera vez que se ejecuta
if 'matricula_buscada' not in st.session_state:
    st.session_state.matricula_buscada = matricula_buscada_url
if 'matricula_seleccionada' not in st.session_state:
    st.session_state.matricula_seleccionada = matricula_seleccionada_url

# 3. Sincronizar el estado con la URL (la URL tiene prioridad)
st.session_state.matricula_buscada = matricula_buscada_url or st.session_state.matricula_buscada
st.session_state.matricula_seleccionada = matricula_seleccionada_url or st.session_state.matricula_buscada

# 4. Caja de texto y botones
matricula_input = st.text_input(
    "Introduce el número de matrícula:",
    value=st.session_state.matricula_buscada,
    placeholder="Ej: 1037473"
)

col1_btn, col2_btn, _ = st.columns([1, 2, 3])
with col1_btn:
    if st.button("Generar Grafo", type="primary"):
        st.session_state.matricula_buscada = matricula_input
        st.session_state.matricula_seleccionada = matricula_input
        st.query_params.update(matricula_buscada=matricula_input, matricula_seleccionada=matricula_input)

with col2_btn:
    analisis_clicked = st.button("Análisis Catastral")


# 5. Diseño de la aplicación en columnas
col_grafo, col_info = st.columns([3, 2])

with col_info:
    st.subheader("🔍 Análisis Catastral")
    matricula_a_mostrar = st.session_state.matricula_seleccionada
    if analisis_clicked:
        matricula_a_mostrar = matricula_input

    if matricula_a_mostrar:
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral_batch([matricula_a_mostrar], db_credentials)
        resultado_individual = info.get(matricula_a_mostrar.strip())
        
        if resultado_individual:
            mostrar_tarjeta_info(resultado_individual)
        else:
            st.warning(f"No se encontró info catastral para: {matricula_a_mostrar}")
    else:
        st.info("Busca una matrícula o haz clic en un nodo para ver sus detalles.")

with col_grafo:
    if st.session_state.matricula_buscada:
        db_credentials = st.secrets["db_credentials"]
        with st.spinner("Generando grafo..."):
            nombre_archivo_html, mensaje = generar_grafo_para_streamlit(st.session_state.matricula_buscada, db_credentials)
        
        st.info(mensaje)

        if nombre_archivo_html:
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=820, scrolling=True, key=st.session_state.matricula_buscada)
            os.remove(nombre_archivo_html)
    else:
        st.info("↑ Introduce una matrícula y presiona 'Generar Grafo' para comenzar.")