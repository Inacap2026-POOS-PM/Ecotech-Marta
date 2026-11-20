from dominio.persona import Persona
from dominio.empleado import Empleado
from dominio.exepciones import ErrorAutenticacionAPI
from infraestructura.conexion import obtener_conexion
from scrip import Conexion


def fila_a_empleado(fila):
    return Empleado(
        fila[0],
        fila[1],
        fila[2],
        fila[3],
        fila[4],
        fila[5],
        fila[6],
        fila[7]
    )



empleado = Empleado(
    1,
    "12345678-9",
    "Ana Rojas",
    "Los Carrera 123",
    "987654321",
    "ana@correo.cl",
    "2024-03-01",
    950000
)



def ejecutar_menu_ecotech(empleado_actual):
    conexion_api = Conexion()
    print("\n=== SISTEMA DE GESTIÓN EXTERNA ECOTECH SOLUTIONS ===")

   
    usuario = input("Ingrese usuario: ")
    contrasenia = input("Ingrese contraseña: ")

    
    if not conexion_api.validar_usuario(usuario, contrasenia):
        print("Cerrando el sistema por seguridad.")
        return

    try:
        while True:
            print(f"\n--- Bienvenido/a {usuario} | Empleado: {empleado_actual.nombre} ---")
            print("1. Consultar clima para planificación de proyectos")
            print("2. Calcular pago internacional del empleado")
            print("3. Salir")

            opcion = input("Seleccione una opción (1-3): ").strip()

            if opcion == "1":
                print("\nConsultando clima actual...")
                clima = conexion_api.consultar_clima()
                if clima:
                    print(f"Ciudad: {clima['ciudad']}")
                    print(f"Temperatura: {clima['temperatura_c']} °C")
                    print(f"Humedad: {clima['humedad_porcentaje']}%")
                    print(f"Fecha consulta: {clima['consulta_fecha']}")

            elif opcion == "2":
                moneda = input("Ingrese indicador a consultar (ej: dolar, euro): ").strip().lower()
                datos_moneda = conexion_api.obtener_datos_api(moneda)

                if datos_moneda:
                    valor_moneda = datos_moneda["valor_clp"]
                    salario_clp = float(empleado_actual.salario)
                    pago_internacional = salario_clp / valor_moneda

                    print(f"\nIndicador: {datos_moneda['indicador']} (${valor_moneda} CLP al {datos_moneda['fecha']})")
                    print(f"Salario base de {empleado_actual.nombre}: ${salario_clp:,.0f} CLP")
                    print(f"Pago equivalente en {datos_moneda['indicador']}: {pago_internacional:,.2f}")

            elif opcion == "3":
                print("Sesión cerrada. Hasta pronto.")
                break
            else:
                print("Opción no válida. Intente nuevamente.")

    except ErrorAutenticacionAPI as e:
        print(f"Error de seguridad: {e}")


if __name__ == "__main__":
    ejecutar_menu_ecotech(empleado)