"""
Gerenciador de Estado do Usuário
Mantém informações sobre o usuário atual: nome, localização, status, raio e contatos.
"""

import json
import threading
import os
from utils.utils import calculate_distance

class UserState:
    def __init__(self, username, latitude, longitude, radius=1000):
        self.username = username
        self.latitude = latitude
        self.longitude = longitude
        self.radius = radius  # Raio em metros
        self.status = "online"  # online, offline, busy, away
        self.contacts = {}  # {username: {lat, lon, status, last_seen}}
        self.socket_port = 8000 + hash(username) % 1000  # Porta única baseada no username
        self.lock = threading.Lock()
        
        # Criar pasta users se não existir
        self.users_dir = "users"
        if not os.path.exists(self.users_dir):
            os.makedirs(self.users_dir)
        
        # Arquivo para persistir dados temporários na pasta users
        self.data_file = os.path.join(self.users_dir, f"user_data_{username}.json")
        self.load_data()
    
    def get_info(self):
        """Retorna informações básicas do usuário"""
        with self.lock:
            return {
                "username": self.username,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "radius": self.radius,
                "status": self.status,
                "port": self.socket_port
            }
    
    def update_location(self, latitude, longitude):
        """Atualiza localização do usuário"""
        with self.lock:
            self.latitude = latitude
            self.longitude = longitude
            self.save_data()
    
    def update_radius(self, radius):
        """Atualiza raio de comunicação"""
        with self.lock:
            self.radius = radius
            self.save_data()
    
    def set_status(self, status):
        """Define status do usuário"""
        valid_statuses = ["online", "offline", "busy", "away"]
        if status in valid_statuses:
            with self.lock:
                self.status = status
                self.save_data()
                return True
        return False
    
    def add_contact(self, username, latitude, longitude, status="online"):
        """Adiciona ou atualiza um contato"""
        with self.lock:
            self.contacts[username] = {
                "latitude": latitude,
                "longitude": longitude,
                "status": status,
                "last_seen": None
            }
            self.save_data()
    
    def remove_contact(self, username):
        """Remove um contato"""
        with self.lock:
            if username in self.contacts:
                del self.contacts[username]
                self.save_data()
                return True
        return False
    
    def get_contacts_in_range(self):
        """Retorna contatos dentro do raio de comunicação"""
        contacts_in_range = {}
        with self.lock:
            for username, contact_info in self.contacts.items():
                distance = calculate_distance(
                    self.latitude, self.longitude,
                    contact_info["latitude"], contact_info["longitude"]
                )
                if distance <= self.radius:
                    contacts_in_range[username] = {
                        **contact_info,
                        "distance": distance
                    }
        return contacts_in_range
    
    def is_contact_in_range(self, username):
        """Verifica se um contato específico está no raio"""
        with self.lock:
            if username not in self.contacts:
                return False
            
            contact = self.contacts[username]
            distance = calculate_distance(
                self.latitude, self.longitude,
                contact["latitude"], contact["longitude"]
            )
            return distance <= self.radius
    
    def get_contact_distance(self, username):
        """Retorna a distância até um contato específico"""
        with self.lock:
            if username not in self.contacts:
                return None
            
            contact = self.contacts[username]
            return calculate_distance(
                self.latitude, self.longitude,
                contact["latitude"], contact["longitude"]
            )
    
    def save_data(self):
        """Salva dados em arquivo JSON"""
        try:
            data = {
                "username": self.username,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "radius": self.radius,
                "status": self.status,
                "contacts": self.contacts,
                "socket_port": self.socket_port
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
    
    def load_data(self):
        """Carrega dados do arquivo JSON"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                # Carrega apenas contatos e configurações, mantém dados atuais
                self.contacts = data.get("contacts", {})
        except FileNotFoundError:
            # Arquivo não existe, usar valores padrão
            pass
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    def cleanup(self):
        """Limpa recursos e arquivos temporários"""
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
        except Exception as e:
            print(f"Erro ao limpar dados: {e}")
    
    @staticmethod
    def cleanup_all_users():
        """Limpa todos os arquivos de usuários"""
        try:
            users_dir = "users"
            if os.path.exists(users_dir):
                for filename in os.listdir(users_dir):
                    if filename.startswith("user_data_") and filename.endswith(".json"):
                        file_path = os.path.join(users_dir, filename)
                        os.remove(file_path)
                        print(f"Removido: {filename}")
                print("Todos os arquivos de usuários foram removidos!")
            else:
                print("Pasta users não encontrada.")
        except Exception as e:
            print(f"Erro ao limpar todos os usuários: {e}")
    
    @staticmethod
    def list_all_users():
        """Lista todos os usuários salvos"""
        try:
            users_dir = "users"
            if os.path.exists(users_dir):
                users = []
                for filename in os.listdir(users_dir):
                    if filename.startswith("user_data_") and filename.endswith(".json"):
                        username = filename.replace("user_data_", "").replace(".json", "")
                        users.append(username)
                return users
            return []
        except Exception as e:
            print(f"Erro ao listar usuários: {e}")
            return []
