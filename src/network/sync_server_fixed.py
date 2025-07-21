"""
Servidor TCP para comunicação síncrona
Permite chat em tempo real entre usuários online e dentro do raio.
"""

import socket
import threading
import json
import time
from src.utils.utils import deserialize_message, serialize_message, format_timestamp

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
            except Exception as e:
                print(f"   ❌ Erro no loop do servidor: {e}")
                break
        
        print("   🛑 Loop do servidor encerrado")
    
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
                        self._handle_chat_message(message)
                        
                    elif message_type == "ping":
                        self._send_pong(client_socket)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Erro ao processar mensagem: {e}")
                    break
                    
        except Exception as e:
            print(f"Erro na conexão com {addr}: {e}")
        finally:
            if username and client_socket in self.clients:
                del self.clients[client_socket]
            client_socket.close()
            
    def _handle_handshake(self, client_socket, message):
        """Processa handshake inicial"""
        try:
            username = message.get("username")
            lat = message.get("latitude")
            lon = message.get("longitude")
            port = message.get("port")
            
            if not all([username, lat, lon, port]):
                response = {
                    "type": "handshake_response",
                    "status": "error",
                    "message": "Dados incompletos no handshake"
                }
                client_socket.send(serialize_message(response))
                return None
            
            # Verifica se o usuário está dentro do raio
            distance = self.user_state.calculate_distance(lat, lon)
            max_distance = self.user_state.max_distance
            
            if distance > max_distance:
                response = {
                    "type": "handshake_response", 
                    "status": "error",
                    "message": f"Usuário fora do raio ({distance:.1f}m > {max_distance}m)"
                }
                client_socket.send(serialize_message(response))
                return None
            
            # Handshake OK - adiciona cliente à lista
            self.clients[client_socket] = username
            
            response = {
                "type": "handshake_response",
                "status": "success", 
                "username": self.user_state.username,
                "latitude": self.user_state.latitude,
                "longitude": self.user_state.longitude,
                "port": self.user_state.socket_port
            }
            client_socket.send(serialize_message(response))
            
            print(f"Handshake concluído com {username} ({distance:.1f}m)")
            return username
            
        except Exception as e:
            print(f"Erro no handshake: {e}")
            return None
    
    def _handle_chat_message(self, message):
        """Processa mensagem de chat"""
        try:
            sender = message.get("sender")
            content = message.get("content")
            timestamp = message.get("timestamp")
            
            if self.gui:
                self.gui.after(0, lambda: self.gui.add_message(
                    f"[{format_timestamp(timestamp)}] {sender}: {content}"
                ))
                
        except Exception as e:
            print(f"Erro ao processar mensagem de chat: {e}")
    
    def _send_pong(self, client_socket):
        """Responde a ping com pong"""
        try:
            pong = {"type": "pong", "timestamp": time.time()}
            client_socket.send(serialize_message(pong))
        except Exception as e:
            print(f"Erro ao enviar pong: {e}")
    
    def broadcast_message(self, sender, content):
        """Envia mensagem para todos os clientes conectados"""
        if not self.clients:
            return
            
        message = {
            "type": "chat_message",
            "sender": sender,
            "content": content,
            "timestamp": time.time()
        }
        
        data = serialize_message(message)
        disconnected = []
        
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.send(data)
            except Exception as e:
                print(f"Erro ao enviar para cliente: {e}")
                disconnected.append(client_socket)
        
        # Remove clientes desconectados
        for client_socket in disconnected:
            if client_socket in self.clients:
                del self.clients[client_socket]
            try:
                client_socket.close()
            except:
                pass
    
    def stop(self):
        """Para o servidor"""
        print("Parando servidor TCP...")
        self.running = False
        
        # Fecha conexões dos clientes
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except:
                pass
        self.clients.clear()
        
        # Fecha socket do servidor
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Servidor TCP parado")
    
    def get_connected_users(self):
        """Retorna lista de usuários conectados"""
        return list(self.clients.values())
    
    def is_running(self):
        """Verifica se o servidor está rodando"""
        return self.running
