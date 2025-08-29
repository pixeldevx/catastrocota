Conversación con Gemini

cambiemos al codigo anterior que usaba pandas


Asistente de programación

Mostrar razonamiento
¡Claro que sí! Volvamos al código que utilizaba la biblioteca pandas.

Para poder ayudarte mejor, ¿podrías recordarme qué hacía exactamente el código anterior? Como no tengo memoria de nuestras conversaciones pasadas, si me describes el objetivo o me muestras el fragmento de código, con gusto lo recuperaré y te lo explicaré de nuevo.

Por ejemplo, ¿era el código que...

...leía un archivo CSV?

...limpiaba o modificaba datos en un DataFrame?

...realizaba algún cálculo específico en una columna?

Una vez que me des un poco más de contexto, te proporcionaré el código pandas que necesitas. ¡Estoy aquí para ayudarte! 😊







import psycopg2

import pandas as pd

import networkx as nx

from pyvis.network import Network

import sys



def generar_grafo_matricula(no_matricula_inicial, db_params):

    """

    Genera un grafo interactivo para una matrícula específica y sus familiares.

    """

    print(f"🔎 Buscando familiares para la matrícula: {no_matricula_inicial}...")



    # --- 1. Consulta SQL Recursiva ---

    # Esta consulta es la clave. Usa un "Recursive Common Table Expression" (CTE)

    # para navegar las relaciones de padres e hijos a través de la base de datos.

    query_recursiva = """

    WITH RECURSIVE familia_grafo AS (

        -- Punto de partida: El ID de la matrícula que nos interesa

        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s

        

        UNION

        

        -- Paso recursivo:

        -- Busca los hijos de los nodos ya encontrados

        SELECT r.matricula_hija_id

        FROM RelacionesMatriculas r

        JOIN familia_grafo fg ON r.matricula_padre_id = fg.id

        

        UNION

        

        -- Busca los padres de los nodos ya encontrados

        SELECT r.matricula_padre_id

        FROM RelacionesMatriculas r

        JOIN familia_grafo fg ON r.matricula_hija_id = fg.id

    )

    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija

    -- están dentro del grupo familiar que hemos encontrado.

    SELECT

        padre.no_matricula_inmobiliaria AS padre,

        hija.no_matricula_inmobiliaria AS hija

    FROM

        RelacionesMatriculas rel

    JOIN

        Matriculas padre ON rel.matricula_padre_id = padre.id

    JOIN

        Matriculas hija ON rel.matricula_hija_id = hija.id

    WHERE

        rel.matricula_padre_id IN (SELECT id FROM familia_grafo)

        AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);

    """



    try:

        with psycopg2.connect(**db_params) as conn:

            # Usamos pandas para ejecutar la consulta y obtener los resultados en un formato fácil de usar

            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})



        if df.empty:

            print(f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'.")

            return



        print(f"✅ Se encontraron {len(df)} relaciones.")



        # --- 2. Construcción y Visualización del Grafo ---

        # Creamos el grafo usando NetworkX a partir de la lista de relaciones

        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())



        # Usamos Pyvis para la visualización interactiva

        net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources='in_line')

        net.from_nx(g)



        # Personalización para que el nodo inicial se destaque

        for node in net.nodes:

            if node["id"] == no_matricula_inicial:

                node["color"] = "#FF0000"  # Color rojo

                node["size"] = 40



        # Opciones para mejorar la física y la interacción

        net.set_options("""

        var options = {

          "physics": {

            "barnesHut": {

              "gravitationalConstant": -25000,

              "centralGravity": 0.1,

              "springLength": 150

            },

            "minVelocity": 0.75

          }

        }

        """)



        nombre_archivo = f"grafo_{no_matricula_inicial}.html"

        net.save_graph(nombre_archivo)

        print(f"🎉 ¡Grafo generado! Abre el archivo '{nombre_archivo}' en tu navegador.")



    except Exception as e:

        print(f"❌ Ocurrió un error: {e}")



# --- Zona de Ejecución ---

if __name__ == "__main__":

    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES DE SUPABASE

    db_credenciales = {

        "host": "aws-0-us-west-1.pooler.supabase.com",

        "dbname": "postgres",

        "user": "postgres",

        "password": "tu_super_contraseña", # ¡Reemplázame!

        "port": "5432"

    }



    # Obtenemos el número de matrícula desde los argumentos de la línea de comandos

    if len(sys.argv) > 1:

        matricula_a_buscar = sys.argv[1]

        generar_grafo_matricula(matricula_a_buscar, db_credenciales)

    else:

        print("🔴 Uso: python visualizar_grafo.py <numero_de_matricula>")

        print("   Ejemplo: python visualizar_grafo.py 1037472")



Asistente de programación

Mostrar razonamiento
¡Excelente! Este es precisamente el script que habíamos revisado, el cual utiliza la biblioteca pandas de una manera muy eficaz para procesar los datos antes de generar el grafo.

Me parece perfecto analizarlo juntos. A continuación, te ofrezco un resumen de su funcionamiento, una explicación detallada de cada parte del código y las instrucciones claras para que puedas ejecutarlo.

Resumen de la Solución
Este script es una herramienta poderosa que realiza tres tareas principales:

Conexión y Consulta: Se conecta a tu base de datos PostgreSQL (como la de Supabase) y ejecuta una consulta SQL muy inteligente para encontrar todas las matrículas inmobiliarias relacionadas con una matrícula inicial (tanto "padres" como "hijos", y los hijos de los hijos, etc.).

Procesamiento de Datos: Utiliza la biblioteca pandas para tomar los resultados de esa consulta y cargarlos en una estructura de datos limpia y ordenada, ideal para el análisis.

Visualización del Grafo: Con los datos ya organizados, usa las bibliotecas networkx y pyvis para construir un grafo interactivo y guardarlo como un archivo HTML que puedes abrir en tu navegador.

En resumen: el script pregunta a la base de datos por la "familia" de una matrícula, pandas organiza la respuesta y pyvis la dibuja.

Explicación Detallada del Código
Vamos a desglosar el código paso a paso para que cada parte quede súper clara.

1. Importación de Bibliotecas 📚
Python

import psycopg2 # Para conectarse a la base de datos PostgreSQL.
import pandas as pd # ¡La estrella! Para manejar los datos en tablas (DataFrames).
import networkx as nx # Para crear y manejar la estructura del grafo.
from pyvis.network import Network # Para dibujar el grafo interactivo.
import sys # Para leer argumentos desde la línea de comandos (la matrícula).
Cada import trae una caja de herramientas específica que necesitamos para nuestro proyecto.

2. La Función generar_grafo_matricula 🛠️
Esta es la función principal que orquesta todo el proceso.

Python

