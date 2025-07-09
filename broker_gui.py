import tkinter as tk
from tkinter import simpledialog, messagebox
import pika
import requests
from requests.auth import HTTPBasicAuth

class BrokerAdmin:
    def __init__(self, master):
        self.master = master
        master.title("Broker MOM - Administrador")
        master.geometry("400x500")

        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar ao RabbitMQ:\n{e}")
            master.destroy()
            return

        tk.Label(master, text="Administrador MOM", font=("Arial", 14)).pack(pady=10)
        tk.Button(master, text="➕ Criar Tópico", command=self.criar_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="➖ Remover Tópico", command=self.remover_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🧑‍💻 Cadastrar Usuário", command=self.criar_usuario).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🗑️ Remover Fila", command=self.remover_fila).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📦 Ver Filas Existentes", command=self.ver_filas).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📑 Ver Tópicos Existentes", command=self.ver_topicos).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="❌ Sair", command=self.sair).pack(fill='x', padx=20, pady=20)
    def ver_topicos(self):
        try:
            resp = requests.get("http://localhost:15672/api/exchanges", auth=HTTPBasicAuth('guest', 'guest'))
            exchanges = resp.json()
            # Filtra exchanges "padrão" do RabbitMQ
            exchanges_user = [ex for ex in exchanges if ex['name'] not in ('', 'amq.direct', 'amq.fanout', 'amq.headers', 'amq.match', 'amq.rabbitmq.trace', 'amq.topic')]
            if not exchanges_user:
                messagebox.showinfo("Tópicos", "Nenhum tópico encontrado.")
                return
            texto = ""
            for ex in exchanges_user:
                nome = ex['name']
                tipo = ex['type']
                texto += f"{nome} (tipo: {tipo})\n"
            messagebox.showinfo("Tópicos Existentes", texto)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao consultar tópicos: {e}")

    def criar_topico(self):
        topico = simpledialog.askstring("Criar Tópico", "Nome do tópico:")
        criador = simpledialog.askstring("Usuário Criador", "Nome do criador do tópico:")
        if not topico or not criador:
            return
        try:
            self.channel.exchange_declare(exchange=topico, exchange_type='fanout')
            fila_criador = f"user_{criador}"
            self.channel.queue_declare(queue=fila_criador)
            self.channel.queue_bind(exchange=topico, queue=fila_criador)
            messagebox.showinfo("Sucesso", f"Tópico '{topico}' criado e {criador} assinado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar tópico: {e}")

    def remover_topico(self):
        topico = simpledialog.askstring("Remover Tópico", "Nome do tópico:")
        if not topico:
            return
        try:
            self.channel.exchange_delete(exchange=topico)
            messagebox.showinfo("Removido", f"Tópico '{topico}' removido.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao remover tópico: {e}")

    def criar_usuario(self):
        nome = simpledialog.askstring("Criar Usuário", "Nome do usuário:")
        if nome:
            fila_usuario = f"user_{nome}"
            try:
                self.channel.queue_declare(queue=fila_usuario)
                messagebox.showinfo("Usuário Criado", f"Usuário '{nome}' cadastrado com fila '{fila_usuario}'.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar usuário: {e}")

    def remover_fila(self):
        nome = simpledialog.askstring("Remover Fila", "Nome do usuário:")
        if nome:
            fila = f"user_{nome}"
            try:
                self.channel.queue_delete(queue=fila)
                messagebox.showinfo("Removido", f"Fila '{fila}' removida.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao remover fila: {e}")

    def ver_filas(self):
        try:
            resp = requests.get("http://localhost:15672/api/queues", auth=HTTPBasicAuth('guest', 'guest'))
            filas = resp.json()
            if not filas:
                messagebox.showinfo("Filas", "Nenhuma fila encontrada.")
                return
            texto = ""
            for fila in filas:
                nome = fila['name']
                msgs = fila['messages']
                texto += f"{nome}: {msgs} mensagens\n"
            messagebox.showinfo("Filas Existentes", texto)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao consultar filas: {e}")

    def sair(self):
        self.connection.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BrokerAdmin(root)
    root.mainloop()
