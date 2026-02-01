import time
print("... Iniciando script de actualizacion ...")

try:
    print("... Importando servicios ...")
    from app.services.evolta_service import evolta_service
    print("... Servicios importados correctamente ...")

    print("... Ejecutando run_update ...")
    start = time.time()
    success = evolta_service.run_update()

    if success:
        print(f"EXITO: Actualizacion completada en {int(time.time() - start)} segundos.")
    else:
        print("FALLO: La actualizacion no pudo completarse.")

except Exception as e:
    print(f"ERROR CRITICO EN SCRIPT: {e}")
    import traceback
    traceback.print_exc()
