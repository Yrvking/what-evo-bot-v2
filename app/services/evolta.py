from app.config import BD_EVOLTA
from typing import Optional, Dict

class EvoltaManager:
    """
    Gestor para interactuar con los datos de Evolta (CRM/ERP).
    Actualmente usa un diccionario Mock.
    """
    
    def get_client_by_dni(self, dni: str) -> Optional[Dict]:
        """
        Busca un cliente por su DNI.
        Retorna el diccionario con datos del cliente o None si no existe.
        """
        # Normalizamos input
        dni = dni.strip()
        return BD_EVOLTA.get(dni)

# Instancia global
evolta_service = EvoltaManager()
