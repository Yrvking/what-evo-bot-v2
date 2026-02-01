import requests
from app.config import TOKEN, PHONE_ID

def verify_meta_token():
    print(f"--- 🕵️‍♂️ Verificando Credenciales con Meta ---")
    print(f"Token en uso: {TOKEN[:15]}...{TOKEN[-10:]}")
    print(f"Phone ID: {PHONE_ID}")

    url = f"https://graph.facebook.com/v22.0/{PHONE_ID}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ ¡ÉXITO TOTAL! El Token es VÁLIDO.")
            print(f"Nombre Verificado: {data.get('verified_name', 'No disponible')}")
            print(f"Calidad del Número: {data.get('quality_rating', 'Desconocido')}")
            print(f"Estado: {data.get('code_verification_status', 'Desconocido')}")
            print("-" * 30)
            print(">> YA PUEDES ENVIAR 'HOLA' DESDE TU CELULAR <<")
        else:
            print(f"\n❌ ERROR CRÍTICO ({response.status_code})")
            print("Meta dice:", response.json())
            print("\nCONCLUSIÓN: Este token NO sirve. Debes generar uno nuevo con los permisos marcados.")

    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")

if __name__ == "__main__":
    verify_meta_token()
