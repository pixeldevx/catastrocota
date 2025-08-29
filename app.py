import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os

# --- NUEVA FUNCIÓN ---
def verificar_informacion_catastral(no_matricula, db_params):
    """
    Verifica si una matrícula tiene al menos un registro en la tabla InformacionCatastral.
    Devuelve True si existe, False si no, o un string de error si algo falla.
    """
    try:
        with psycopg2.connect(**db_params) as conn:
            # Usamos una consulta simple y eficiente para verificar la existencia
            query = "SELECT EXISTS (SELECT 1 FROM public.informacioncatastral WHERE matricula = %(matricula)s);"
            # Pandas facilita la ejecución y obtención del resultado booleano
            df = pd.read_sql_query(query, conn, params={'matricula': no_matricula})
            # El resultado es un DataFrame con una sola celda [0, 'exists'] que contiene True o False
            return df.iloc[0]['exists']
    except Exception as e:
        # En caso de un error de conexión o consulta, lo notificamos
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

st.title("Visor de Grafos de Matrículas 🕸️")
st.write("Esta herramienta visualiza las relaciones jerárquicas entre matrículas y verifica su información catastral.")

matricula_input = st.text_input("Introduce el número de matrícula inmobiliaria:", placeholder="Ej: 1037472")

if st.button("Consultar y Generar Grafo"):
    if matricula_input:
        # Obtenemos las credenciales de forma segura
        db_credentials = st.secrets["db_credentials"]
        
        st.markdown("---") # Una línea para separar visualmente
        
        # --- SECCIÓN MODIFICADA: TARJETA DE INFORMACIÓN ---
        st.subheader("Tarjeta de Información Rápida")
        
        # 1. Ejecutamos la nueva función de verificación
        existe_en_catastro = verificar_informacion_catastral(matricula_input, db_credentials)
        
        # 2. Mostramos el resultado en una "métrica" o tarjeta
        if isinstance(existe_en_catastro, bool):
            # Si la función devuelve True/False, mostramos el resultado
            resultado_texto = "Sí" if existe_en_catastro else "No"
            st.metric(label="R1: ¿En Base Catastral?", value=resultado_texto)
        else:
            # Si la función devolvió un error, lo mostramos
            st.error(existe_en_catastro)
        
        st.markdown("---")

        # --- CÓDIGO EXISTENTE: GENERACIÓN DEL GRAFO ---
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