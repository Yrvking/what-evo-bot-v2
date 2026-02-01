import os

# --- CREDENCIALES ---
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# --- RUTAS DE ARCHIVOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Excel de Clientes (Base de Datos de Lectura)
def get_client_db_path():
    # 1. Prioridad: Base generada automáticamente por EvoltaService
    auto_db = os.path.join(PROJECT_ROOT, "CLIENTES_DB.xlsx")
    if os.path.exists(auto_db):
        return auto_db
        
    # 2. Fallback: Archivos manuales antiguos
    import glob
    files = glob.glob(os.path.join(PROJECT_ROOT, "Reporte_Stock_*.xlsx"))
    if files:
        return max(files, key=os.path.getmtime)
        
    return auto_db # Retornamos path por defecto aunque no exista aún

EXCEL_FILE_PATH = get_client_db_path()

# Archivos de Persistencia (Escritura)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MEDIA_DIR = os.path.join(DATA_DIR, "media")
CLAIMS_DB = os.path.join(DATA_DIR, "claims.csv")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# --- COLUMNAS DEL EXCEL ---
# --- COLUMNAS DEL EXCEL (VENTAS REPORT) ---
# Basado en ETL_Evolta script
COL_CELULAR = "TelefonoCelular"  # Antes: Celular
COL_DNI = "NroDocumentoTitular"  # Antes: NroDocumento
COL_NOMBRE = "NombresTitular"    # Antes: Nombres
COL_PROYECTO = "Proyecto"        # Se mantiene
COL_DPTO = "NroInmueble_1"       # Usamos la 1ra unidad como referencia principal

# --- LISTA DE PROYECTOS VÁLIDOS (MENÚ) ---
PROYECTOS_VALIDOS = [
    "Loma de Carabayllo 3",
    "Loma de Carabayllo 4",
    "Loma de Carabayllo 5",
    "Sunny",
    "Helio Cercado",
    "Helio Santa Beatriz",
    "Litoral 900",
    "Monte Umbroso",
    "Sucre 296",
    "San Martin 230"
]

# --- LEGACY SUPPORT ---
# Variable necesaria para evitar crash en archivos antiguos (app.services.evolta)
BD_EVOLTA = {}
