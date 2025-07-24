"""
Sistema de Comunicação baseado em Localização
Versão Reorganizada - Estrutura de Projeto Profissional

Arquivo principal que inicializa a interface e coordena os componentes do sistema.
"""

import tkinter as tk
import threading
import signal
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv('config/.env')

# Adiciona o diretório src ao path para imports
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Imports do sistema
from src.gui.gui import ChatGUI
from src.core.user_state import UserState
from src.core.contacts_manager import ContactsManager
from src.network.sync_server import SyncServer
from src.messaging.async_consumer import AsyncConsumer
import pika

class MainApp:
    def __init__(self):
        self.root = None
        self.gui = None
        self.user_state = None
        self.contacts_manager = None
        self.sync_server = None
        self.async_consumer = None
        self.running = False
        
    def test_rabbitmq_connection(self):
        """Testa conexão com RabbitMQ antes de inicializar"""
        try:
            host = os.getenv('RABBITMQ_HOST', 'localhost')
            username = os.getenv('RABBITMQ_USER', 'admin')
            password = os.getenv('RABBITMQ_PASS', 'admin123')
            
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(host=host, credentials=credentials)
            
            connection = pika.BlockingConnection(parameters)
            connection.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar com RabbitMQ: {e}")
            print("💡 Certifique-se de que o RabbitMQ está rodando:")
            print("   - Windows: .\\scripts\\docker-setup.ps1 start")
            print("   - Linux/Mac: ./scripts/docker-setup.sh start")
            return False
    
    def initialize_components(self, username, latitude, longitude, radius):
        """Inicializa todos os componentes do sistema com delay entre componentes"""
        try:
            # Inicializa estado do usuário
            self.user_state = UserState(username, latitude, longitude, radius)
            
            # Pequeno delay para estabilizar
            import time
            time.sleep(0.5)
            
            # Inicializa gerenciador de contatos
            self.contacts_manager = ContactsManager(self.user_state)
            time.sleep(0.5)
            
            # Inicializa servidor de comunicação síncrona
            self.sync_server = SyncServer(self.user_state, self.gui)
            
            # Conecta componentes
            self.gui.set_components(
                self.user_state, 
                self.contacts_manager, 
                self.sync_server, 
                None  # async_consumer será definido depois
            )
            
            # Inicia discovery de contatos primeiro (menos crítico)
            print("🔄 Iniciando discovery de contatos...")
            self.contacts_manager.start_discovery()
            time.sleep(1)  # Delay maior para permitir conexões se estabilizarem
            
            # Inicia servidor TCP
            print("🔄 Iniciando servidor TCP...")
            self.sync_server.start()
            time.sleep(0.5)
            
            # Inicializa e inicia consumidor assíncrono por último
            print("🔄 Iniciando consumidor assíncrono...")
            self.async_consumer = AsyncConsumer(username, self.gui)
            
            # Atualiza referência no GUI
            self.gui.async_consumer = self.async_consumer
            
            if not self.async_consumer.start():
                print("⚠️ Falha ao iniciar consumidor, continuando sem ele...")
            
            self.running = True
            print(f"✅ Sistema iniciado para usuário: {username}")
            print(f"📍 Localização: {latitude}, {longitude}")
            print(f"📡 Raio de comunicação: {radius}m")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inicializar componentes: {e}")
            self.cleanup()
            raise
    
    def cleanup(self):
        """Limpa recursos antes de fechar"""
        if not self.running:
            return
            
        try:
            print("🧹 Limpando recursos...")
            
            if self.async_consumer:
                self.async_consumer.stop()
            
            if self.sync_server:
                self.sync_server.stop()
                
            if self.contacts_manager:
                self.contacts_manager.stop()
                
            self.running = False
            print("✅ Recursos limpos com sucesso")
            
        except Exception as e:
            print(f"⚠️ Erro na limpeza: {e}")
    
    def signal_handler(self, signum, frame):
        """Handler para sinais do sistema (Ctrl+C)"""
        print("\\n🛑 Recebido sinal de interrupção...")
        self.cleanup()
        if self.root:
            self.root.quit()
        sys.exit(0)
    
    def run(self):
        """Execução principal da aplicação"""
        print("🚀 Iniciando Sistema de Chat por Localização")
        print("=" * 50)
        
        # Testa conexão com RabbitMQ
        if not self.test_rabbitmq_connection():
            return False
        
        # Configura handlers para sinais
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Inicializa interface
            self.root = tk.Tk()
            self.gui = ChatGUI(self.root, self.initialize_components)
            
            # Configura fechamento da janela
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            print("🖥️ Interface gráfica iniciada")
            print("📝 Configure seus dados e comece a usar!")
            
            # Executa loop principal
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("\\n🛑 Interrompido pelo usuário")
        except Exception as e:
            print(f"❌ Erro crítico: {e}")
        finally:
            self.cleanup()
        
        return True
    
    def on_closing(self):
        """Callback para fechamento da janela"""
        self.cleanup()
        self.root.destroy()

def main():
    """Função principal"""
    app = MainApp()
    success = app.run()
    
    if success:
        print("\\n👋 Sistema finalizado com sucesso!")
    else:
        print("\\n❌ Sistema não pôde ser iniciado.")
        sys.exit(1)

if __name__ == "__main__":
    main()