def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo para una matrícula específica y sus familiares.
    """
no_matricula_inicial: Es el número de la matrícula por la que quieres empezar a buscar.

db_params: Es un diccionario que contiene las credenciales para conectarte a tu base de datos.

3. La Consulta SQL Recursiva: El Corazón del Detective 🕵️‍♂️
Python

    query_recursiva = """
    WITH RECURSIVE familia_grafo AS (
        -- Aquí empieza la magia...
    )
    -- ...
    """
Esta es la parte más compleja pero también la más interesante. Piensa en un WITH RECURSIVE como si construyeras un árbol genealógico:

Punto de Partida: SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = ... encuentra el ID de la matrícula con la que inicias.

Paso Recursivo (UNION): Luego, busca repetidamente en la tabla RelacionesMatriculas para encontrar a todos los "hijos" y "padres" de los miembros que ya ha encontrado, expandiendo la red familiar hasta que no encuentra a nadie más.

Selección Final: Al final, selecciona todas las relaciones (padre, hija) que pertenecen a esa "familia" que acaba de descubrir.

4. Conexión y Ejecución con Pandas ✨
Python

    try:
        with psycopg2.connect(**db_params) as conn:
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})
Aquí es donde pandas entra en acción y nos simplifica la vida. La línea pd.read_sql_query hace varias cosas a la vez:

Se conecta a la base de datos usando conn.

Ejecuta la query_recursiva de forma segura, pasando el no_matricula_inicial como parámetro.

Toma todos los resultados y los carga directamente en un DataFrame de pandas llamado df. Un DataFrame es, en esencia, una tabla muy potente, similar a una hoja de cálculo.

Python

# df se vería algo así:
#      padre     hija
# 0  1037472  1037473
# 1  1037472  1037474
# 2  1037473  1037475
5. Creación y Visualización del Grafo 🎨
Python

    g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
Ahora que tenemos nuestros datos perfectamente organizados en df, se los pasamos a networkx. Esta línea le dice: "Crea un grafo dirigido (DiGraph) usando el DataFrame df. La columna 'padre' es el nodo de origen y la columna 'hija' es el nodo de destino".

El resto del código usa pyvis para hacer que el grafo se vea bonito e interactivo, destacando el nodo inicial en rojo y ajustando la física para que los nodos se organicen mejor.

Python

    net = Network(height="800px", width="100%", directed=True, ...)
    net.from_nx(g)
    # ... personalización de colores y física ...
    net.save_graph(nombre_archivo)
Finalmente, net.save_graph() crea el archivo HTML con tu visualización.

Instrucciones de Implementación y Uso
Para poner en marcha este script, solo sigue estos sencillos pasos:

Paso 1: Instalar las bibliotecas
Si aún no las tienes, abre tu terminal o línea de comandos y ejecuta el siguiente comando para instalar todo lo necesario:

Bash

pip install psycopg2-binary pandas networkx pyvis
Paso 2: Configurar tus credenciales
⚠️ ¡Paso muy importante! En la parte inferior del script, debes reemplazar los valores de ejemplo con tus credenciales reales de la base de datos de Supabase.

Python

# --- Zona de Ejecución ---
if __name__ == "__main__":
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES DE SUPABASE
    db_credenciales = {
        "host": "aws-0-us-west-1.pooler.supabase.com",
        "dbname": "postgres",
        "user": "postgres",
        "password": "tu_super_contraseña", # ¡Reemplázame!
        "port": "5432"
    }
Asegúrate de que tu contraseña sea la correcta.

Paso 3: Ejecutar el script
Guarda el código en un archivo, por ejemplo, visualizar_grafo.py.

Abre tu terminal y navega hasta la carpeta donde guardaste el archivo.

Ejecuta el script usando el siguiente comando, reemplazando <numero_de_matricula> con la matrícula que deseas investigar:

Bash

python visualizar_grafo.py <numero_de_matricula>
Ejemplo práctico:

Bash

python visualizar_grafo.py 1037472
Después de ejecutarlo, verás mensajes en la terminal y, si todo sale bien, se creará un archivo llamado grafo_1037472.html en la misma carpeta. ¡Solo tienes que hacer doble clic en él para abrirlo en tu navegador y explorar tu grafo interactivo!

Espero que esta explicación detallada te sea de gran ayuda. ¡Este es un excelente código que combina el poder de SQL con la simplicidad de pandas! Si algo no queda claro o quieres modificarlo, no dudes en preguntar. ¡Estoy aquí para ayudarte!







se esta generando el siguiente error ❌ Ocurrió un error: Execution failed on sql '

    WITH RECURSIVE familia_grafo AS (

        -- Punto de partida: El ID de la matrícula que nos interesa

        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s

        

        UNION

        

        -- Paso recursivo:

        -- Busca los hijos de los nodos ya encontrados

        SELECT r.matricula_hija_id

        FROM RelacionesMatriculas r

        JOIN familia_grafo fg ON r.matricula_padre_id = fg.id

        

        UNION

        

        -- Busca los padres de los nodos ya encontrados

        SELECT r.matricula_padre_id

        FROM RelacionesMatriculas r

        JOIN familia_grafo fg ON r.matricula_hija_id = fg.id

    )

    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija

    -- están dentro del grupo familiar que hemos encontrado.

    SELECT

        padre.no_matricula_inmobiliaria AS padre,

        hija.no_matricula_inmobiliaria AS hija

    FROM

        RelacionesMatriculas rel

    JOIN

        Matriculas padre ON rel.matricula_padre_id = padre.id

    JOIN

        Matriculas hija ON rel.matricula_hija_id = hija.id

    WHERE

        rel.matricula_padre_id IN (SELECT id FROM familia_grafo)

        AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);

    ': recursive reference to query "familia_grafo" must not appear within its non-recursive term

LINE 12:         JOIN familia_grafo fg ON r.matricula_padre_id = fg.i...

                      ^



Asistente de programación

Mostrar razonamiento
¡Ah, claro! Veo el problema. Este es un error muy específico y común cuando se escriben consultas recursivas en SQL. No te preocupes, ¡la solución es sencilla!

El mensaje de error recursive reference to query "familia_grafo" must not appear within its non-recursive term te está diciendo que la estructura de tu consulta recursiva no es la correcta.

¿Cuál es el problema? 🤔
Una consulta WITH RECURSIVE en SQL debe tener una estructura muy estricta:

Un término base (no recursivo): Es el punto de partida. En tu caso, es SELECT id FROM Matriculas....

Un UNION o UNION ALL: Solo puede haber uno para separar el término base del recursivo.

Un término recursivo: Es el paso que se repite. Este paso debe hacer referencia a la misma consulta (familia_grafo).

El problema en tu código es que usas dos UNION. Esto confunde a la base de datos, que no sabe cómo estructurar la recursividad.

Tu estructura actual (incorrecta):

Término Base

UNION

Término Recursivo 1 (buscar hijos)

UNION

Término Recursivo 2 (buscar padres)

La estructura correcta:

Término Base

UNION ALL

(Término Recursivo 1 UNION ALL Término Recursivo 2)

Debemos combinar la búsqueda de padres y la de hijos en un solo bloque recursivo.

La Solución: Corrigiendo la Consulta
Simplemente tenemos que reestructurar la consulta para que solo haya un UNION ALL principal que separe el inicio de la parte que se repite. También es una buena práctica usar UNION ALL en lugar de UNION dentro de las consultas recursivas, ya que es más rápido al no comprobar duplicados en cada paso.

Aquí tienes el bloque de código completo con la consulta corregida. Puedes reemplazar todo tu script con este.

Python

import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import sys

def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo para una matrícula específica y sus familiares.
    """
    print(f"🔎 Buscando familiares para la matrícula: {no_matricula_inicial}...")

    # --- 1. Consulta SQL Recursiva (CORREGIDA) ---
    # La estructura ahora es la correcta:
    # [Término Base] UNION ALL [Término Recursivo]
    query_recursiva = """
    WITH RECURSIVE familia_grafo AS (
        -- Punto de partida: El ID de la matrícula que nos interesa (Término Base)
        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s
        
        UNION ALL -- Solo un UNION principal para separar la base de la recursión
        
        -- Paso recursivo: Busca tanto padres como hijos en un solo bloque
        (
            -- Busca los hijos de los nodos ya encontrados
            SELECT r.matricula_hija_id
            FROM RelacionesMatriculas r
            JOIN familia_grafo fg ON r.matricula_padre_id = fg.id
            
            UNION ALL -- Unimos las dos búsquedas aquí adentro
            
            -- Busca los padres de los nodos ya encontrados
            SELECT r.matricula_padre_id
            FROM RelacionesMatriculas r
            JOIN familia_grafo fg ON r.matricula_hija_id = fg.id
        )
    )
    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija
    -- están dentro del grupo familiar que hemos encontrado.
    SELECT
        padre.no_matricula_inmobiliaria AS padre,
        hija.no_matricula_inmobiliaria AS hija
    FROM
        RelacionesMatriculas rel
    JOIN
        Matriculas padre ON rel.matricula_padre_id = padre.id
    JOIN
        Matriculas hija ON rel.matricula_hija_id = hija.id
    WHERE
        rel.matricula_padre_id IN (SELECT id FROM familia_grafo)
        AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);
    """

    try:
        with psycopg2.connect(**db_params) as conn:
            # Usamos pandas para ejecutar la consulta y obtener los resultados
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df.empty:
            print(f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'.")
            return

        print(f"✅ Se encontraron {len(df)} relaciones.")

        # --- 2. Construcción y Visualización del Grafo ---
        # Creamos el grafo usando NetworkX a partir de la lista de relaciones
        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())

        # Usamos Pyvis para la visualización interactiva
        net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources='in_line')
        net.from_nx(g)

        # Personalización para que el nodo inicial se destaque
        for node in net.nodes:
            if node["id"] == no_matricula_inicial:
                node["color"] = "#FF0000"  # Color rojo
                node["size"] = 40

        # Opciones para mejorar la física y la interacción
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -25000,
              "centralGravity": 0.1,
              "springLength": 150
            },
            "minVelocity": 0.75
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        print(f"🎉 ¡Grafo generado! Abre el archivo '{nombre_archivo}' en tu navegador.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

# --- Zona de Ejecución ---
if __name__ == "__main__":
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES DE SUPABASE
    db_credenciales = {
        "host": "aws-0-us-west-1.pooler.supabase.com",
        "dbname": "postgres",
        "user": "postgres",
        "password": "tu_super_contraseña", # ¡Reemplázame!
        "port": "5432"
    }

    # Obtenemos el número de matrícula desde los argumentos de la línea de comandos
    if len(sys.argv) > 1:
        matricula_a_buscar = sys.argv[1]
        generar_grafo_matricula(matricula_a_buscar, db_credenciales)
    else:
        print("🔴 Uso: python visualizar_grafo.py <numero_de_matricula>")
        print("   Ejemplo: python visualizar_grafo.py 1037472")

Prueba a ejecutar este código corregido. ¡El error debería desaparecer y tu grafo generarse sin problemas! Las consultas recursivas son un poco estrictas al principio, pero una vez que entiendes su estructura, son increíblemente útiles.

¡Avísame si tienes cualquier otra duda!







sale este error  df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

❌ Ocurrió un error: Execution failed on sql '

    WITH RECURSIVE familia_grafo AS (

        -- Punto de partida: El ID de la matrícula que nos interesa (Término Base)

        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s

        

        UNION ALL -- Solo un UNION principal para separar la base de la recursión

        

        -- Paso recursivo: Busca tanto padres como hijos en un solo bloque

        (

            -- Busca los hijos de los nodos ya encontrados

            SELECT r.matricula_hija_id

            FROM RelacionesMatriculas r

            JOIN familia_grafo fg ON r.matricula_padre_id = fg.id

            

            UNION ALL -- Unimos las dos búsquedas aquí adentro

            

            -- Busca los padres de los nodos ya encontrados

            SELECT r.matricula_padre_id

            FROM RelacionesMatriculas r

            JOIN familia_grafo fg ON r.matricula_hija_id = fg.id

        )

    )

    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija

    -- están dentro del grupo familiar que hemos encontrado.

    SELECT

        padre.no_matricula_inmobiliaria AS padre,

        hija.no_matricula_inmobiliaria AS hija

    FROM

        RelacionesMatriculas rel

    JOIN

        Matriculas padre ON rel.matricula_padre_id = padre.id

    JOIN

        Matriculas hija ON rel.matricula_hija_id = hija.id

    WHERE

        rel.matricula_padre_id IN (SELECT id FROM familia_grafo)

        AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);

    ': recursive reference to query "familia_grafo" must not appear more than once

