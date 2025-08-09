# app/utils/database.py
import psycopg2
from psycopg2 import pool, OperationalError
import logging
from dotenv import load_dotenv
import os

load_dotenv()

class Database:
    def __init__(self):
        self.logger = logging.getLogger("nova.db")
        self.connection_pool = self._create_connection_pool()
    
    def _create_connection_pool(self):
        try:
            return psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST", ""),
                database=os.getenv("DB_NAME", "nova_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "1234"),
                port=os.getenv("DB_PORT", "5432"),
                options="-c client_encoding=UTF8"
            )
        except OperationalError as e:
            self.logger.error(f"Error al crear pool de conexiones: {str(e)}")
            return None
    
    def get_connection(self):
        """Obtiene una conexión del pool"""
        try:
            if self.connection_pool:
                conn = self.connection_pool.getconn()
                conn.autocommit = False
                return conn
        except Exception as e:
            self.logger.error(f"Error al obtener conexión: {str(e)}")
            return None
    
    def release_connection(self, conn):
        """Libera una conexión al pool"""
        try:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)
        except Exception as e:
            self.logger.error(f"Error al liberar conexión: {str(e)}")
    
    def close_all_connections(self):
        """Cierra todas las conexiones del pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.logger.info("Todas las conexiones de la pool cerradas")

    def __del__(self):
        self.close_all_connections()
