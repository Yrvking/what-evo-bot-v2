from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from app.config import VERIFY_TOKEN
from app.models.schemas import WebhookPayload
from app.services.whatsapp import wa_client
from app.services.evolta import evolta_service
from app.services.procore import procore_service
from app.services.session import session_manager
from app.utils.logger import logger

app = FastAPI(title="Grupo Padova Postventa Bot")

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    """
    Endpoint de verifiación de Meta.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verificado exitosamente.")
        return PlainTextResponse(content=challenge, status_code=200)
    logger.warning("Fallo en verificación de Webhook.")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint principal para recibir mensajes.
    Usamos Request directamente para loguear todo antes de validar.
    """
    try:
        body = await request.json()
        logger.info(f"--- NUEVO EVENTO RECIBIDO ---")
        import json
        logger.info(f"PAYLOAD: {json.dumps(body, indent=2)}")
        
        # Validamos estructura básica manualmente o por esquema
        if body.get("entry") and body["entry"][0].get("changes") and body["entry"][0]["changes"][0].get("value").get("messages"):
            message_data = body["entry"][0]["changes"][0]["value"]["messages"][0]
            phone_number = message_data.get("from")
            
            # Determinamos el contenido del mensaje
            text_body = ""
            msg_type = message_data.get("type")
            
            if msg_type == "text" and message_data.get("text"):
                text_body = message_data["text"]["body"]
            elif msg_type == "interactive" and message_data.get("interactive"):
                int_data = message_data["interactive"]
                if int_data["type"] == "button_reply":
                    text_body = int_data["button_reply"]["id"]
                elif int_data["type"] == "list_reply":
                    text_body = int_data["list_reply"]["id"]
            
            logger.info(f"📩 Procesando mensaje de {phone_number}: {text_body}")
            background_tasks.add_task(process_message_flow, phone_number, text_body)
            
        return JSONResponse(content={"status": "success"}, status_code=200)
        
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        # Retornamos 200 para que Meta no siga reintentando si es un error lógico nuestro
        return JSONResponse(content={"status": "error"}, status_code=200)

async def process_message_flow(phone: str, text: str):
    """
    Lógica de negocio principal (Orquestador).
    """
    text_upper = text.strip().upper()
    current_state = session_manager.get_session(phone)
    
    # 1. Inicio / Saludo
    if text_upper in ["HOLA", "INICIO", "MENU", "TEST"]:
        await wa_client.send_text(
            phone, 
            "¡Hola! Bienvenido a Postventa Padova. 🏗️\nPara ubicar tu propiedad, por favor *escribe tu número de DNI o Carnet de Extranjería*."
        )
        session_manager.set_session(phone, "ESPERANDO_DNI")
        return

    # 2. Flujo DNI
    if current_state == "ESPERANDO_DNI":
        client = evolta_service.get_client_by_dni(text_upper)
        
        if client:
            nombre = client["nombre"]
            proyecto = client["proyecto"]
            unidad = client["unidad"]
            
            # Guardamos datos temporales básicos en el estado o podríamos ampliar el session_manager
            # Por simplicidad, asumimos que si está en MENU_PRINCIPAL ya sabemos quién es o lo volvemos A pedir
            # (En prod, guardaríamos el user_id en la sesión)
            
            mensaje = (
                f"✅ ¡Hola *{nombre}*!\nHemos validado tu identidad.\n\n"
                f"📂 *Tus Datos:*\n🏢 Proyecto: {proyecto}\n🏠 Unidad: {unidad}\n"
                f"🚗 Estac: {client['estacionamiento']}"
            )
            await wa_client.send_text(phone, mensaje)
            
            await wa_client.send_interactive_buttons(
                phone,
                "¿En qué podemos ayudarte hoy?",
                [
                    {"id": "BTN_RECLAMO", "title": "🛠️ Reportar Falla"},
                    {"id": "BTN_CONSULTA", "title": "📄 Consulta Admin"},
                    {"id": "BTN_SALIR", "title": "👋 Salir"}
                ]
            )
            session_manager.set_session(phone, "MENU_PRINCIPAL")
            # Hack simple para "recordar" el cliente: podríamos adjuntarlo al estado o usar otra key
            # Por ahora, confiamos en que en el siguiente paso solo necesitamos el teléfono
            
        else:
            await wa_client.send_text(
                phone, 
                "❌ No encontramos ese documento en nuestra base de datos Evolta.\nPor favor verifica y escríbelo nuevamente."
            )
            # Nos mantenemos en ESPERANDO_DNI

    # 3. Menú Principal
    elif current_state == "MENU_PRINCIPAL":
        if text_upper == "BTN_RECLAMO":
            sections = [
                {
                    "title": "Categorías",
                    "rows": [
                        {"id": "CAT_ELECTRICA", "title": "⚡ Electricidad", "description": "Luz, tomacorrientes"},
                        {"id": "CAT_GASFITERIA", "title": "💧 Gasfitería", "description": "Fugas, grifos"},
                        {"id": "CAT_ACABADOS", "title": "🎨 Acabados", "description": "Pintura, pisos"}
                    ]
                }
            ]
            await wa_client.send_interactive_list(
                phone, 
                "Selecciona el tipo de falla:", 
                "Menú de Categorías", 
                sections
            )
            session_manager.set_session(phone, "ESPERANDO_CATEGORIA")
            
        elif text_upper == "BTN_CONSULTA":
            await wa_client.send_text(phone, "Para consultas administrativas, por favor escribe a admin@padova.com.")
            session_manager.set_session(phone, None) # Reset
            
        elif text_upper == "BTN_SALIR":
            await wa_client.send_text(phone, "Gracias por usar nuestro servicio. ¡Hasta pronto!")
            session_manager.set_session(phone, None)

    # 4. Creación de Ticket
    elif current_state == "ESPERANDO_CATEGORIA":
        if text_upper.startswith("CAT_"):
            categoria = text_upper.replace("CAT_", "")
            
            # Recuperamos datos del cliente (Esto es una simplificación, 
            # idealmente el session manager debería guardar metadata del usuario también)
            # Para este MVP, usamos datos dummy o volvemos a consultar si tuvieramos el DNI guardado.
            # Aquí usaremos datos genéricos en el log para no complicar el SessionManager ahora.
            dummy_client_data = {"nombre": "Cliente (Recuperado)", "unidad": "Unidad X"}
            
            ticket_id = await procore_service.create_ticket(categoria, dummy_client_data, phone)
            
            mensaje_final = (
                f"✅ *Ticket #{ticket_id} Generado*\n"
                f"Hemos registrado tu reclamo de tipo: *{categoria}*.\n"
                f"🚀 Enviado a *Procore* para atención."
            )
            await wa_client.send_text(phone, mensaje_final)
            session_manager.set_session(phone, None)
        else:
             await wa_client.send_text(phone, "Por favor selecciona una categoría válida de la lista.")

    else:
        # Estado desconocido o mensaje fuera de flujo
        await wa_client.send_text(phone, "No entendí tu mensaje. Escribe 'HOLA' para comenzar.")
