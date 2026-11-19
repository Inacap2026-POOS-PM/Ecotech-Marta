class EcoTechError(Exception):
    """Excepción base para errores del sistema EcoTech."""
    pass


class RutDuplicadoError(EcoTechError):
    """Se lanza cuando se intenta registrar un empleado con un RUT existente."""
    pass


class SueldoInvalidoError(EcoTechError, ValueError):
    """Se lanza cuando el sueldo no cumple las restricciones laborales."""
    pass


class EmpleadoNoEncontradoError(EcoTechError):
    """Se lanza cuando no se encuentra un empleado solicitado."""
    pass

class ErrorConexionAPI(EcoTechError):
    """Se lanza cuando falla la conexión, el tiempo de espera o el estado HTTP de una API."""
    pass


class ErrorAutenticacionAPI(EcoTechError):
    """Se lanza cuando un usuario no autenticado intenta consumir servicios externos."""
    pass