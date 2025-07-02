import pandas as pd

def crear_plantilla_repuestos():
    """
    Crea un archivo Excel que sirve como plantilla para la carga masiva de repuestos.
    """
    # Define las columnas exactas que espera tu vista 'carga_masiva'
    columnas = [
        'nombre',
        'numero_parte',
        'calidad',
        'stock_actual',
        'stock_minimo',
        'ubicacion',
        'precio_unitario'
    ]
    
    # Crea algunos datos de ejemplo para guiar al usuario
    datos_ejemplo = [
        {
            'nombre': 'Filtro de Aceite Motor OM906',
            'numero_parte': 'A0001802909',
            'calidad': 'Original',  # Puedes usar 'Original', 'OEM', o 'Genérico'
            'stock_actual': 10,
            'stock_minimo': 2,
            'ubicacion': 'Estante A-1',
            'precio_unitario': 15000.50
        },
        {
            'nombre': 'Pastillas de Freno Delanteras',
            'numero_parte': 'BP-451-G',
            'calidad': 'Genérico',
            'stock_actual': 8,
            'stock_minimo': 4,
            'ubicacion': 'Bodega 2, Caja 5',
            'precio_unitario': 8500.00
        }
    ]
    
    # Crea un DataFrame de pandas con los datos y las columnas
    df = pd.DataFrame(datos_ejemplo, columns=columnas)
    
    # Define el nombre del archivo de salida
    nombre_archivo = 'plantilla_inventario_repuestos.xlsx'
    
    # Guarda el DataFrame en un archivo Excel, sin el índice de pandas
    df.to_excel(nombre_archivo, index=False)
    
    print(f"\n¡Plantilla '{nombre_archivo}' creada con éxito en el directorio actual!")
    print("Puedes abrir este archivo, llenarlo con tus datos y luego subirlo en la página de 'Carga Masiva'.\n")

# Llama a la función para crear el archivo
if __name__ == "__main__":
    crear_plantilla_repuestos()