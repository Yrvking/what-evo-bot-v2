import time
import os
import glob
import shutil
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from app.config import PROJECT_ROOT, DATA_DIR

# --- CREDENCIALES ---
USER_CRED = "calopez"
PASS_CRED = "Lopez201217**"

URL_LOGIN = "https://v4.evolta.pe/Login/Acceso/Index"
URL_REPORTE_VENTAS = "https://v4.evolta.pe/Reportes/RepVenta/Index"

# Lista de años a descargar
AÑOS_VENTAS = [2021, 2022, 2023, 2024, 2025, 2026]

class EvoltaService:
    def __init__(self):
        self.download_dir = os.path.join(DATA_DIR, "temp_downloads")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def get_driver(self):
        """Inicializa driver Chrome Headless."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") 
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--log-level=3") 
        
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error iniciando Chrome Driver: {e}")
            return None

    def login(self, driver):
        """Logueo en Evolta."""
        print("Iniciando Login en Evolta...")
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 20)
        
        try:
            # Selector robusto como en el script original
            try: 
                user_field = driver.find_element(By.ID, "UserName")
            except:
                try: 
                    user_field = driver.find_element(By.NAME, "Usuario")
                except: 
                    user_field = driver.find_element(By.XPATH, "//input[@type='text']")

            user_field.clear()
            user_field.send_keys(USER_CRED)
            
            # Password por XPath como en original
            driver.find_element(By.XPATH, "//input[@type='password']").send_keys(PASS_CRED)
            
            driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']").click()
            time.sleep(5)
            print("Login enviado. Esperando...")
        except Exception as e:
            print(f"Error en Login: {e}")
            raise e

    def download_sales_year(self, driver, year):
        """Descarga el reporte de un año específico con REINTENTOS."""
        # Verificar si ya existe para saltarlo (Resume)
        dest_file = os.path.join(self.download_dir, f"ventas_{year}.xlsx")
        if os.path.exists(dest_file):
            print(f"Skipping {year} (Ya descargado).")
            return

        print(f"Descargando Ventas {year}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get(URL_REPORTE_VENTAS)
                wait = WebDriverWait(driver, 20)
                time.sleep(4)
                
                # Injection de fechas
                fecha_inicio = f"01/01/{year}"
                fecha_fin = f"31/12/{year}"
                if year == datetime.now().year:
                    fecha_fin = datetime.now().strftime("%d/%m/%Y")

                driver.execute_script(f"""
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
                    }}
                """)
                time.sleep(1)
                
                # Click Csv/Exportar...
                try:
                    driver.find_element(By.XPATH, "//label[contains(text(),'Csv')]").click()
                except:
                    pass

                export_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnExportar")))
                driver.execute_script("arguments[0].click();", export_btn)
                
                # Esperar archivo
                if self._wait_for_download(year):
                    return # Exito
                else:
                    raise Exception("Timeout esperando archivo")
                
            except Exception as e:
                print(f"Error intento {attempt+1}/{max_retries} para {year}: {e}")
                print("Refrescando pagina...")
                driver.refresh()
                time.sleep(5)
        
        print(f"FALLO DEFINITIVO descargando {year}")

    def _wait_for_download(self, suffix, timeout=60):
        elapsed = 0
        while elapsed < timeout:
            # Buscar archivos Excel descargados
            files = glob.glob(os.path.join(self.download_dir, "Reporte*.xlsx"))
            
            if files:
                newest = max(files, key=os.path.getctime)
                # Verificar que sea reciente (último minuto)
                if (datetime.now().timestamp() - os.path.getctime(newest)) < 60:
                    dest = os.path.join(self.download_dir, f"ventas_{suffix}.xlsx")
                    if os.path.exists(dest): os.remove(dest)
                    
                    # Esperar desbloqueo de archivo
                    time.sleep(2) 
                    try:
                        shutil.move(newest, dest)
                        print(f"   Archivo guardado: ventas_{suffix}.xlsx")
                        return True
                    except Exception as e:
                        print(f"   Reintentando mover archivo... {e}")
            
            time.sleep(1)
            elapsed += 1
        print(f"   Timeout esperando archivo {suffix}")
        return False

    def consolidate_and_save(self):
        """Une todos los XLSX descargados en un solo Excel."""
        print("Consolidando informacion...")
        all_files = glob.glob(os.path.join(self.download_dir, "ventas_*.xlsx"))
        
        if not all_files:
            print("No hay archivos para consolidar.")
            return False

        dfs = []
        for f in all_files:
            try:
                # Leer Excel asumiendo formato de Evolta
                df = pd.read_excel(f, dtype=str)
                df['AÑO_ORIGEN'] = os.path.basename(f).replace("ventas_", "").replace(".xlsx", "")
                dfs.append(df)
            except Exception as e:
                print(f"Error leyendo {f}: {e}")

        if not dfs: return False

        final_df = pd.concat(dfs, ignore_index=True)
        
        # Guardar en la raíz como CLIENTES_DB.xlsx
        output_path = os.path.join(PROJECT_ROOT, "CLIENTES_DB.xlsx")
        final_df.to_excel(output_path, index=False)
        print(f"Base de Datos Generada: {output_path} ({len(final_df)} registros)")
        
        # Limpieza
        for f in all_files: os.remove(f)
        return True

    def run_update(self):
        driver = self.get_driver()
        if not driver: return False
        
        try:
            self.login(driver)
            for year in AÑOS_VENTAS:
                self.download_sales_year(driver, year)
            
            success = self.consolidate_and_save()
            return success
        except Exception as e:
            print(f"Error Critico Evolta Update: {e}")
            return False
        finally:
            driver.quit()

evolta_service = EvoltaService()
