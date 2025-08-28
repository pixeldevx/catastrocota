import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os # Usaremos 'os' para manejar nombres de archivo

# --- La función que ya conoces (con pequeños ajustes) ---
# La hemos modificado para que DEVUELVA el nombre del archivo HTML en lugar de solo imprimirlo.
def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo y devuelve el nombre del archivo HTML.
    """
    # Usamos un bloque try-except para manejar cualquier error durante la ejecución
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
            # En lugar de imprimir, devolvemos un mensaje de error
            return None, f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'."

        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if str(node["id"]) == str(no_matricula_inicial):
                node["color"] = "#FF0000"
                node["size"] = 40
        
        net.set_options("""
        var options = { "physics": { "barnesHut": { "gravitationalConstant": -25000, "centralGravity": 0.1, "springLength": 150 }, "minVelocity": 0.75 } }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df)} relaciones."

    except Exception as e:
        # Si algo falla, devolvemos el error
        return None, f"❌ Ocurrió un error: {e}"

# --- INTERFAZ GRÁFICA CON STREAMLIT ---

# st.title() crea un título grande en la página web
st.title("Visor de Grafos de Matrículas 🕸️")

# st.text_input() crea una caja de texto para que el usuario escriba
# El texto que escriba el usuario se guarda en la variable 'matricula_input'
matricula_input = st.text_input("Introduce el número de matrícula inmobiliaria:", placeholder="Ej: 1037472")

# st.button() crea un botón. El código dentro del 'if' solo se ejecuta cuando se hace clic.
if st.button("Generar Grafo"):
    # Verificamos que el usuario haya escrito algo
    if matricula_input:
        # st.spinner() muestra un mensaje de "cargando..." mientras el código se ejecuta
        with st.spinner(f"🔎 Buscando familiares para la matrícula {matricula_input}..."):
            
            # ¡MANEJO DE SECRETOS! Así se accede a las credenciales de forma segura
            # Streamlit las leerá desde una configuración especial, no desde el código.
            db_credentials = st.secrets["db_credentials"]

            # Llamamos a nuestra función para que genere el grafo
            nombre_archivo_html, mensaje = generar_grafo_matricula(matricula_input, db_credentials)
        
        # Mostramos el mensaje (de éxito o error)
        st.info(mensaje)

        # Si se generó un archivo HTML...
        if nombre_archivo_html:
            # Lo abrimos, leemos su contenido y lo mostramos en pantalla
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                # st.components.v1.html() es la función mágica para mostrar HTML
                st.components.v1.html(source_code, height=820)
            
            # (Opcional) Borramos el archivo para no acumular basura en el servidor
            os.remove(nombre_archivo_html)
    else:
        # Si el usuario no escribió nada, mostramos una advertencia
        st.warning("Por favor, introduce un número de matrícula.")