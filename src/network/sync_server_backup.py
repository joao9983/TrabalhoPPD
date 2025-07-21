"""
Servidor TCP para comunicação síncrona
Permite chat em tempo real entre usuários online e dentro do raio.
"""

import socket
import threading
import json
import time
from utils.utils import deserialize_message, serialize_message, format_timestamp

class SyncServer:
    def __init__(self, user_state, gui):
        self.user_state = user_state
        self.gui = gui
        self.server_socket = None
        self.running = False
        self.clients = {}  # {client_socket: username}
        self.client_threads = []
        
    def start(self):
        """Inicia o servidor TCP"""
        print(f"🔄 SyncServer.start() na porta {self.user_state.socket_port}...")
        
        if self.running:
            print("   ⚠️ Servidor já está rodando")
            return
            
        try:
            print("   🔌 Criando socket...")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind na porta específica do usuário
            port = self.user_state.socket_port
            print(f"   📡 Fazendo bind na porta {port}...")
            self.server_socket.bind(('localhost', port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"   ✅ Servidor iniciado na porta {port}")
            
            # Inicia loop do servidor em thread separada para não bloquear
            server_thread = threading.Thread(target=self._server_loop, daemon=True)
            server_thread.start()
            print("   🧵 Thread do servidor iniciada")
            
        except Exception as e:
            print(f"   ❌ Erro ao iniciar servidor: {e}")
            self.running = False
            raise
    
    def _server_loop(self):
        """Loop principal do servidor em thread separada"""
        print("   🔄 Loop do servidor iniciado...")
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"   📞 Nova conexão de {addr}")
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)
                
            except socket.error:
                if self.running:
                    print("   ⚠️ Erro ao aceitar conexão")
                break
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    self.client_threads.append(client_thread)
                    
                except socket.error:
                    if self.running:
                        print("Erro ao aceitar conexão")
                    break
                    
        except Exception as e:
            print(f"Erro ao iniciar servidor: {e}")
            self.running = False
    
    def _handle_client(self, client_socket, addr):
        """Manipula conexão de um cliente"""
        username = None
        try:
            # Timeout para receber dados
            client_socket.settimeout(30)
            
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    message = deserialize_message(data)
                    if not message:
                        continue
                    
                    message_type = message.get("type")
                    
                    if message_type == "handshake":
                        username = self._handle_handshake(client_socket, message)
                        
                    elif message_type == "chat_message":
                        self._handle_chat_message(client_socket, message, username)
                        
                    elif message_type == "ping":
                        self._send_pong(client_socket)
                        
                except socket.timeout:
                    # Timeout - envia ping para verificar se cliente ainda está ativo
                    try:
                        self._send_ping(client_socket)
                    except:
                        break
                        
                except Exception as e:
                    print(f"Erro ao processar dados do cliente: {e}")
                    break
                    
        except Exception as e:
            print(f"Erro na conexão com cliente {addr}: {e}")
            
        finally:
            # Limpa conexão
            if username and client_socket in self.clients:
                del self.clients[client_socket]
                
            try:
                client_socket.close()
            except:
                pass
                
            print(f"Cliente {addr} desconectado")
    
    def _handle_handshake(self, client_socket, message):
        """Processa handshake inicial do cliente"""
        try:
            sender = message.get("sender")
            
            if not sender:
                self._send_error(client_socket, "Username obrigatório")
                return None
            
            # Verifica se o usuário está no raio
            if not self.user_state.is_contact_in_range(sender):
                self._send_error(client_socket, "Usuário fora do raio de comunicação")
                return None
            
            # Registra cliente
            self.clients[client_socket] = sender
            
            # Envia confirmação
            response = {
                "type": "handshake_ok",
                "message": "Conectado com sucesso",
                "server_user": self.user_state.username
            }
            
            client_socket.send(serialize_message(response).encode('utf-8'))
            
            # Notifica GUI sobre nova conexão
            if self.gui:
                self.gui.on_sync_connection(sender, True)
            
            return sender
            
        except Exception as e:
            print(f"Erro no handshake: {e}")
            return None
    
    def _handle_chat_message(self, client_socket, message, sender):
        """Processa mensagem de chat recebida"""
        try:
            content = message.get("content")
            timestamp = message.get("timestamp", time.time())
            
            if not content:
                return
            
            # Exibe mensagem na GUI
            if self.gui:
                formatted_msg = f"[{format_timestamp(str(timestamp))}] {sender}: {content}"
                self.gui.display_sync_message(formatted_msg)
            
            # Confirma recebimento
            response = {
                "type": "message_received",
                "timestamp": timestamp
            }
            
            client_socket.send(serialize_message(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
    
    def _send_ping(self, client_socket):
        """Envia ping para cliente"""
        ping_msg = {
            "type": "ping",
            "timestamp": time.time()
        }
        client_socket.send(serialize_message(ping_msg).encode('utf-8'))
    
    def _send_pong(self, client_socket):
        """Responde ping do cliente"""
        pong_msg = {
            "type": "pong",
            "timestamp": time.time()
        }
        client_socket.send(serialize_message(pong_msg).encode('utf-8'))
    
    def _send_error(self, client_socket, error_message):
        """Envia mensagem de erro para cliente"""
        error_msg = {
            "type": "error",
            "message": error_message
        }
        try:
            client_socket.send(serialize_message(error_msg).encode('utf-8'))
        except:
            pass
    
    def broadcast_message(self, message, exclude_user=None):
        """Envia mensagem para todos os clientes conectados"""
        to_remove = []
        
        for client_socket, username in self.clients.items():
            if exclude_user and username == exclude_user:
                continue
                
            try:
                client_socket.send(serialize_message(message).encode('utf-8'))
            except:
                to_remove.append(client_socket)
        
        # Remove conexões mortas
        for client_socket in to_remove:
            if client_socket in self.clients:
                del self.clients[client_socket]
    
    def send_message_to_user(self, username, message):
        """Envia mensagem para um usuário específico"""
        for client_socket, client_username in self.clients.items():
            if client_username == username:
                try:
                    client_socket.send(serialize_message(message).encode('utf-8'))
                    return True
                except:
                    # Remove conexão morta
                    if client_socket in self.clients:
                        del self.clients[client_socket]
                    return False
        return False
    
    def get_connected_users(self):
        """Retorna lista de usuários conectados"""
        return list(self.clients.values())
    
    def is_user_connected(self, username):
        """Verifica se um usuário está conectado"""
        return username in self.clients.values()
    
    def disconnect_user(self, username):
        """Desconecta um usuário específico"""
        to_remove = []
        for client_socket, client_username in self.clients.items():
            if client_username == username:
                try:
                    # Envia mensagem de desconexão
                    disconnect_msg = {
                        "type": "disconnect",
                        "message": "Desconectado pelo servidor"
                    }
                    client_socket.send(serialize_message(disconnect_msg).encode('utf-8'))
                    client_socket.close()
                except:
                    pass
                to_remove.append(client_socket)
        
        for client_socket in to_remove:
            if client_socket in self.clients:
                del self.clients[client_socket]
    
    def stop(self):
        """Para o servidor"""
        self.running = False
        
        # Desconecta todos os clientes
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        
        # Fecha servidor
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Servidor TCP parado")
    
    def get_server_status(self):
        """Retorna status do servidor"""
        return {
            "running": self.running,
            "port": self.user_state.socket_port if self.user_state else None,
            "connected_clients": len(self.clients),
            "clients": list(self.clients.values())
        }
