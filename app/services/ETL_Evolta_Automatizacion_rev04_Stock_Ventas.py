import time
import os
import glob
import shutil
import pandas as pd
import smtplib
import traceback
import random
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN DE CREDENCIALES ---
USER_CRED = "calopez"
PASS_CRED = "Lopez201217**"

URL_LOGIN = "https://v4.evolta.pe/Login/Acceso/Index"
URL_REPORTE_STOCK = "https://v4.evolta.pe/Reportes/RepCargaStock/IndexNuevoRepStock"
URL_REPORTE_VENTAS = "https://v4.evolta.pe/Reportes/RepVenta/Index"

# Configuración SMTP
EMAIL_FROM = "sistema.padova@gmail.com"
EMAIL_TO = "yleon@padovasac.com"
EMAIL_PASS = "mrby sonn jpnp lcvw"

# Reglas de Negocio
TARGET_PROJECTS = [
    'SUNNY', 
    'LITORAL 900', 
    'HELIO - SANTA BEATRIZ', 
    'LOMAS DE CARABAYLLO'
]

# Directorio de trabajo principal (Stock)
DOWNLOAD_DIR = r"C:\Users\Administrador.SERVERPADOVA\Documents\EVOLTA\Script\descargas_stock"
DOWNLOAD_DIR_VENTAS = r"C:\Users\Administrador.SERVERPADOVA\Documents\EVOLTA\Script\descargas_ventas"

# Crear directorios si no existen
for dir_path in [DOWNLOAD_DIR, DOWNLOAD_DIR_VENTAS]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# Configuración de años para reporte de ventas (máximo 1 año por descarga)
AÑOS_VENTAS = [2021, 2022, 2023, 2024, 2025, 2026]

# ============================================================================
# DEFINICIÓN DE COLUMNAS MAESTRAS PARA NORMALIZACIÓN
# ============================================================================

COLUMNAS_BASE = [
    'CorrelativoOC', 'FechaVenta', 'FechaPreminuta', 'FechaEntrega_Minuta',
    'Fecha_Registro_Sistema', 'Fecha_Primera_Visita', 'FechaProspecto', 'FechaDevolucion',
    'Estado', 'EstadoOC', 'TipoDocumentoTitular', 'NroDocumentoTitular', 'NombresTitular',
    'CorreoElectronico', 'CorreoElectronico2', 'TelefonoCasa', 'TelefonoCelular',
    'TelefonoCelular2', 'Genero', 'Estado_Civil', 'Provincia_Procedencia',
    'Distrito_Procedencia', 'Direccion', 'RangoEdad', 'NivelInteres', 'ComoSeEntero',
    'FormaContacto', 'PerfilCrediticio', 'Institucion', 'NivelIngresos', 'MotivoCompra',
    'Promocion', 'ContenidoPromocion', 'ValorTotalCombo', 'ReferidoPor'
]

def generar_columnas_inmueble(n):
    """Genera las 12 columnas para un inmueble n"""
    return [
        f'T/M_{n}', f'TipoInmueble_{n}', f'Modelo_{n}', f'NroInmueble_{n}',
        f'NroPiso_{n}', f'Vista_{n}', f'PrecioBase_{n}', f'PrecioLista_{n}',
        f'DescuentoLista_{n}', f'TotalLista_{n}', f'PrioridadOC_{n}', f'Orden_{n}'
    ]

COLUMNAS_INMUEBLES = []
for i in range(1, 9):
    COLUMNAS_INMUEBLES.extend(generar_columnas_inmueble(i))

