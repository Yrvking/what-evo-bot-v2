import pandas as pd
import os
from app import config

class ExcelService:
    def __init__(self):
        self.file_path = config.EXCEL_FILE_PATH
        self.df = None
        self._load_data()

    def _load_data(self):
        """Carga el Excel en memoria."""
        if os.path.exists(self.file_path):
            try:
                print(f"📂 Cargando Excel desde: {self.file_path}")
                # Leemos todo como string para evitar problemas de formato (ej. ceros a la izquierda en DNI)
                self.df = pd.read_excel(self.file_path, dtype=str)
                # Normalizamos columnas clave
                self.df[config.COL_CELULAR] = self.df[config.COL_CELULAR].apply(self._normalize_phone)
                self.df[config.COL_PROYECTO] = self.df[config.COL_PROYECTO].str.strip()
                print(f"✅ Excel cargado correctamente. {len(self.df)} registros.")
            except Exception as e:
                print(f"❌ Error cargando Excel: {e}")
                self.df = pd.DataFrame()
        else:
            print(f"⚠️ Archivo Excel no encontrado en {self.file_path}")
            self.df = pd.DataFrame()

    def _normalize_phone(self, val):
        """Limpia el número de teléfono para dejar solo dígitos."""
        if pd.isna(val): return ""
        return ''.join(filter(str.isdigit, str(val)))

    def find_users_by_phone(self, phone):
        """Busca usuarios que coincidan con el teléfono (triangulación)."""
        if self.df.empty: return []
        
        # El phone de WhatsApp viene como "51999999999" o "52155..."
        # Debemos buscar si el celular del excel está contenido en el phone o viceversa/match
        # Estrategia: Buscar coincidencia exacta de los últimos 9 dígitos
        
        target = str(phone)[-9:] # Tomamos los últimos 9
        
        # Filtramos
        # Asegúrate de que comparamos strings limpios
        matches = self.df[self.df[config.COL_CELULAR].str.endswith(target, na=False)]
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "nombre": row.get(config.COL_NOMBRE, "Cliente"),
                "dni": row.get(config.COL_DNI, ""),
                "proyecto": row.get(config.COL_PROYECTO, ""),
                "unidad": row.get(config.COL_DPTO, "")
            })
        
        # Deduplicar por proyecto/unidad si es necesario, pero devolvemos todo por ahora
        return results


    def find_users_by_dni(self, dni):
        """Busca por DNI exacto."""
        if self.df.empty: return []
        dni_clean = str(dni).strip()
        matches = self.df[self.df[config.COL_DNI].str.contains(dni_clean, na=False)]
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "nombre": row.get(config.COL_NOMBRE, "Cliente"),
                "dni": row.get(config.COL_DNI, ""),
                "proyecto": row.get(config.COL_PROYECTO, ""),
                "unidad": row.get(config.COL_DPTO, "")
            })
        return results

    def find_users_by_name(self, name):
        """Busca por Nombre (match parcial)."""
        if self.df.empty: return []
        name_clean = str(name).strip().upper()
        # Buscamos que contenga el texto (case insensitive)
        matches = self.df[self.df[config.COL_NOMBRE].str.upper().str.contains(name_clean, na=False)]
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "nombre": row.get(config.COL_NOMBRE, "Cliente"),
                "dni": row.get(config.COL_DNI, ""),
                "proyecto": row.get(config.COL_PROYECTO, ""),
                "unidad": row.get(config.COL_DPTO, "")
            })
        return results

excel_service = ExcelService()
