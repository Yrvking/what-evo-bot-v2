from flask import Flask, request, jsonify, render_template, redirect
from dotenv import load_dotenv
load_dotenv() # Cargar variables de entorno desde .env local
import requests
import os
import time
import threading
import schedule
import datetime
from app.config import TOKEN, PHONE_ID, VERIFY_TOKEN, PROYECTOS_VALIDOS, MEDIA_DIR
from app.services.excel_service import excel_service
from app.services.claims_service import claims_service
from app.services.db_service import db_service
from app.services.evolta_service import evolta_service
from app import messages

app = Flask(__name__, template_folder="app/templates")

# --- ESTADO DE SESIÓN (RAM) ---
# --- ESTADO DE SESIÓN (RAM) ---
user_sessions = {}
processed_msg_ids = set() # Cache de IDs procesados

def is_message_processed(msg_id):
    return msg_id in processed_msg_ids

def mark_message_processed(msg_id):
    processed_msg_ids.add(msg_id)
    # Limpieza básica si crece mucho (opcional, por ahora simple)
    if len(processed_msg_ids) > 1000:
        processed_msg_ids.clear()

# --- CONSTANTES DE ESTADO ---
STATE_INIT = "INIT"
STATE_MENU_PRINCIPAL = "MENU_PRINCIPAL" 
STATE_SEL_PROYECTO = "SEL_PROYECTO"
STATE_ING_UNIDAD = "ING_UNIDAD"
STATE_SEL_CATEGORIA = "SEL_CATEGORIA" # Nuevo Estado
STATE_DESC_PROBLEMA = "DESC_PROBLEMA"
STATE_MULTI_OPTION = "MULTI_OPTION"   # Nuevo Estado: ¿Otro reclamo?

# --- CONFIGURACIÓN DE TIEMPO ---
TIMEOUT_SECONDS = 300 # 5 Minutos

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Token inválido", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    try:
        if data.get("entry"):
            changes = data["entry"][0].get("changes", [])
            if changes and changes[0].get("value").get("messages"):
                message_data = changes[0]["value"]["messages"][0]
                phone_number = message_data["from"]
                
                # Gestión de tipos de mensaje
                msg_type = message_data["type"]
                text_body = ""
                
                if msg_type == "text":
                    text_body = message_data["text"]["body"]
                elif msg_type == "interactive":
                    int_type = message_data["interactive"]["type"]
                    if int_type == "button_reply":
                        text_body = message_data["interactive"]["button_reply"]["id"]
                    elif int_type == "list_reply":
                        text_body = message_data["interactive"]["list_reply"]["id"]
                elif msg_type in ["image", "video", "document"]:
                    media_id = message_data[msg_type].get("id")
                    text_body = f"__MEDIA_{msg_type.upper()}__"

                msg_id = message_data.get("id", "NO_ID")
                print(f"📩 Msg ID: {msg_id} | De: {phone_number} | Texto: {text_body}")
                
                # --- DEDUPLICACIÓN SIMPLE ---
                if is_message_processed(msg_id):
                    print(f"🔁 Mensaje duplicado ignorado: {msg_id}")
                    return jsonify({"status": "ignored"}), 200
                mark_message_processed(msg_id)

                procesar_mensaje(phone_number, text_body, message_data)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error webhook: {e}")
        return jsonify({"status": "error"}), 500

