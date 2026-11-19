import hashlib
import requests
import re

class ConexionEcoTech:
    def __init__(self):
        self.base_url = "https://mindicador.cl/api"
        self.session = requests.Session()
        self._usuarios_registrados = {
            "admin": hashlib.sha256("EcoTech2026".encode()).hexdigest()
        }

    def _sanear_texto(self, texto):
        return re.sub(r'[^a-zA-Z0-9]', '', texto.strip())

    def validar_usuario(self, usuario, contraseña):
        usuario = self._sanear_texto(usuario)
        contraseña = contraseña.strip()

        if not usuario or not contraseña:
            print("Error: debe ingresar usuario y contraseña correctos")
            return False

        contraseña_hash = hashlib.sha256(contraseña.encode()).hexdigest()

        if usuario in self._usuarios_registrados and self._usuarios_registrados[usuario] == contraseña_hash:
            print("Usuario y contraseña están correctos")
            return True
        else:
            print("Error: usuario o contraseña incorrectos")
            return False

    def obtener_datos_api(self):
        try:
            print("Consultamos datos externos vía HTTP")
            respuesta = self.session.get(self.base_url, timeout=20)

            if respuesta.status_code == 200:
                datos = respuesta.json()
                return datos
            else:
                print(f"Error en el servicio externo. Código HTTP: {respuesta.status_code}")
                return None
        except requests.exceptions.RequestException as error:
            print(f"Error de conexión HTTP: {error}")
            return None