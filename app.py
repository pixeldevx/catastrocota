import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os
import json
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# --- FUNCIONES DE BASE DE DATOS ---

def obtener_info_catastral(matricula, db_params):
    """Busca información de propietarios y avalúos."""
    return obtener_info_catastral_batch([matricula], db_params)

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
            info = {}
            for m, group in df.groupby('Matricula'):
                info[m] = {
                    "numero_predial": group['numero_predial'].iloc[0],
                    "area_terreno": group['area_terreno'].iloc[0],
                    "area_construida": group['area_construida'].iloc[0],
                    "propietarios": [p.strip() for p in group['nombre'].tolist()]
                }
            return info
    except Exception as e:
        st.error(f"Error en info catastral: {e}")
        return {}

# --- NUEVA FUNCIÓN PARA DATOS GEOGRÁFICOS ---
def obtener_info_terreno(matricula, db_params):
    """Busca la dirección y geometría del terreno, devolviendo la geometría como GeoJSON."""
    try:
        with psycopg2.connect(**db_params) as conn:
            # ST_AsGeoJSON convierte la geometría a un formato que folium puede leer
            query = """
                SELECT direccion, ST_AsGeoJSON(wkb_geometry) as geojson
                FROM public.terrenos
                WHERE matricula_inmobiliaria = %(matricula)s
                LIMIT 1;
            """
            df = pd.read_sql_query(query, conn, params={'matricula': str(matricula).strip()})
            if not df.empty:
                return df.to_dict('records')[0]
            return None
    except Exception as e:
        st.error(f"Error en info terreno: {e}")
        return None

def generar_grafo_interactivo(no_matricula_inicial, db_params):
    # (Esta función no necesita cambios, la dejamos como está)
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

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---
st.title("Panel de Análisis de Matrículas 🕸️")

# Inicializar el estado de la sesión
if 'matricula_grafo' not in st.session_state:
    st.session_state.matricula_grafo = ""
if 'matricula_analisis' not in st.session_state:
    st.session_state.matricula_analisis = ""

# Layout de dos columnas
col_grafo, col_analisis = st.columns([2, 1])

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
            st.session_state.matricula_analisis = matricula_input_grafo
        else:
            st.warning("Por favor, introduce una matrícula para generar el grafo.")

    if st.session_state.matricula_grafo:
        db_credentials = st.secrets["db_credentials"]
        with st.spinner("Generando grafo..."):
            nombre_archivo_html, mensaje = generar_grafo_interactivo(st.session_state.matricula_grafo, db_credentials)
        st.info(mensaje)

        if nombre_archivo_html:
            st.markdown("""
                **Leyenda:** <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#dc3545; vertical-align:middle;"></span> Matrícula Buscada &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#28a745; vertical-align:middle;"></span> En Base Catastral &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#ffc107; vertical-align:middle;"></span> No en Base Catastral
            """, unsafe_allow_html=True)
            
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=800, scrolling=True)
            os.remove(nombre_archivo_html)

with col_analisis:
    st.subheader("Análisis Catastral y Geográfico")
    
    matricula_input_analisis = st.text_input(
        "Matrícula a analizar:",
        value=st.session_state.matricula_analisis,
        key="input_analisis"
    )
    
    if st.button("Analizar"):
        st.session_state.matricula_analisis = matricula_input_analisis

    if st.session_state.matricula_analisis:
        st.markdown("---")
        matricula_a_analizar = st.session_state.matricula_analisis
        
        db_credentials = st.secrets["db_credentials"]
        info_catastral = obtener_info_catastral(matricula_a_analizar, db_credentials).get(matricula_a_analizar.strip())
        info_terreno = obtener_info_terreno(matricula_a_analizar, db_credentials)
        
        if not info_catastral and not info_terreno:
            st.error(f"❌ No se encontró la matrícula '{matricula_a_analizar}' en ninguna base de datos.")
        else:
            # Mostrar datos de info_catastral si existen
            if info_catastral:
                st.success("✅ ¡Encontrada en la Base Catastral!")
                st.metric(label="Número Predial", value=info_catastral['numero_predial'])
                c1, c2 = st.columns(2)
                c1.metric(label="Área Terreno (m²)", value=info_catastral['area_terreno'])
                c2.metric(label="Área Construida (m²)", value=info_catastral['area_construida'])
                with st.expander(f"Propietarios ({len(info_catastral['propietarios'])})"):
                    for p in info_catastral['propietarios']: st.write(f"- {p}")
            
            # Mostrar datos de info_terreno si existen
            if info_terreno:
                st.success("✅ ¡Encontrada en la Base Geográfica!")
                if info_terreno.get('direccion'):
                    st.metric(label="Dirección", value=info_terreno['direccion'])
                
                # Renderizar el mapa
                if info_terreno.get('geojson'):
                    geojson_data = json.loads(info_terreno['geojson'])
                    # Crear un mapa centrado en Colombia
                    m = folium.Map(location=[4.5709, -74.2973], zoom_start=6) 
                    # Añadir el polígono al mapa
                    folium.GeoJson(geojson_data).add_to(m) 
                    # Ajustar el mapa para que se centre y haga zoom en el polígono
                    m.fit_bounds(folium.GeoJson(geojson_data).get_bounds()) 
                    
                    st.write("**Visualización Geográfica del Terreno:**")
                    st_folium(m, width=700, height=500)
    else:
        st.info("Introduce una matrícula y presiona 'Analizar'.")