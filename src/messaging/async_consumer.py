"""
Consumidor de mensagens assíncronas
Recebe mensagens da fila RabbitMQ quando o usuário está online.
"""

import pika
import json
import threading
import time
import os
from dotenv import load_dotenv
from utils.utils import deserialize_message, get_queue_name, format_timestamp

# Carrega variáveis de ambiente do arquivo .env
load_dotenv('config/.env')

# Configurações RabbitMQ centralizadas
class RabbitMQConfig:
    HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    USERNAME = os.getenv('RABBITMQ_USER', 'admin')
    PASSWORD = os.getenv('RABBITMQ_PASS', 'admin123')
    HEARTBEAT = 300
    BLOCKED_CONNECTION_TIMEOUT = 300
    CONNECTION_ATTEMPTS = 3
    RETRY_DELAY = 2
    
    @classmethod
    def get_connection_parameters(cls):
        credentials = pika.PlainCredentials(cls.USERNAME, cls.PASSWORD)
        return pika.ConnectionParameters(
            host=cls.HOST,
            credentials=credentials,
            heartbeat=cls.HEARTBEAT,
            blocked_connection_timeout=cls.BLOCKED_CONNECTION_TIMEOUT,
            connection_attempts=cls.CONNECTION_ATTEMPTS,
            retry_delay=cls.RETRY_DELAY
        )

