import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import pika

class UserClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Cliente MOM - Usuário")
        self.master.geometry("400x400")

        # Nome do usuário
        self.username = simpledialog.askstring("Login", "Digite seu nome de usuário:")
        if not self.username:
            messagebox.showerror("Erro", "Nome de usuário obrigatório.")
            master.destroy()
            return

        self.user_queue = f"user_{self.username}"
        self.messages = []

        # Conectar ao RabbitMQ
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.user_queue)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao conectar ao RabbitMQ:\n{e}")
            master.destroy()
            return

        # Interface
        tk.Label(master, text=f"Usuário: {self.username}", font=("Arial", 14)).pack(pady=10)

        tk.Button(master, text="✉️ Enviar para Usuário", command=self.enviar_para_usuario).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📢 Enviar para Tópico", command=self.enviar_para_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🔔 Assinar Tópico", command=self.assinar_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🗒️ Ver Últimas Mensagens", command=self.ver_mensagens).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="❌ Sair", command=self.sair).pack(fill='x', padx=20, pady=20)

        # Inicializar consumidores
        self.consuming = True
        threading.Thread(target=self.consome_fila_usuario, daemon=True).start()

        # Guardar filas temporárias para tópicos
        self.topico_threads = []

    def enviar_para_usuario(self):
        destino = simpledialog.askstring("Enviar", "Destinatário:")
        mensagem = simpledialog.askstring("Mensagem", "Digite a mensagem:")
        if destino and mensagem:
            fila_destino = f"user_{destino}"
            try:
                self.channel.basic_publish(exchange='', routing_key=fila_destino, body=f"[{self.username}] {mensagem}")
                messagebox.showinfo("Enviado", f"Mensagem enviada para {destino}.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao enviar: {e}")

    def enviar_para_topico(self):
        topico = simpledialog.askstring("Tópico", "Nome do tópico:")
        mensagem = simpledialog.askstring("Mensagem", "Digite a mensagem:")
        if topico and mensagem:
            try:
                # self.channel.exchange_declare(exchange=topico, exchange_type='fanout')
                self.channel.basic_publish(exchange=topico, routing_key='', body=f"[{self.username}] {mensagem}")
                messagebox.showinfo("Enviado", f"Mensagem publicada no tópico '{topico}'.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao publicar no tópico (será que ele existe?): {e}")

    def assinar_topico(self):
        topico = simpledialog.askstring("Assinar Tópico", "Nome do tópico:")
        if not topico:
            return
        try:
            # Criar conexão e canal separados para esse tópico
            conn_topico = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            canal_topico = conn_topico.channel()

            canal_topico.exchange_declare(exchange=topico, exchange_type='fanout')
            result = canal_topico.queue_declare(queue='', exclusive=True)
            temp_queue = result.method.queue
            canal_topico.queue_bind(exchange=topico, queue=temp_queue)

            def consumidor_topico():
                def callback(ch, method, properties, body):
                    self.messages.append(f"[TOPICO:{topico}] {body.decode()}")
                    print(f"[TOPICO:{topico}] {body.decode()}")

                canal_topico.basic_consume(queue=temp_queue, on_message_callback=callback, auto_ack=True)
                while self.consuming:
                    try:
                        conn_topico.process_data_events(time_limit=1)
                    except Exception:
                        break

            t = threading.Thread(target=consumidor_topico, daemon=True)
            t.start()
            self.topico_threads.append(t)
            messagebox.showinfo("Assinado", f"Agora você assina o tópico '{topico}'.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao assinar tópico: {e}")

    def consome_fila_usuario(self):
        def callback(ch, method, properties, body):
            self.messages.append(body.decode())
            print(f"[DIRETA] {body.decode()}")

        try:
            self.channel.basic_consume(queue=self.user_queue, on_message_callback=callback, auto_ack=True)
            while self.consuming:
                self.connection.process_data_events(time_limit=1)
        except Exception as e:
            print("Erro ao consumir fila de usuário:", e)

    def ver_mensagens(self):
        if not self.messages:
            messagebox.showinfo("Mensagens", "Nenhuma mensagem recebida.")
        else:
            texto = "\n".join(self.messages[-10:])
            messagebox.showinfo("Mensagens", texto)

    def sair(self):
        self.consuming = False
        self.connection.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UserClient(root)
    root.mainloop()