COLUMNAS_FINALES = [
    'CargaFamiliar', 'Proyecto', 'Etapa', 'SubTotal', 'MontoDescuento', 'PrecioVenta',
    'MontoSeparacion', 'BonoVerde', 'TipodeBono', 'MontoBono', 'MontoPagadoBono',
    'PorcentajePagado', 'EstadoBono', 'MontoCuotaInicial', 'MontoPagadoCI',
    'PorcetanjePagadoCI', 'Estado_CI', 'MontoFinanciamiento', 'MontoDesembolsado',
    'PorcetanjePagado_SF', 'EstadoSF', 'TipoMoneda', 'TipoCambio', 'TipoFinanciamiento',
    'EntidadFinanciamiento', 'Vendedor', 'utm_medium', 'utm_source', 'utm_campaign',
    'utm_term', 'utm_content', 'Es_Cotizador_Evolta', 'Es_Formulario_Evolta',
    'Es_Cotizador_y_Formulario_Evolta', 'Ult_Comentario', 'MigracionMasiva',
    'TotalCuotaInicial', 'TotalCuotaFinanciar', 'Areaterreno', 'TasaInteres',
    'CallCenter', 'TipoProceso', 'Puesto', 'IdProforma', 'AÑO'
]

COLUMNAS_MAESTRAS = COLUMNAS_BASE + COLUMNAS_INMUEBLES + COLUMNAS_FINALES


def get_driver(download_dir):
    """Inicializa driver con configuración de descarga específica."""
    options = webdriver.ChromeOptions()
    
    # --- FLAGS DE ESTABILIDAD ---
    options.add_argument("--headless=new") 
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu") 
    options.add_argument("--no-sandbox") 
    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("--disable-software-rasterizer") 
    options.add_argument("--disable-features=VizDisplayCompositor") 
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3") 
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def clean_environment(directory, extension="*.xlsx"):
    """Limpia archivos previos de un directorio."""
    print(f">> [MAINTENANCE] Limpiando directorio: {directory}")
    files = glob.glob(os.path.join(directory, extension))
    for f in files:
        try: 
            os.remove(f)
        except: 
            pass


def dismiss_popup(driver):
    """Estrategia 'Anti-Propaganda'."""
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(1)
        driver.execute_script("document.body.click();")
        time.sleep(1)
    except Exception:
        pass


def robust_login(driver, wait):
    """Manejo de Login."""
    print(">> [LOGIN] Navegando al login...")
    try:
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        
        try: 
            user_field = driver.find_element(By.ID, "UserName")
        except:
            try: 
                user_field = driver.find_element(By.NAME, "Usuario")
            except: 
                user_field = driver.find_element(By.XPATH, "//input[@type='text']")
        
        user_field.clear()
        user_field.send_keys(USER_CRED)
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(PASS_CRED)

        try:
            driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']").click()
        except: 
            pass

        try:
            wait.until(EC.url_changes(URL_LOGIN))
            print(">> [LOGIN] Exitoso (URL Changed).")
        except:
            print(">> [LOGIN] Continuamos (Sin cambio URL detectado, asumiendo éxito).")
            
        time.sleep(2)
        dismiss_popup(driver)
            
    except Exception as e:
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_login.png"))
        raise Exception(f"Error Login: {e}")


def execute_stock_extraction(driver):
    """Descarga reporte de Stock usando el ID fijo 'btnExportar'."""
    print(f">> [EXTRACTION STOCK] Navegando al módulo: {URL_REPORTE_STOCK}")
    driver.get(URL_REPORTE_STOCK)
    wait = WebDriverWait(driver, 30)
    time.sleep(3)
    dismiss_popup(driver)
    
    # 1. FILTRO PROYECTO: TODOS
    try:
        print("   -> Configurando filtro de Proyecto...")
        select_element = None
        try: 
            select_element = wait.until(EC.presence_of_element_located((By.ID, "ProyectoId")))
        except: 
            select_element = driver.find_element(By.TAG_NAME, "select")
            
        select = Select(select_element)
        try: 
            select.select_by_visible_text("Todos")
        except: 
            try: 
                select.select_by_visible_text("TODOS")
            except: 
                select.select_by_index(0)
        print("   -> Filtro establecido: TODOS")
        time.sleep(1)
    except Exception as e:
        print(f"   !! Warning UI: No se pudo manipular dropdown (Usando default): {e}")

    # 2. CLICK EN EXPORTAR
    try:
        print("   -> Buscando botón 'btnExportar'...")
        export_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnExportar")))
        
        print("   -> Click en Exportar (JS)...")
        driver.execute_script("arguments[0].click();", export_btn)
        
        # 3. ESPERA DE DESCARGA
        timeout = 300 
        elapsed = 0
        file_downloaded = False
        
        print("   -> Esperando descarga (Max 300s)...")
        while elapsed < timeout:
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
            valid_files = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
            
            if valid_files:
                latest = max(valid_files, key=os.path.getctime)
                if (datetime.now().timestamp() - os.path.getctime(latest)) < 300:
                    print(f"   -> [OK] Archivo descargado: {os.path.basename(latest)}")
                    file_downloaded = True
                    break
            
            time.sleep(1)
            elapsed += 1
            
        if not file_downloaded:
            raise Exception("Tiempo de espera agotado. El archivo no se descargó.")
            
    except Exception as e:
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_extraction.png"))
        raise Exception(f"Fallo crítico en botón exportar: {e}")


