"""
Script para limpar e configurar usuários para testes
Instituto Federal do Ceará - Programação Paralela e Distribuída
"""

import sys
import os
import subprocess
import json

# Adicionar o diretório src ao path
sys.path.append('src')

from core.user_state import UserState

def clear_rabbitmq_queues():
    """Limpa todas as filas do RabbitMQ"""
    try:
        print("🧹 Limpando filas do RabbitMQ...")
        
        # Listar filas
        result = subprocess.run([
            'docker', 'exec', 'location_chat_rabbitmq', 
            'rabbitmqctl', 'list_queues'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[2:]:  # Pular cabeçalhos
                if line.strip():
                    queue_name = line.split()[0]
                    if queue_name.startswith('user_'):
                        print(f"  Limpando fila: {queue_name}")
                        subprocess.run([
                            'docker', 'exec', 'location_chat_rabbitmq',
                            'rabbitmqctl', 'purge_queue', queue_name
                        ], capture_output=True)
        
        print("✅ Filas do RabbitMQ limpas!")
        
    except Exception as e:
        print(f"❌ Erro ao limpar RabbitMQ: {e}")

def clear_user_files():
    """Limpa todos os arquivos de usuários"""
    try:
        print("🧹 Limpando arquivos de usuários...")
        UserState.cleanup_all_users()
        print("✅ Arquivos de usuários limpos!")
    except Exception as e:
        print(f"❌ Erro ao limpar arquivos: {e}")

def create_test_users():
    """Cria os 5 usuários base para testes"""
    print("👥 Criando usuários base para testes...")
    
    test_users = [
        {
            "name": "João",
            "latitude": -3.7327,
            "longitude": -38.5267,
            "status": "online",
            "radius": 1000
        },
        {
            "name": "Maria",
            "latitude": -3.7400,
            "longitude": -38.5300,
            "status": "online",
            "radius": 1000
        },
        {
            "name": "Pedro",
            "latitude": -3.7500,
            "longitude": -38.5400,
            "status": "offline",
            "radius": 500
        },
        {
            "name": "Ana",
            "latitude": -3.7200,
            "longitude": -38.5100,
            "status": "online",
            "radius": 2000
        },
        {
            "name": "Carlos",
            "latitude": -3.7327,
            "longitude": -38.5267,
            "status": "offline",
            "radius": 1500
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        try:
            user = UserState(
                username=user_data["name"],
                latitude=user_data["latitude"],
                longitude=user_data["longitude"],
                radius=user_data["radius"]
            )
            user.set_status(user_data["status"])
            user.save_data()
            
            created_users.append({
                "name": user_data["name"],
                "location": f"({user_data['latitude']}, {user_data['longitude']})",
                "status": user_data["status"],
                "radius": f"{user_data['radius']}m"
            })
            
            print(f"  ✅ {user_data['name']} criado - {user_data['status']} - {user_data['radius']}m")
            
        except Exception as e:
            print(f"  ❌ Erro ao criar {user_data['name']}: {e}")
    
    print(f"\n✅ {len(created_users)} usuários criados com sucesso!")
    return created_users

def show_status():
    """Mostra o status atual do sistema"""
    print("\n📊 STATUS DO SISTEMA:")
    print("=" * 50)
    
    # Verificar RabbitMQ
    try:
        result = subprocess.run([
            'docker', 'ps', '--filter', 'name=location_chat_rabbitmq', '--format', 'table {{.Status}}'
        ], capture_output=True, text=True)
        
        if 'Up' in result.stdout:
            print("🟢 RabbitMQ: RODANDO")
        else:
            print("🔴 RabbitMQ: PARADO")
    except:
        print("🔴 RabbitMQ: ERRO")
    
    # Verificar usuários
    users = UserState.list_all_users()
    print(f"👥 Usuários criados: {len(users)}")
    for user in users:
        print(f"  - {user}")
    
    # Verificar filas
    try:
        result = subprocess.run([
            'docker', 'exec', 'location_chat_rabbitmq', 
            'rabbitmqctl', 'list_queues'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            queue_count = len([line for line in lines[2:] if line.strip() and line.split()[0].startswith('user_')])
            print(f"📬 Filas RabbitMQ: {queue_count}")
    except:
        print("📬 Filas RabbitMQ: ERRO")

def main():
    print("🚀 CONFIGURADOR DE TESTES - SISTEMA DE COMUNICAÇÃO")
    print("=" * 60)
    
    while True:
        print("\nOpções:")
        print("1. Limpar TUDO (RabbitMQ + Arquivos)")
        print("2. Criar usuários base para testes")
        print("3. Mostrar status do sistema")
        print("4. Limpar apenas arquivos de usuários")
        print("5. Limpar apenas filas RabbitMQ")
        print("0. Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == "1":
            print("\n🧹 LIMPEZA COMPLETA")
            clear_rabbitmq_queues()
            clear_user_files()
            print("✅ Limpeza completa realizada!")
            
        elif choice == "2":
            print("\n👥 CRIANDO USUÁRIOS BASE")
            create_test_users()
            
        elif choice == "3":
            show_status()
            
        elif choice == "4":
            clear_user_files()
            
        elif choice == "5":
            clear_rabbitmq_queues()
            
        elif choice == "0":
            print("👋 Saindo...")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    main()
