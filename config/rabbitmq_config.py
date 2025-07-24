"""
Configurações centralizadas para conexões RabbitMQ
"""

import pika
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv('config/.env')

class RabbitMQConfig:
    """Configurações centralizadas para RabbitMQ"""
    
    # Configurações de conexão
    HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    USERNAME = os.getenv('RABBITMQ_USER', 'admin')
    PASSWORD = os.getenv('RABBITMQ_PASS', 'admin123')
    
    # Timeouts e limites
    HEARTBEAT = 300  # 5 minutos
    BLOCKED_CONNECTION_TIMEOUT = 300  # 5 minutos
    CONNECTION_ATTEMPTS = 3
    RETRY_DELAY = 2
    
    # Configurações de QoS
    PREFETCH_COUNT = 1
    
    @classmethod
    def get_connection_parameters(cls):
        """Retorna parâmetros de conexão padronizados"""
        credentials = pika.PlainCredentials(cls.USERNAME, cls.PASSWORD)
        return pika.ConnectionParameters(
            host=cls.HOST,
            credentials=credentials,
            heartbeat=cls.HEARTBEAT,
            blocked_connection_timeout=cls.BLOCKED_CONNECTION_TIMEOUT,
            connection_attempts=cls.CONNECTION_ATTEMPTS,
            retry_delay=cls.RETRY_DELAY
        )
    
    @classmethod
    def test_connection(cls):
        """Testa conexão com RabbitMQ"""
        try:
            connection = pika.BlockingConnection(cls.get_connection_parameters())
            connection.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar com RabbitMQ: {e}")
            return False
    
    @classmethod
    def create_robust_connection(cls):
        """Cria conexão robusta com tratamento de erro"""
        try:
            connection = pika.BlockingConnection(cls.get_connection_parameters())
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            print(f"❌ Erro ao criar conexão RabbitMQ: {e}")
            return None, None
