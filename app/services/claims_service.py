from app.services.db_service import db_service
import csv
import os
import datetime
import random
from app import config

class ClaimsService:
    def __init__(self):
        pass # Ya no necesitamos csv file path

    def check_rate_limit(self, phone, limit=3, hours=24):
        """Delegamos la verificación a la Base de Datos."""
        return db_service.check_rate_limit(str(phone), limit, hours)

    def create_ticket(self, user_data, claim_type, description, media_files=[]):
        """Genera un ticket y lo guarda en Supabase."""
        
        # Guardamos en DB
        ticket_id = db_service.create_ticket(
            user_data,
            claim_type,
            description,
            media_files
        )
        
        return ticket_id

claims_service = ClaimsService()
