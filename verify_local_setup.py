import os
import sys

# Color output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def log(msg, success=True):
    color = GREEN if success else RED
    print(f"{color}{msg}{RESET}")

print("🔍 Iniciando Verificación Pre-Despliegue...")

# 1. Verificar .env
if os.path.exists(".env"):
    log("✅ Archivo .env encontrado.")
else:
    log("❌ FALTA archivo .env", False)
    sys.exit(1)

# 2. Verificar Carga de Variables (Refactor Seguridad)
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from app.config import TOKEN, PHONE_ID
    from app.services.media_service import API_KEY, CLOUD_NAME
    
    if TOKEN and PHONE_ID and API_KEY and CLOUD_NAME:
        log(f"✅ Variables de Entorno cargadas correctamente.")
        log(f"   - TOKEN: {TOKEN[:5]}...")
        log(f"   - CLOUD_NAME: {CLOUD_NAME}")
    else:
        log("❌ Variables de entorno incompletas (Revisar .env)", False)
except Exception as e:
    log(f"❌ Error importando configuración: {e}", False)
    sys.exit(1)

# 3. Verificar Procore Constants
try:
    from app.services.procore_constants import PROCORE_ESPECIALIDADES
    if len(PROCORE_ESPECIALIDADES) > 0:
        log(f"✅ Constantes Procore cargadas ({len(PROCORE_ESPECIALIDADES)} especialidades).")
    else:
        log("❌ Lista de especialidades vacía", False)
except ImportError:
    log("❌ No se encontró app.services.procore_constants", False)

# 4. Verificar Base de Datos y Dashboard (Backend)
try:
    from app.services.db_service import db_service
    tickets = db_service.get_all_tickets()
    log(f"✅ Conexión a Base de Datos (Supabase) exitosa. {len(tickets)} tickets encontrados.")
    
    # Verificar columnas nuevas en el primer ticket si existe
    if tickets:
        last_t = tickets[0]
        if "procore_status" in last_t:
            log("✅ Campo 'procore_status' detectado en tickets.")
        else:
            log("❌ Falta campo 'procore_status' en respuesta de DB.", False)

except Exception as e:
    log(f"❌ Error en Base de Datos: {e}", False)

# 5. Verificar Dashboard Route (Flask)
try:
    from run import app
    client = app.test_client()
    response = client.get('/dashboard')
    
    if response.status_code == 200:
        content = response.data.decode('utf-8')
        if "Status Procore" in content and "Revisar" in content:
            log("✅ Dashboard renderizado correctamente con campos Procore.")
        else:
            log("⚠️ Dashboard cargó pero no veo las columnas Procore nuevas.", False)
    else:
        log(f"❌ Error cargando /dashboard: Status {response.status_code}", False)

    # 6. Simular Mensaje Webhook ("HOLA")
    log("🤖 Simulando mensaje 'HOLA' al Webhook...")
    mock_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "1234567890", "phone_number_id": "1234567890"},
                    "messages": [{
                        "from": "51999999999",
                        "id": "wamid.TEST",
                        "timestamp": "1234567890",
                        "text": {"body": "HOLA"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    # Mockear requests.post para no enviar mensaje real a Meta (evitar errores de token real en test)
    import unittest.mock
    with unittest.mock.patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        res_hook = client.post('/webhook', json=mock_payload)
        
        if res_hook.status_code == 200:
            log("✅ Webhook procesó el mensaje exitosamente (Status 200).")
            # Verificar si intentó responder (side effect check)
            if mock_post.called:
                log("✅ El bot intentó enviar una respuesta a Meta (requests.post llamado).")
            else:
                log("⚠️ El bot no respondió nada (¿Lógica falló?).", False)
        else:
            log(f"❌ Webhook falló: {res_hook.status_code}", False)

except Exception as e:
    log(f"❌ Error probando Flask: {e}", False)

print("\n🏁 Verificación Completada.")
