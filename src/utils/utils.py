"""
Funções utilitárias para o sistema de comunicação baseado em localização
"""

import math
import json
import time
from datetime import datetime

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcula a distância entre duas coordenadas geográficas usando a fórmula de Haversine
    Retorna a distância em metros
    """
    # Converter graus para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Raio da Terra em metros
    radius_earth = 6371000
    
    # Distância em metros
    distance = radius_earth * c
    return distance

def format_distance(distance_meters):
    """
    Formata a distância para exibição amigável
    """
    if distance_meters < 1000:
        return f"{distance_meters:.0f}m"
    else:
        return f"{distance_meters/1000:.1f}km"

def validate_coordinates(latitude, longitude):
    """
    Valida se as coordenadas estão dentro dos limites válidos
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False

def validate_status(status):
    """
    Valida se o status é válido
    """
    valid_statuses = ["online", "offline", "busy", "away"]
    return status in valid_statuses

def create_message(sender, recipient, content, message_type="direct"):
    """
    Cria uma mensagem estruturada
    """
    return {
        "sender": sender,
        "recipient": recipient,
        "content": content,
        "type": message_type,  # direct, broadcast, system
        "timestamp": datetime.now().isoformat(),
        "delivered": False
    }

def serialize_message(message):
    """
    Serializa uma mensagem para transmissão
    """
    try:
        return json.dumps(message)
    except Exception as e:
        print(f"Erro ao serializar mensagem: {e}")
        return None

def deserialize_message(message_str):
    """
    Deserializa uma mensagem recebida
    """
    try:
        return json.loads(message_str)
    except Exception as e:
        print(f"Erro ao deserializar mensagem: {e}")
        return None

def format_timestamp(timestamp_str):
    """
    Formata timestamp para exibição
    """
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%H:%M:%S")
    except:
        return time.strftime("%H:%M:%S")

def get_port_from_username(username, base_port=8000):
    """
    Gera uma porta única baseada no username
    """
    return base_port + (hash(username) % 1000)

def is_valid_radius(radius):
    """
    Valida se o raio está dentro dos limites aceitáveis
    """
    try:
        r = float(radius)
        return 100 <= r <= 50000  # Entre 100m e 50km
    except (ValueError, TypeError):
        return False

def get_queue_name(username):
    """
    Gera nome da fila RabbitMQ baseado no username
    """
    return f"user_{username.lower()}"

def save_contacts_to_file(contacts, filename):
    """
    Salva lista de contatos em arquivo
    """
    try:
        with open(filename, 'w') as f:
            json.dump(contacts, f, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar contatos: {e}")
        return False

def load_contacts_from_file(filename):
    """
    Carrega lista de contatos de arquivo
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Erro ao carregar contatos: {e}")
        return {}

def format_user_info(user_info):
    """
    Formata informações do usuário para exibição
    """
    return f"{user_info['username']} ({user_info['status']}) - {format_distance(0)}"

def log_message(message, log_file="chat.log"):
    """
    Registra mensagem em arquivo de log
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Erro ao registrar log: {e}")

def cleanup_temp_files(username):
    """
    Remove arquivos temporários do usuário
    """
    import os
    temp_files = [
        f"user_data_{username}.json",
        f"contacts_{username}.json"
    ]
    
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Erro ao remover {file}: {e}")

def get_local_ip():
    """
    Obtém o IP local da máquina
    """
    import socket
    try:
        # Conecta a um servidor externo para descobrir IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