def set_date_field(driver, field_id, date_str):
    """Establece una fecha en un campo de fecha."""
    try:
        date_field = driver.find_element(By.ID, field_id)
        driver.execute_script("arguments[0].value = '';", date_field)
        date_field.clear()
        date_field.send_keys(date_str)
        time.sleep(0.5)
    except Exception as e:
        print(f"   !! Error estableciendo fecha en {field_id}: {e}")


def execute_ventas_extraction_year(driver, wait, año):
    """Descarga reporte de Ventas para un año específico en formato CSV."""
    print(f"\n>> [EXTRACTION VENTAS {año}] Procesando...")
    
    driver.get(URL_REPORTE_VENTAS)
    time.sleep(4)  # Esperar carga completa
    dismiss_popup(driver)
    
    # Calcular fechas del año
    fecha_inicio = f"01/01/{año}"
    fecha_fin = f"31/12/{año}"
    
    # Si es el año actual, usar la fecha de hoy como fin
    if año == datetime.now().year:
        fecha_fin = datetime.now().strftime("%d/%m/%Y")
    
    print(f"   -> Rango: {fecha_inicio} - {fecha_fin}")
    
    try:
        # 1. FILTRO PROYECTO: TODOS (el primero en la página)
        try:
            # Buscar todos los selects y tomar el primero (Proyecto)
            proyecto_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select")))
            select = Select(proyecto_select)
            select.select_by_index(0)  # Primera opción suele ser "TODOS"
            print("   -> Proyecto: TODOS (index 0)")
            time.sleep(0.5)
        except Exception as e:
            print(f"   !! Warning Proyecto: {e}")
        
        # 2. ESTABLECER FECHAS - Buscar por label "Fecha de inicio" y "Fecha de fin"
        print("   -> Configurando fechas...")
        
        fecha_inicio_ok = False
        fecha_fin_ok = False
        
        # Estrategia 1: Buscar input después del label "Fecha de inicio"
        try:
            # Buscar el contenedor que tiene el label y el input
            fecha_inicio_input = driver.find_element(By.XPATH, 
                "//label[contains(text(),'Fecha de inicio')]/following::input[1] | " +
                "//span[contains(text(),'Fecha de inicio')]/following::input[1] | " +
                "//div[contains(text(),'Fecha de inicio')]/following::input[1]")
            driver.execute_script("arguments[0].value = '';", fecha_inicio_input)
            fecha_inicio_input.clear()
            time.sleep(0.2)
            fecha_inicio_input.send_keys(fecha_inicio)
            fecha_inicio_ok = True
            print(f"   -> Fecha inicio: {fecha_inicio} ✓")
        except Exception as e:
            print(f"   !! Fecha inicio (método 1): {e}")
        
        # Estrategia 2 para fecha inicio si la primera falló
        if not fecha_inicio_ok:
            try:
                # Buscar todos los inputs con valor que contenga fecha
                all_inputs = driver.find_elements(By.CSS_SELECTOR, "input")
                for inp in all_inputs:
                    val = inp.get_attribute("value") or ""
                    if "/2025" in val or "/2026" in val or "/2024" in val:
                        # Este podría ser un campo de fecha, verificar posición
                        rect = inp.rect
                        # El primero de izquierda a derecha debería ser fecha inicio
                        driver.execute_script("arguments[0].value = '';", inp)
                        inp.clear()
                        inp.send_keys(fecha_inicio)
                        fecha_inicio_ok = True
                        print(f"   -> Fecha inicio (alternativo): {fecha_inicio} ✓")
                        break
            except Exception as e:
                print(f"   !! Fecha inicio (método 2): {e}")
        
        time.sleep(0.3)
        
        # Estrategia 1: Buscar input después del label "Fecha de fin"
        try:
            fecha_fin_input = driver.find_element(By.XPATH, 
                "//label[contains(text(),'Fecha de fin')]/following::input[1] | " +
                "//span[contains(text(),'Fecha de fin')]/following::input[1] | " +
                "//div[contains(text(),'Fecha de fin')]/following::input[1]")
            driver.execute_script("arguments[0].value = '';", fecha_fin_input)
            fecha_fin_input.clear()
            time.sleep(0.2)
            fecha_fin_input.send_keys(fecha_fin)
            fecha_fin_ok = True
            print(f"   -> Fecha fin: {fecha_fin} ✓")
        except Exception as e:
            print(f"   !! Fecha fin (método 1): {e}")
        
        # Estrategia 2: Buscar el segundo input con formato fecha
        if not fecha_fin_ok:
            try:
                all_inputs = driver.find_elements(By.CSS_SELECTOR, "input")
                date_inputs_found = []
                for inp in all_inputs:
                    val = inp.get_attribute("value") or ""
                    if "/2025" in val or "/2026" in val or "/2024" in val or "/2021" in val:
                        date_inputs_found.append(inp)
                
                if len(date_inputs_found) >= 2:
                    # El segundo debería ser fecha fin
                    driver.execute_script("arguments[0].value = '';", date_inputs_found[1])
                    date_inputs_found[1].clear()
                    date_inputs_found[1].send_keys(fecha_fin)
                    fecha_fin_ok = True
                    print(f"   -> Fecha fin (alternativo): {fecha_fin} ✓")
            except Exception as e:
                print(f"   !! Fecha fin (método 2): {e}")
        
        # Estrategia 3: JavaScript directo si todo lo demás falla
        if not fecha_inicio_ok or not fecha_fin_ok:
            print("   -> Intentando establecer fechas por JavaScript...")
            try:
                result = driver.execute_script(f"""
                    var inputs = document.querySelectorAll('input');
                    var dateInputs = [];
                    for (var i = 0; i < inputs.length; i++) {{
                        var val = inputs[i].value || '';
                        if (val.match(/\\d{{2}}\\/\\d{{2}}\\/\\d{{4}}/)) {{
                            dateInputs.push(inputs[i]);
                        }}
                    }}
                    if (dateInputs.length >= 2) {{
                        dateInputs[0].value = '{fecha_inicio}';
                        dateInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        dateInputs[1].value = '{fecha_fin}';
                        dateInputs[1].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'OK: ' + dateInputs.length + ' campos encontrados';
                    }}
                    return 'FAIL: Solo ' + dateInputs.length + ' campos encontrados';
                """)
                print(f"   -> JS Result: {result}")
            except Exception as e:
                print(f"   !! Error JS fechas: {e}")
        
        time.sleep(1)
        
        # 3. SELECCIONAR FORMATO CSV
        try:
            # Buscar radio button de CSV
            csv_radio = driver.find_element(By.XPATH, 
                "//input[@type='radio'][following-sibling::text()[contains(.,'Csv')] or " +
                "following-sibling::label[contains(.,'Csv')] or " +
                "@value='Csv' or @value='csv' or @value='CSV']")
            driver.execute_script("arguments[0].click();", csv_radio)
            print("   -> Formato: CSV seleccionado")
        except:
            try:
                # Alternativa: buscar label con texto Csv y hacer click
                csv_label = driver.find_element(By.XPATH, "//label[contains(text(),'Csv')]")
                csv_label.click()
                print("   -> Formato: CSV (por label)")
            except:
                try:
                    # Buscar por el texto "Csv" en cualquier parte
                    csv_element = driver.find_element(By.XPATH, "//*[text()='Csv']")
                    csv_element.click()
                    print("   -> Formato: CSV (por texto)")
                except Exception as e:
                    print(f"   !! Warning CSV: usando formato por defecto")
        
        time.sleep(1)
        
        # 4. Registrar archivos ANTES de exportar (para detectar el nuevo)
        # Buscar CSV y XLSX en ambos directorios
        existing_files_ventas_csv = set(glob.glob(os.path.join(DOWNLOAD_DIR_VENTAS, "*.csv")))
        existing_files_ventas_xlsx = set(glob.glob(os.path.join(DOWNLOAD_DIR_VENTAS, "*.xlsx")))
        existing_files_stock_csv = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
        existing_files_stock_xlsx = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx")))
        existing_files = existing_files_ventas_csv | existing_files_ventas_xlsx | existing_files_stock_csv | existing_files_stock_xlsx
        
        print(f"   -> Archivos existentes antes de exportar: {len(existing_files)}")
        
        # 5. CLICK EN EXPORTAR
        print("   -> Buscando botón Exportar...")
        export_btn = None
        
        try:
            export_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Exportar')]")))
        except:
            try:
                export_btn = driver.find_element(By.XPATH, "//button[contains(@class,'btn-primary')]")
            except:
                try:
                    export_btn = driver.find_element(By.ID, "btnExportar")
                except:
                    try:
                        export_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                    except:
                        export_btn = driver.find_element(By.CSS_SELECTOR, "button.btn")
        
        if export_btn:
            print(f"   -> Botón encontrado: {export_btn.text if export_btn.text else 'Sin texto'}")
        
        print("   -> Click en Exportar...")
        driver.execute_script("arguments[0].click();", export_btn)
        
        # Esperar a que inicie la descarga
        time.sleep(5)
        
        # 6. ESPERA DE DESCARGA (buscar NUEVOS archivos en ambos directorios)
        timeout = 120  # Reducido a 2 minutos para no esperar tanto si falla
        elapsed = 0
        file_downloaded = False
        
        print("   -> Esperando descarga (Max 120s)...")
        while elapsed < timeout:
            # Buscar CSV y XLSX en ambos directorios
            files_ventas_csv = set(glob.glob(os.path.join(DOWNLOAD_DIR_VENTAS, "*.csv")))
            files_ventas_xlsx = set(glob.glob(os.path.join(DOWNLOAD_DIR_VENTAS, "*.xlsx")))
            files_stock_csv = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
            files_stock_xlsx = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx")))
            
            # También buscar en Downloads del usuario por si acaso
            user_downloads = os.path.expanduser("~\\Downloads")
            files_user_csv = set(glob.glob(os.path.join(user_downloads, "*.csv")))
            files_user_xlsx = set(glob.glob(os.path.join(user_downloads, "Reporte*.xlsx")))
            
            all_current_files = files_ventas_csv | files_ventas_xlsx | files_stock_csv | files_stock_xlsx | files_user_csv | files_user_xlsx
            
            # Encontrar archivos NUEVOS (que no existían antes)
            new_files = all_current_files - existing_files
            
            # Filtrar archivos en proceso de descarga
            valid_new_files = [f for f in new_files 
                              if not f.endswith('.crdownload') 
                              and not f.endswith('.tmp')
                              and os.path.getsize(f) > 0]  # Verificar que tenga contenido
            
            if valid_new_files:
                new_file = valid_new_files[0]
                print(f"   -> Archivo detectado: {new_file}")
                
                # Determinar extensión
                file_ext = os.path.splitext(new_file)[1].lower()
                new_name = os.path.join(DOWNLOAD_DIR_VENTAS, f"ReporteVenta{año}{file_ext}")
                
                try:
                    if os.path.exists(new_name):
                        os.remove(new_name)
                    shutil.move(new_file, new_name)
                    print(f"   -> [OK] Archivo movido: ReporteVenta{año}{file_ext}")
                except Exception as e:
                    print(f"   -> [OK] Archivo en: {new_file} (Error moviendo: {e})")
                file_downloaded = True
                break
            
            # Log cada 30 segundos para saber que sigue buscando
            if elapsed > 0 and elapsed % 30 == 0:
                print(f"   -> Buscando... ({elapsed}s)")
            
            time.sleep(1)
            elapsed += 1
        
        if not file_downloaded:
            # Debug: mostrar qué archivos existen ahora
            print(f"   !! Warning: No se descargó archivo para {año}")
            print(f"   !! Archivos en stock: {list(glob.glob(os.path.join(DOWNLOAD_DIR, '*.*')))[-5:]}")
            print(f"   !! Archivos en ventas: {list(glob.glob(os.path.join(DOWNLOAD_DIR_VENTAS, '*.*')))}")
            
            # Guardar screenshot para debug
            driver.save_screenshot(os.path.join(DOWNLOAD_DIR_VENTAS, f"debug_ventas_{año}.png"))
            
    except Exception as e:
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR_VENTAS, f"error_ventas_{año}.png"))
        print(f"   !! Error extrayendo ventas {año}: {e}")


