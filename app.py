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
            
            # SOLUCIÓN: Usamos un enlace <a> con target="_top" para asegurar que la URL principal cambie
            # El 'title' ahora es el popup HTML que SÍ debería funcionar con este método
            propietarios_html = '<br>- '.join(info_catastral_nodos.get(node_id, {}).get('propietarios', []))
            popup_html = (
                f'<a href="?matricula_buscada={no_matricula_inicial}&matricula_seleccionada={node_id}" target="_top">'
                f'Click para ver detalles de {node_id}'
                f'</a>'
            )
            net.add_node(node_id, label=node_id, title=popup_html, color=color, size=size)

        net.add_edges(g.edges())
        
        options = {"layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}}, "physics": {"enabled": False}}
        net.set_options(json.dumps(options))

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"


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

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---
st.title("Visor Interactivo de Matrículas 🕸️")

# Leemos los parámetros de la URL para mantener el estado
params = st.query_params
matricula_buscada_url = params.get("matricula_buscada", "")
matricula_seleccionada_url = params.get("matricula_seleccionada", "")

# Usamos st.session_state para una gestión más robusta
if "matricula_buscada" not in st.session_state:
    st.session_state.matricula_buscada = matricula_buscada_url

# El input se controla con el session_state
matricula_input = st.text_input(
    "Introduce el número de matrícula para generar el grafo:",
    key="matricula_buscada",
    placeholder="Ej: 1037473"
)

# Creamos el diseño de dos columnas
col_grafo, col_info = st.columns([3, 2])

# --- COLUMNA DERECHA: TARJETA DE INFORMACIÓN ---
with col_info:
    st.subheader("🔍 Análisis Catastral")
    
    # La matrícula a mostrar en la tarjeta tiene prioridad si fue seleccionada por clic (desde la URL)
    matricula_a_mostrar = matricula_seleccionada_url or st.session_state.matricula_buscada

    if matricula_a_mostrar:
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral_batch([matricula_a_mostrar], db_credentials)
        resultado_individual = info.get(matricula_a_mostrar.strip())
        
        if resultado_individual:
            mostrar_tarjeta_info(resultado_individual)
        else:
            st.warning("No se encontró información catastral para la matrícula seleccionada.")
    else:
        st.info("Busca una matrícula o haz clic en un nodo del grafo para ver sus detalles aquí.")

# --- COLUMNA IZQUIERDA: GRAFO ---
with col_grafo:
    if st.session_state.matricula_buscada:
        db_credentials = st.secrets["db_credentials"]
        
        # Generamos el grafo basado en el estado de la sesión
        with st.spinner("Buscando relaciones y generando grafo..."):
            nombre_archivo_html, mensaje = generar_grafo_para_streamlit(st.session_state.matricula_buscada, db_credentials)
        
        st.info(mensaje)

        if nombre_archivo_html:
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=820, scrolling=True)
            os.remove(nombre_archivo_html)
    else:
        st.info("↑ Introduce una matrícula para comenzar.")