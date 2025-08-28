import csv

def depurar_csv(nombre_archivo):
    """
    Lee y procesa un archivo CSV en modo de depuración (dry run).
    No se conecta a ninguna base de datos. En su lugar, simula las
    operaciones y muestra un informe final.

    Args:
        nombre_archivo (str): La ruta al archivo CSV que se va a procesar.
    """
    print("🚀 Iniciando script en MODO DEPURACIÓN (DRY RUN)...")
    print("   (No se realizarán cambios en la base de datos)\n")

    # --- Simulación de la Base de Datos ---
    # Usamos un diccionario para simular la tabla 'Matriculas'
    # Formato: {'numero_matricula': id_simulado}
    matriculas_simuladas = {}
    
    # Usamos un diccionario inverso para buscar por ID fácilmente
    # Formato: {id_simulado: 'numero_matricula'}
    id_a_matricula = {}

    # Usamos un set para simular la tabla 'RelacionesMatriculas' y evitar duplicados
    # Formato: {(id_padre, id_hija)}
    relaciones_simuladas = set()
    
    # Un contador para simular los IDs autoincrementales de la base de datos
    siguiente_id = 1

    # --- Función Auxiliar Simulada ---
    def obtener_o_crear_matricula_id_simulado(no_matricula):
        nonlocal siguiente_id
        if not no_matricula or not no_matricula.strip():
            return None
        
        no_matricula = no_matricula.strip()
        
        # Si la matrícula ya existe en nuestra simulación, devolvemos su ID
        if no_matricula in matriculas_simuladas:
            return matriculas_simuladas[no_matricula]
        # Si no existe, la "creamos" en nuestra simulación
        else:
            id_actual = siguiente_id
            matriculas_simuladas[no_matricula] = id_actual
            id_a_matricula[id_actual] = no_matricula
            siguiente_id += 1
            print(f"   [+] Matrícula nueva detectada: '{no_matricula}' (ID simulado: {id_actual})")
            return id_actual

    # --- Lógica Principal de Lectura ---
    try:
        with open(nombre_archivo, mode='r', encoding='utf-8') as archivo_csv:
            lector_csv = csv.reader(archivo_csv, delimiter=';')
            next(lector_csv, None)  # Saltamos el encabezado

            for fila in lector_csv:
                no_matricula_actual = fila[0]
                matriculas_padre_str = fila[2]
                matricula_hija_str = fila[3]

                id_actual = obtener_o_crear_matricula_id_simulado(no_matricula_actual)

                # Procesamos sus padres (relación "hacia arriba")
                if matriculas_padre_str:
                    for no_padre in matriculas_padre_str.split(','):
                        id_padre = obtener_o_crear_matricula_id_simulado(no_padre)
                        if id_padre and id_actual:
                            relaciones_simuladas.add((id_padre, id_actual))

                # Procesamos su hija (relación "hacia abajo")
                if matricula_hija_str:
                    id_hija = obtener_o_crear_matricula_id_simulado(matricula_hija_str)
                    if id_actual and id_hija:
                        relaciones_simuladas.add((id_actual, id_hija))

    except FileNotFoundError:
        print(f"❌ ERROR: No se pudo encontrar el archivo '{nombre_archivo}'.")
        return # Salimos de la función si no hay archivo

    # --- Informe Final ---
    print("\n-------------------------------------------")
    print("✅ ANÁLISIS COMPLETADO")
    print("-------------------------------------------")
    print(f"📄 Matrículas únicas que se crearían: {len(matriculas_simuladas)}")
    print(f"🔗 Relaciones únicas que se crearían: {len(relaciones_simuladas)}")
    print("-------------------------------------------\n")

    # Mostramos algunos ejemplos para verificación
    print("🕵️‍♂️ MUESTRA DE DATOS PROCESADOS:\n")

    # Imprimir las primeras 10 matrículas que se crearían
    print("--- Primeras 10 Matrículas ---")
    for i, (num, sim_id) in enumerate(matriculas_simuladas.items()):
        if i >= 10: break
        print(f"  - Matrícula: '{num}' (tendría el ID: {sim_id})")

    # Imprimir las primeras 20 relaciones que se crearían (en formato legible)
    print("\n--- Primeras 20 Relaciones (Padre -> Hija) ---")
    for i, (id_padre, id_hija) in enumerate(relaciones_simuladas):
        if i >= 20: break
        # Usamos el diccionario inverso para mostrar los números originales
        num_padre = id_a_matricula.get(id_padre, "N/A")
        num_hija = id_a_matricula.get(id_hija, "N/A")
        print(f"  - Relación: '{num_padre}' -> '{num_hija}'")
    
    print("\n\n✨ Revisión finalizada. Si los datos son correctos, puedes usar el script principal.")

# --- Zona de Ejecución ---
# Simplemente llama a la función con el nombre de tu archivo CSV
depurar_csv('matriculas_input.csv')