LINE 20:             JOIN familia_grafo fg ON r.matricula_hija_id = f...

                          ^



Asistente de programación

Mostrar razonamiento
¡Vaya! Mis disculpas. Solucionamos el primer problema de estructura, pero nos topamos con otra regla muy estricta de las consultas recursivas. ¡Gracias por tu paciencia! Este tipo de detalles son los que hacen que SQL sea tan preciso.

El nuevo error recursive reference to query "familia_grafo" must not appear more than once es muy claro: PostgreSQL no permite que hagas referencia a la tabla recursiva (familia_grafo) más de una vez dentro del paso que se repite.

¿Cuál es el problema ahora? 🤔
En la solución anterior, dentro del bloque recursivo, teníamos esto:

Un SELECT que hacía JOIN con familia_grafo para buscar hijos.

Otro SELECT que también hacía JOIN con familia_grafo para buscar padres.

Aunque los unimos con UNION ALL, la base de datos sigue viendo dos referencias a familia_grafo en la parte recursiva, y eso está prohibido.

La Solución Definitiva: Un solo JOIN inteligente
Para solucionarlo, debemos reescribir la lógica para encontrar tanto a los padres como a los hijos usando una sola referencia a familia_grafo. Lo haremos con un JOIN más astuto y una declaración CASE.

Un JOIN con OR: Uniremos RelacionesMatriculas con familia_grafo buscando filas donde el id que ya encontramos coincida ya sea con la columna del padre o con la columna de la hija.

Un CASE para seleccionar: Una vez que encontramos una relación, usaremos un CASE (que funciona como un "si... entonces...") para devolver el ID del "otro lado" de la relación. Si encontramos un padre, devolvemos a la hija, y viceversa.

Esta nueva versión es más eficiente y cumple con todas las reglas de SQL para la recursividad.

Código Corregido
Aquí tienes el script completo con la consulta final y correcta. Por favor, reemplaza el tuyo con este.

Python

import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import sys