def procesar_mensaje(phone, text, raw_msg):
    if phone not in user_sessions:
        user_sessions[phone] = {"state": STATE_INIT, "data": {}}
    
    # Actualizar Timestamp
    user_sessions[phone]["last_interaction"] = time.time()
    
    session = user_sessions[phone]
    state = session["state"]
    text_upper = text.strip().upper()

    # --- COMANDOS GLOBALES ---
    if text_upper in ["HOLA", "INICIO", "REINICIAR", "MENU"]:
        session["state"] = STATE_INIT
        state = STATE_INIT

    # --- MÁQUINA DE ESTADOS ---

    # --- MÁQUINA DE ESTADOS ---

    # 1. IDENTIFICACIÓN (Flow Triangulación)
    if state == STATE_INIT:
        users = excel_service.find_users_by_phone(phone)
        if users:
            # ENCONTRADO POR TELÉFONO
            nombre = users[0]["nombre"]
            session["data"]["nombre"] = nombre
            session["data"]["dni"] = users[0]["dni"]
            session["data"]["phone"] = phone
            session["data"]["tipo_cliente"] = "REGISTRADO"
            
            msg = messages.MSG_WELCOME_KNOWN.format(nombre=nombre)
            send_interactive_buttons(phone, msg, [
                {"id": "OPT_CONSULTA", "title": messages.BTN_CONSULTA},
                {"id": "OPT_RECLAMO", "title": messages.BTN_RECLAMO},
                {"id": "OPT_OTROS", "title": messages.BTN_OTROS}
            ])
            session["state"] = STATE_MENU_PRINCIPAL
        else:
            # NO ENCONTRADO -> PEDIR DNI
            send_message(phone, messages.MSG_WELCOME_UNKNOWN)
            time.sleep(1)
            send_message(phone, messages.MSG_ASK_DNI)
            session["state"] = "WAITING_DNI"
        return

    # 1.5. ESPERANDO DNI
    elif state == "WAITING_DNI":
        dni_input = text.strip()
        users = excel_service.find_users_by_dni(dni_input)
        
        if users:
            # ENCONTRADO POR DNI
            nombre = users[0]["nombre"]
            session["data"]["nombre"] = nombre
            session["data"]["dni"] = users[0]["dni"]
            session["data"]["phone"] = phone # Mantenemos el phone actual aunque no matchee en DB
            session["data"]["tipo_cliente"] = "REGISTRADO"

            send_message(phone, messages.MSG_WELCOME_KNOWN.format(nombre=nombre))
            send_interactive_buttons(phone, messages.MSG_MENU_TITLE, [
                {"id": "OPT_CONSULTA", "title": messages.BTN_CONSULTA},
                {"id": "OPT_RECLAMO", "title": messages.BTN_RECLAMO},
                {"id": "OPT_OTROS", "title": messages.BTN_OTROS}
            ])
            session["state"] = STATE_MENU_PRINCIPAL
        else:
            # NO ENCONTRADO DNI -> PEDIR NOMBRE
            session["data"]["dni"] = dni_input # Guardamos el DNI ingresado aunque no esté en DB
            send_message(phone, messages.MSG_ASK_NAME)
            session["state"] = "WAITING_NAME"

    # 1.6. ESPERANDO NOMBRE
    elif state == "WAITING_NAME":
        name_input = text.strip()
        users = excel_service.find_users_by_name(name_input)
        
        if users:
            # ENCONTRADO POR NOMBRE (Tomamos el primero por convención)
            nombre = users[0]["nombre"]
            session["data"]["nombre"] = nombre
            session["data"]["dni"] = users[0]["dni"]
            session["data"]["phone"] = phone
            session["data"]["tipo_cliente"] = "REGISTRADO"
            
            send_message(phone, messages.MSG_WELCOME_KNOWN.format(nombre=nombre))
            send_interactive_buttons(phone, messages.MSG_MENU_TITLE, [
                {"id": "OPT_CONSULTA", "title": messages.BTN_CONSULTA},
                {"id": "OPT_RECLAMO", "title": messages.BTN_RECLAMO},
                {"id": "OPT_OTROS", "title": messages.BTN_OTROS}
            ])
            session["state"] = STATE_MENU_PRINCIPAL
        else:
            # NO ENCONTRADO NADA -> CLIENTE NO REGISTRADO
            session["data"]["nombre"] = name_input # Usamos el nombre que nos dio
            # Mantenemos el session["data"]["dni"] que guardamos en el paso anterior
            session["data"]["phone"] = phone
            session["data"]["tipo_cliente"] = "NO-REGISTRADO"
            
            # Directo a Reclamos (como pedía el prompt) o Menú? 
            # El prompt dice: "SI AUN ASI NO COINCIDE DEBEMOS SEGUIR CON EL PROCESO DE SIEMPRE DE MOSTRARLE LAS OPCIONES DE PROYECTO"
            # O sea, saltamos directo a elegir proyecto (asumiendo que quiere reclamar)
            
            send_message(phone, messages.MSG_NOT_FOUND_FINAL)
            
            # Mostramos Proyectos directamente
            rows = [{"id": p, "title": p, "description": ""} for p in PROYECTOS_VALIDOS]
            send_interactive_list(phone, messages.MSG_SEL_PROYECTO_TITLE, messages.MSG_SEL_PROYECTO_BTN, [{"title": "Proyectos", "rows": rows}])
            session["state"] = STATE_SEL_PROYECTO

    # 2. MENÚ PRINCIPAL
    elif state == STATE_MENU_PRINCIPAL:
        if text_upper == "OPT_RECLAMO" or "RECLAMO" in text_upper or text_upper == "2":
            # Verificar Rate Limit antes de empezar
            if not claims_service.check_rate_limit(phone):
                send_message(phone, messages.MSG_RATE_LIMIT)
                session["state"] = STATE_INIT # Reset
                return

            # Mostrar Proyectos
            rows = [{"id": p, "title": p, "description": ""} for p in PROYECTOS_VALIDOS]
            send_interactive_list(phone, messages.MSG_SEL_PROYECTO_TITLE, messages.MSG_SEL_PROYECTO_BTN, [{"title": "Proyectos", "rows": rows}])
            session["state"] = STATE_SEL_PROYECTO
        
        elif text_upper == "OPT_CONSULTA" or text_upper == "1":
            send_message(phone, messages.MSG_CONSULTA_INFO)
        else:
            send_message(phone, messages.MSG_OTROS_INFO)
    
    # 3. SELECCIÓN DE PROYECTO
    elif state == STATE_SEL_PROYECTO:
        proyecto_elegido = text 
        if proyecto_elegido in PROYECTOS_VALIDOS:
            session["data"]["proyecto"] = proyecto_elegido
            send_message(phone, messages.MSG_ING_UNIDAD.format(proyecto=proyecto_elegido))
            session["state"] = STATE_ING_UNIDAD
        else:
            send_message(phone, messages.MSG_ERROR_PROYECTO)

    # 4. INGRESO DE UNIDAD
    elif state == STATE_ING_UNIDAD:
        session["data"]["unidad"] = text
        # Ahora vamos a Categorías en vez de directo al problema
        rows = [{"id": c["id"], "title": c["title"], "description": c["desc"]} for c in messages.CATEGORIAS]
        send_interactive_list(phone, messages.MSG_SEL_CATEGORIA_TITLE, messages.MSG_SEL_CATEGORIA_BTN, [{"title": "Categorías", "rows": rows}])
        session["state"] = STATE_SEL_CATEGORIA

    # 5. SELECCIÓN DE CATEGORÍA (NUEVO)
    elif state == STATE_SEL_CATEGORIA:
        # Validar si selección válida (buscamos por ID)
        cat_found = next((c for c in messages.CATEGORIAS if c["id"] == text), None)
        
        if cat_found:
            session["data"]["categoria"] = cat_found["title"] # Guardamos el nombre bonito
            session["data"]["descripcion"] = []
            session["data"]["media_paths"] = []
            
            send_message(phone, messages.MSG_DESC_PROBLEMA.format(categoria=cat_found["title"]))
            session["state"] = STATE_DESC_PROBLEMA
        else:
            # Si escribió texto en vez de clickear lista, intentamos mapear o repetimos
            send_message(phone, "⚠️ Por favor selecciona una categoría de la lista.")

    # 6. DESCRIPCIÓN DEL PROBLEMA
    elif state == STATE_DESC_PROBLEMA:
        # Normalizamos la entrada para aceptar el botón (ID: BTN_FIN) o el texto manual
        is_finish_command = (text_upper == "FIN" or text_upper == "BTN_FIN" or "GENERAR TICKET" in text_upper or "GENERAR RECLAMO" in text_upper)

        if is_finish_command:
            desc_full = "\n".join(session["data"]["descripcion"])
            if not desc_full and not session["data"]["media_paths"]:
                send_message(phone, messages.MSG_DESC_EMPTY)
                return

            # Guardar Ticket
            ticket_id = claims_service.create_ticket(
                session["data"], 
                session["data"].get("categoria", "General"), 
                desc_full,
                session["data"]["media_paths"]
            )
            
            send_message(phone, messages.MSG_TICKET_CREATED.format(ticket_id=ticket_id, proyecto=session["data"]["proyecto"]))
            
            # PREGUNTAR SI QUIERE OTRO (MULTI-RECLAMO)
            if claims_service.check_rate_limit(phone):
                send_interactive_buttons(phone, messages.MSG_ANOTHER_ONE, [
                    {"id": "BTN_YES", "title": messages.BTN_YES},
                    {"id": "BTN_NO", "title": messages.BTN_NO}
                ])
                session["state"] = STATE_MULTI_OPTION
            else:
                send_message(phone, messages.MSG_GOODBYE)
                session["state"] = STATE_INIT
        
        else:
            # Recepción de inputs (texto o multimedia)
            msg_type = raw_msg.get("type", "text")
            
            # Caso Multimedia (Imagen, Video, Documento)
            if msg_type in ["image", "video", "document"]:
                media_id = raw_msg[msg_type].get("id")
                # Capturar caption si existe
                caption = raw_msg[msg_type].get("caption", "")
                
                session["data"]["media_paths"].append(f"[{msg_type}:{media_id}]")
                
                reply_text = "👍 Archivo recibido."
                if caption:
                    session["data"]["descripcion"].append(caption)
                    reply_text += " (Texto adjunto guardado)"
            
            # Caso Texto Normal
            elif msg_type == "text":
                session["data"]["descripcion"].append(text)
                reply_text = "👍 Texto agregado."
            
            # Caso Raro (Sticker, Location, etc)
            else:
                reply_text = "⚠️ Tipo de mensaje no soportado."

            # SIEMPRE enviamos el botón para confirmar fin
            send_interactive_buttons(phone, f"{reply_text} ¿Algo más?", [
                {"id": "BTN_FIN", "title": messages.BTN_FIN}
            ])

    # 7. MULTI-OPCIÓN (NUEVO)
    elif state == STATE_MULTI_OPTION:
        if text_upper == "BTN_YES":
            # Volvemos a elegir Categoría (mantenemos Proyecto y Unidad)
            rows = [{"id": c["id"], "title": c["title"], "description": c["desc"]} for c in messages.CATEGORIAS]
            send_interactive_list(phone, messages.MSG_SEL_CATEGORIA_TITLE, messages.MSG_SEL_CATEGORIA_BTN, [{"title": "Categorías", "rows": rows}])
            session["state"] = STATE_SEL_CATEGORIA
        else:
            send_message(phone, messages.MSG_GOODBYE)
            session["state"] = STATE_INIT

