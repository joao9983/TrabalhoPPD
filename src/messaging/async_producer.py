"""
Produtor de mensagens assíncronas
Envia mensagens via RabbitMQ quando usuários estão offline ou fora do raio.
"""

import pika
import json
import time
import os
from dotenv import load_dotenv
from utils.utils import create_message, serialize_message, get_queue_name

# Carrega variáveis de ambiente do arquivo .env
load_dotenv('config/.env')

class AsyncProducer:
    def __init__(self, user_state):
        self.user_state = user_state
        self.connection = None
        self.channel = None
        
        # Configurações RabbitMQ
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.username = os.getenv('RABBITMQ_USER', 'admin')
        self.password = os.getenv('RABBITMQ_PASS', 'admin123')
        
        self._connect()
    
    def _connect(self):
        """Conecta ao RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            print(f"✅ Produtor conectado ao RabbitMQ em {self.host}")
        except Exception as e:
            print(f"❌ Erro ao conectar produtor ao RabbitMQ: {e}")
            self.connection = None
            self.channel = None
    
    def _ensure_connection(self):
        """Garante que a conexão está ativa"""
        try:
            if not self.connection or self.connection.is_closed:
                self._connect()
            elif not self.channel or self.channel.is_closed:
                self.channel = self.connection.channel()
            return self.connection and self.channel and not self.connection.is_closed
        except:
            return False
    
    def _ensure_connection(self):
        """Garante que a conexão está ativa"""
        if not self.connection or self.connection.is_closed:
            self._connect()
        return self.connection and self.channel
    
    def send_async_message(self, recipient, content, message_type="direct"):
        """Envia mensagem assíncrona para a fila do destinatário"""
        if not self._ensure_connection():
            return False, "Erro de conexão com RabbitMQ"
        
        try:
            # Cria fila do destinatário se não existir
            queue_name = get_queue_name(recipient)
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            # Cria mensagem estruturada
            message = create_message(
                sender=self.user_state.username,
                recipient=recipient,
                content=content,
                message_type=message_type
            )
            
            # Envia mensagem
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=serialize_message(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Mensagem persistente
                    timestamp=int(time.time())
                )
            )
            
            print(f"📤 Mensagem assíncrona enviada para {recipient}")
            return True, "✅ Mensagem enviada via RabbitMQ"
            
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem assíncrona: {e}")
            self.connection = None
            self.channel = None
            return False, f"Erro: {e}"
    
    def send_location_broadcast(self):
        """Envia broadcast da localização atual"""
        if not self._ensure_connection():
            return False
        
        try:
            # Declara exchange para broadcast de localização
            self.channel.exchange_declare(exchange='location_broadcast', exchange_type='fanout')
            
            user_info = self.user_state.get_info()
            location_data = {
                "type": "location_update",
                "username": user_info["username"],
                "latitude": user_info["latitude"],
                "longitude": user_info["longitude"],
                "status": user_info["status"],
                "radius": user_info["radius"],
                "port": user_info["port"],
                "timestamp": time.time()
            }
            
            self.channel.basic_publish(
                exchange='location_broadcast',
                routing_key='',
                body=json.dumps(location_data)
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar broadcast de localização: {e}")
            return False
    
    def send_status_update(self, new_status):
        """Envia atualização de status"""
        if not self._ensure_connection():
            return False
        
        try:
            self.channel.exchange_declare(exchange='status_updates', exchange_type='fanout')
            
            status_data = {
                "type": "status_update",
                "username": self.user_state.username,
                "old_status": self.user_state.status,
                "new_status": new_status,
                "timestamp": time.time()
            }
            
            self.channel.basic_publish(
                exchange='status_updates',
                routing_key='',
                body=json.dumps(status_data)
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar atualização de status: {e}")
            return False
    
    def check_user_queue_exists(self, username):
        """Verifica se a fila de um usuário existe"""
        if not self._ensure_connection():
            return False
        
        try:
            queue_name = get_queue_name(username)
            # Tenta declarar fila passivamente (só verifica se existe)
            self.channel.queue_declare(queue=queue_name, passive=True)
            return True
        except pika.exceptions.ChannelClosedByBroker:
            # Fila não existe
            self._connect()  # Reconecta após erro
            return False
        except Exception as e:
            print(f"Erro ao verificar fila: {e}")
            return False
    
    def create_user_queue(self, username):
        """Cria fila para um usuário"""
        if not self._ensure_connection():
            return False
        
        try:
            queue_name = get_queue_name(username)
            self.channel.queue_declare(queue=queue_name, durable=True)
            return True
        except Exception as e:
            print(f"Erro ao criar fila: {e}")
            return False
    
    def send_notification(self, recipient, notification_type, data):
        """Envia notificação específica"""
        if not self._ensure_connection():
            return False, "Erro de conexão"
        
        try:
            queue_name = f"notifications_{recipient}"
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            notification = {
                "type": notification_type,
                "sender": self.user_state.username,
                "recipient": recipient,
                "data": data,
                "timestamp": time.time()
            }
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(notification),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            return True, "Notificação enviada"
            
        except Exception as e:
            print(f"Erro ao enviar notificação: {e}")
            return False, f"Erro: {e}"
    
    def get_queue_message_count(self, username):
        """Retorna número de mensagens na fila de um usuário"""
        if not self._ensure_connection():
            return 0
        
        try:
            queue_name = get_queue_name(username)
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            return method.method.message_count
        except:
            return 0
    
    def purge_user_queue(self, username):
        """Limpa todas as mensagens da fila de um usuário"""
        if not self._ensure_connection():
            return False
        
        try:
            queue_name = get_queue_name(username)
            self.channel.queue_purge(queue=queue_name)
            return True
        except Exception as e:
            print(f"Erro ao limpar fila: {e}")
            return False
    
    def close(self):
        """Fecha conexão com RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                print("Conexão do produtor fechada")
        except Exception as e:
            print(f"Erro ao fechar conexão do produtor: {e}")
    
    def get_producer_status(self):
        """Retorna status do produtor"""
        return {
            "connected": self.connection and not self.connection.is_closed,
            "user": self.user_state.username if self.user_state else None
        }