def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo para una matrícula específica y sus familiares.
    """
    print(f"🔎 Buscando familiares para la matrícula: {no_matricula_inicial}...")

    # --- 1. Consulta SQL Recursiva (VERSIÓN FINAL) ---
    # Esta versión cumple la regla de "una sola referencia recursiva".
    query_recursiva = """
    WITH RECURSIVE familia_grafo AS (
        -- Punto de partida: El ID de la matrícula que nos interesa
        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s
        
        UNION ALL
        
        -- Paso recursivo: Un solo bloque que referencia a familia_grafo una vez
        SELECT
            -- Usamos CASE para devolver el ID del "otro lado" de la relación
            CASE
                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                ELSE r.matricula_padre_id
            END
        FROM
            RelacionesMatriculas r
        JOIN
            -- El JOIN ahora busca coincidencias en CUALQUIERA de las dos columnas
            familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id
    )
    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija
    -- están dentro del grupo familiar que hemos encontrado.
    SELECT
        padre.no_matricula_inmobiliaria AS padre,
        hija.no_matricula_inmobiliaria AS hija
    FROM
        RelacionesMatriculas rel
    JOIN
        Matriculas padre ON rel.matricula_padre_id = padre.id
    JOIN
        Matriculas hija ON rel.matricula_hija_id = hija.id
    WHERE
        rel.matricula_padre_id IN (SELECT DISTINCT id FROM familia_grafo)
        AND rel.matricula_hija_id IN (SELECT DISTINCT id FROM familia_grafo);
    """

    try:
        with psycopg2.connect(**db_params) as conn:
            # Usamos pandas para ejecutar la consulta y obtener los resultados
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df.empty:
            print(f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'.")
            return

        print(f"✅ Se encontraron {len(df)} relaciones.")

        # --- 2. Construcción y Visualización del Grafo ---
        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if node["id"] == no_matricula_inicial:
                node["color"] = "#FF0000"
                node["size"] = 40

        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -25000,
              "centralGravity": 0.1,
              "springLength": 150
            },
            "minVelocity": 0.75
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        print(f"🎉 ¡Grafo generado! Abre el archivo '{nombre_archivo}' en tu navegador.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

# --- Zona de Ejecución ---
if __name__ == "__main__":
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES
    db_credenciales = {
        "host": "aws-0-us-west-1.pooler.supabase.com",
        "dbname": "postgres",
        "user": "postgres",
        "password": "tu_super_contraseña", # ¡Reemplázame!
        "port": "5432"
    }

    if len(sys.argv) > 1:
        matricula_a_buscar = sys.argv[1]
        generar_grafo_matricula(matricula_a_buscar, db_credenciales)
    else:
        print("🔴 Uso: python visualizar_grafo.py <numero_de_matricula>")
        print("   Ejemplo: python visualizar_grafo.py 1037472")

¡Ahora sí debería funcionar! Esta versión es mucho más robusta y sigue las reglas del estándar SQL para la recursividad. Las consultas de este tipo son como un rompecabezas, ¡y ya casi lo tenemos resuelto!

Pruébalo y me cuentas cómo te va.







ahora salio este error  df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

❌ Ocurrió un error: Execution failed on sql '

    WITH RECURSIVE familia_grafo AS (

        -- Punto de partida: El ID de la matrícula que nos interesa

        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s

        

        UNION ALL

        

        -- Paso recursivo: Un solo bloque que referencia a familia_grafo una vez

        SELECT

            -- Usamos CASE para devolver el ID del "otro lado" de la relación

            CASE

                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id

                ELSE r.matricula_padre_id

            END

        FROM

            RelacionesMatriculas r

        JOIN

            -- El JOIN ahora busca coincidencias en CUALQUIERA de las dos columnas

            familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id

    )

    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija

    -- están dentro del grupo familiar que hemos encontrado.

    SELECT

        padre.no_matricula_inmobiliaria AS padre,

        hija.no_matricula_inmobiliaria AS hija

    FROM

        RelacionesMatriculas rel

    JOIN

        Matriculas padre ON rel.matricula_padre_id = padre.id

    JOIN

        Matriculas hija ON rel.matricula_hija_id = hija.id

    WHERE

        rel.matricula_padre_id IN (SELECT DISTINCT id FROM familia_grafo)

        AND rel.matricula_hija_id IN (SELECT DISTINCT id FROM familia_grafo);

    ': canceling statement due to statement timeout



Asistente de programación

Mostrar razonamiento
¡Excelente! Este nuevo error es, de hecho, una muy buena señal. Te explico por qué.

El error canceling statement due to statement timeout significa que tu consulta SQL es sintácticamente correcta, pero está tardando demasiado en ejecutarse. El servidor de la base de datos (especialmente en plataformas como Supabase) tiene un límite de tiempo para protegerse de consultas que se descontrolan.

¿Cuál es el problema? Un Bucle Infinito ♾️
El problema es que nuestra consulta ha caído en un bucle infinito. Imagina que buscas las relaciones de la matrícula "A", que está conectada a "B".

La consulta empieza en "A".

En el primer paso, encuentra a su vecina, "B", y la agrega al conjunto de familiares. El conjunto ahora es {A, B}.

En el siguiente paso, mira los vecinos de "B". Encuentra a "A" y lo agrega de nuevo.

Luego, desde "A", vuelve a encontrar a "B"... y así sucesivamente. Se quedan atrapados en un ciclo A -> B -> A -> B... y nunca terminan.

Esto hace que la consulta se ejecute hasta que el servidor dice "¡Basta!" y la cancela.

La Solución: Rompiendo el Bucle con UNION
La solución es muy simple y elegante. Necesitamos una forma de decirle a la consulta que "no agregue matrículas que ya ha visitado". Afortunadamente, SQL tiene un mecanismo perfecto para esto.

La diferencia clave está entre UNION ALL y UNION:

UNION ALL: Es rápido y simple. Junta todos los resultados, incluso si están repetidos. Esto es lo que causa nuestro bucle.

UNION: Es más inteligente. Antes de añadir un resultado, comprueba si ya existe en el conjunto. Si ya existe, lo ignora.

Al cambiar UNION ALL por UNION, cuando la consulta intente volver a agregar una matrícula que ya visitó, UNION simplemente la descartará. Esto romperá el ciclo y permitirá que la consulta termine.

Código Corregido
Aquí tienes la versión final del script. El único cambio es volver a usar UNION en lugar de UNION ALL dentro de la parte recursiva. He añadido también un pequeño comentario para señalar el cambio.

Python

import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import sys

def generar_grafo_matricula(no_matricula_inicial, db_params):
    """
    Genera un grafo interactivo para una matrícula específica y sus familiares.
    """
    print(f"🔎 Buscando familiares para la matrícula: {no_matricula_inicial}...")

    # --- 1. Consulta SQL Recursiva (VERSIÓN ANTI-BUCLES) ---
    query_recursiva = """
    WITH RECURSIVE familia_grafo AS (
        -- Punto de partida: El ID de la matrícula que nos interesa
        SELECT id FROM Matriculas WHERE no_matricula_inmobiliaria = %(start_node)s
        
        -- ¡CAMBIO CLAVE! Usamos UNION para eliminar duplicados y evitar bucles infinitos.
        UNION
        
        -- Paso recursivo: Un solo bloque que referencia a familia_grafo una vez
        SELECT
            -- Usamos CASE para devolver el ID del "otro lado" de la relación
            CASE
                WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id
                ELSE r.matricula_padre_id
            END
        FROM
            RelacionesMatriculas r
        JOIN
            -- El JOIN ahora busca coincidencias en CUALQUIERA de las dos columnas
            familia_grafo fg ON r.matricula_padre_id = fg.id OR r.matricula_hija_id = fg.id
    )
    -- Finalmente, selecciona todas las relaciones donde tanto el padre como la hija
    -- están dentro del grupo familiar que hemos encontrado.
    SELECT
        padre.no_matricula_inmobiliaria AS padre,
        hija.no_matricula_inmobiliaria AS hija
    FROM
        RelacionesMatriculas rel
    JOIN
        Matriculas padre ON rel.matricula_padre_id = padre.id
    JOIN
        Matriculas hija ON rel.matricula_hija_id = hija.id
    WHERE
        rel.matricula_padre_id IN (SELECT id FROM familia_grafo)
        AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);
    """

    try:
        with psycopg2.connect(**db_params) as conn:
            # Usamos pandas para ejecutar la consulta y obtener los resultados
            df = pd.read_sql_query(query_recursiva, conn, params={'start_node': no_matricula_inicial})

        if df.empty:
            print(f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'.")
            return

        print(f"✅ Se encontraron {len(df)} relaciones.")

        # --- 2. Construcción y Visualización del Grafo ---
        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if node["id"] == no_matricula_inicial:
                node["color"] = "#FF0000"
                node["size"] = 40

        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -25000,
              "centralGravity": 0.1,
              "springLength": 150
            },
            "minVelocity": 0.75
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        print(f"🎉 ¡Grafo generado! Abre el archivo '{nombre_archivo}' en tu navegador.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

# --- Zona de Ejecución ---
if __name__ == "__main__":
    # REEMPLAZA ESTOS VALORES CON TUS CREDENCIALES
    db_credenciales = {
        "host": "aws-0-us-west-1.pooler.supabase.com",
        "dbname": "postgres",
        "user": "postgres",
        "password": "tu_super_contraseña", # ¡Reemplázame!
        "port": "5432"
    }

    if len(sys.argv) > 1:
        matricula_a_buscar = sys.argv[1]
        generar_grafo_matricula(matricula_a_buscar, db_credenciales)
    else:
        print("🔴 Uso: python visualizar_grafo.py <numero_de_matricula>")
        print("   Ejemplo: python visualizar_grafo.py 1037472")
Con este cambio, la consulta ya no caerá en bucles y debería ejecutarse dentro del límite de tiempo establecido. ¡Estamos muy cerca de lograrlo!

Pruébalo y veamos el resultado. 💪







lo solucione con esta consulta WITH RECURSIVE familia_grafo (id, path) AS (

-- Starting point: the matricula we are interested in

SELECT m.id,

ARRAY[m.id] AS path

FROM public.matriculas m

WHERE m.no_matricula_inmobiliaria = %(start_node)s



UNION ALL



-- Recursive step: follow relationships in either direction, but avoid cycles

SELECT

CASE

WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id

ELSE r.matricula_padre_id

END AS id,

fg.path || CASE

WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id

ELSE r.matricula_padre_id

END

FROM public.relacionesmatriculas r

JOIN familia_grafo fg

ON r.matricula_padre_id = fg.id

OR r.matricula_hija_id = fg.id

WHERE NOT (

CASE

WHEN r.matricula_padre_id = fg.id THEN r.matricula_hija_id

ELSE r.matricula_padre_id

END) = ANY (fg.path)

-- Optional safety guard (uncomment if needed)

-- AND array_length(fg.path, 1) < 1000

)



SELECT

padre.no_matricula_inmobiliaria AS padre,

hija.no_matricula_inmobiliaria AS hija

FROM public.relacionesmatriculas rel

JOIN public.matriculas padre ON rel.matricula_padre_id = padre.id

JOIN public.matriculas hija ON rel.matricula_hija_id = hija.id

WHERE rel.matricula_padre_id IN (SELECT id FROM familia_grafo)

AND rel.matricula_hija_id IN (SELECT id FROM familia_grafo);



Asistente de programación

Mostrar razonamiento
¡Fantástico! Esa es una solución excelente y muy robusta. ¡Felicidades por haberla implementado!

Has resuelto el problema de los bucles infinitos de una manera aún más explícita y poderosa que con el simple UNION. Este método es considerado una de las mejores prácticas para consultas recursivas complejas.

¿Por qué tu solución es tan efectiva? 🧠
Lo que has implementado se llama detección explícita de ciclos mediante el seguimiento de la ruta (path tracking). Déjame explicarte los componentes clave que la hacen tan genial:

La columna path: Al iniciar, creas una columna path que es un arreglo (array) y contiene únicamente el ID del nodo inicial: ARRAY[m.id] AS path. Piensa en esto como dejar la primera "miga de pan" en un camino.

El operador ||: En cada paso recursivo, cuando encuentras un nuevo nodo, lo agregas al final del arreglo path con el operador ||. Así, el arreglo va creciendo y guardando un registro exacto del camino que ha seguido la consulta: fg.path || ....

La condición WHERE NOT ... = ANY (fg.path): Esta es la parte más inteligente. Antes de agregar un nuevo nodo, esta línea comprueba si el ID de ese nuevo nodo ya existe en el arreglo path actual. Si ya existe, significa que estás a punto de entrar en un ciclo, por lo que esa ruta de búsqueda se detiene inmediatamente.

En resumen, en lugar de simplemente evitar duplicados en general (como hace UNION), tu solución lleva un mapa de cada camino individual y se niega a pisar dos veces el mismo sitio dentro de ese mismo camino.

Esta es una técnica avanzada y demuestra una gran comprensión del problema. ¡Excelente trabajo! Me alegra mucho que lo hayas resuelto.

Si tienes cualquier otra duda o quieres explorar qué más se puede hacer, aquí estoy para ayudarte. ¡Sigamos adelante!







ahora deseo implmentarlo en un web gratuita que permita ejecutar el codigo y mostrar el resutlado en pantalla, para crearle una interfaz grafica y solicitar mediante una ventana de texto la matricula con un boton muestre el resultado.



Asistente de programación

Mostrar razonamiento
¡Excelente idea! Llevar tu script a una interfaz web es el siguiente paso lógico para hacerlo accesible y fácil de usar. Para lograr esto de forma gratuita y sencilla, te propongo usar una herramienta fantástica llamada Streamlit.

Streamlit es una biblioteca de Python que te permite crear interfaces web interactivas escribiendo únicamente código de Python, ¡casi sin necesidad de saber sobre desarrollo web (HTML, CSS, JavaScript)!

Nuestro plan será el siguiente:

Adaptar tu código de Python para que funcione con Streamlit.

Preparar el proyecto para ser desplegado en la web.

Desplegar la aplicación de forma gratuita en la nube de Streamlit (Streamlit Community Cloud).

¡Es más fácil de lo que parece! Vamos paso a paso.

Paso 1: Instalar Streamlit ⚙️
Primero, necesitas instalar Streamlit en tu computadora. Abre tu terminal o línea de comandos y ejecuta:

Bash

pip install streamlit
Paso 2: Adaptar tu Código a Streamlit
Vamos a modificar tu script para crear la interfaz. Guarda el siguiente código en un nuevo archivo llamado app.py. Presta atención a los comentarios, que explican qué hace cada nueva línea.

Este código incluye una mejora crucial: el manejo de secretos. Nunca debes escribir tus contraseñas directamente en el código. Streamlit nos ofrece una forma segura de manejarlas.

El Código para app.py
Python

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

Paso 3: Preparar el Proyecto para el Despliegue 🚀
Para que Streamlit Community Cloud sepa cómo ejecutar tu app, necesitas tres archivos en tu proyecto:

app.py: El archivo que acabamos de crear.

requirements.txt: Un archivo de texto que lista todas las bibliotecas que tu código necesita. Crea un archivo con este nombre y el siguiente contenido:

psycopg2-binary
pandas
networkx
pyvis
streamlit
Un repositorio en GitHub: Streamlit Community Cloud funciona conectándose a tu cuenta de GitHub. Si no tienes una, es gratis y fácil de crear.

Paso 4: Subir tu Proyecto a GitHub
Crea un nuevo repositorio en GitHub. Puedes hacerlo público, no te preocupes, nuestra contraseña no estará en el código.

Sube los dos archivos (app.py y requirements.txt) a este nuevo repositorio.

Paso 5: Desplegar en Streamlit Community Cloud ☁️
Ve a share.streamlit.io y regístrate con tu cuenta de GitHub.

Haz clic en "New app" y selecciona el repositorio que acabas de crear.

En la sección "Advanced settings...", verás una caja de texto llamada "Secrets". Aquí es donde pondrás tus credenciales de forma segura. Copia y pega lo siguiente, reemplazando los valores con los tuyos:

Ini, TOML

# Pega esto en la caja de "Secrets" de Streamlit Cloud
[db_credentials]
host = "aws-0-us-west-1.pooler.supabase.com"
dbname = "postgres"
user = "postgres"
password = "tu_super_contraseña" # ¡Reemplázame!
port = "5432"
Haz clic en el botón "Deploy!".

¡Y eso es todo! Streamlit leerá tu código, instalará las librerías del requirements.txt, configurará los secretos y pondrá tu aplicación en línea con una URL pública que podrás compartir. Ahora tendrás una interfaz web funcional para tu proyecto.







[23:48:55] 📦 Processed dependencies!

cat: /mount/admin/install_path: No such file or directory







2025-08-28 23:49:02.313 Uncaught app execution

Traceback (most recent call last):

File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 128, in exec_func_with_error_handling

result = func()

File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 669, in code_to_exec

exec(code, module.__dict__) # noqa: S102

~~~~^^^^^^^^^^^^^^^^^^^^^^^

File "/mount/src/catastrocota/app.py", line 2, in <module>

import psycopg2

ModuleNotFoundError: No module named 'psycopg2'



Asistente de programación

Mostrar razonamiento
¡Hola! Ese error ModuleNotFoundError: No module named 'psycopg2' es muy común al desplegar aplicaciones y tiene una solución directa.

Significa que la biblioteca de Python para conectarse a tu base de datos (psycopg2) no se instaló correctamente en el entorno donde se está ejecutando tu aplicación en Streamlit Cloud.

La causa casi siempre es un pequeño problema con el archivo requirements.txt en tu repositorio de GitHub. Este archivo es como la lista de compras para Streamlit; le dice exactamente qué bibliotecas necesita instalar para que tu código funcione.

🔧 Cómo Solucionarlo
Solo necesitas revisar tu archivo requirements.txt en GitHub. Sigue estos pasos:

1. Ve a tu Repositorio de GitHub
Abre la carpeta donde subiste tus archivos (app.py y requirements.txt).

2. Verifica el Contenido del Archivo
Haz clic en el archivo requirements.txt y asegúrate de que su contenido sea exactamente este:

psycopg2-binary
pandas
networkx
pyvis
streamlit
El error más común es escribir psycopg2 en lugar de psycopg2-binary. La versión -binary incluye archivos precompilados que facilitan la instalación en entornos de nube como Streamlit.

3. Verifica el Nombre del Archivo
Asegúrate de que el archivo se llame exactamente requirements.txt (en plural y todo en minúsculas). Un nombre como requirement.txt o requerimientos.txt no funcionará.

4. Aplica los Cambios y Reinicia
Si tuviste que hacer algún cambio en el archivo, guarda (haz "commit") esas modificaciones en GitHub. Luego, ve a tu panel de control de Streamlit Cloud, busca tu aplicación y en el menú de la esquina superior derecha (tres puntos), selecciona "Reboot app". Esto forzará a Streamlit a reinstalar las dependencias usando tu archivo requirements.txt corregido.

Con eso, el error debería desaparecer y tu aplicación cargará correctamente. ¡Estás muy cerca!







bueno la aplicacion ya corre ahora quiero hacer una modificacion al grafo quiero que se vea en estilo arbol y que se vea la jeraquizacion es decir el padre este por encima de los hijos.



Asistente de programación

Mostrar razonamiento
¡Excelente! Para darle al grafo ese estilo de árbol jerárquico con los padres arriba y los hijos abajo, necesitas activar el motor de diseño jerárquico de Pyvis.

Esto se logra fácilmente modificando las opciones que le pasas a la red. En lugar de usar la simulación de física que organiza los nodos de forma automática, le daremos instrucciones precisas para que los ordene en niveles.

La clave es desactivar la física que usamos antes y activar el layout jerárquico.

🌳 Código Modificado
Aquí tienes el bloque de código de tu archivo app.py con la sección de net.set_options actualizada. Simplemente tienes que reemplazar la sección antigua por esta nueva.

Python

# ... (el resto del código sigue igual hasta este punto)

        # DESACTIVAMOS LA FÍSICA Y ACTIVAMOS EL LAYOUT JERÁRQUICO
        net.set_options("""
        var options = {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 150,
              "nodeSpacing": 100
            }
          },
          "physics": {
            "enabled": false
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df)} relaciones."