# --- UTILS WHATSAPP API ---

def send_message(to_number, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text}}
    requests.post(url, headers=headers, json=payload)

def send_interactive_buttons(to_number, body_text, buttons):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    # Cortamos title a 20 chars por límite de API
    buttons_data = [{"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}} for b in buttons]
    payload = {
        "messaging_product": "whatsapp", "to": to_number, "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": buttons_data}
        }
    }
    requests.post(url, headers=headers, json=payload)

def send_interactive_list(to_number, body_text, button_text, sections):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", "to": to_number, "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

# --- THREAD TIMEOUT ---
# --- DASHBOARD ROUTES ---
from app.services.procore_constants import PROCORE_ESPECIALIDADES

@app.route('/dashboard')
def dashboard():
    tickets = db_service.get_all_tickets()
    return render_template('dashboard.html', tickets=tickets, especialidades=PROCORE_ESPECIALIDADES)

@app.route('/dashboard/update_procore', methods=['POST'])
def update_ticket_procore():
    data = request.json
    success = db_service.update_ticket_procore(
        ticket_id=data.get("id"),
        especialidad=data.get("especialidad"),
        tipo=data.get("tipo"),
        prioridad=data.get("prioridad"),
        asignado=data.get("asignado"),
        status=data.get("status")
    )
    return jsonify({"success": success})

