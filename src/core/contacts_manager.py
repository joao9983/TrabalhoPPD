"""
Gerenciador de Contatos
Responsável por gerenciar a lista de contatos disponíveis baseado na localização e raio.
"""

import threading
import time
import pika
import os
from dotenv import load_dotenv
from utils.utils import calculate_distance, get_queue_name, validate_coordinates

# Carrega variáveis de ambiente do arquivo .env
load_dotenv('config/.env')

class ContactsManager:
    def __init__(self, user_state):
        self.user_state = user_state
        self.contacts = {}  # {username: contact_info}
        self.lock = threading.Lock()
        self.running = False
        self.update_thread = None
        self.connection = None
        self.channel = None
        
        # Configurações RabbitMQ
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.username = os.getenv('RABBITMQ_USER', 'admin')
        self.password = os.getenv('RABBITMQ_PASS', 'admin123')
        
        self._connect_rabbitmq()
    
    def _connect_rabbitmq(self):
        """Conecta ao RabbitMQ com tratamento de erro"""
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
            
            # Declara exchange para descoberta de usuários
            self.channel.exchange_declare(exchange='user_discovery', exchange_type='fanout', durable=False)
            print(f"✅ ContactsManager conectado ao RabbitMQ")
            
        except Exception as e:
            print(f"❌ Erro ao conectar ContactsManager ao RabbitMQ: {e}")
            self.connection = None
            self.channel = None
    
    def _ensure_connection(self):
        """Garante que a conexão está ativa"""
        try:
            if not self.connection or self.connection.is_closed:
                self._connect_rabbitmq()
            elif not self.channel or self.channel.is_closed:
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange='user_discovery', exchange_type='fanout', durable=False)
            return True
        except:
            return False
    
    def start_discovery(self):
        """Inicia o processo de descoberta de usuários"""
        if self.running:
            return
            
        self.running = True
        
        # Thread para broadcast periódico da posição
        self.update_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.update_thread.start()
        
        # Thread para escutar broadcasts de outros usuários
        discovery_thread = threading.Thread(target=self._listen_discovery, daemon=True)
        discovery_thread.start()
    
    def stop_discovery(self):
        """Para o processo de descoberta"""
        self.running = False
        if self.connection and not self.connection.is_closed:
            self.connection.close()
    
    def _discovery_loop(self):
        """Loop principal de broadcast da posição"""
        while self.running:
            try:
                self._broadcast_position()
                time.sleep(10)  # Broadcast a cada 10 segundos
            except Exception as e:
                print(f"Erro no loop de descoberta: {e}")
                time.sleep(5)
    
    def _broadcast_position(self):
        """Envia broadcast com a posição atual do usuário"""
        if not self._ensure_connection() or self.user_state.status == "offline":
            return
            
        try:
            user_info = self.user_state.get_info()
            message = {
                "type": "position_update",
                "username": user_info["username"],
                "latitude": user_info["latitude"],
                "longitude": user_info["longitude"],
                "status": user_info["status"],
                "port": user_info["port"]
            }
            
            import json
            self.channel.basic_publish(
                exchange='user_discovery',
                routing_key='',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=1  # Non-persistent
                )
            )
            
        except Exception as e:
            print(f"⚠️ Erro ao enviar broadcast: {e}")
            self.connection = None
            self.channel = None
    
    def _listen_discovery(self):
        """Escuta broadcasts de outros usuários"""
        if not self._ensure_connection():
            return
            
        try:
            # Cria fila temporária para receber broadcasts
            result = self.channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            self.channel.queue_bind(exchange='user_discovery', queue=queue_name)
            
            def callback(ch, method, properties, body):
                try:
                    import json
                    message = json.loads(body.decode())
                    self._process_discovery_message(message)
                except Exception as e:
                    print(f"⚠️ Erro ao processar mensagem de descoberta: {e}")
            
            self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            
            while self.running:
                try:
                    if self.connection and not self.connection.is_closed:
                        self.connection.process_data_events(time_limit=1)
                    else:
                        print("📡 Reconectando listener de descoberta...")
                        if not self._ensure_connection():
                            time.sleep(5)
                            continue
                        # Recriar queue após reconexão
                        result = self.channel.queue_declare(queue='', exclusive=True)
                        queue_name = result.method.queue
                        self.channel.queue_bind(exchange='user_discovery', queue=queue_name)
                        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                except Exception as e:
                    print(f"⚠️ Erro no listener, tentando reconectar: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"❌ Erro no listener de descoberta: {e}")
            self.connection = None
            self.channel = None
    
    def _process_discovery_message(self, message):
        """Processa mensagem de descoberta recebida"""
        if message.get("type") != "position_update":
            return
            
        username = message.get("username")
        if not username or username == self.user_state.username:
            return
        
        latitude = message.get("latitude")
        longitude = message.get("longitude")
        status = message.get("status", "online")
        port = message.get("port", 8000)
        
        if not validate_coordinates(latitude, longitude):
            return
        
        # Calcula distância
        user_info = self.user_state.get_info()
        distance = calculate_distance(
            user_info["latitude"], user_info["longitude"],
            latitude, longitude
        )
        
        with self.lock:
            # Atualiza informações do contato
            self.contacts[username] = {
                "latitude": latitude,
                "longitude": longitude,
                "status": status,
                "port": port,
                "distance": distance,
                "last_seen": time.time()
            }
            
            # Adiciona ao estado do usuário se estiver no raio
            if distance <= user_info["radius"]:
                self.user_state.add_contact(username, latitude, longitude, status)
    
    def get_contacts_in_range(self):
        """Retorna contatos dentro do raio atual"""
        user_info = self.user_state.get_info()
        contacts_in_range = {}
        
        with self.lock:
            for username, contact in self.contacts.items():
                if contact["distance"] <= user_info["radius"] and contact["status"] != "offline":
                    contacts_in_range[username] = contact.copy()
        
        return contacts_in_range
    
    def get_contact_info(self, username):
        """Retorna informações de um contato específico"""
        with self.lock:
            return self.contacts.get(username)
    
    def is_contact_online_and_in_range(self, username):
        """Verifica se um contato está online e no raio"""
        contact = self.get_contact_info(username)
        if not contact:
            return False
        
        user_info = self.user_state.get_info()
        return (contact["status"] == "online" and 
                contact["distance"] <= user_info["radius"])
    
    def cleanup_old_contacts(self, max_age=300):
        """Remove contatos que não foram vistos há muito tempo"""
        current_time = time.time()
        
        with self.lock:
            to_remove = []
            for username, contact in self.contacts.items():
                if current_time - contact.get("last_seen", 0) > max_age:
                    to_remove.append(username)
            
            for username in to_remove:
                del self.contacts[username]
                self.user_state.remove_contact(username)
    
    def add_manual_contact(self, username, latitude, longitude):
        """Adiciona um contato manualmente"""
        if not validate_coordinates(latitude, longitude):
            return False
        
        user_info = self.user_state.get_info()
        distance = calculate_distance(
            user_info["latitude"], user_info["longitude"],
            latitude, longitude
        )
        
        with self.lock:
            self.contacts[username] = {
                "latitude": latitude,
                "longitude": longitude,
                "status": "unknown",
                "port": 8000 + hash(username) % 1000,
                "distance": distance,
                "last_seen": time.time(),
                "manual": True
            }
        
        self.user_state.add_contact(username, latitude, longitude, "unknown")
        return True
    
    def remove_contact(self, username):
        """Remove um contato"""
        with self.lock:
            if username in self.contacts:
                del self.contacts[username]
        
        return self.user_state.remove_contact(username)
    
    def update_user_radius(self, new_radius):
        """Atualiza o raio e recalcula contatos no raio"""
        self.user_state.update_radius(new_radius)
        
        # Força atualização da lista de contatos no raio
        user_info = self.user_state.get_info()
        
        with self.lock:
            for username, contact in self.contacts.items():
                if contact["distance"] <= new_radius:
                    self.user_state.add_contact(
                        username, 
                        contact["latitude"], 
                        contact["longitude"], 
                        contact["status"]
                    )
                else:
                    self.user_state.remove_contact(username)
    
    def get_all_contacts(self):
        """Retorna todos os contatos conhecidos"""
        with self.lock:
            return self.contacts.copy()
    
    def get_contacts_count(self):
        """Retorna número de contatos no raio"""
        return len(self.get_contacts_in_range())
    
    def stop(self):
        """Para todos os serviços e fecha conexões"""
        self.running = False
        
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
        except:
            pass
            
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
        
        print("📴 ContactsManager finalizado")