class AsyncConsumer:
    def __init__(self, username, gui):
        self.username = username
        self.gui = gui
        self.connection = None
        self.channel = None
        self.consuming = False
        self.consumer_thread = None
        self.queue_name = get_queue_name(username)
        self.auto_check_timer = None
        self.auto_check_enabled = False
        
    def _connect(self):
        """Conecta ao RabbitMQ com melhor tratamento de erro"""
        try:
            self.connection = pika.BlockingConnection(RabbitMQConfig.get_connection_parameters())
            self.channel = self.connection.channel()
            
            # Declara a fila do usuário
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            # Configura QoS para processar uma mensagem por vez
            self.channel.basic_qos(prefetch_count=1)
            
            print(f"✅ Consumidor conectado ao RabbitMQ para fila: {self.queue_name}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar consumidor ao RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            return False
    
    def start(self):
        """Inicia o consumidor de mensagens"""
        print(f"🔄 AsyncConsumer.start() para {self.username}...")
        
        if self.consuming:
            print("   ⚠️ Já está consumindo, retornando True")
            return True
        
        print("   📞 Tentando conectar...")
        if not self._connect():
            print("   ❌ Falha na conexão")
            return False
        
        try:
            print("   🎯 Configurando consumidor...")
            self.consuming = True
            
            # Configura callback para processar mensagens
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self._process_message,
                auto_ack=False
            )
            print("   📝 Callback configurado")
            
            # Inicia thread para consumir mensagens
            print("   🧵 Iniciando thread de consumo...")
            self.consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
            self.consumer_thread.start()
            print("   ✅ Thread de consumo iniciada")
            
            # Inicia thread para escutar broadcasts
            print("   📡 Iniciando thread de broadcasts...")
            broadcast_thread = threading.Thread(target=self._listen_broadcasts, daemon=True)
            broadcast_thread.start()
            print("   ✅ Thread de broadcasts iniciada")
            
            print(f"   🎉 Consumidor iniciado para {self.username}")
            return True
            
        except Exception as e:
            print(f"   ❌ Erro ao iniciar consumidor: {e}")
            self.consuming = False
            return False
    
    def _consume_loop(self):
        """Loop principal de consumo com melhor recuperação de erro"""
        retry_count = 0
        max_retries = 5
        
        try:
            while self.consuming and retry_count < max_retries:
                try:
                    if not self.connection or self.connection.is_closed:
                        print("Conexão perdida, tentando reconectar...")
                        if self._reconnect():
                            retry_count = 0  # Reset contador após reconexão bem-sucedida
                        else:
                            retry_count += 1
                            time.sleep(5)
                            continue
                    
                    # Processa eventos de dados
                    self.connection.process_data_events(time_limit=1)
                    
                except pika.exceptions.AMQPConnectionError as e:
                    print(f"Erro de conexão AMQP: {e}")
                    retry_count += 1
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"Erro no loop de consumo: {e}")
                    retry_count += 1
                    time.sleep(2)
                    
        except Exception as e:
            print(f"Erro fatal no consumidor: {e}")
        finally:
            print("Loop de consumo encerrado")
    
    def _reconnect(self):
        """Tenta reconectar ao RabbitMQ com melhor tratamento"""
        try:
            # Fecha conexão anterior se existir
            if self.connection and not self.connection.is_closed:
                try:
                    self.connection.close()
                except:
                    pass
        except:
            pass
        
        # Tenta reconectar
        if self._connect() and self.consuming:
            try:
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._process_message,
                    auto_ack=False
                )
                print("Reconectado com sucesso")
                return True
            except Exception as e:
                print(f"Erro ao reconfigurar consumidor após reconexão: {e}")
                return False
        
        return False
    
    def _process_message(self, ch, method, properties, body):
        """Processa mensagem recebida"""
        try:
            # Deserializa mensagem
            message_str = body.decode('utf-8')
            message = deserialize_message(message_str)
            
            if not message:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Processa diferentes tipos de mensagem
            msg_type = message.get("type", "direct")
            sender = message.get("sender", "Desconhecido")
            content = message.get("content", "")
            timestamp = message.get("timestamp", time.time())
            
            if msg_type == "direct":
                self._handle_direct_message(sender, content, timestamp)
            elif msg_type == "broadcast":
                self._handle_broadcast_message(sender, content, timestamp)
            elif msg_type == "system":
                self._handle_system_message(content, timestamp)
            
            # Confirma processamento da mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            # Rejeita mensagem em caso de erro
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def _handle_direct_message(self, sender, content, timestamp):
        """Processa mensagem direta"""
        if self.gui:
            formatted_msg = f"[{format_timestamp(str(timestamp))}] [OFFLINE] {sender}: {content}"
            self.gui.display_async_message(formatted_msg)
    
    def _handle_broadcast_message(self, sender, content, timestamp):
        """Processa mensagem de broadcast"""
        if self.gui:
            formatted_msg = f"[{format_timestamp(str(timestamp))}] [BROADCAST] {sender}: {content}"
            self.gui.display_async_message(formatted_msg)
    
    def _handle_system_message(self, content, timestamp):
        """Processa mensagem do sistema"""
        if self.gui:
            formatted_msg = f"[{format_timestamp(str(timestamp))}] [SISTEMA] {content}"
            self.gui.display_async_message(formatted_msg)
    
    def _listen_broadcasts(self):
        """Escuta broadcasts de localização e status com melhor recuperação"""
        max_retries = 3
        retry_count = 0
        
        while self.consuming and retry_count < max_retries:
            try:
                if not self.connection or self.connection.is_closed:
                    print("🔄 Reconectando listener de broadcasts...")
                    if not self._connect():
                        retry_count += 1
                        time.sleep(5)
                        continue
                
                # Reset contador após conexão bem-sucedida
                retry_count = 0
                
                # Cria canal separado para broadcasts
                broadcast_channel = self.connection.channel()
                
                # Configura exchanges para diferentes tipos de broadcast
                exchanges = ['location_broadcast', 'status_updates', 'user_discovery']
                temp_queues = []
                
                for exchange in exchanges:
                    try:
                        broadcast_channel.exchange_declare(exchange=exchange, exchange_type='fanout')
                        
                        # Cria fila temporária para receber broadcasts
                        result = broadcast_channel.queue_declare(queue='', exclusive=True)
                        temp_queue = result.method.queue
                        temp_queues.append(temp_queue)
                        
                        broadcast_channel.queue_bind(exchange=exchange, queue=temp_queue)
                        
                        # Configura callback
                        broadcast_channel.basic_consume(
                            queue=temp_queue,
                            on_message_callback=self._process_broadcast,
                            auto_ack=True
                        )
                    except Exception as e:
                        print(f"⚠️ Erro ao configurar exchange {exchange}: {e}")
                
                # Loop de escuta de broadcasts
                while self.consuming:
                    try:
                        if self.connection and not self.connection.is_closed:
                            self.connection.process_data_events(time_limit=1)
                        else:
                            print("🔄 Conexão de broadcast perdida, reconectando...")
                            break
                    except Exception as e:
                        print(f"⚠️ Erro no loop de broadcasts: {e}")
                        break
                        
            except Exception as e:
                print(f"Erro ao escutar broadcasts: {e}")
                retry_count += 1
                time.sleep(5)
                
        if retry_count >= max_retries:
            print("❌ Listener de broadcasts falhou após múltiplas tentativas")
    
    def _process_broadcast(self, ch, method, properties, body):
        """Processa broadcasts recebidos"""
        try:
            data = json.loads(body.decode('utf-8'))
            broadcast_type = data.get("type")
            
            if broadcast_type == "location_update":
                self._handle_location_update(data)
            elif broadcast_type == "status_update":
                self._handle_status_update(data)
            elif broadcast_type == "position_update":
                self._handle_position_update(data)
                
        except Exception as e:
            print(f"Erro ao processar broadcast: {e}")
    
    def _handle_location_update(self, data):
        """Processa atualização de localização"""
        username = data.get("username")
        if username != self.username and self.gui:
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            status = data.get("status")
            
            # Notifica GUI sobre atualização de localização
            self.gui.on_location_update(username, latitude, longitude, status)
    
    def _handle_status_update(self, data):
        """Processa atualização de status"""
        username = data.get("username")
        if username != self.username and self.gui:
            new_status = data.get("new_status")
            
            # Notifica GUI sobre mudança de status
            self.gui.on_status_update(username, new_status)
    
    def _handle_position_update(self, data):
        """Processa atualização de posição (para descoberta)"""
        username = data.get("username")
        if username != self.username and self.gui:
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            status = data.get("status")
            port = data.get("port")
            
            # Notifica GUI sobre novo usuário descoberto
            self.gui.on_user_discovered(username, latitude, longitude, status, port)
    
    def consume_pending_messages(self):
        """Força consumo de mensagens pendentes"""
        if not self.channel:
            return 0
        
        messages_consumed = 0
        try:
            while True:
                method_frame, header_frame, body = self.channel.basic_get(
                    queue=self.queue_name, 
                    auto_ack=False
                )
                
                if method_frame:
                    self._process_message(self.channel, method_frame, header_frame, body)
                    messages_consumed += 1
                else:
                    break
                    
        except Exception as e:
            print(f"Erro ao consumir mensagens pendentes: {e}")
        
        return messages_consumed
    
    def start_auto_check_when_online(self):
        """Inicia verificação automática de mensagens quando usuário está online"""
        if not self.auto_check_enabled:
            self.auto_check_enabled = True
            self._schedule_auto_check()
    
    def stop_auto_check_when_offline(self):
        """Para verificação automática quando usuário não está online"""
        self.auto_check_enabled = False
        if self.auto_check_timer:
            try:
                self.auto_check_timer.cancel()
                self.auto_check_timer = None
            except:
                pass
    
    def _schedule_auto_check(self):
        """Agenda próxima verificação automática"""
        if self.auto_check_enabled and self.gui:
            # Verifica se há mensagens pendentes e processa automaticamente
            try:
                count = self.consume_pending_messages()
                if count > 0:
                    print(f"🔄 [AUTO] Processadas {count} mensagem(s) para usuário online")
            except Exception as e:
                print(f"⚠️ Erro na verificação automática: {e}")
            
            # Agenda próxima verificação em 3 segundos
            if self.auto_check_enabled:
                self.auto_check_timer = threading.Timer(3.0, self._schedule_auto_check)
                self.auto_check_timer.daemon = True
                self.auto_check_timer.start()
    
    def get_queue_message_count(self):
        """Retorna número de mensagens na fila"""
        if not self.channel:
            return 0
        
        try:
            method = self.channel.queue_declare(queue=self.queue_name, passive=True)
            return method.method.message_count
        except:
            return 0
    
    def stop(self):
        """Para o consumidor"""
        self.consuming = False
        
        # Para verificação automática
        self.stop_auto_check_when_offline()
        
        try:
            if self.channel:
                self.channel.stop_consuming()
        except:
            pass
        
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
        
        print(f"Consumidor parado para {self.username}")
    
    def get_consumer_status(self):
        """Retorna status do consumidor"""
        return {
            "username": self.username,
            "consuming": self.consuming,
            "connected": self.connection and not self.connection.is_closed,
            "queue_name": self.queue_name,
            "pending_messages": self.get_queue_message_count()
        }
