import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import threading

# --- CONFIGURACIÓN BASE DE DATOS ---
# Usamos el string del Session Pooler (IPv4 Compatible) - CORREGIDO (aws-1)
# Usamos el string del Session Pooler (IPv4 Compatible) - CORREGIDO (aws-1)
DB_URI = os.getenv("SUPABASE_URI")
if not DB_URI:
    print("❌ ERROR CRÍTICO: No se encontró SUPABASE_URI en las variables de entorno.")

engine = create_engine(DB_URI, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ---
class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(String(20), primary_key=True) # TCK-XXXXX
    phone = Column(String(20))
    nombre = Column(String(100))
    dni = Column(String(20))
    proyecto = Column(String(100))
    unidad = Column(String(50))
    categoria = Column(String(50))
    descripcion = Column(Text)
    estado = Column(String(20), default="Pendiente")
    # ... (previous columns)
    tipo_cliente = Column(String(50), default="REGISTRADO") 
    created_at = Column(DateTime, default=datetime.now)
    media_files = Column(Text, default="") 

    # --- CAMPOS PROCORE (STAGING) ---
    procore_especialidad = Column(String(200), default="")
    procore_tipo = Column(String(100), default="Garantía - Llamada de servicio")
    procore_prioridad = Column(String(50), default="Urgente")
    procore_asignado = Column(String(100), default="Cesar Arrunategui Saavedra")
    procore_status = Column(String(50), default="PENDIENTE") # PENDIENTE, LISTO, SINCRONIZADO


# --- SERVICIO ---
class DatabaseService:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Crea las tablas si no existen."""
        try:
            Base.metadata.create_all(bind=engine)
            # Migraciones Manuales
            with engine.connect() as con:
                try:
                    # Array de columnas nuevas para asegurar existencia
                    new_cols = [
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tipo_cliente VARCHAR(50) DEFAULT 'REGISTRADO'",
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS procore_especialidad VARCHAR(200) DEFAULT ''",
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS procore_tipo VARCHAR(100) DEFAULT 'Garantía - Llamada de servicio'",
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS procore_prioridad VARCHAR(50) DEFAULT 'Urgente'",
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS procore_asignado VARCHAR(100) DEFAULT 'Cesar Arrunategui Saavedra'",
                        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS procore_status VARCHAR(50) DEFAULT 'PENDIENTE'"
                    ]
                    
                    for sql in new_cols:
                        con.execute(text(sql))
                    
                    con.commit() 
                    print("✅ Schema verificado (Columnas Procore agregadas).")
                except Exception as e:
                    print(f"⚠️ Nota sobre schema: {e}")
            
            print("✅ Base de datos (Supabase) conectada y tablas listas.")
        except Exception as e:
            print(f"❌ Error conectando a BD: {e}")

    def create_ticket(self, user_data, category, description, media_urls=[]):
        session = SessionLocal()
        try:
            import random
            from app.services.media_service import media_service
            
            # --- PROCESAMIENTO DE MEDIA ---
            processed_urls = []
            for item in media_urls:
                # El formato interno es "[type:ID]", ej: "[image:12345]"
                if "[" in item and ":" in item:
                    try:
                        # Extraer ID: "[image:123]" -> "123"
                        media_id = item.split(":")[1].replace("]", "")
                        print(f"📤 Subiendo ID: {media_id}...")
                        
                        public_url = media_service.upload_file(media_id)
                        processed_urls.append(public_url if public_url else item)
                    except:
                        processed_urls.append(item)
                else:
                    processed_urls.append(item)

            # --- GENERACIÓN DE ID CONSECUTIVO ---
            # 1. Buscamos el último ticket creado
            last_ticket = session.query(Ticket).order_by(Ticket.created_at.desc()).first()
            
            new_id_number = 1
            if last_ticket and last_ticket.id:
                try:
                    # Formato esperado: TCK-12345
                    last_str = last_ticket.id.split("-")[1]
                    new_id_number = int(last_str) + 1
                except:
                    # Si el ID anterior tenía formato raro, reseteamos o usamos random de fallback
                    new_id_number = random.randint(10000, 99999)

            # Formato simple: TCK-00001 (padding de 5 ceros)
            ticket_id = f"TCK-{new_id_number:05d}"
            
            new_ticket = Ticket(
                id=ticket_id,
                phone=user_data.get("phone", ""),
                nombre=user_data.get("nombre", "Cliente"),
                dni=user_data.get("dni", ""),
                proyecto=user_data.get("proyecto", ""),
                unidad=user_data.get("unidad", ""),
                categoria=category,
                descripcion=description,
                tipo_cliente=user_data.get("tipo_cliente", "REGISTRADO"),
                media_files=";".join(processed_urls),
                # Defaults Procore
                procore_status="PENDIENTE"
            )
            session.add(new_ticket)
            session.commit()
            print(f"💾 Ticket guardado en Supabase: {ticket_id}")
            return ticket_id
        except Exception as e:
            print(f"❌ Error guardando ticket DB: {e}")
            session.rollback()
            return "ERROR-DB"
        finally:
            session.close()

    def get_all_tickets(self):
        session = SessionLocal()
        try:
            tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).all()
            return [{
                "id": t.id,
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
                "nombre": t.nombre,
                "dni": t.dni,
                "telefono": t.phone,
                "proyecto": t.proyecto,
                "unidad": t.unidad,
                "categoria": t.categoria,
                "tipo_cliente": t.tipo_cliente,
                "desc": t.descripcion,
                "media": [m for m in t.media_files.split(";") if m] if t.media_files else [],
                # Datos Procore
                "procore_especialidad": t.procore_especialidad,
                "procore_tipo": t.procore_tipo,
                "procore_prioridad": t.procore_prioridad,
                "procore_asignado": t.procore_asignado,
                "procore_status": t.procore_status
            } for t in tickets]
        except Exception as e:
            print(f"Error getting tickets: {e}")
            return []
        finally:
            session.close()

    def update_ticket_procore(self, ticket_id, especialidad, tipo, prioridad, asignado, status):
        session = SessionLocal()
        try:
            ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket:
                ticket.procore_especialidad = especialidad
                ticket.procore_tipo = tipo
                ticket.procore_prioridad = prioridad
                ticket.procore_asignado = asignado
                ticket.procore_status = status
                session.commit()
                return True
            return False
        except Exception as e:
             print(f"Error updating ticket: {e}")
             session.rollback()
             return False
        finally:
             session.close()

    def check_rate_limit(self, phone, limit=3, hours=24):
        session = SessionLocal()
        try:
            from datetime import timedelta
            time_limit = datetime.now() - timedelta(hours=hours)
            count = session.query(Ticket).filter(
                Ticket.phone == phone, 
                Ticket.created_at > time_limit
            ).count()
            return count < limit
        except Exception as e:
            print(f"Error rate limit DB: {e}")
            return True
        finally:
            session.close()

db_service = DatabaseService()
