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
        self.button_send_chat.grid(row=2, column=0, padx=(10,2), pady=(0,5), sticky="e")

        self.button_resign = tk.Button(master, text="Desistir", command=self.resign)
        self.button_resign.grid(row=2, column=1, padx=(2,10), pady=(0,5), sticky="w")

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

        # Exibe quem começa e de quem é a vez
        if "Jogo iniciado!" in msg:
            self.chat_area.insert(tk.END, f"🎲 {msg.strip()}\n")  # Exibe mensagem de início
        elif "Seu adversário jogou" in msg:
            self.chat_area.insert(tk.END, "🎯 Sua vez!\n")
        elif "Aguarde seu turno" in msg:
            self.chat_area.insert(tk.END, "⏳ Aguardando adversário...\n")

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
            try:
                # Sempre envia no formato correto "chat mensagem"
                self.socket.send(f"chat {msg}".encode())
                self.entry_chat.delete(0, tk.END)
            except Exception as e:
                self.display_message(f"Erro ao enviar mensagem: {e}")

    def receive_messages(self):
        while True:
            try:
                msg = self.socket.recv(2048).decode()
                if not msg:
                    break

                linhas = msg.split('\n')
                for linha in linhas:
                    linha = linha.strip()
                    if not linha:
                        continue

                    # Exibe a mensagem indicando o jogador
                    if linha.startswith("Você é o jogador"):
                        self.display_message(f"🎮 {linha}")
                    elif linha.startswith("Jogo iniciado!"):
                        self.display_message(f"🎲 {linha}")
                    elif linha.startswith("Seu adversário jogou"):
                        self.display_message("🎯 Sua vez!")  # Exibe mensagem de "Sua vez!"
                    elif linha.startswith("🎯 Seu adversário jogou. Sua vez!"):  # Ajuste para capturar a mensagem exata
                        self.display_message("🎯 Sua vez!")  # Exibe mensagem de "Sua vez!"
                    elif "Aguarde seu turno" in linha:
                        self.display_message("⏳ Aguardando adversário...")
                    elif "desistiu" in linha:
                        if "Você" in linha:
                            self.display_message("🚪 Você saiu.")
                        else:
                            self.display_message("🚪 Jogador adversário saiu. Você venceu!!")
                    elif "Fim do jogo" in linha or "venceu" in linha:
                        self.display_message(f"🏁 {linha}")
                    elif linha.startswith("[Chat]"):
                        self.display_message(f"💬 {linha}")
                    elif (linha.startswith("Peça colocada") or
                          linha.startswith("Movimento realizado") or
                          "Movimento deve ser para uma casa adjacente" in linha or
                          "Casa já ocupada" in linha or
                          "Destino inválido" in linha or
                          "Você só pode mover suas próprias peças" in linha or
                          "Posição inválida" in linha or
                          "Ainda estamos na fase de colocação." in linha):
                        self.display_message(f"🎮 {linha}")
                    else:
                        # Ignorar tudo que for tabuleiro e outras mensagens
                        pass

                # Atualiza o tabuleiro visual separadamente
                if "Tabuleiro atual:" in msg:
                    self.update_board(msg)

                # Detecta mudança de fase
                if "Fase de movimentação iniciada" in msg:
                    self.phase = 'movement'

            except Exception as e:
                self.display_message(f"⚠️ Erro de conexão: {e}")
                break
            
    def resign(self):
        try:
            self.socket.send("exit".encode())
            self.display_message("Você desistiu da partida.")
            self.master.quit()
        except Exception as e:
            self.display_message(f"Erro ao desistir: {e}")

def main():
    root = tk.Tk()
    client = SeegaClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
