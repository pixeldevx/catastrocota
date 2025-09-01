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

# --- FUNCIÓN DEL GRAFO (MODIFICADA PARA DEVOLVER DATOS) ---
def generar_grafo_y_datos(no_matricula_inicial, db_params):
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
            return None, None, f"⚠️ No se encontraron relaciones para '{no_matricula_inicial}'."

        nodos_del_grafo = sorted(list(set(df_relaciones['padre']).union(set(df_relaciones['hija']))))
        info_catastral_nodos = obtener_info_catastral_batch(nodos_del_grafo, db_params)

        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="600px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        
        for node_id in nodos_del_grafo:
            color = "#FF0000" if node_id == str(no_matricula_inicial).strip() else "#97C2FC"
            size = 40 if node_id == str(no_matricula_inicial).strip() else 25
            title = f"Matrícula: {node_id}"
            net.add_node(node_id, label=node_id, title=title, color=color, size=size)

        net.add_edges(g.edges())
        
        options = {"layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}}, "physics": {"enabled": False}}
        net.set_options(json.dumps(options))

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, (nodos_del_grafo, info_catastral_nodos), f"✅ Se encontraron {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, None, f"❌ Ocurrió un error al generar el grafo: {e}"

# --- FUNCIÓN PARA MOSTRAR LA TARJETA (sin cambios) ---
def mostrar_tarjeta_info(info_dict):
    st.success("✅ ¡Encontrada en la Base Catastral!")
    st.metric(label="Número Predial", value=info_dict['numero_predial'])
    col1, col2 = st.columns(2)
    col1.metric(label="Área Terreno (m²)", value=info_dict['area_terreno'])
    col2.metric(label="Área Construida (m²)", value=info_dict['area_construida'])
    with st.expander(f"Propietarios ({len(info_dict['propietarios'])})"):
        for propietario in info_dict['propietarios']:
            st.write(f"- {propietario}")

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL (REESTRUCTURADA) ---
st.title("Visor y Analizador de Matrículas 🕸️")

matricula_input = st.text_input(
    "Introduce el número de matrícula:",
    placeholder="Ej: 1037473"
)

col1_btn, col2_btn, _ = st.columns([1, 2, 3])

with col1_btn:
    generar_clicked = st.button("Generar Grafo y Reporte", type="primary")

with col2_btn:
    analisis_clicked = st.button("Análisis Catastral Individual")

# Lógica para el análisis individual
if analisis_clicked:
    if matricula_input:
        st.subheader(f"🔍 Análisis Catastral para: {matricula_input}")
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral_batch([matricula_input], db_credentials)
        resultado_individual = info.get(matricula_input.strip())
        
        if resultado_individual:
            mostrar_tarjeta_info(resultado_individual)
        else:
            st.error("❌ No se encontró la matrícula en la base catastral.")
    else:
        st.warning("Por favor, introduce una matrícula para el análisis.")

# Lógica para generar el grafo y el reporte completo
if generar_clicked:
    if matricula_input:
        db_credentials = st.secrets["db_credentials"]
        
        with st.spinner("Buscando relaciones y generando reporte..."):
            nombre_archivo_html, datos_reporte, mensaje = generar_grafo_y_datos(matricula_input, db_credentials)
        
        st.info(mensaje)

        # 1. Mostrar el Grafo
        if nombre_archivo_html:
            st.subheader("Grafo de Relaciones")
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=600, scrolling=True)
            os.remove(nombre_archivo_html)

        # 2. Mostrar el Reporte de Nodos
        if datos_reporte:
            nodos, info_nodos = datos_reporte
            st.markdown("---")
            st.subheader("🔍 Reporte de Nodos del Grafo")
            st.write(f"Se encontró información catastral para **{len(info_nodos)}** de los **{len(nodos)}** nodos del grafo.")

            for nodo in nodos:
                info_nodo = info_nodos.get(nodo)
                if info_nodo:
                    with st.expander(f"✅ Matrícula: {nodo} (Con datos catastrales)"):
                        mostrar_tarjeta_info(info_nodo)
                else:
                    with st.expander(f"⚠️ Matrícula: {nodo} (Sin datos catastrales)"):
                        st.warning("No se encontró información para esta matrícula en la base catastral.")
    else:
        st.warning("Por favor, introduce una matrícula para generar el grafo.")