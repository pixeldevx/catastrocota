import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os
import json
import folium
from io import BytesIO

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# --- FUNCIONES DE BASE DE DATOS Y PROCESAMIENTO ---

@st.cache_data(ttl=600)
def generar_datos_completos(no_matricula_inicial, db_params):
    """
    Función central que ejecuta la consulta recursiva y obtiene todos los datos
    necesarios para el grafo y el reporte en una sola vez.
    """
    try:
        with psycopg2.connect(**db_params) as conn:
            # 1. Obtener todas las relaciones (padre, hija)
            query_relaciones = """
                WITH RECURSIVE familia_grafo AS (
                    SELECT id FROM public.matriculas WHERE TRIM(no_matricula_inmobiliaria) = %(start_node)s
                    UNION
                    SELECT CASE WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id ELSE r.matricula_padre_id END
                    FROM public.relacionesmatriculas r JOIN familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id
                )
                SELECT DISTINCT
                    TRIM(padre.no_matricula_inmobiliaria) AS "Matricula_Padre",
                    TRIM(hija.no_matricula_inmobiliaria) AS "Matricula_Hija"
                FROM public.relacionesmatriculas rel
                JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id
                JOIN public.matriculas hija ON rel.matricula_hija_id = hija.id
                WHERE padre.id IN (SELECT id FROM familia_grafo) AND hija.id IN (SELECT id FROM familia_grafo);
            """
            df_relaciones = pd.read_sql_query(query_relaciones, conn, params={'start_node': str(no_matricula_inicial).strip()})

            if df_relaciones.empty:
                return None, f"⚠️ No se encontraron relaciones para '{no_matricula_inicial}'."

            # 2. Obtener atributos para todas las matrículas "hijas" del reporte
            matriculas_hijas = df_relaciones["Matricula_Hija"].unique().tolist()
            
            query_estados = "SELECT TRIM(no_matricula_inmobiliaria) as matricula, estado_folio FROM public.matriculas WHERE TRIM(no_matricula_inmobiliaria) = ANY(%(matriculas)s);"
            df_estados = pd.read_sql_query(query_estados, conn, params={'matriculas': matriculas_hijas})
            
            query_catastro = 'SELECT DISTINCT TRIM("Matricula") AS matricula, numero_predial_nacional FROM public.informacioncatastral WHERE TRIM("Matricula") = ANY(%(matriculas)s);'
            df_catastro = pd.read_sql_query(query_catastro, conn, params={'matriculas': matriculas_hijas})
            
            prediales_en_catastro = df_catastro["numero_predial_nacional"].dropna().unique().tolist()
            prediales_en_geo = set()
            if prediales_en_catastro:
                query_geo = "SELECT DISTINCT codigo FROM public.terrenos WHERE codigo = ANY(%(codigos)s);"
                df_geo = pd.read_sql_query(query_geo, conn, params={'codigos': prediales_en_catastro})
                prediales_en_geo = set(df_geo["codigo"].tolist())

            # 3. Unir toda la información para el reporte de Excel
            df_reporte = pd.merge(df_relaciones.copy(), df_estados, left_on="Matricula_Hija", right_on="matricula", how="left").rename(columns={"estado_folio": "Hija_Estado_Folio"})
            df_reporte = pd.merge(df_reporte, df_catastro, left_on="Matricula_Hija", right_on="matricula", how="left")
            
            df_reporte["Hija_En_Base_Catastral"] = df_reporte["numero_predial_nacional"].notna().map({True: 'Sí', False: 'No'})
            df_reporte["Hija_En_Base_Geografica"] = df_reporte["numero_predial_nacional"].isin(prediales_en_geo).map({True: 'Sí', False: 'No'})
            
            df_reporte_final = df_reporte[["Matricula_Padre", "Matricula_Hija", "Hija_En_Base_Catastral", "Hija_Estado_Folio", "Hija_En_Base_Geografica"]]
            
            return df_reporte_final, f"✅ Datos generados para {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error al procesar los datos: {e}"