@app.route('/dashboard/update_db', methods=['POST'])
def manual_update_db():
    # Ejecutar en hilo para no bloquear
    def run_async():
        evolta_service.run_update()
        # Recargar servicio de excel
        excel_service._load_data()
    
    threading.Thread(target=run_async).start()
    return redirect('/dashboard')

# --- SCHEDULER & THREADS ---
def run_scheduler():
    """Ejecuta tareas programadas (1 PM)."""
    schedule.every().day.at("13:00").do(evolta_service.run_update)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def check_timeouts():
    while True:
        time.sleep(60)
        # ... (Mantener lógica original de timeouts si se desea, por brevedad omitida en reemplazo parcial pero asumimos existe)
        # Por seguridad, incluimos la lógica completa de timeout aquí o usamos la existente.
        # Al reemplazar, debo asegurame de no borrar la lógica de timeouts existente si uso replace parcial.
        # ESTE BLOQUE SOLO AGREGA EL SCHEDULER, EL TIMEOUT YA ESTABA. 
        # PERO el replace afecta la llamada a Thread.
        
        now = time.time()
        for phone, session in list(user_sessions.items()):
            if session["state"] == STATE_DESC_PROBLEMA:
                last_time = session.get("last_interaction", 0)
                if now - last_time > TIMEOUT_SECONDS:
                    desc_full = "\n".join(session["data"].get("descripcion", []))
                    media_files = session["data"].get("media_paths", [])
                    if desc_full or media_files:
                        ticket_id = claims_service.create_ticket(session["data"], session["data"].get("categoria", "Auto"), desc_full, media_files)
                        send_message(phone, messages.MSG_TIMEOUT.format(ticket_id=ticket_id))
                    else:
                        send_message(phone, messages.MSG_TIMEOUT_EMPTY)
                    user_sessions[phone] = {"state": STATE_INIT, "data": {}}

# Iniciar hilos
threading.Thread(target=check_timeouts, daemon=True).start()
threading.Thread(target=run_scheduler, daemon=True).start()

if __name__ == "__main__":
    app.run(port=8000, debug=True)
