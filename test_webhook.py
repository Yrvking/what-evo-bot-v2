import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/webhook"
VERIFY_TOKEN = "HOLA_PADOVA"

def test_verify():
    print("--- Probando Verificación (GET) ---")
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": VERIFY_TOKEN,
        "hub.challenge": "CHALLENGE_ACCEPTED"
    }
    try:
        response = requests.get(BASE_URL, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200 and response.text == "CHALLENGE_ACCEPTED":
            print("✅ Verificación EXITOSA")
        else:
            print("❌ Verificación FALLIDA")
    except Exception as e:
        print(f"❌ Error conectando: {e}")

def send_message_mock(phone, type_msg, content):
    """
    Simula el payload que envía Meta
    """
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123456", "phone_number_id": "123"},
                    "messages": [{
                        "from": phone,
                        "id": "wamid.HBgL...",
                        "timestamp": "123456789",
                        "type": type_msg,
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    message_node = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    
    if type_msg == "text":
        message_node["text"] = {"body": content}
    elif type_msg == "interactive":
        message_node["interactive"] = content

    return payload

def test_flow():
    phone = "51999999999"
    
    print("\n--- Probando Flujo: HOLA (POST) ---")
    payload = send_message_mock(phone, "text", "HOLA")
    requests.post(BASE_URL, json=payload)
    time.sleep(1) # Esperar background tasks

    print("\n--- Probando Flujo: DNI Correcto (POST) ---")
    payload = send_message_mock(phone, "text", "12345678")
    requests.post(BASE_URL, json=payload)
    time.sleep(1)

    print("\n--- Probando Flujo: Seleccionar Reclamo (POST) ---")
    # Interactive Button Reply
    interactive_content = {
        "type": "button_reply",
        "button_reply": {"id": "BTN_RECLAMO", "title": "Reportar Falla"}
    }
    payload = send_message_mock(phone, "interactive", interactive_content)
    requests.post(BASE_URL, json=payload)
    time.sleep(1)
    
    print("\n--- Probando Flujo: Seleccionar Categoría Electricidad (POST) ---")
    # Interactive List Reply
    interactive_content = {
        "type": "list_reply",
        "list_reply": {"id": "CAT_ELECTRICA", "title": "Electricidad", "description": "..."}
    }
    payload = send_message_mock(phone, "interactive", interactive_content)
    requests.post(BASE_URL, json=payload)
    time.sleep(1)

if __name__ == "__main__":
    test_verify()
    test_flow()