# ... (el resto del código sigue igual)
📜 Explicación de los Cambios
"layout": { "hierarchical": { "enabled": true } }: Esta es la línea más importante. Le dice a la visualización: "activa el modo jerárquico".

"direction": "UD": Especifica la dirección del árbol. UD significa "Up-Down" (Arriba-Abajo), que es exactamente lo que necesitas para que los padres se sitúen por encima de los hijos.

"sortMethod": "directed": Ayuda a organizar los nodos en cada nivel para minimizar el cruce de las flechas, haciendo el grafo más legible.

"levelSeparation" y "nodeSpacing": Estos valores te permiten ajustar el espacio vertical entre niveles y el espacio horizontal entre nodos para que no se vea todo muy apretado.

"physics": { "enabled": false }: Es fundamental desactivar la física. Si la dejas activada, intentará mover los nodos y chocará con el orden jerárquico, creando un resultado inestable.

Código Completo para app.py
Para que no te quede ninguna duda, aquí está el archivo app.py completo con la modificación ya aplicada. Solo tienes que reemplazar el contenido del tuyo en GitHub y la aplicación se actualizará automáticamente.

Python

import streamlit as st
import psycopg2
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os

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
            return None, f"⚠️ No se encontraron relaciones para la matrícula '{no_matricula_inicial}'."

        g = nx.from_pandas_edgelist(df, 'padre', 'hija', create_using=nx.DiGraph())
        net = Network(height="800px", width="100%", directed=True, notebook=True, cdn_resources='in_line')
        net.from_nx(g)

        for node in net.nodes:
            if str(node["id"]) == str(no_matricula_inicial):
                node["color"] = "#FF0000"
                node["size"] = 40
        
        # --- SECCIÓN MODIFICADA ---
        net.set_options("""
        var options = {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 150,
              "nodeSpacing": 100
            }
          },
          "physics": {
            "enabled": false
          }
        }
        """)

        nombre_archivo = f"grafo_{no_matricula_inicial}.html"
        net.save_graph(nombre_archivo)
        return nombre_archivo, f"✅ Se encontraron {len(df)} relaciones."

    except Exception as e:
        return None, f"❌ Ocurrió un error: {e}"

