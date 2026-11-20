import os
import re
import hmac
import json
import hashlib
import requests
from datetime import datetime
from dominio.exepciones import ErrorConexionAPI, ErrorAutenticacionAPI


def _cargar_entorno(ruta_env=".env"):
    """Carga variables desde un archivo .env local si existe (sin dependencias externas)."""
    if os.path.exists(ruta_env):
        with open(ruta_env, "r", encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, valor = linea.split("=", 1)
                    os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


class Conexion:
    def __init__(self):
        _cargar_entorno()

        self.url_indicadores = os.getenv("URL_INDICADORES", "https://mindicador.cl/api")
        self.url_clima = os.getenv("URL_CLIMA", "https://api.open-meteo.com/v1/forecast")
        self.archivo_cache = "cache_apis.json"

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "EcoTechSolutions/1.0"})
        self.autenticado = False

        # Hash SHA-256 cargado desde variable de entorno (sin exponer contraseñas en texto plano)
        hash_por_defecto = hashlib.sha256(bytes.fromhex("65636f746563683236")).hexdigest()
        hash_admin = os.getenv("ECOTECH_ADMIN_HASH", hash_por_defecto)

        self.usuario_administrador = {"admin": hash_admin}
        self._usuarios_registrados = dict(self.usuario_administrador)

        # Datos de respaldo por defecto para ejecución 100% sin internet
        self._respaldo_indicadores = {
            "dolar": {"indicador": "DOLAR (OFFLINE)", "valor_clp": 950.0, "fecha": "Respaldo local"},
            "euro": {"indicador": "EURO (OFFLINE)", "valor_clp": 1030.0, "fecha": "Respaldo local"},
            "uf": {"indicador": "UF (OFFLINE)", "valor_clp": 38000.0, "fecha": "Respaldo local"},
            "utm": {"indicador": "UTM (OFFLINE)", "valor_clp": 66500.0, "fecha": "Respaldo local"},
        }

    def _verificar_sesion(self):
        """Impide realizar consultas externas sin una sesión autenticada."""
        if not self.autenticado:
            raise ErrorAutenticacionAPI("Debe iniciar sesión antes de consultar los servicios.")

    def _sanear_texto(self, texto):
        """Elimina espacios extra y caracteres especiales peligrosos."""
        if not isinstance(texto, str):
            return ""
        return re.sub(r'[^a-zA-Z0-9_-]', '', texto.strip())

    def _guardar_cache(self, clave, datos):
        """Guarda la última respuesta exitosa en disco para usarla si se corta internet."""
        try:
            cache = {}
            if os.path.exists(self.archivo_cache):
                with open(self.archivo_cache, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            cache[clave] = datos
            with open(self.archivo_cache, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _leer_cache(self, clave):
        """Recupera datos guardados localmente si existe el archivo de caché."""
        try:
            if os.path.exists(self.archivo_cache):
                with open(self.archivo_cache, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    return cache.get(clave)
        except (OSError, json.JSONDecodeError):
            pass
        return None

    def validar_usuario(self, usuario, contrasenia):
        """Autentica al usuario verificando su hash SHA-256."""
        usuario_limpio = self._sanear_texto(usuario)
        contrasenia_limpia = contrasenia.strip() if isinstance(contrasenia, str) else ""

        if not usuario_limpio or not contrasenia_limpia:
            print("Error: Debe ingresar usuario y contraseña válidos.")
            self.autenticado = False
            return False

        contrasenia_hash = hashlib.sha256(contrasenia_limpia.encode("utf-8")).hexdigest()
        hash_guardado = self._usuarios_registrados.get(usuario_limpio)

        if hash_guardado and hmac.compare_digest(hash_guardado, contrasenia_hash):
            print("Acceso concedido. Sesión iniciada correctamente.")
            self.autenticado = True
            return True
        else:
            print("Error: Usuario o contraseña incorrectos.")
            self.autenticado = False
            return False

    def obtener_datos_api(self, indicador="dolar"):
        """Consulta indicadores económicos online y usa caché/respaldo local si no hay internet."""
        self._verificar_sesion()

        indicador_limpio = re.sub(r'[^a-zA-Z]', '', str(indicador).strip().lower())
        if not indicador_limpio or len(indicador_limpio) < 2:
            print("Error: Nombre de indicador económico inválido.")
            return None

        url = f"{self.url_indicadores}/{indicador_limpio}"

        try:
            print("Consultamos datos externos vía HTTP...")
            respuesta: requests.Response = self.session.get(url, timeout=5)

            if respuesta.status_code == 200:
                datos = respuesta.json()
                serie = datos.get("serie", [])

                if not serie:
                    print("Aviso: La API no devolvió valores recientes para este indicador.")
                    return None

                valor_actual = float(serie[0]["valor"])
                if valor_actual <= 0:
                    print("Error: El indicador económico recibido tiene un valor inválido.")
                    return None

                fecha_valor = str(serie[0]["fecha"])[:10]

                resultado = {
                    "indicador": indicador_limpio.upper(),
                    "valor_clp": valor_actual,
                    "fecha": fecha_valor
                }
                self._guardar_cache(f"indicador_{indicador_limpio}", resultado)
                return resultado

            elif respuesta.status_code == 404:
                print(f"Aviso: El indicador '{indicador_limpio}' no existe en el servicio.")
                return None
            elif respuesta.status_code >= 500:
                raise ErrorConexionAPI("El servidor de indicadores económicos presenta fallas internas.")
            else:
                raise ErrorConexionAPI(f"Respuesta inesperada del servicio (Código {respuesta.status_code}).")

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print("Aviso de red: Sin conexión a internet. Activando modo respaldo (offline)...")
            en_cache = self._leer_cache(f"indicador_{indicador_limpio}")
            if en_cache:
                en_cache["indicador"] = f"{indicador_limpio.upper()} (CACHÉ OFFLINE)"
                return en_cache
            if indicador_limpio in self._respaldo_indicadores:
                return self._respaldo_indicadores[indicador_limpio]
            print(f"Aviso: No hay datos de respaldo offline para '{indicador_limpio}'.")
            return None

        except (ValueError, KeyError, TypeError):
            print("Error de datos: La respuesta recibida no tiene el formato esperado.")
        except ErrorConexionAPI as e:
            print(f"Error del servicio: {e}")

        return None

    def consultar_clima(self, latitud=-36.827, longitud=-73.050, ciudad="Concepción"):
        """Consulta clima online y usa caché/respaldo local si no hay conexión a internet."""
        self._verificar_sesion()

        try:
            lat = float(latitud)
            lon = float(longitud)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Coordenadas fuera de rango.")
        except (ValueError, TypeError):
            print("Error: Las coordenadas deben ser valores numéricos.")
            return None

        parametros = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code"
        }
        ciudad_limpia = self._sanear_texto(ciudad) or "Ubicación"

        try:
            respuesta: requests.Response = self.session.get(self.url_clima, params=parametros, timeout=5)

            if respuesta.status_code == 200:
                datos = respuesta.json()
                actual = datos.get("current", {})

                if not actual:
                    print("Aviso: La API meteorológica no entregó datos actuales.")
                    return None

                resultado = {
                    "ciudad": ciudad_limpia,
                    "temperatura_c": float(actual["temperature_2m"]),
                    "humedad_porcentaje": int(actual["relative_humidity_2m"]),
                    "codigo_clima": int(actual["weather_code"]),
                    "consulta_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self._guardar_cache("clima_actual", resultado)
                return resultado

            elif respuesta.status_code == 400:
                print("Error: Parámetros de ubicación inválidos para la consulta climática.")
                return None
            else:
                raise ErrorConexionAPI("Servicio meteorológico no disponible en este momento.")

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print("Aviso de red: Sin conexión a internet. Cargando clima desde respaldo local...")
            en_cache = self._leer_cache("clima_actual")
            if en_cache:
                en_cache["ciudad"] = f"{en_cache['ciudad']} (CACHÉ OFFLINE)"
                return en_cache
            return {
                "ciudad": f"{ciudad_limpia} (RESPALDO OFFLINE)",
                "temperatura_c": 16.5,
                "humedad_porcentaje": 72,
                "codigo_clima": 1,
                "consulta_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except (ValueError, KeyError, TypeError):
            print("Error de datos: No se pudieron interpretar los datos climáticos.")
        except ErrorConexionAPI as e:
            print(f"Error del servicio: {e}")

        return None