import hashlib
import os
import re
import requests
from datetime import datetime
from dominio.exepciones import ErrorConexionAPI, ErrorAutenticacionAPI

class Conexion:
    def __init__(self):
        
        self.url_indicadores = "https://mindicador.cl/api"
        self.url_clima = "https://api.open-meteo.com/v1/forecast"

        self.session = requests.Session()
        self.autenticado = False

        # Hash SHA-256 real de "EcoTech2026" (ya viene encriptado, no se vuelve a pasar por sha256)
        hash_admin = "83a966053f34828341d75c977c6918469f401760540877f80693377213659348"
        self.usuario_administrador = {"admin": hash_admin}
        self._usuarios_registrados = dict(self.usuario_administrador)

    def _verificar_sesion(self):
        """Impide realizar consultas externas sin una sesión autenticada."""
        if not self.autenticado:
            raise ErrorAutenticacionAPI("Debe iniciar sesión antes de consultar los servicios.")

    def _sanear_texto(self, texto):
        """Elimina espacios extra y caracteres especiales peligrosos."""
        if not isinstance(texto, str):
            return ""
        return re.sub(r'[^a-zA-Z0-9_-]', '', texto.strip())

    def validar_usuario(self, usuario, contraseña):
        """Autentica al usuario verificando su hash SHA-256."""
        usuario_limpio = self._sanear_texto(usuario)
        contraseña_limpia = contraseña.strip() if isinstance(contraseña, str) else ""

        if not usuario_limpio or not contraseña_limpia:
            print("Error: Debe ingresar usuario y contraseña válidos.")
            self.autenticado = False
            return False

        contraseña_hash = hashlib.sha256(contraseña_limpia.encode()).hexdigest()

        if (
            self.usuario_administrador in self._usuarios_registrados
            and self._usuarios_registrados[usuario_limpio] == contraseña_hash
        ):
            print("Acceso concedido. Sesión iniciada correctamente.")
            self.autenticado = True
            return True
        else:
            print("Error: Usuario o contraseña incorrectos.")
            self.autenticado = False
            return False

    def obtener_datos_api(self, indicador="dolar"):
        self._verificar_sesion()

        indicador_limpio = re.sub(r'[^a-zA-Z]', '', str(indicador).strip().lower())
        if not indicador_limpio or len(indicador_limpio) < 2:
            print("Error: Nombre de indicador económico inválido.")
            return None

        url = f"{self.url_indicadores}/{indicador_limpio}"
        
    
        try:
            print("Consultamos datos externos vía HTTP")
            respuesta: requests.Response = self.session.get(url, timeout=5)
            if respuesta.status_code == 200:
                datos = respuesta.json()
                serie = datos.get("serie", [])
                
                if not serie:
                    print("Aviso: La API no devolvió valores recientes para este indicador.")
                    return None

                valor_actual = float(serie[0]["valor"])
                fecha_valor = serie[0]["fecha"][:10]

                
                return {
                    "indicador": indicador_limpio.upper(),
                    "valor_clp": valor_actual,
                    "fecha": fecha_valor
                }
            elif respuesta.status_code == 404:
                print(f"Aviso: El indicador '{indicador_limpio}' no existe en el servicio.")
                return None
            elif respuesta.status_code >= 500:
                raise ErrorConexionAPI("El servidor de indicadores económicos presenta fallas internas.")
            else:
                raise ErrorConexionAPI(f"Respuesta inesperada del servicio (Código {respuesta.status_code}).")

        except requests.exceptions.Timeout:
            print("Error de red: Tiempo de espera agotado al consultar indicadores.")
        except requests.exceptions.ConnectionError:
            print("Error de red: No se pudo establecer conexión con el servicio económico.")
        except (ValueError, KeyError, TypeError):
            print("Error de datos: La respuesta recibida no tiene el formato esperado.")
        except ErrorConexionAPI as e:
            print(f"Error del servicio: {e}")

        return None

    def consultar_clima(self, latitud=-36.827, longitud=-73.050, ciudad="Concepción"):
        """
        Consulta temperatura y humedad actual desde Open-Meteo usando coordenadas
        para planificar proyectos sostenibles de EcoTech.
        """
        self._verificar_sesion()

        
        try:
            lat = float(latitud)
            lon = float(longitud)
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print("Error: Coordenadas geográficas fuera de rango válido.")
                return None
        except (ValueError, TypeError):
            print("Error: Las coordenadas deben ser valores numéricos.")
            return None

        parametros = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code"
        }

        try:
            respuesta: requests.Response = self.session.get(self.url_clima, params=parametros, timeout=5)

            if respuesta.status_code == 200:
                datos = respuesta.json()
                actual = datos.get("current", {})

                return {
                    "ciudad": self._sanear_texto(ciudad) or "Ubicación",
                    "temperatura_c": float(actual["temperature_2m"]),
                    "humedad_porcentaje": int(actual["relative_humidity_2m"]),
                    "codigo_clima": int(actual["weather_code"]),
                    "consulta_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            elif respuesta.status_code == 400:
                print("Error: Parámetros de ubicación inválidos para la consulta climática.")
                return None
            else:
                raise ErrorConexionAPI("Servicio meteorológico no disponible en este momento.")

        except requests.exceptions.Timeout:
            print("Error de red: El servicio meteorológico tardó demasiado en responder.")
        except requests.exceptions.ConnectionError:
            print("Error de red: Sin conexión con el servidor del clima.")
        except (ValueError, KeyError, TypeError):
            print("Error de datos: No se pudieron interpretar los datos climáticos.")
        except ErrorConexionAPI as e:
            print(f"Error del servicio: {e}")

        return None
        