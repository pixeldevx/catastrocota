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
    Función optimizada: Busca detalles para una LISTA de matrículas en una sola consulta.
    Limpia los datos de matrícula para asegurar la coincidencia.
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
    Genera un grafo donde al hacer clic en un nodo, se muestra un popup con la información catastral.
    """
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
            return None, f"⚠️ No se encontraron relaciones de parentesco para '{no_matricula_inicial}'."

        nodos_del_grafo = set(df_relaciones['padre']).union(set(df_relaciones['hija']))
        info_catastral_nodos = obtener_info_catastral_batch(nodos_del_grafo, db_params)

        g = nx.from_pandas_edgelist(df_relaciones, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            node_id = str(node["id"])
            info_nodo = info_catastral_nodos.get(node_id)
            
            # --- CORRECCIÓN CLAVE: CONSTRUIR EL CONTENIDO HTML PARA EL POPUP ---
            # Guardamos el HTML completo en un atributo 'value' personalizado del nodo
            if info_nodo:
                propietarios_html = '<br>- '.join(info_nodo['propietarios'])
                popup_content_html = (
                    f'<div style="text-align: left; font-family: sans-serif; padding: 10px; border-radius: 8px; background-color: #f8f9fa; color: #343a40; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 1px solid #dee2e6;">'
                    f'<h5 style="margin-top: 0; margin-bottom: 10px; color: #007bff; border-bottom: 1px solid #ced4da; padding-bottom: 5px;">Info Catastral</h5>'
                    f'<b>Matrícula:</b> {node_id}<br>'
                    f'<b>Predial:</b> {info_nodo["numero_predial"]}<br>'
                    f'<b>Á. Terreno:</b> {info_nodo["area_terreno"]} m²<br>'
                    f'<b>Á. Construida:</b> {info_nodo["area_construida"]} m²<br>'
                    f'<h6 style="margin-top: 10px; margin-bottom: 5px; color: #6c757d;">Propietarios:</h6><ul style="margin: 0; padding-left: 20px;"><li>{propietarios_html.replace("<br>", "</li><li>")}</li></ul>'
                    f'</div>'
                )
                # El 'title' se usa para un tooltip más simple o se deja vacío si solo queremos el popup
                node["title"] = f"Matrícula: {node_id} (Click para ver detalles)" # Un tooltip simple al pasar el ratón
                node["_popup_content"] = popup_content_html # Atributo personalizado para el contenido del popup
            else:
                node["title"] = f"Matrícula: {node_id} (Sin datos catastrales)"
                node["_popup_content"] = f'<div style="text-align: left; font-family: sans-serif; padding: 10px; border-radius: 8px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba;">' \
                                         f'<h5 style="margin-top: 0; margin-bottom: 10px; color: #856404;">Info Catastral</h5>' \
                                         f'<b>Matrícula:</b> {node_id}<br>(No encontrada en base catastral)</div>'

            if node_id == str(no_matricula_inicial).strip():
                node["color"] = "#FF0000"
                node["size"] = 40
        
        # --- OPCIONES DE RED Y JS PARA MANEJAR EL CLICK Y EL POPUP ---
        # Desactivamos el tooltip por defecto de vis.js si estamos usando un popup
        # y definimos un evento de clic para mostrar nuestro contenido HTML personalizado
        net.set_options("""
        var options = { 
            "layout": { 
                "hierarchical": { 
                    "enabled": true, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 100 
                }
            }, 
            "physics": { "enabled": false },
            "interaction": {
                "hover": true,
                "tooltipDelay": 300 // Retraso para el tooltip simple
            }
            // Los tooltips de Pyvis a veces se comportan como popups. Aseguramos que el contenido HTML esté ahí.
        };
        """)

        # Agregamos JavaScript para manejar el evento de clic y mostrar el popup.
        # Este script se inyecta directamente en el HTML final.
        js_code = """
        <script type="text/javascript">
            // Seleccionamos el elemento de la red de Pyvis
            var network_div = document.getElementById('mynetwork');
            if (network_div) {
                var network = network_div.__network__; // Accedemos al objeto network de vis.js

                network.on("click", function (params) {
                    if (params.nodes.length > 0) { // Si se hizo clic en un nodo
                        var nodeId = params.nodes[0];
                        var nodeData = network.body.data.nodes.get(nodeId);
                        
                        // Si el nodo tiene nuestro atributo de contenido de popup
                        if (nodeData && nodeData._popup_content) {
                            // Usamos el 'showPopup' interno de vis.js para mostrar el HTML
                            network.showPopup(nodeData._popup_content, params.pointer.DOM);
                        }
                    } else {
                        // Si se hizo clic fuera de un nodo, ocultamos cualquier popup existente
                        network.hidePopup();
                    }
                });
                // También ocultar popup al mover el ratón fuera del nodo
                network.on("hoverNode", function (params) {
                    // Podemos dejar el tooltip simple del 'title' para el hover,
                    // y el popup para el click, o desactivar el title aquí.
                });
                network.on("blurNode", function (params) {
                    // network.hidePopup(); // Opcional: ocultar popup al salir del nodo, si se mostró al hover
                });
            }
        </script>
        """

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        
        # Leemos el contenido HTML generado por pyvis
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inyectamos nuestro JavaScript justo antes del cierre del </body>
        html_content = html_content.replace('</body>', js_code + '</body>')

        # Guardamos el archivo modificado o lo devolvemos para Streamlit
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return nombre_archivo, f"✅ Se encontraron {len(df_relaciones)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error al generar el grafo: {e}"


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
    # --- BOTÓN RENOMBRADO ---
    analisis_clicked = st.button("Análisis Catastral")

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
            st.info("Verifica que no haya espacios en blanco o errores en el número.")
    else:
        st.warning("Por favor, introduce una matrícula para realizar el análisis.")

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