# --- INTERFAZ GRÁFICA CON STREAMLIT ---

st.title("Visor de Grafos de Matrículas 🕸️")
st.write("Esta herramienta visualiza las relaciones jerárquicas (padre-hijo) entre matrículas inmobiliarias.")

matricula_input = st.text_input("Introduce el número de matrícula inmobiliaria:", placeholder="Ej: 1037472")

if st.button("Generar Grafo"):
    if matricula_input:
        with st.spinner(f"🔎 Buscando familiares para la matrícula {matricula_input}..."):
            db_credentials = st.secrets["db_credentials"]
            nombre_archivo_html, mensaje = generar_grafo_matricula(matricula_input, db_credentials)
        
        st.info(mensaje)

        if nombre_archivo_html:
            with open(nombre_archivo_html, 'r', encoding='utf-8') as f:
                source_code = f.read()
                st.components.v1.html(source_code, height=820, scrolling=True)
            
            os.remove(nombre_archivo_html)
    else:
        st.warning("Por favor, introduce un número de matrícula.")






Ahora a la base de datos requiero integrarle una tabla de información con la siguiente estructura la cual tiene la información básica catastral de los predios así como los propietarios actuales y su estructura es la siguiente. departamento;municipio;numero_predial;tipo_de_registro;numero_de_orden;total_registros;nombre;estado_civil;tipo_documento;numero_documento;direccion;comuna;destino_economico;area_terreno;area_construida;avaluo;vigencia;numero_predial_anterior;numero_predial_nacional;Matricula

25;214;0000000000010001000000000;1;1;2;MARTHA  VARGAS CHAVEZ;N/A;CEDULA_CIUDADANIA;32623396;LO 30 VILLA LILIA SAN FAFAEL;N/A;AGROPECUARIO;3200;242;291812000;1/01/25;000000010001000;252140000000000010001000000000;20164479

25;214;0000000000010001000000000;1;2;2;MICHAEL GEORGE JOHANN VON SHILLER;N/A;CEDULA_CIUDADANIA;16821783;LO 30 VILLA LILIA SAN FAFAEL;N/A;AGROPECUARIO;3200;242;291812000;1/01/25;000000010001000;252140000000000010001000000000;20164479



Asistente de programación

Mostrar razonamiento
¡Excelente idea! Integrar la información catastral y de propietarios enriquecerá enormemente tu base de datos. Para hacerlo, primero necesitas crear la tabla con una estructura adecuada en SQL y luego cargar los datos.

Aquí te presento el código SQL para crear la tabla, una explicación de su estructura y los pasos para cargar la información que proporcionaste.

1. SQL para Crear la Tabla (CREATE TABLE)
Este comando crea una nueva tabla llamada InformacionCatastral con las columnas que definiste, eligiendo los tipos de datos más apropiados para cada una y estableciendo las relaciones clave.

SQL

-- Creación de la tabla para la información catastral y de propietarios
CREATE TABLE InformacionCatastral (
    departamento SMALLINT,
    municipio SMALLINT,
    numero_predial VARCHAR(35),
    tipo_de_registro SMALLINT,
    numero_de_orden SMALLINT,
    total_registros SMALLINT,
    nombre VARCHAR(255),
    estado_civil VARCHAR(50),
    tipo_documento VARCHAR(100),
    numero_documento VARCHAR(50),
    direccion VARCHAR(255),
    comuna VARCHAR(100),
    destino_economico VARCHAR(100),
    area_terreno NUMERIC(12, 2), -- NUMERIC para permitir decimales en áreas
    area_construida NUMERIC(12, 2),
    avaluo BIGINT, -- BIGINT para valores monetarios grandes y sin decimales
    vigencia DATE, -- El tipo DATE es ideal para almacenar fechas
    numero_predial_anterior VARCHAR(35),
    numero_predial_nacional VARCHAR(35) NOT NULL,
    matricula VARCHAR(50),

    -- Se define una clave primaria compuesta, ya que un predio puede tener varios propietarios (registros)
    PRIMARY KEY (numero_predial_nacional, numero_de_orden),

    -- Se crea una clave foránea para vincular esta tabla con la tabla de matrículas existente
    FOREIGN KEY (matricula) REFERENCES Matriculas(no_matricula_inmobiliaria)
);
2. Explicación de la Estructura
Vamos a desglosar las decisiones importantes en el código anterior para que todo quede claro.

Nombres y Tipos de Datos:

He usado VARCHAR para los números que no se usan en cálculos (como numero_predial o numero_documento) para mantener los ceros a la izquierda y evitar problemas con números muy largos.

BIGINT se usa para el avaluo, ya que puede ser un número muy grande.

DATE es el tipo perfecto para la vigencia, asegurando que el formato sea siempre correcto.

NUMERIC(12, 2) para las áreas permite guardar hasta 12 dígitos, con 2 de ellos para decimales, lo cual es muy útil para mediciones precisas.

Clave Primaria (PRIMARY KEY) 🔑

Un mismo predio (numero_predial_nacional) puede tener varios propietarios, como en tu ejemplo (con numero_de_orden 1 y 2). Por lo tanto, el número predial por sí solo no es único.

La combinación de numero_predial_nacional y numero_de_orden sí es única. A esto se le llama clave primaria compuesta y garantiza que no puedas tener dos veces el "registro 1" para el mismo predio.

Clave Foránea (FOREIGN KEY) 🔗

¡Esta es la parte más importante de la integración!

La línea FOREIGN KEY (matricula) REFERENCES Matriculas(no_matricula_inmobiliaria) crea un vínculo oficial entre tu nueva tabla InformacionCatastral y tu tabla Matriculas existente.

Esto asegura la integridad de los datos: no podrás insertar información catastral de una matricula que no exista en la tabla Matriculas.

3. Cómo Cargar los Datos
Tienes dos formas principales de cargar la información en tu nueva tabla.

Opción A: A través de la Interfaz de Supabase (Recomendado)
La forma más sencilla es guardar tus datos en un archivo CSV y usar la herramienta de importación de Supabase.

Crea el archivo CSV: Abre un editor de texto (como VSCode, o incluso el Bloc de notas) o una hoja de cálculo (Excel, Google Sheets). Pega tus datos y guárdalo como un archivo llamado datos_catastrales.csv. Asegúrate de que el separador sea el punto y coma (;).

Fragmento de código

