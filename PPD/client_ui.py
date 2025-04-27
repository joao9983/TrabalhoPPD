import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

class SeegaClient:
    def __init__(self, master):
        self.master = master
        master.title("Seega - Cliente")

        self.board_frame = tk.Frame(master)
        self.board_frame.grid(row=0, column=0, padx=10, pady=10)

        self.chat_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=40, height=10, state="disabled")
        self.chat_area.grid(row=1, column=0, padx=10, pady=10)

        self.entry_chat = tk.Entry(master, width=30)
        self.entry_chat.grid(row=2, column=0, padx=10, pady=(0,5), sticky="w")

        self.button_send_chat = tk.Button(master, text="Enviar Chat", command=self.send_chat)
        self.button_send_chat.grid(row=2, column=0, padx=10, pady=(0,5), sticky="e")

        self.buttons = []
        for y in range(5):
            row = []
            for x in range(5):
                btn = tk.Button(self.board_frame, text=" ", width=4, height=2,
                                command=lambda x=x, y=y: self.handle_click(x, y))
                btn.grid(row=y, column=x)
                row.append(btn)
            self.buttons.append(row)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = 'localhost'
        self.port = 5555

        self.selected = None  # Armazena peça selecionada para mover
        self.phase = 'placement'  # Começa na fase de colocação

        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            self.display_message(f"Erro ao conectar no servidor: {e}")
            return

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def display_message(self, msg):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, msg + "\n")
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

        # Atualiza tabuleiro se vier nova configuração
        if "Tabuleiro atual:" in msg:
            self.update_board(msg)

        # Detecta mudança de fase
        if "Fase de movimentação iniciada" in msg:
            self.phase = 'movement'

    def update_board(self, msg):
        linhas = msg.split("\n")
        tab = []
        start = False
        for linha in linhas:
            if start:
                if linha.strip() == "":
                    break
                tab.append(linha.split())
            if "Tabuleiro atual:" in linha:
                start = True
        if tab:
            for y in range(5):
                for x in range(5):
                    text = tab[y][x]
                    if text == '.':
                        text = " "
                    self.buttons[y][x].config(text=text)

    def handle_click(self, x, y):
        if self.phase == 'placement':
            self.send_command(f"place {x} {y}")
        elif self.phase == 'movement':
            if self.selected:
                from_x, from_y = self.selected
                self.send_command(f"move {from_x} {from_y} {x} {y}")
                self.selected = None
            else:
                self.selected = (x, y)

    def send_command(self, cmd):
        try:
            self.socket.send(cmd.encode())
        except Exception as e:
            self.display_message(f"Erro ao enviar comando: {e}")

    def send_chat(self):
        msg = self.entry_chat.get().strip()
        if msg:
            self.send_command(f"chat {msg}")
            self.entry_chat.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                msg = self.socket.recv(2048).decode()
                if not msg:
                    break
                self.display_message(msg)
            except:
                self.display_message("Conexão encerrada pelo servidor.")
                break

def main():
    root = tk.Tk()
    client = SeegaClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
