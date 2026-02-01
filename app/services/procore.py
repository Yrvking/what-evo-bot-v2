import random
from typing import Dict, Any

class ProcoreIntegration:
    """
    Integración simulada con Procore para creación de tickets.
    """
    
    async def create_ticket(self, category: str, client_data: Dict[str, Any], phone: str) -> str:
        """
        Simula la creación de un ticket en Procore.
        Retorna el ID del ticket generado.
        """
        # Simulamos un pequeño delay o proceso asíncrono si fuera real
        ticket_id = str(random.randint(1000, 9999))
        
        print(f"--- [PROCORE] Creando Ticket ---")
        print(f"Categoría: {category}")
        print(f"Cliente: {client_data.get('nombre')}")
        print(f"Unidad: {client_data.get('unidad')}")
        print(f"ID Generado: {ticket_id}")
        print(f"--------------------------------")
        
        return ticket_id

# Instancia global
procore_service = ProcoreIntegration()