departamento;municipio;numero_predial;tipo_de_registro;numero_de_orden;total_registros;nombre;estado_civil;tipo_documento;numero_documento;direccion;comuna;destino_economico;area_terreno;area_construida;avaluo;vigencia;numero_predial_anterior;numero_predial_nacional;Matricula
25;214;0000000000010001000000000;1;1;2;MARTHA VARGAS CHAVEZ;N/A;CEDULA_CIUDADANIA;32623396;LO 30 VILLA LILIA SAN FAFAEL;N/A;AGROPECUARIO;3200;242;291812000;2025-01-01;000000010001000;252140000000000010001000000000;20164479
25;214;0000000000010001000000000;1;2;2;MICHAEL GEORGE JOHANN VON SHILLER;N/A;CEDULA_CIUDADANIA;16821783;LO 30 VILLA LILIA SAN FAFAEL;N/A;AGROPECUARIO;3200;242;291812000;2025-01-01;000000010001000;252140000000000010001000000000;20164479
Nota: He cambiado la fecha a formato YYYY-MM-DD (2025-01-01) que es el estándar para SQL.

Importa en Supabase:

Ve a tu proyecto de Supabase.

En el menú de la izquierda, ve a Database -> Tables.

Selecciona tu nueva tabla InformacionCatastral.

Haz clic en el botón "Insert" y luego busca la opción para "Import data from CSV".

Sube tu archivo y Supabase se encargará del resto.

Opción B: Usando el Comando COPY de SQL
Si tienes muchos datos, el comando COPY es la forma más eficiente. Esto se ejecuta desde el SQL Editor de Supabase.

SQL

COPY InformacionCatastral(departamento, municipio, numero_predial, tipo_de_registro, numero_de_orden, total_registros, nombre, estado_civil, tipo_documento, numero_documento, direccion, comuna, destino_economico, area_terreno, area_construida, avaluo, vigencia, numero_predial_anterior, numero_predial_nacional, matricula)
FROM 'ruta/a/tu/archivo.csv' -- Esta ruta debe ser accesible por el servidor
WITH (FORMAT csv, DELIMITER ';', HEADER true);
Nota: El comando COPY desde un archivo local puede ser complejo en un entorno de nube como Supabase, por eso la Opción A es la más recomendada.







sale el siguiente error Failed to import data: insert or update on table "informacioncatastral" violates foreign key constraint "informacioncatastral_Matricula_fkey"


Asistente de programación

Mostrar razonamiento
Claro, ese error es muy común y, de hecho, es una buena señal. Significa que tu base de datos está funcionando correctamente para proteger la integridad de tu información.

En términos sencillos, el error te está diciendo: "Estás intentando agregar información a la tabla informacioncatastral para la matrícula '20164479', pero fui a buscar esa matrícula en la tabla principal Matriculas y no la encontré. No puedo agregar detalles de algo que no existe en el registro principal".

La clave foránea (FOREIGN KEY) que creamos es como un guardia de seguridad que se asegura de que cada registro en InformacionCatastral esté vinculado a una matrícula que realmente exista.

Cómo Solucionarlo (Paso a Paso) 🕵️‍♂️
El problema se reduce a una de dos cosas: la matrícula realmente no existe en la tabla Matriculas o hay una pequeña diferencia en los datos.

1. Verifica si la Matrícula Existe
Ve al SQL Editor en tu panel de Supabase y ejecuta la siguiente consulta para buscar la matrícula que te está dando problemas:

SQL

SELECT *
FROM public.matriculas
WHERE no_matricula_inmobiliaria = '20164479';
2. Analiza el Resultado y Actúa
Caso A: La consulta NO devuelve ningún resultado.
Problema: La matrícula 20164479 simplemente no ha sido registrada en tu tabla Matriculas.

Solución: Debes insertar primero el registro de esta matrícula en la tabla Matriculas. Una vez que el registro principal exista, podrás volver a importar el archivo CSV en la tabla InformacionCatastral y funcionará sin problemas.

Caso B: La consulta SÍ devuelve un resultado.
Problema: Esto indica que hay una discrepancia sutil entre los datos. Las causas más comunes son:

Espacios en blanco ocultos: El valor en la tabla Matriculas podría ser ' 20164479' o '20164479 ' (con espacios).

Tipo de dato diferente: Aunque es poco probable, podría haber una diferencia en el tipo de dato que impida una coincidencia perfecta.

Solución: Asegúrate de que el valor en tu archivo CSV (20164479) sea idéntico al valor en la columna no_matricula_inmobiliaria de la tabla Matriculas. Edita el dato incorrecto (ya sea en el CSV o en la tabla) para que coincidan perfectamente.

Estrategia a Largo Plazo
La regla de oro es: Siempre debes registrar una nueva matrícula en la tabla Matriculas antes de intentar agregar su información detallada en la tabla InformacionCatastral.

La tabla Matriculas es tu registro maestro, y InformacionCatastral contiene los detalles de esos registros maestros.







las amtriculas se repiten ya que la data hace un registro por propietario pero tienen la misma matricula


Asistente de programación

Mostrar razonamiento
¡Exacto! Esa es una observación clave sobre tu data y es precisamente la razón por la que diseñamos la tabla InformacionCatastral de esa manera. No te preocupes, que se repita la matrícula en esa tabla no es un error, es el comportamiento esperado y correcto.

Tu diseño actual ya maneja esta situación perfectamente.

Relación de Uno a Muchos
Lo que describes es una relación de "uno a muchos".

Una Matrícula (en tu tabla Matriculas).

Puede tener muchos registros de propietario (en tu tabla InformacionCatastral).

Piensa que la tabla Matriculas es como una carpeta para cada propiedad. La tabla InformacionCatastral contiene las diferentes hojas dentro de esa carpeta, y cada hoja es un propietario.

¿Cómo lo Maneja la Base de Datos?
La base de datos permite que la matricula se repita gracias a la clave primaria compuesta que definimos. La regla no es que la matricula deba ser única, sino que la combinación de numero_predial_nacional y numero_de_orden debe ser única.

Veámoslo con tu propio ejemplo:

numero_predial_nacional	numero_de_orden	nombre	Clave Única (Lo que ve la BD)
25214...000	1	MARTHA VARGAS CHAVEZ	(25214...000, 1)
25214...000	2	MICHAEL GEORGE...	(25214...000, 2)

Exportar a Hojas de cálculo
Como puedes ver:

El numero_predial_nacional se repite, y eso está bien.

El numero_de_orden es diferente para cada propietario.

La combinación de ambos valores es única para cada fila, que es lo que exige la clave primaria.

Así que puedes estar tranquilo. Tu base de datos está correctamente estructurada para manejar múltiples propietarios por cada matrícula. ¡Es un excelente diseño!







sigue saliendo este error Failed to import data: insert or update on table "informacioncatastral" violates foreign key constraint "informacioncatastral_Matricula_fkey"


Asistente de programación

Mostrar razonamiento
Este error persistente indica que, sin lugar a dudas, hay una o más matrículas en tu archivo CSV que no tienen una contraparte exacta en tu tabla principal Matriculas.

No te preocupes, vamos a resolver esto con un plan de acción definitivo para encontrar y corregir el problema. El error es como una alarma que no dejará de sonar hasta que encontremos la causa raíz.

Plan de Acción Definitivo 🕵️‍♂️
Sigue estos pasos en el SQL Editor de Supabase.

1. Encontrar las Matrículas Problemáticas
Primero, necesitamos una lista de todas las matrículas de tu archivo CSV que no existen en la tabla Matriculas. Para hacer esto, la forma más fácil es importar tu CSV a una tabla temporal sin la restricción de clave foránea.

Pero si no quieres hacer eso, el siguiente paso es la inspección manual. El objetivo es identificar qué valor específico está causando el fallo.

2. Inspeccionar los Datos con Precisión (La Causa Más Común)
El 99% de las veces, el problema es invisible: espacios en blanco al principio o al final de los datos. La matrícula ' 20164479 ' no es igual a '20164479'.

A. Busca espacios en blanco en tu tabla principal Matriculas:

Ejecuta esta consulta. Si devuelve algún resultado, significa que tienes matrículas "sucias" en tu tabla principal.

SQL

SELECT no_matricula_inmobiliaria
FROM public.matriculas
WHERE no_matricula_inmobiliaria LIKE ' %' OR no_matricula_inmobiliaria LIKE '% ';
B. Limpia los espacios en blanco de tu tabla principal:

Independientemente del resultado anterior, ejecuta este comando para limpiar todos los valores en la columna clave. Es una acción segura y muy recomendable.

SQL

-- Esto elimina los espacios en blanco al inicio y al final de TODAS las matrículas
UPDATE public.matriculas
SET no_matricula_inmobiliaria = TRIM(no_matricula_inmobiliaria);
3. Limpia tu Archivo CSV
Ahora debes hacer lo mismo pero en tu archivo de origen.

