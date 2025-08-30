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

            info = {
                "encontrado": True,
                "numero_predial": df['numero_predial'].iloc[0],
                "area_terreno": df['area_terreno'].iloc[0],
                "area_construida": df['area_construida'].iloc[0],
                "propietarios": df['nombre'].tolist()
            }
            return info
            
    except Exception as e:
        return {"encontrado": False, "error": str(e)}


def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo con nodos clicables y devuelve el nombre del archivo HTML.
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
            node_id = str(node["id"])
            # --- MODIFICACIÓN AQUÍ: CAMBIO EN EL TITLE DEL TOOLTIP ---
            node["title"] = f"Matrícula: {node_id} (Click para ver detalles)" 
            # El js_redirect permanece igual, es para el click
            js_redirect = f'window.parent.location.href = "?matricula_buscada={no_matricula_inicial}&matricula_seleccionada={node_id}"'
            node["_onclick"] = js_redirect
            
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

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---

st.title("Visor Interactivo de Matrículas 🕸️")

params = st.query_params
matricula_buscada_url = params.get("matricula_buscada")
matricula_seleccionada_url = params.get("matricula_seleccionada")

matricula_input = st.text_input(
    "Introduce el número de matrícula para generar el grafo:", 
    value=matricula_buscada_url or "",
    placeholder="Ej: 1037472"
)

col1, col2 = st.columns([3, 1])

with col2:
    st.subheader("🔎 Detalles Catastrales")
    
    matricula_a_mostrar = matricula_seleccionada_url or matricula_input

    if matricula_a_mostrar:
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral(matricula_a_mostrar, db_credentials)
        
        st.metric(label="Matrícula Seleccionada", value=matricula_a_mostrar)

        if "error" in info:
             st.error(f"Error de base de datos: {info['error']}")
        elif info["encontrado"]:
            st.success("✅ Encontrada en Base Catastral")
            st.write(f"**Número Predial:** {info['numero_predial']}")
            st.write(f"**Área Terreno:** {info['area_terreno']} m²")
            st.write(f"**Área Construida:** {info['area_construida']} m²")
            
            with st.expander(f"Propietarios ({len(info['propietarios'])})"):
                for propietario in info['propietarios']:
                    st.write(f"- {propietario.strip()}")
        else:
            st.warning("❌ No encontrada en Base Catastral")
    else:
        st.info("Busca una matrícula o haz clic en un nodo del grafo para ver sus detalles.")

with col1:
    if matricula_input:
        # Solo mostrar el botón si no estamos ya mostrando un grafo por URL
        if not matricula_buscada_url:
            st.button("Generar Grafo")
        
        # Generar el grafo si hay input o si se ha buscado desde la URL
        if matricula_input: # Se valida que haya algo en el input
            st.subheader(f"Grafo de Relaciones para: {matricula_input}")
            db_credentials = st.secrets["db_credentials"]
            
            with st.spinner("Generando grafo..."):
                nombre_archivo_html, mensaje = generar_grafo_matricula(matricula_input, db_credentials)
            
            st.write(mensaje)

            if nombre_archivo_html:
                with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                    st.components.v1.html(source_code, height=820, scrolling=True)
                os.remove(nombre_archivo_html)
    else:
        st.info("↑ Introduce una matrícula y presiona 'Generar Grafo' para comenzar.")