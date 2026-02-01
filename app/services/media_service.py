import cloudinary
import cloudinary.uploader
import os

# --- CREDENTIALS PLACEHOLDERS ---
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

class MediaService:
    def configure(self):
        cloudinary.config( 
            cloud_name = CLOUD_NAME, 
            api_key = API_KEY, 
            api_secret = API_SECRET,
            secure = True
        )
        print("✅ Cloudinary configurado.")

    def upload_file(self, media_id_or_url, folder="claims_media"):
        """
        1. Obtiene la URL de descarga desde Meta usando el Media ID.
        2. Descarga el archivo en memoria.
        3. Lo sube a Cloudinary.
        4. Retorna la URL pública segura.
        """
        if not media_id_or_url or "media_url" in media_id_or_url: 
            return None # Evitar procesar si no es un ID válido

        # Si ya es una URL completa (ej. reintento), intentar subirla directo
        if media_id_or_url.startswith("http"):
            try:
                res = cloudinary.uploader.upload(media_id_or_url, folder=folder)
                return res["secure_url"]
            except:
                return None

        # --- FLUJO WHATSAPP (MEDIA ID) ---
        from app.config import TOKEN, PHONE_ID
        import requests

        try:
            # PASO 1: Obtener URL de descarga de Meta
            url_info = f"https://graph.facebook.com/v21.0/{media_id_or_url}"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            resp_info = requests.get(url_info, headers=headers)
            
            if resp_info.status_code != 200:
                print(f"❌ Error Meta Info: {resp_info.text}")
                return None
                
            media_url = resp_info.json().get("url")
            
            # PASO 2: Descargar el binario
            resp_bin = requests.get(media_url, headers=headers)
            if resp_bin.status_code != 200:
                 print(f"❌ Error Descarga Binaria: {resp_bin.status_code}")
                 return None

            # PASO 3: Subir a Cloudinary (Desde Memoria - Stream)
            from io import BytesIO
            file_stream = BytesIO(resp_bin.content)
            file_stream.name = f"{media_id_or_url}" # Nombre temporal para Cloudinary

            upload_result = cloudinary.uploader.upload(
                file_stream, 
                folder=folder, 
                public_id=f"whatsapp_{media_id_or_url}", 
                overwrite=True,
                resource_type="auto" # Detectar si es imagen o video
            )
            
            print(f"✅ Foto subida exitosamente: {upload_result['secure_url']}")
            return upload_result["secure_url"]

        except Exception as e:
            print(f"❌ Error Proceso Upload: {e}")
            return None

media_service = MediaService()
