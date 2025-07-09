import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import pika

class UserClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Cliente MOM - Usuário")
        self.master.geometry("500x500")

        self.username = simpledialog.askstring("Login", "Digite seu nome de usuário:")
        if not self.username:
            messagebox.showerror("Erro", "Nome de usuário obrigatório.")
            master.destroy()
            return

        self.user_queue = f"user_{self.username}"
        self.messages = []

        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.user_queue)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao conectar ao RabbitMQ:\n{e}")
            master.destroy()
            return

        tk.Label(master, text=f"Usuário: {self.username}", font=("Arial", 14)).pack(pady=10)
        tk.Button(master, text="✉️ Enviar para Usuário", command=self.enviar_para_usuario).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📢 Enviar para Tópico", command=self.enviar_para_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="🔔 Assinar Tópico", command=self.assinar_topico).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="📥 Consultar Mensagens Diretas", command=self.consultar_mensagens_diretas).pack(fill='x', padx=20, pady=5)
        tk.Button(master, text="❌ Sair", command=self.sair).pack(fill='x', padx=20, pady=20)

        self.texto_mensagens = tk.Text(master, height=10, state="disabled")
        self.texto_mensagens.pack(fill='both', padx=10, pady=5)

        self.consuming = True
        self.topico_threads = []
    def consultar_mensagens_diretas(self):
        try:
            msgs = []
            while True:
                method_frame, header_frame, body = self.channel.basic_get(queue=self.user_queue, auto_ack=True)
                if method_frame:
                    msg = body.decode()
                    msgs.append(msg)
                else:
                    break
            if msgs:
                for msg in msgs:
                    self.mostrar_mensagem(f"[DIRETA] {msg}")
            else:
                messagebox.showinfo("Mensagens Diretas", "Nenhuma mensagem direta nova.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao consultar mensagens diretas: {e}")

    def mostrar_mensagem(self, msg):
        self.messages.append(msg)
        self.texto_mensagens.configure(state="normal")
        self.texto_mensagens.insert("end", msg + "\n")
        self.texto_mensagens.configure(state="disabled")
        self.texto_mensagens.see("end")

    def enviar_para_usuario(self):
        destino = simpledialog.askstring("Enviar", "Destinatário:")
        mensagem = simpledialog.askstring("Mensagem", "Digite a mensagem:")
        if destino and mensagem:
            fila_destino = f"user_{destino}"
            try:
                # Verifica se a fila do destinatário existe
                self.channel.queue_declare(queue=fila_destino, passive=True)
            except pika.exceptions.ChannelClosedByBroker:
                messagebox.showerror("Erro", f"O usuário '{destino}' não está cadastrado.")
                self.channel = self.connection.channel()  # Reabre canal se fechar
                return
            try:
                self.channel.basic_publish(exchange='', routing_key=fila_destino, body=f"[{self.username}] {mensagem}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao enviar: {e}")

    def enviar_para_topico(self):
        topico = simpledialog.askstring("Tópico", "Nome do tópico:")
        mensagem = simpledialog.askstring("Mensagem", "Digite a mensagem:")
        if not topico or not mensagem:
            return
        try:
            self.channel.exchange_declare(exchange=topico, passive=True)
        except pika.exceptions.ChannelClosedByBroker:
            messagebox.showerror("Erro", f"O tópico '{topico}' não existe.")
            self.channel = self.connection.channel()
            return
        self.channel.basic_publish(exchange=topico, routing_key='', body=f"[{self.username}] {mensagem}")

    def assinar_topico(self):
        topico = simpledialog.askstring("Assinar Tópico", "Nome do tópico:")
        if not topico:
            return
        try:
            conn_topico = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            canal_topico = conn_topico.channel()
            try:
                canal_topico.exchange_declare(exchange=topico, passive=True)
            except pika.exceptions.ChannelClosedByBroker:
                messagebox.showerror("Erro", f"O tópico '{topico}' não existe.")
                conn_topico.close()
                return
            result = canal_topico.queue_declare(queue='', exclusive=True)
            temp_queue = result.method.queue
            canal_topico.queue_bind(exchange=topico, queue=temp_queue)

            def consumidor_topico():
                def callback(ch, method, properties, body):
                    msg = f"[TOPICO:{topico}] {body.decode()}"
                    self.master.after(0, self.mostrar_mensagem, msg)

                canal_topico.basic_consume(queue=temp_queue, on_message_callback=callback, auto_ack=True)
                while self.consuming:
                    try:
                        conn_topico.process_data_events(time_limit=1)
                    except:
                        break

            t = threading.Thread(target=consumidor_topico, daemon=True)
            t.start()
            self.topico_threads.append(t)
            messagebox.showinfo("Assinado", f"Agora você assina o tópico '{topico}'.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao assinar tópico: {e}")

    # Removido consumo automático da fila do usuário

    def sair(self):
        self.consuming = False
        self.connection.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UserClient(root)
    root.mainloop()
