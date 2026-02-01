import logging
import sys
import os
import time
import traceback

# Configuración de Logging
log_file = os.path.join(os.getcwd(), "evolta.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("EvoltaUpdate")

logger.info("... Iniciando script de actualización con LOGGING ...")

try:
    logger.info("Importando servicios...")
    from app.services.evolta_service import evolta_service
    
    # Redirigir el print standard a logger para capturar lo que diga el servicio
    # (Aunque lo ideal sería actualizar el servicio para usar logger, esto es un wrapper rápido)
    
    logger.info("Iniciando run_update()...")
    start = time.time()
    
    # Monkey patch print para que salga en el log también (truco rápido)
    original_print = print
    def logged_print(*args, **kwargs):
        msg = " ".join(map(str, args))
        logger.info(f"[SERVICE] {msg}")
        # original_print(*args, **kwargs) # Ya sale por StreamHandler
    
    import builtins
    builtins.print = logged_print
    
    success = evolta_service.run_update()
    
    # Restaurar print
    builtins.print = original_print

    if success:
        logger.info(f"✅ EXITO: Actualización completada en {int(time.time() - start)} segundos.")
    else:
        logger.error("❌ FALLO: La función run_update retornó False.")

except Exception as e:
    logger.critical(f"🔥 ERROR CRÍTICO NO CONTROLADO: {e}")
    logger.critical(traceback.format_exc())

logger.info("Fin del script.")
