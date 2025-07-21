"""
Cliente TCP para comunicação síncrona
Conecta-se a outros usuários para chat em tempo real.
"""

import socket
import threading
import time
import json
from utils.utils import serialize_message, deserialize_message, format_timestamp, get_port_from_username

class SyncClient:
    def __init__(self, user_state, gui):
        self.user_state = user_state
        self.gui = gui
        self.connections = {}  # {username: connection_info}
        self.connection_threads = {}
        
    def connect_to_user(self, username, host='localhost'):
        """Conecta-se a outro usuário para chat síncrono"""
        if username in self.connections:
            return True, "Já conectado a este usuário"
        
        # Verifica se usuário está no raio
        if not self.user_state.is_contact_in_range(username):
            return False, "Usuário fora do raio de comunicação"
        
        try:
            # Obtém porta do usuário
            contact_info = self.user_state.contacts.get(username)
            if contact_info:
                port = contact_info.get("port", get_port_from_username(username))
            else:
                port = get_port_from_username(username)
            
            # Cria socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10)  # Timeout de 10 segundos
            
            # Conecta
            client_socket.connect((host, port))
            
            # Handshake
            handshake_msg = {
                "type": "handshake",
                "sender": self.user_state.username,
                "timestamp": time.time()
            }
            
            client_socket.send(serialize_message(handshake_msg).encode('utf-8'))
            
            # Aguarda confirmação
            response_data = client_socket.recv(1024).decode('utf-8')
            response = deserialize_message(response_data)
            
            if not response or response.get("type") != "handshake_ok":
                client_socket.close()
                error_msg = response.get("message", "Falha no handshake") if response else "Sem resposta"
                return False, f"Erro na conexão: {error_msg}"
            
            # Armazena conexão
            self.connections[username] = {
                "socket": client_socket,
                "host": host,
                "port": port,
                "connected_at": time.time(),
                "active": True
            }
            
            # Inicia thread para receber mensagens
            receive_thread = threading.Thread(
                target=self._receive_messages,
                args=(username, client_socket),
                daemon=True
            )
            receive_thread.start()
            self.connection_threads[username] = receive_thread
            
            # Notifica GUI
            if self.gui:
                self.gui.on_sync_connection(username, True)
            
            return True, "Conectado com sucesso"
            
        except socket.timeout:
            return False, "Timeout na conexão"
        except ConnectionRefusedError:
            return False, "Usuário não está disponível para chat"
        except Exception as e:
            return False, f"Erro na conexão: {e}"
    
    def _receive_messages(self, username, client_socket):
        """Thread para receber mensagens de um usuário"""
        try:
            while username in self.connections and self.connections[username]["active"]:
                try:
                    client_socket.settimeout(30)  # Timeout para recebimento
                    data = client_socket.recv(1024).decode('utf-8')
                    
                    if not data:
                        break
                    
                    message = deserialize_message(data)
                    if not message:
                        continue
                    
                    message_type = message.get("type")
                    
                    if message_type == "chat_message":
                        self._handle_received_message(username, message)
                        
                    elif message_type == "ping":
                        self._send_pong(client_socket)
                        
                    elif message_type == "pong":
                        # Atualiza última atividade
                        if username in self.connections:
                            self.connections[username]["last_pong"] = time.time()
                    
                    elif message_type == "disconnect":
                        break
                        
                    elif message_type == "error":
                        error_msg = message.get("message", "Erro desconhecido")
                        if self.gui:
                            self.gui.display_sync_message(f"[ERRO] {username}: {error_msg}")
                        break
                
                except socket.timeout:
                    # Envia ping para verificar conexão
                    try:
                        self._send_ping(client_socket)
                    except:
                        break
                        
                except Exception as e:
                    print(f"Erro ao receber mensagem de {username}: {e}")
                    break
                    
        except Exception as e:
            print(f"Erro na thread de recebimento para {username}: {e}")
        
        finally:
            self._cleanup_connection(username)
    
    def _handle_received_message(self, username, message):
        """Processa mensagem recebida"""
        content = message.get("content")
        timestamp = message.get("timestamp", time.time())
        
        if content and self.gui:
            formatted_msg = f"[{format_timestamp(str(timestamp))}] {username}: {content}"
            self.gui.display_sync_message(formatted_msg)
    
    def _send_ping(self, client_socket):
        """Envia ping para verificar conexão"""
        ping_msg = {
            "type": "ping",
            "timestamp": time.time()
        }
        client_socket.send(serialize_message(ping_msg).encode('utf-8'))
    
    def _send_pong(self, client_socket):
        """Responde ping"""
        pong_msg = {
            "type": "pong",
            "timestamp": time.time()
        }
        client_socket.send(serialize_message(pong_msg).encode('utf-8'))
    
    def send_message(self, username, content):
        """Envia mensagem para um usuário conectado"""
        if username not in self.connections:
            return False, "Não conectado a este usuário"
        
        connection = self.connections[username]
        if not connection["active"]:
            return False, "Conexão não está ativa"
        
        try:
            message = {
                "type": "chat_message",
                "sender": self.user_state.username,
                "content": content,
                "timestamp": time.time()
            }
            
            connection["socket"].send(serialize_message(message).encode('utf-8'))
            
            # Exibe mensagem enviada na GUI
            if self.gui:
                formatted_msg = f"[{format_timestamp(str(message['timestamp']))}] Você: {content}"
                self.gui.display_sync_message(formatted_msg)
            
            return True, "Mensagem enviada"
            
        except Exception as e:
            self._cleanup_connection(username)
            return False, f"Erro ao enviar: {e}"
    
    def disconnect_from_user(self, username):
        """Desconecta de um usuário específico"""
        if username not in self.connections:
            return False, "Não conectado a este usuário"
        
        try:
            connection = self.connections[username]
            
            # Envia mensagem de desconexão
            disconnect_msg = {
                "type": "disconnect",
                "sender": self.user_state.username,
                "message": "Desconectando..."
            }
            
            try:
                connection["socket"].send(serialize_message(disconnect_msg).encode('utf-8'))
            except:
                pass
            
            self._cleanup_connection(username)
            
            # Notifica GUI
            if self.gui:
                self.gui.on_sync_connection(username, False)
            
            return True, "Desconectado"
            
        except Exception as e:
            return False, f"Erro ao desconectar: {e}"
    
    def _cleanup_connection(self, username):
        """Limpa recursos de uma conexão"""
        if username in self.connections:
            connection = self.connections[username]
            connection["active"] = False
            
            try:
                connection["socket"].close()
            except:
                pass
            
            del self.connections[username]
        
        if username in self.connection_threads:
            del self.connection_threads[username]
    
    def disconnect_all(self):
        """Desconecta de todos os usuários"""
        usernames = list(self.connections.keys())
        for username in usernames:
            self.disconnect_from_user(username)
    
    def get_connected_users(self):
        """Retorna lista de usuários conectados"""
        return [username for username, conn in self.connections.items() if conn["active"]]
    
    def is_connected_to_user(self, username):
        """Verifica se está conectado a um usuário"""
        return (username in self.connections and 
                self.connections[username]["active"])
    
    def get_connection_info(self, username):
        """Retorna informações da conexão com um usuário"""
        if username not in self.connections:
            return None
        
        connection = self.connections[username]
        return {
            "host": connection["host"],
            "port": connection["port"],
            "connected_at": connection["connected_at"],
            "active": connection["active"]
        }
    
    def check_connections_health(self):
        """Verifica saúde das conexões ativas"""
        to_cleanup = []
        
        for username, connection in self.connections.items():
            if not connection["active"]:
                continue
                
            try:
                # Tenta enviar ping
                self._send_ping(connection["socket"])
            except:
                to_cleanup.append(username)
        
        # Limpa conexões mortas
        for username in to_cleanup:
            self._cleanup_connection(username)
            if self.gui:
                self.gui.on_sync_connection(username, False)
    
    def get_client_status(self):
        """Retorna status do cliente"""
        active_connections = len([c for c in self.connections.values() if c["active"]])
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "connected_users": self.get_connected_users()
        }