def generar_grafo_visual(no_matricula_inicial, df_relaciones, db_params):
    """Genera el archivo HTML del grafo a partir de un DataFrame de relaciones."""
    nodos_del_grafo = set(df_relaciones['Matricula_Padre']).union(set(df_relaciones['Matricula_Hija']))
    
    def obtener_existencia_catastral_batch(matriculas, db_params):
        if not matriculas: return set()
        matriculas_limpias = [str(m).strip() for m in matriculas]
        try:
            with psycopg2.connect(**db_params) as conn_batch:
                query_batch = 'SELECT DISTINCT TRIM("Matricula") AS matricula_limpia FROM public.informacioncatastral WHERE TRIM("Matricula") = ANY(%(matriculas)s);'
                df_batch = pd.read_sql_query(query_batch, conn_batch, params={'matriculas': matriculas_limpias})
                return set(df_batch['matricula_limpia'].tolist())
        except: return set()

    matriculas_en_catastro = obtener_existencia_catastral_batch(nodos_del_grafo, db_params)

    net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
    for node_id in nodos_del_grafo:
        color = "#ffc107"
        title = f"Matrícula: {node_id}\nEstado: No se encuentra en la base catastral."
        if node_id in matriculas_en_catastro:
            color = "#28a745"
            title = f"Matrícula: {node_id}\nEstado: Se encuentra en la base catastral."
        if node_id == str(no_matricula_inicial).strip():
            color = "#dc3545"
        
        size = 40 if node_id == str(no_matricula_inicial).strip() else 25
        net.add_node(node_id, label=node_id, title=title, color=color, size=size)

    # Corregir la forma de añadir las aristas
    edges = df_relaciones.rename(columns={"Matricula_Padre": "source", "Matricula_Hija": "to"}).to_dict(orient='records')
    net.add_edges(edges)

    options = {"layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}}, "physics": {"enabled": False}}
    net.set_options(json.dumps(options))

    nombre_archivo = f"grafo_{no_matricula_inicial}.html"
    net.save_graph(nombre_archivo)
    return nombre_archivo

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='ReporteRelaciones')
    processed_data = output.getvalue()
    return processed_data

def obtener_info_catastral(matricula, db_params):
    if not matricula: return {}
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT TRIM("Matricula") as "Matricula", numero_predial, area_terreno, area_construida, nombre, numero_predial_nacional
                FROM public.informacioncatastral WHERE TRIM("Matricula") = %(matricula)s;
            """
            df = pd.read_sql_query(query, conn, params={'matricula': str(matricula).strip()})
            if df.empty: return {}
            info_catastral = {}
            for m, group in df.groupby('Matricula'):
                info_catastral[m] = {
                    "numero_predial": group['numero_predial'].iloc[0],
                    "area_terreno": group['area_terreno'].iloc[0],
                    "area_construida": group['area_construida'].iloc[0],
                    "propietarios": [p.strip() for p in group['nombre'].tolist()],
                    "numero_predial_nacional": group['numero_predial_nacional'].iloc[0]
                }
            return info_catastral
    except Exception as e:
        st.error(f"Error en info catastral: {e}")
        return {}
        
def mostrar_tarjeta_analisis(matricula_a_analizar, db_params):
    # (El resto de esta función no necesita cambios)
    pass
    
# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---
st.title("Asistente de Análisis Catastral 🗺️")

if 'matricula_grafo' not in st.session_state:
    st.session_state.matricula_grafo = ""
if 'reporte_df' not in st.session_state:
    st.session_state.reporte_df = None

col_grafo, col_analisis = st.columns([2, 1])

with col_grafo:
    st.subheader("Visualizador de Grafo de Relaciones")
    matricula_input_grafo = st.text_input("Introduce la matrícula para generar el grafo:", key="input_grafo")
    
    if st.button("Generar Grafo", type="primary"):
        if matricula_input_grafo:
            st.session_state.matricula_grafo = matricula_input_grafo
            db_credentials = st.secrets["db_credentials"]
            with st.spinner("Generando datos para grafo y reporte..."):
                df_reporte, mensaje = generar_datos_completos(matricula_input_grafo, db_credentials)
            st.session_state.reporte_df = df_reporte
            st.info(mensaje)
        else:
            st.warning("Por favor, introduce una matrícula.")

    if st.session_state.reporte_df is not None:
        db_credentials = st.secrets["db_credentials"]
        # Usamos las relaciones del DataFrame ya generado para el reporte
        df_relaciones_para_grafo = st.session_state.reporte_df[['Matricula_Padre', 'Matricula_Hija']]
        nombre_archivo_html = generar_grafo_visual(st.session_state.matricula_grafo, df_relaciones_para_grafo, db_credentials)
        
        # Leyenda de colores
        st.markdown("""
            **Leyenda:** &nbsp;
            <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#dc3545; vertical-align:middle; border:1px solid #555;"></span> Matrícula Buscada &nbsp;
            <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#28a745; vertical-align:middle; border:1px solid #555;"></span> En Base Catastral &nbsp;
            <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#ffc107; vertical-align:middle; border:1px solid #555;"></span> No en Base Catastral
        """, unsafe_allow_html=True)
        
        with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
            source_code = f.read()
            st.components.v1.html(source_code, height=800, scrolling=True)
        os.remove(nombre_archivo_html)

with col_analisis:
    st.subheader("Análisis y Reportes")
    
    # Botón de descarga condicional
    if st.session_state.reporte_df is not None:
        excel_data = to_excel(st.session_state.reporte_df)
        st.download_button(
            label="📥 Descargar Reporte en Excel",
            data=excel_data,
            file_name=f"reporte_relaciones_{st.session_state.matricula_grafo}.xlsx"
        )
    else:
        st.info("Genere un grafo para habilitar la descarga del reporte.")
        
    st.markdown("---")
    
    # Análisis individual (la lógica se mantiene, aquí solo un placeholder)
    st.info("La sección de análisis individual se mantiene para futuras consultas.")