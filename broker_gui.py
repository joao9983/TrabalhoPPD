import tkinter as tk
from tkinter import simpledialog, messagebox
import pika

class BrokerAdmin:
    def __init__(self, master):
        self.master = master
        master.title("Broker MOM - Administrador")
        master.geometry("400x400")

        # Conexão com RabbitMQ
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar ao RabbitMQ:\n{e}")
            master.destroy()
            return

        # Widgets
        tk.Label(master, text="Administrador MOM", font=("Arial", 14)).pack(pady=10)

        tk.Button(master, text="➕ Criar Tópico", command=self.criar_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🧑‍💻 Cadastrar Usuário", command=self.criar_usuario).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📦 Ver Filas Existentes", command=self.ver_filas).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="❌ Sair", command=self.sair).pack(fill='x', padx=20, pady=20)

    def criar_topico(self):
        topico = simpledialog.askstring("Criar Tópico", "Nome do tópico:")
        criador = simpledialog.askstring("Usuário Criador", "Nome do criador do tópico:")
        if not topico or not criador:
            return
        try:
            # Criar exchange tipo fanout
            self.channel.exchange_declare(exchange=topico, exchange_type='fanout')
            # Criar fila do criador (caso não exista)
            fila_criador = f"user_{criador}"
            self.channel.queue_declare(queue=fila_criador)
            # Assinar automaticamente o criador ao tópico
            self.channel.queue_bind(exchange=topico, queue=fila_criador)
            messagebox.showinfo("Sucesso", f"Tópico '{topico}' criado e {criador} assinado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar tópico: {e}")

    def criar_usuario(self):
        nome = simpledialog.askstring("Criar Usuário", "Nome do usuário:")
        if nome:
            fila_usuario = f"user_{nome}"
            try:
                self.channel.queue_declare(queue=fila_usuario)
                messagebox.showinfo("Usuário Criado", f"Usuário '{nome}' cadastrado com fila '{fila_usuario}'.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar usuário: {e}")

    def ver_filas(self):
        try:
            # Consulta HTTP ao RabbitMQ management (requer autenticação e habilitar API)
            messagebox.showinfo("Info", "Visualize as filas no painel: http://localhost:15672 → aba 'Queues'")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar filas: {e}")

    def sair(self):
        self.connection.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BrokerAdmin(root)
    root.mainloop()
