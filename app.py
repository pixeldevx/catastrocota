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

# --- FUNCIONES DE BASE DE DATOS (sin cambios) ---
def obtener_info_catastral(matricula, db_params):
    if not matricula: return {}
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT TRIM("Matricula") as "Matricula", numero_predial, area_terreno, area_construida, nombre, numero_predial_nacional
                FROM public.informacioncatastral
                WHERE TRIM("Matricula") = %(matricula)s;
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

def obtener_info_terreno_por_predial(numero_predial, db_params):
    try:
        with psycopg2.connect(**db_params) as conn:
            query = """
                SELECT 
                    direccion, 
                    terrarfi,
                    ST_AsGeoJSON(ST_Transform(geom, 4326)) as geojson
                FROM public.terrenos
                WHERE codigo = %(numero_predial)s
                LIMIT 1;
            """
            df = pd.read_sql_query(query, conn, params={'numero_predial': str(numero_predial).strip()})
            if not df.empty:
                return df.to_dict('records')[0]
            return None
    except Exception as e:
        st.error(f"Error en info terreno: {e}")
        return None

def obtener_existencia_catastral_batch(matriculas, db_params):
    if not matriculas: return set()
    matriculas_limpias = [str(m).strip() for m in matriculas]
    try:
        with psycopg2.connect(**db_params) as conn_batch:
            query_batch = 'SELECT DISTINCT TRIM("Matricula") AS matricula_limpia FROM public.informacioncatastral WHERE TRIM("Matricula") = ANY(%(matriculas)s);'
            df_batch = pd.read_sql_query(query_batch, conn_batch, params={'matriculas': matriculas_limpias})
            return set(df_batch['matricula_limpia'].tolist())
    except Exception as e:
        st.error(f"Error al verificar existencia catastral: {e}")
        return set()

def obtener_info_geografica_batch(prediales, db_params):
    """Verifica si los números prediales tienen información geográfica."""
    if not prediales:
        return set()
    prediales_limpios = [str(p).strip() for p in prediales]
    try:
        with psycopg2.connect(**db_params) as conn:
            query = 'SELECT DISTINCT codigo FROM public.terrenos WHERE codigo = ANY(%(prediales)s);'
            df = pd.read_sql_query(query, conn, params={'prediales': prediales_limpios})
            return set(df['codigo'].tolist())
    except Exception as e:
        st.error(f"Error al verificar existencia geográfica: {e}")
        return set()

