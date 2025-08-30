import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# --- FUNCIONES DE BASE DE DATOS ---

def obtener_info_catastral(no_matricula, db_params):
    """
    Busca todos los detalles de una matrícula en la tabla InformacionCatastral.
    Devuelve un diccionario con los datos encontrados.
    """
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT numero_predial, area_terreno, area_construida, nombre 
                FROM public.informacioncatastral 
                WHERE "Matricula" = %(matricula)s;
            """
            df = pd.read_sql_query(query, conn, params={'matricula': no_matricula})

            if df.empty:
                return {"encontrado": False}

            # Agregamos los datos. El área, etc., será la misma para todos los registros.
            # Juntamos todos los nombres de propietarios en una lista.
            info = {
                "encontrado": True,
                "numero_predial": df['numero_predial'].iloc[0],
                "area_terreno": df['area_terreno'].iloc[0],
                "area_construida": df['area_construida'].iloc[0],
                "propietarios": df['nombre'].tolist()
            }
            return info
            
    except Exception as e:
        st.error(f"Error al obtener info catastral: {e}")
        return {"encontrado": False}


def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo con nodos clicables y devuelve el nombre del archivo HTML.
    """
    try:
        # ... (La consulta SQL recursiva para el grafo no cambia)
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

        # --- MODIFICACIÓN CLAVE: Nodos Clicables ---
        for node in net.nodes:
            node_id = str(node["id"])
            # Cada nodo ahora es un enlace que recarga la app con un parámetro en la URL
            node["href"] = f"?matricula_seleccionada={node_id}"
            node["title"] = f"Matrícula: {node_id}<br>Click para ver detalles catastrales"
            if node_id == str(no_matricula_inicial):
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

st.title("Visor Interactivo de Matrículas 🕸️")

# Usamos el estado de la sesión para recordar la última matrícula buscada
if 'matricula_buscada' not in st.session_state:
    st.session_state.matricula_buscada = ''

# Caja de texto para la búsqueda principal
matricula_input = st.text_input(
    "Introduce el número de matrícula para generar el grafo:", 
    st.session_state.matricula_buscada,
    placeholder="Ej: 1037472"
)

# Detectamos si el usuario ha hecho una nueva búsqueda
if matricula_input != st.session_state.matricula_buscada:
    st.session_state.matricula_buscada = matricula_input
    # Limpiamos la selección de la URL para evitar confusiones
    st.query_params.clear()

# --- LÓGICA DE VISUALIZACIÓN ---

# Leemos la matrícula seleccionada desde la URL (si un nodo fue clickeado)
params = st.query_params
matricula_seleccionada = params.get("matricula_seleccionada")

# Definimos las columnas para el diseño
col1, col2 = st.columns([3, 1])

# --- Columna Derecha (Tarjeta de Información Dinámica) ---
with col2:
    st.subheader("🔎 Detalles Catastrales")
    
    # Decidimos qué matrícula mostrar: la seleccionada en el grafo o la buscada
    matricula_a_mostrar = matricula_seleccionada or st.session_state.matricula_buscada

    if matricula_a_mostrar:
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral(matricula_a_mostrar, db_credentials)
        
        st.metric(label="Matrícula Seleccionada", value=matricula_a_mostrar)

        if info["encontrado"]:
            st.success("✅ Encontrada en Base Catastral")
            st.write(f"**Número Predial:** {info['numero_predial']}")
            st.write(f"**Área Terreno:** {info['area_terreno']} m²")
            st.write(f"**Área Construida:** {info['area_construida']} m²")
            
            with st.expander(f"Propietarios ({len(info['propietarios'])})"):
                for propietario in info['propietarios']:
                    st.write(f"- {propietario}")
        else:
            st.warning("❌ No encontrada en Base Catastral")
    else:
        st.info("Busca una matrícula o haz clic en un nodo del grafo para ver sus detalles.")

# --- Columna Izquierda (Grafo) ---
with col1:
    if st.session_state.matricula_buscada:
        st.subheader(f"Grafo de Relaciones para: {st.session_state.matricula_buscada}")
        db_credentials = st.secrets["db_credentials"]
        
        with st.spinner("Generando grafo..."):
            nombre_archivo_html, mensaje = generar_grafo_matricula(st.session_state.matricula_buscada, db_credentials)
        
        st.write(mensaje)

        if nombre_archivo_html:
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=820, scrolling=True)
            os.remove(nombre_archivo_html)
    else:
        st.info("↑ Introduce una matrícula para comenzar.")