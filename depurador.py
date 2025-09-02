import re
import os

def depurar_sql(ruta_archivo):
    """
    Analiza un archivo .sql para encontrar errores de conteo en las
    instrucciones INSERT.
    """
    # Verificamos si el archivo existe antes de continuar
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: El archivo '{ruta_archivo}' no fue encontrado.")
        return

    print(f"✅ Iniciando la revisión del archivo: {ruta_archivo}\n")
    
    errores_encontrados = 0
    
    # Abrimos y leemos el archivo línea por línea
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
        # Usamos enumerate para tener el número de línea actual (empezando en 1)
        for num_linea, linea in enumerate(archivo, 1):
            
            # Buscamos solo las líneas que contienen un INSERT INTO
            # La 'i' en re.IGNORECASE hace que no distinga mayúsculas/minúsculas
            if re.search(r'INSERT INTO', linea, re.IGNORECASE):
                
                # 1. Extraer las columnas
                # Buscamos el texto entre el primer par de paréntesis (...)
                match_columnas = re.search(r'\((.*?)\)', linea)
                
                # 2. Extraer los valores
                # Buscamos el texto en el paréntesis que sigue a VALUES (...)
                match_valores = re.search(r'VALUES[ ]*\((.*)\)', linea, re.IGNORECASE)

                if match_columnas and match_valores:
                    # Obtenemos el string dentro de los paréntesis
                    columnas_str = match_columnas.group(1)
                    valores_str = match_valores.group(1)

                    # Contamos los elementos dividiendo por la coma
                    # Esto asume que no hay comas dentro de los valores de texto
                    lista_columnas = columnas_str.split(',')
                    lista_valores = valores_str.split(',')

                    num_columnas = len(lista_columnas)
                    num_valores = len(lista_valores)

                    # 3. Comparar y reportar si hay un error
                    if num_columnas != num_valores:
                        print(f"🚨 ¡Error encontrado en la línea {num_linea}!")
                        print(f"   -> Columnas declaradas: {num_columnas}")
                        print(f"   -> Valores proporcionados: {num_valores}")
                        print("-" * 20)
                        errores_encontrados += 1

    if errores_encontrados == 0:
        print("🎉 ¡Excelente! No se encontraron errores de conteo en las instrucciones INSERT.")
    else:
        print(f"\nRevisión completada. Se encontraron un total de {errores_encontrados} errores.")


# --- Ejecución del script ---
if __name__ == "__main__":
    # Pedimos al usuario que ingrese la ruta del archivo a revisar
    ruta_del_sql = input("Por favor, introduce la ruta completa de tu archivo .sql y presiona Enter: ")
    depurar_sql(ruta_del_sql)