# --- FUNCIÓN DEL GRAFO (MODIFICADA) ---
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
                TRIM(hija.no_matricula_inmobiliaria) AS hija,
                padre.estado_folio AS padre_estado,
                hija.estado_folio AS hija_estado
            FROM public.relacionesmatriculas rel
            JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id
            JOIN public.matriculas hija ON rel.matricula_hija_id = hija.id
            WHERE padre.id IN (SELECT id FROM familia_grafo)
                AND hija.id IN (SELECT id FROM familia_grafo);
            """
            df_relaciones = pd.read_sql_query(query_recursiva, conn, params={'start_node': str(no_matricula_inicial).strip()})

        if df_relaciones.empty:
            return None, f"⚠️ No se encontraron relaciones para '{no_matricula_inicial}'.", pd.DataFrame()

        nodos_del_grafo = set(df_relaciones['padre']).union(set(df_relaciones['hija']))
        
        info_catastral_full = {}
        with psycopg2.connect(**db_params) as conn_batch:
            query_catastral = 'SELECT TRIM("Matricula") as matricula, numero_predial_nacional FROM public.informacioncatastral WHERE TRIM("Matricula") = ANY(%(matriculas)s);'
            df_catastral = pd.read_sql_query(query_catastral, conn_batch, params={'matriculas': list(nodos_del_grafo)})
        
        matriculas_en_catastro = set(df_catastral['matricula'].tolist())
        prediales_nacionales = {row['matricula']: row['numero_predial_nacional'] for index, row in df_catastral.iterrows()}
        
        prediales_con_geo = obtener_info_geografica_batch(list(prediales_nacionales.values()), db_params)

        estado_folio_map = {}
        for index, row in df_relaciones.iterrows():
            estado_folio_map[row['padre']] = row['padre_estado']
            estado_folio_map[row['hija']] = row['hija_estado']

        # Crear el DataFrame para la exportación con la nueva columna
        df_export = pd.DataFrame(list(nodos_del_grafo), columns=['Matrícula'])
        df_export['Estado_Folio'] = df_export['Matrícula'].apply(lambda x: estado_folio_map.get(x, 'No disponible'))
        df_export['Tiene_Info_Catastral'] = df_export['Matrícula'].isin(matriculas_en_catastro).apply(lambda x: 'Sí' if x else 'No')
        df_export['Tiene_Info_Geográfica'] = df_export.apply(
            lambda row: 'Sí' if row['Tiene_Info_Catastral'] == 'Sí' and prediales_nacionales.get(row['Matrícula']) in prediales_con_geo else 'No', axis=1
        )
        
        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')

        for node_id in g.nodes():
            estado_folio = estado_folio_map.get(str(node_id), 'No disponible')
            
            tiene_catastral = str(node_id) in matriculas_en_catastro
            
            if tiene_catastral:
                title = f"Matrícula: {node_id}\nEstado Folio: {estado_folio}\nEstado: Se encuentra en la base catastral."
                color = "#28a745"
            else:
                title = f"Matrícula: {node_id}\nEstado Folio: {estado_folio}\nEstado: No se encuentra en la base catastral."
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
        return nombre_archivo, f"✅ Grafo interactivo generado con {len(g.nodes())} nodos.", df_export
    except Exception as e:
        st.error(f"❌ Ocurrió un error al generar el grafo: {e}")
        return None, None, pd.DataFrame()

# --- FUNCIÓN PARA MOSTRAR LA TARJETA DE ANÁLISIS ---
def mostrar_tarjeta_analisis(matricula_a_analizar, db_params):
    st.markdown("---")
    
    info_catastral = obtener_info_catastral(matricula_a_analizar, db_params).get(matricula_a_analizar.strip())
    
    if not info_catastral:
        st.error(f"❌ No se encontró la matrícula '{matricula_a_analizar}' en la base catastral.")
    else:
        st.success("✅ ¡Encontrada en la Base Catastral!")
        
        st.markdown("""
            <style>
            div[data-testid="metric-container"] > div > p {
                font-size: 1.2rem;
                white-space: normal;
                word-wrap: break-word;
            }
            </style>
            """, unsafe_allow_html=True)
        st.metric(label="Número Predial", value=info_catastral['numero_predial'])

        c1, c2 = st.columns(2)
        c1.metric(label="Área Terreno (m²)", value=info_catastral['area_terreno'])
        c2.metric(label="Área Construida (m²)", value=info_catastral['area_construida'])
        with st.expander(f"Propietarios ({len(info_catastral['propietarios'])})"):
            for p in info_catastral['propietarios']: st.write(f"- {p}")

        st.markdown("---")
        numero_predial_nacional = info_catastral.get('numero_predial_nacional')
        if numero_predial_nacional:
            with st.spinner(f"Buscando información geográfica para {numero_predial_nacional}..."):
                info_terreno = obtener_info_terreno_por_predial(numero_predial_nacional, db_params)
            
            if info_terreno:
                st.success("✅ ¡Encontrada en la Base Geográfica!")
                if info_terreno.get('direccion'):
                    st.metric(label="Dirección", value=info_terreno['direccion'])
                if info_terreno.get('terrarfi'):
                    st.metric(label="Area Geometrica", value=info_terreno['terrarfi'])

                if info_terreno.get('geojson'):
                    geojson_data = json.loads(info_terreno['geojson'])
                    m = folium.Map(tiles="OpenStreetMap")
                    folium.GeoJson(geojson_data).add_to(m)
                    m.fit_bounds(folium.GeoJson(geojson_data).get_bounds())
                    
                    st.write("**Visualización Geográfica del Terreno:**")
                    mapa_path = "mapa_terreno.html"
                    m.save(mapa_path)
                    with open(mapa_path, "r", encoding="utf-8") as f:
                        map_html = f.read()
                    st.components.v1.html(map_html, height=500)
                    os.remove(mapa_path)

            else:
                st.warning(f"⚠️ No se encontró registro geográfico para el número predial: '{numero_predial_nacional}'.")
        else:
            st.warning("⚠️ La información catastral no contiene un 'Número Predial Nacional' para buscar.")

# --- INTERFAZ GRÁFICA Y LÓGICA PRINCIPAL ---
st.title("Asistente de Análisis Catastral 🗺️")

if 'matricula_grafo' not in st.session_state:
    st.session_state.matricula_grafo = ""
if 'matricula_analisis' not in st.session_state:
    st.session_state.matricula_analisis = ""

col_grafo, col_analisis = st.columns([2, 1])

with col_grafo:
    st.subheader("Visualizador de Grafo de Relaciones")
    matricula_input_grafo = st.text_input("Introduce la matrícula para generar el grafo:", key="input_grafo")
    if st.button("Generar Grafo Interactivo", type="primary"):
        if matricula_input_grafo:
            st.session_state.matricula_grafo = matricula_input_grafo
            st.session_state.matricula_analisis = matricula_input_grafo
        else:
            st.warning("Por favor, introduce una matrícula para generar el grafo.")

    if st.session_state.matricula_grafo:
        db_credentials = st.secrets["db_credentials"]
        with st.spinner("Generando grafo..."):
            nombre_archivo_html, mensaje, df_nodos = generar_grafo_interactivo(st.session_state.matricula_grafo, db_credentials)
        st.info(mensaje)

        if nombre_archivo_html:
            st.markdown("""
                **Leyenda:** &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#dc3545; vertical-align:middle; border:1px solid #555;"></span> Matrícula Buscada &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#28a745; vertical-align:middle; border:1px solid #555;"></span> En Base Catastral &nbsp;
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:#ffc107; vertical-align:middle; border:1px solid #555;"></span> No en Base Catastral
            """, unsafe_allow_html=True)
            st.markdown("---")
            
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=800, scrolling=True)
            os.remove(nombre_archivo_html)

            # Botón de descarga
            if not df_nodos.empty:
                csv_data = df_nodos.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar datos del grafo",
                    data=csv_data,
                    file_name=f"nodos_grafo_{st.session_state.matricula_grafo}.csv",
                    mime="text/csv",
                )

with col_analisis:
    st.subheader("Análisis Catastral y Geográfico")
    matricula_input_analisis = st.text_input("Matrícula a analizar:", value=st.session_state.matricula_analisis, key="input_analisis")
    
    if st.button("Analizar"):
        st.session_state.matricula_analisis = matricula_input_analisis

    if st.session_state.matricula_analisis:
        db_credentials = st.secrets["db_credentials"]
        mostrar_tarjeta_analisis(st.session_state.matricula_analisis, db_credentials)
    else:
        st.info("Introduce una matrícula y presiona 'Analizar'.")