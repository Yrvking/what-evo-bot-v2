# --- MENSAJES DEL CHATBOT ---
# Puedes editar estos textos libremente.

# Saludos
MSG_WELCOME_KNOWN = "👋 Hola *{nombre}*, bienvenido a Postventa.\n¿En qué podemos ayudarte hoy?"
MSG_WELCOME_UNKNOWN = "👋 Hola, bienvenido a Postventa.\nNo reconozco tu número en nuestra base de datos."
MSG_ASK_DNI = "🔍 Por favor, escribe tu **DNI o Carnet de Extranjería** para buscarte."
MSG_ASK_NAME = "⚠️ Tampoco encontré ese DNI. Por favor, escribe tu **Nombre y Apellido** completo."
MSG_NOT_FOUND_FINAL = "📋 No hemos encontrado tus datos. Continuaremos como **Cliente No Registrado**.\nPor favor selecciona tu proyecto:"

# Menú Principal

# Menú Principal
MSG_MENU_TITLE = "¿Qué deseas hacer?"
BTN_CONSULTA = "1. Consultas"
BTN_RECLAMO = "2. Reclamos"
BTN_OTROS = "3. Otros"

# Respuestas Menú
MSG_CONSULTA_INFO = "ℹ️ Para consultas generales, por favor revisa nuestro FAQ en la web o escribe tu consulta brevemente."
MSG_OTROS_INFO = "📞 Para otros temas, un asesor te contactará pronto."
MSG_RATE_LIMIT = "⚠️ *Límite Diario Alcanzado*\n\nPor seguridad y calidad de atención, solo procesamos **3 tickets diarios** por usuario.\nUn asesor revisará tus pendientes. ¡Intenta de nuevo mañana!"

# Flujo Reclamos
MSG_SEL_PROYECTO_TITLE = "Selecciona tu Proyecto:"
MSG_SEL_PROYECTO_BTN = "Ver Proyectos"
MSG_ERROR_PROYECTO = "⚠️ Por favor selecciona un proyecto de la lista."

MSG_ING_UNIDAD = "✅ Proyecto: *{proyecto}*\n\nPor favor escribe tu **Número de Departamento/Unidad** (Ej: 501, A-202)."

# Categorías Detalladas
MSG_SEL_CATEGORIA_TITLE = "Selecciona la categoría del problema:"
MSG_SEL_CATEGORIA_BTN = "Ver Categorías"
CATEGORIAS = [
    {"id": "CAT_ACABADOS", "title": "1. Acabados Húmedos", "desc": "Pintura, Enchapes, Papel"},
    {"id": "CAT_PISOS", "title": "2. Pisos y Zócalos", "desc": "Mármol, Laminado, Cerámico"},
    {"id": "CAT_CARPINTERIA", "title": "3. Carpintería", "desc": "Puertas, Ventanas, Muebles"},
    {"id": "CAT_SANITARIAS", "title": "4. Inst. Sanitarias", "desc": "Grifería, Inodoros, Fugas"},
    {"id": "CAT_ELECTRICAS", "title": "5. Inst. Eléctricas", "desc": "Tomacorrientes, Luces"},
    {"id": "CAT_EQUIPAMIENTO", "title": "6. Equipamiento", "desc": "Cocina, Campana, Terma"},
    {"id": "CAT_COMUNES", "title": "7. Áreas Comunes", "desc": "Hall, Ascensor, Pasillos"},
    {"id": "CAT_OTROS", "title": "8. Otros", "desc": "Otros problemas"}
]

MSG_DESC_PROBLEMA = "📝 **Categoría: {categoria}**\n\nCuéntanos el detalle. Puedes enviar texto, fotos 📸 o videos 🎥.\nCuando termines, presiona el botón **Generar Ticket** 👇."
MSG_DESC_EMPTY = "⚠️ Necesitamos al menos una descripción o foto."

BTN_FIN = "Generar Reclamo"

# Cierre
MSG_TICKET_CREATED = "✅ **Ticket Generado: {ticket_id}**\n\nHemos registrado tu reclamo para *{proyecto}*.\nUn asesor te contactará en 48 horas."
MSG_TIMEOUT = "⏳ Hemos detectado inactividad.\n\n✅ Se ha generado tu ticket automáticamente con la información recibida: *{ticket_id}*.\n\n¡Gracias por contactarnos! 👋"
MSG_TIMEOUT_EMPTY = "⏳ Sesión cerrada por inactividad. ¡Gracias por contactarnos! 👋"

# Multi-Reclamo
MSG_ANOTHER_ONE = "¿Deseas reportar algo más?"
BTN_YES = "Sí, otro reclamo"
BTN_NO = "No, gracias"
MSG_GOODBYE = "¡Gracias por contactarnos! 👋"