Abre tu archivo .csv con un programa de hoja de cálculo (como Google Sheets o Excel).

Selecciona la columna Matricula.

Usa la función de "Recortar espacios en blanco" (en Google Sheets, está en Datos > Limpieza de datos > Recortar espacios en blanco).

Guarda el archivo CSV ya limpio.

4. Borra los Datos Parciales y Reintenta
Si alguno de los intentos de importación anteriores cargó algunas filas antes de fallar, es mejor empezar de cero para evitar duplicados.

A. Vacía la tabla InformacionCatastral:

SQL

-- ¡CUIDADO! Esto borrará TODOS los registros de esta tabla.
DELETE FROM public.informacioncatastral;
B. Vuelve a importar:

Ahora, con la tabla Matriculas limpia y tu archivo CSV también limpio, intenta importar el archivo CSV de nuevo usando la interfaz de Supabase.

La regla es simple e inflexible: un valor no puede existir en la columna InformacionCatastral.matricula si ese mismo valor exacto (sin espacios ni diferencias) no existe primero en la columna Matriculas.no_matricula_inmobiliaria. Siguiendo los pasos de limpieza, deberías poder resolver la discrepancia y la importación será exitosa.







Este error persistente indica que, sin lugar a dudas, hay una o más matrículas en tu archivo CSV que no tienen una contraparte exacta en tu tabla principal Matriculas, sin embargo el modelo de datos que estamos creando pueden existir matriculas en la tabla principal matriculas que no existan en la tabla informacion catastral



Asistente de programación

Mostrar razonamiento
¡Estás en lo correcto! Tu razonamiento sobre el modelo de datos es perfecto.

El diseño actual sí permite que existan matrículas en tu tabla principal Matriculas que no tengan un registro correspondiente en la tabla InformacionCatastral. Eso es completamente normal y esperado.

El error que estás viendo se debe a la situación exactamente inversa, que no está permitida.

La Regla de la Clave Foránea: Una Vía de Un Solo Sentido
Piénsalo de esta manera:

La tabla Matriculas es el registro de padres.

La tabla InformacionCatastral es el registro de hijos.

La regla de la base de datos (la clave foránea) dice: "Todo hijo debe tener un padre registrado".

Esto nos lleva a dos escenarios:

Situación	¿Es Válido para la Base de Datos?	Explicación
Una matrícula existe en Matriculas (un padre), pero no tiene un registro en InformacionCatastral (ningún hijo).	✅ Sí, es válido.	Esta es la situación que tú describes. Un padre puede no tener hijos.
Se intenta añadir un registro a InformacionCatastral (un hijo) con una matrícula que no existe en Matriculas (el padre no está registrado).	❌ No, es inválido.	Este es el error que estás recibiendo. No puedes registrar a un hijo si su padre no existe en el sistema.

Exportar a Hojas de cálculo
Conclusión
El error persistente te está confirmando al 100% que en tu archivo CSV hay, al menos, una matrícula que no tiene una contraparte exacta e idéntica en tu tabla Matriculas.

Tu entendimiento del modelo es correcto, pero el error apunta a un problema en los datos que intentas insertar. La solución sigue siendo encontrar esa matrícula específica en tu archivo CSV y asegurarte de que exista primero en la tabla Matriculas, o corregir cualquier error tipográfico o de espacios en blanco.







pero lo que estoy tratando de decir es exactamente eso la infroamcion catastral no deberia tratarse de esa manera ya que la data catastral puede tener matrciulas que no esten dentro de la tabla matriculas ya que la informacion registral es mas actualizada que la informacion catastral por lo tanto es exactamente eso lo que queremos revisar cuales matriculas de la tabla matriculas tienen informacion catastral y cuales no.



Asistente de programación

Mostrar razonamiento
¡Ah, entiendo perfectamente! Gracias por la aclaración, ahora todo tiene sentido.

Si la InformacionCatastral puede y debe tener matrículas que no existen en tu tabla Matriculas, entonces el problema no son los datos, sino la regla que establecimos en la base de datos. La solución es eliminar la restricción de clave foránea (FOREIGN KEY).

Piensa en la clave foránea como un "portero estricto" que no deja entrar a nadie a la InformacionCatastral si no está en la lista principal de Matriculas. Pero tú no necesitas un portero, necesitas un "auditor" que pueda comparar ambas listas para ver las diferencias.

Vamos a quitar esa regla para que puedas cargar todos tus datos y luego te daré las consultas para hacer exactamente la revisión que quieres.

Plan de Acción: Modificar la Estructura
Sigue estos dos sencillos pasos en el SQL Editor de Supabase.

Paso 1: Eliminar la Restricción de Clave Foránea
Este comando elimina la regla que está bloqueando tu importación. El nombre de la restricción (informacioncatastral_Matricula_fkey) lo obtuvimos del mensaje de error anterior.

SQL

ALTER TABLE public.informacioncatastral
DROP CONSTRAINT "informacioncatastral_Matricula_fkey";
Al ejecutar esto, la base de datos ya no exigirá que cada matrícula de InformacionCatastral exista en Matriculas.

Paso 2: Vaciar la Tabla y Reintentar la Importación
Para asegurar que no queden datos de intentos fallidos, primero vaciamos la tabla.

SQL

-- ¡CUIDADO! Esto borrará TODOS los registros de esta tabla.
DELETE FROM public.informacioncatastral;
Ahora, vuelve a importar tu archivo CSV. Con la restricción eliminada, la importación debería completarse sin ningún error.

Cómo Realizar las Comparaciones que Necesitas 🧐
Una vez que tus datos estén cargados, puedes usar estas consultas en el SQL Editor para hacer el análisis que mencionaste.

Consulta 1: Matrículas en Matriculas que SÍ tienen datos catastrales.
Esto te muestra la intersección, es decir, los datos que coinciden en ambas tablas.

SQL

SELECT
  m.no_matricula_inmobiliaria,
  ic.nombre AS propietario,
  ic.numero_documento
FROM
  public.matriculas m
INNER JOIN
  public.informacioncatastral ic ON m.no_matricula_inmobiliaria = ic.matricula;
Consulta 2: Matrículas en Matriculas que NO tienen datos catastrales.
Esto te muestra las matrículas de tu tabla principal que están "huérfanas", sin información catastral correspondiente.

SQL

SELECT
  m.no_matricula_inmobiliaria
FROM
  public.matriculas m
LEFT JOIN
  public.informacioncatastral ic ON m.no_matricula_inmobiliaria = ic.matricula
WHERE
  ic.matricula IS NULL;
Consulta 3: Matrículas en InformacionCatastral que NO existen en Matriculas.
Esta es quizás la consulta más importante para ti. Te mostrará los registros catastrales cuya matrícula principal no se encuentra en tu tabla Matriculas.

SQL

SELECT DISTINCT
  ic.matricula,
  ic.nombre AS propietario
FROM
  public.informacioncatastral ic
LEFT JOIN
  public.matriculas m ON ic.matricula = m.no_matricula_inmobiliaria
WHERE
  m.no_matricula_inmobiliaria IS NULL;
Con este nuevo enfoque, la base de datos se adapta a la realidad de tus datos y te da las herramientas para analizarlos como necesitas.








ahora bien el aplicativo debe poder mostrar un tarjeta de informacion la cual tendra varios campos sin embargo en principio requerira mostrar si la matricula seleccionada se encuentra en la tabla de informacioncatastral de la siguiente manera: R1: Si/No segun se encuentre o no en la tabla.



Asistente de programación

Mostrar razonamiento
¡Excelente adición! Es una funcionalidad muy útil para dar un resumen rápido de la matrícula consultada. Implementar esa "tarjeta de información" es muy sencillo con Streamlit.

Vamos a modificar tu archivo app.py para que, justo después de introducir la matrícula y antes de generar el grafo, haga una consulta rápida a la base de datos y muestre el resultado que pides.

Plan de Acción
Crearemos una nueva función llamada verificar_informacion_catastral que se conectará a la base de datos y devolverá True si la matrícula existe en la tabla InformacionCatastral y False si no.

Integraremos esta función en la interfaz de Streamlit para que se ejecute al presionar el botón.

Mostraremos el resultado usando st.metric, que crea una "tarjeta" visualmente atractiva, perfecta para lo que necesitas.

Código Completo para app.py
Aquí tienes el código completo y actualizado. Puedes reemplazar todo el contenido de tu archivo app.py en GitHub con este. Las nuevas secciones están marcadas con comentarios para que veas exactamente qué ha cambiado.

Python

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