def execute_ventas_extraction(driver):
    """Descarga todos los reportes de ventas por año."""
    print("\n" + "="*60)
    print(">> [EXTRACTION VENTAS] Iniciando descarga de reportes de ventas")
    print("="*60)
    
    wait = WebDriverWait(driver, 30)
    
    for año in AÑOS_VENTAS:
        try:
            execute_ventas_extraction_year(driver, wait, año)
            time.sleep(2)  # Pausa entre descargas
        except Exception as e:
            print(f"   !! Error procesando año {año}: {e}")
            continue
    
    print("\n>> [EXTRACTION VENTAS] Descarga completada")


def normalizar_dataframe(df, año):
    """Normaliza un DataFrame agregando columnas faltantes y reordenando."""
    df_norm = df.copy()
    
    for col in COLUMNAS_MAESTRAS:
        if col not in df_norm.columns:
            df_norm[col] = pd.NA
    
    df_norm['AÑO'] = int(año)
    df_norm = df_norm[COLUMNAS_MAESTRAS]
    
    return df_norm


def process_ventas_data():
    """Normaliza y consolida los reportes de ventas. Retorna DataFrame consolidado."""
    print("\n>> [TRANSFORMATION VENTAS] Normalizando y consolidando datos de ventas...")
    
    dataframes = {}
    
    for año in AÑOS_VENTAS:
        # Buscar archivo CSV o XLSX
        ruta_csv = os.path.join(DOWNLOAD_DIR_VENTAS, f"ReporteVenta{año}.csv")
        ruta_xlsx = os.path.join(DOWNLOAD_DIR_VENTAS, f"ReporteVenta{año}.xlsx")
        
        ruta = None
        if os.path.exists(ruta_csv):
            ruta = ruta_csv
        elif os.path.exists(ruta_xlsx):
            ruta = ruta_xlsx
        
        if not ruta:
            print(f"   ️  Archivo no encontrado: ReporteVenta{año}.[csv/xlsx]")
            continue
        
        try:
            if ruta.endswith('.csv'):
                df = pd.read_csv(ruta, encoding='utf-8', low_memory=False)
            else:
                df = pd.read_excel(ruta)
            
            inmuebles = [col for col in df.columns if col.startswith('T/M_')]
            print(f"    {año}: {len(df):,} filas, {len(df.columns)} cols, {len(inmuebles)} inmuebles")
            dataframes[str(año)] = df
        except Exception as e:
            print(f"    Error al cargar {año}: {e}")
            continue
    
    if not dataframes:
        print("   !! No se encontraron archivos de ventas para procesar")
        return None
    
    print(f"\n    Archivos cargados: {len(dataframes)}/{len(AÑOS_VENTAS)}")
    
    # Normalizar
    print("\n    Normalizando datos...")
    dfs_normalizados = {}
    for año, df in dataframes.items():
        df_norm = normalizar_dataframe(df, año)
        dfs_normalizados[año] = df_norm
        print(f"    {año}: Normalizado ({len(df_norm)} filas, {len(df_norm.columns)} cols)")
    
    # Consolidar
    print("\n    Consolidando datos...")
    df_consolidado = pd.concat(dfs_normalizados.values(), ignore_index=True)
    print(f"    Total filas: {len(df_consolidado):,}")
    print(f"    Total columnas: {len(df_consolidado.columns)}")
    print(f"    Años: {sorted(df_consolidado['AÑO'].unique().tolist())}")
    
    return df_consolidado


