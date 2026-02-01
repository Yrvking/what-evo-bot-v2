import httpx
from typing import List, Dict, Any
from app.config import TOKEN, PHONE_ID
from app.utils.logger import logger

class WhatsAppClient:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v22.0/{PHONE_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }

    async def _send_request(self, payload: Dict[str, Any]):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url, 
                    headers=self.headers, 
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Mensaje enviado con éxito: {response.json()}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP enviando mensaje: {e.response.text}")
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")

    async def send_text(self, to_number: str, text: str):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": text}
        }
        await self._send_request(payload)

    async def send_interactive_buttons(self, to_number: str, body_text: str, buttons: List[Dict[str, str]]):
        """
        buttons: List of dicts with keys 'id' and 'title'
        """
        buttons_data = [
            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}} 
            for b in buttons
        ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": buttons_data}
            }
        }
        await self._send_request(payload)

    async def send_interactive_list(self, to_number: str, body_text: str, button_text: str, sections: List[Dict[str, Any]]):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        await self._send_request(payload)

# Instancia global
wa_client = WhatsAppClient()
