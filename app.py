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
    Busca detalles para una LISTA de matrículas en una sola consulta.
    Limpia los datos para asegurar la coincidencia.
    """
    if not matriculas:
        return {}
    
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
        st.error(f"Error al obtener datos catastrales en lote: {e}")
        return {}


def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo donde los tooltips de los nodos contienen la información catastral en HTML.
    """
    try:
        # ... (El resto de la función del grafo no necesita cambios) ...
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
            return None, f"⚠️ No se encontraron relaciones de parentesco para '{no_matricula_inicial}'."

        nodos_del_grafo = set(df_relaciones['padre']).union(set(df_relaciones['hija']))
        info_catastral_nodos = obtener_info_catastral_batch(nodos_del_grafo, db_params)

        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            node_id = str(node["id"])
            info_nodo = info_catastral_nodos.get(node_id)
            
            if info_nodo:
                propietarios_html = '<br>- '.join(info_nodo['propietarios'])
                tooltip_html = (
                    f"<b>--- Info Catastral ---</b><br>"
                    f"<b>Matrícula:</b> {node_id}<br>"
                    f"<b>Predial:</b> {info_nodo['numero_predial']}<br>"
                    f"<b>Á. Terreno:</b> {info_nodo['area_terreno']} m²<br>"
                    f"<b>Á. Construida:</b> {info_nodo['area_construida']} m²<br>"
                    f"<b>Propietarios:</b><br>- {propietarios_html}"
                )
                node["title"] = tooltip_html
            else:
                node["title"] = f"<b>Matrícula:</b> {node_id}<br>(Sin datos en base catastral)"

            if node_id == str(no_matricula_inicial).strip():
                node["color"] = "#FF0000"
                node["size"] = 40
        
        net.set_options("""
        var options = { "layout": { "hierarchical": { "enabled": true, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 100 }}, "physics": { "enabled": false }}
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"


# --- NUEVA FUNCIÓN PARA MOSTRAR LA TARJETA ---
def mostrar_tarjeta_info(info_dict):
    """
    Toma un diccionario con información catastral y lo muestra en una tarjeta de Streamlit.
    """
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

matricula_input = st.text_input(
    "Introduce el número de matrícula:",
    placeholder="Ej: 1037473"
)

col1_btn, col2_btn, _ = st.columns([1, 2, 3])

with col1_btn:
    generar_clicked = st.button("Generar Grafo", type="primary")

with col2_btn:
    probar_clicked = st.button("Probar Búsqueda Catastral")

# --- LÓGICA DE LA HERRAMIENTA DE DIAGNÓSTICO ---
if probar_clicked:
    if matricula_input:
        st.subheader(f"🔍 Tarjeta de Información para: {matricula_input}")
        db_credentials = st.secrets["db_credentials"]
        info = obtener_info_catastral_batch([matricula_input], db_credentials)
        resultado_individual = info.get(matricula_input.strip())
        
        if resultado_individual:
            # Llamamos a la nueva función para mostrar la tarjeta
            mostrar_tarjeta_info(resultado_individual)
        else:
            st.error("❌ No se encontró la matrícula en la base catastral.")
            st.info("Verifica que no haya espacios en blanco o errores en el número.")
    else:
        st.warning("Por favor, introduce una matrícula para probar la búsqueda.")


# --- LÓGICA DE GENERACIÓN DEL GRAFO ---
if generar_clicked:
    if matricula_input:
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
        st.warning("Por favor, introduce una matrícula para generar el grafo.")