def process_stock_data(df_ventas=None):
    """ETL de Stock con FORMATO VISUAL MEJORADO. Incluye pestaña VENTAS si se proporciona."""
    print("\n>> [TRANSFORMATION STOCK] Procesando lógica de negocio y aplicando formatos...")
    
    list_of_files = glob.glob(os.path.join(DOWNLOAD_DIR, '*.xlsx'))
    if not list_of_files:
        raise Exception("No se encontró el archivo Excel en la carpeta de stock.")
        
    latest_file = max(list_of_files, key=os.path.getctime)
    
    try:
        df = pd.read_excel(latest_file)
        df.columns = df.columns.str.strip() 
        print(f"   -> Filas leídas: {len(df)}")
    except Exception as e:
        raise Exception(f"Error abriendo Excel descargado: {e}")
    
    # --- FILTROS DE NEGOCIO ---
    if 'Proyecto' in df.columns:
        df = df[df['Proyecto'].str.upper().isin(TARGET_PROJECTS)]
        
    print(f"   -> Filas tras filtros: {len(df)}")

    output_filename = os.path.join(DOWNLOAD_DIR, f"Reporte_Stock_BIEVO25_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    try:
        writer = pd.ExcelWriter(output_filename, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Stock')
        
        workbook = writer.book
        worksheet = writer.sheets['Stock']
        (max_row, max_col) = df.shape
        
        fmt_base = workbook.add_format({'font_name': 'Arial', 'font_size': 9})
        fmt_header = workbook.add_format({
            'bold': True, 'font_name': 'Arial', 'font_size': 9,
            'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        fmt_currency = workbook.add_format({
            'num_format': '"S/" #,##0.00', 'font_name': 'Arial', 'font_size': 9
        })
        fmt_decimal = workbook.add_format({
            'num_format': '0.00', 'font_name': 'Arial', 'font_size': 9
        })

        for i, col in enumerate(df.columns):
            worksheet.write(0, i, col, fmt_header)
            col_upper = col.upper()
            
            if 'PRECIO' in col_upper or 'MONTO' in col_upper or 'CUOTA' in col_upper or 'IMPORTE' in col_upper:
                worksheet.set_column(i, i, 16, fmt_currency)
            elif 'AREA' in col_upper:
                worksheet.set_column(i, i, 12, fmt_decimal)
            elif 'PROYECTO' in col_upper:
                worksheet.set_column(i, i, 25, fmt_base)
            else:
                worksheet.set_column(i, i, 15, fmt_base)

        if max_row > 0:
            options = {
                'columns': [{'header': col} for col in df.columns],
                'style': 'Table Style Medium 2',
                'name': 'TablaStock'
            }
            worksheet.add_table(0, 0, max_row, max_col - 1, options)
        
        # --- AGREGAR PESTAÑA VENTAS SI EXISTE DATA ---
        if df_ventas is not None and len(df_ventas) > 0:
            print("\n   -> Agregando pestaña VENTAS al archivo...")
            df_ventas.to_excel(writer, index=False, sheet_name='VENTAS')
            
            worksheet_ventas = writer.sheets['VENTAS']
            (max_row_v, max_col_v) = df_ventas.shape
            
            # Aplicar formatos a pestaña VENTAS
            for i, col in enumerate(df_ventas.columns):
                worksheet_ventas.write(0, i, col, fmt_header)
                col_upper = col.upper()
                
                if 'PRECIO' in col_upper or 'MONTO' in col_upper or 'CUOTA' in col_upper or 'IMPORTE' in col_upper or 'SUBTOTAL' in col_upper:
                    worksheet_ventas.set_column(i, i, 16, fmt_currency)
                elif 'AREA' in col_upper:
                    worksheet_ventas.set_column(i, i, 12, fmt_decimal)
                elif 'PROYECTO' in col_upper:
                    worksheet_ventas.set_column(i, i, 25, fmt_base)
                elif 'AÑO' in col_upper:
                    worksheet_ventas.set_column(i, i, 8, fmt_base)
                else:
                    worksheet_ventas.set_column(i, i, 15, fmt_base)
            
            if max_row_v > 0:
                options_ventas = {
                    'columns': [{'header': col} for col in df_ventas.columns],
                    'style': 'Table Style Medium 2',
                    'name': 'TablaVentas'
                }
                worksheet_ventas.add_table(0, 0, max_row_v, max_col_v - 1, options_ventas)
            
            print(f"    Pestaña VENTAS agregada ({len(df_ventas):,} filas)")
        
        writer.close()
        return output_filename

    except Exception as e:
        print(f"!! Error aplicando formato (guardando simple): {e}")
        df.to_excel(output_filename, index=False)
        return output_filename


def dispatch_report(file_path):
    """Envío Correo con el reporte consolidado (Stock + Ventas)."""
    print("\n>> [DISTRIBUTION] Enviando correo...")
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = f"REPORTE STOCK COMERCIAL - BIEVO25 - {datetime.now().strftime('%d/%m/%Y')}"
    
    body = f"""
    <html><body>
        <h3>Reporte Automatizado de Stock</h3>
        <p>Adjunto reporte actualizado al {datetime.now().strftime('%d/%m/%Y %H:%M')}.</p>
        <p>El archivo contiene las siguientes pestañas:</p>
        <ul>
            <li><b>Stock:</b> Información actualizada de inventario comercial</li>
            <li><b>VENTAS:</b> Histórico consolidado de ventas 2021-2026</li>
        </ul>
    </body></html>
    """
    msg.attach(MIMEText(body, 'html'))
    
    # Adjuntar reporte único
    with open(file_path, 'rb') as f:
        part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASS)
            smtp.send_message(msg)
        print(">> [SUCCESS] Correo enviado.")
    except Exception as e:
        print(f"!! Error SMTP: {e}")


def main():
    print("="*70)
    print("   PIPELINE ETL EVOLTA - STOCK Y VENTAS")
    print(f"   Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Limpiar directorios
    clean_environment(DOWNLOAD_DIR, "*.xlsx")
    clean_environment(DOWNLOAD_DIR_VENTAS, "*.csv")
    clean_environment(DOWNLOAD_DIR_VENTAS, "*.xlsx")
    
    # Inicializar driver (directorio de descarga principal para Stock)
    driver = get_driver(DOWNLOAD_DIR)
    wait = WebDriverWait(driver, 30)
    
    final_file = None
    df_ventas = None
    
    try:
        # 1. LOGIN (único)
        robust_login(driver, wait)
        
        # 2. EXTRAER STOCK
        execute_stock_extraction(driver)
        
        # 3. Cambiar directorio de descarga para Ventas
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": DOWNLOAD_DIR_VENTAS
        })
        
        # 4. EXTRAER VENTAS (misma sesión)
        execute_ventas_extraction(driver)
        
    except Exception as e:
        print(f"!! CRITICAL ERROR: {e}")
    finally:
        driver.quit()
    
    # 5. PROCESAR DATOS DE VENTAS (consolidar)
    try:
        df_ventas = process_ventas_data()
    except Exception as e:
        print(f"!! DATA ERROR (Ventas): {e}")
        df_ventas = None
    
    # 6. PROCESAR DATOS DE STOCK (incluye pestaña VENTAS)
    try:
        final_file = process_stock_data(df_ventas)
    except Exception as e:
        print(f"!! DATA ERROR (Stock): {e}")
    
    # 7. ENVIAR CORREO (un solo archivo)
    if final_file:
        try:
            dispatch_report(final_file)
        except Exception as e:
            print(f"!! EMAIL ERROR: {e}")
    else:
        print("!! No hay reporte para enviar")
    
    print("\n" + "="*70)
    print("   PIPELINE COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
