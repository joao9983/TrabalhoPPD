import xmlrpc.client
import tkinter as tk
from tkinter import scrolledtext
import tkinter.simpledialog
import threading
import time

class SeegaClient:
    def __init__(self, master):
        self.master = master
        master.title("Seega - Cliente")

        self.server_url = tk.simpledialog.askstring("Endereço do Servidor", "Digite o endereço do servidor (ex: http://localhost:8000):", initialvalue="http://localhost:8000")
        if not self.server_url:
            self.display_message("Nenhum endereço informado.")
            return

        self.server = xmlrpc.client.ServerProxy(self.server_url, allow_none=True)
        self.player_id, self.symbol = self.server.join_game()
        if self.player_id == -1:
            self.display_message("Jogo já está cheio!")
            return

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

        self.selected = None
        self.phase = 'placement'
        self.running = True
        self.turn = self.symbol == 'X'  # X sempre começa
        self.display_message(f"Você é o jogador {self.symbol}.")
        if self.symbol == 'X':
            self.display_message("Você começa a partida!")
        else:
            self.display_message("Aguarde o jogador X começar.")
        self.last_turn_state = None  # Para evitar spam de 'Sua vez!'
        self.awaiting_server = False  # Para bloquear interface após jogada
        self.polling_lock = threading.Lock()
        threading.Thread(target=self.poll_server, daemon=True).start()

    def display_message(self, msg):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, msg + "\n")
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def update_board(self, board_str):
        linhas = board_str.strip().split("\n")
        for y in range(5):
            for x in range(5):
                text = linhas[y].split()[x]
                if text == '.':
                    text = " "
                self.buttons[y][x].config(text=text)

    def handle_click(self, x, y):
        # Primeiro, verifica se é o turno do jogador
        try:
            with self.polling_lock:
                state = self.server.get_game_state(self.player_id)
        except Exception as e:
            self.display_message(f"Erro de conexão: {e}")
            return
        if state['current_player'] != self.symbol:
            self.display_message("Aguarde seu turno!")
            return
        # Depois, verifica se está aguardando resposta do servidor
        if self.awaiting_server:
            self.display_message("Aguarde o servidor responder sua última jogada.")
            return
        self.awaiting_server = True
        try:
            with self.polling_lock:
                if self.phase == 'placement':
                    success, resp = self.server.place_piece(self.player_id, x, y)
                    self.display_message(resp)
                    state = self.server.get_game_state(self.player_id)
                    self.update_board(state['board'])
                elif self.phase == 'movement':
                    if self.selected:
                        from_x, from_y = self.selected
                        success, resp = self.server.move_piece(self.player_id, from_x, from_y, x, y)
                        self.display_message(resp)
                        state = self.server.get_game_state(self.player_id)
                        self.update_board(state['board'])
                        self.selected = None
                    else:
                        self.selected = (x, y)
        finally:
            self.awaiting_server = False

    def send_chat(self):
        msg = self.entry_chat.get().strip()
        if msg:
            try:
                with self.polling_lock:
                    self.server.send_chat(self.player_id, msg)
                # Não exibe imediatamente no chat local para evitar duplicidade
            except Exception as e:
                self.display_message(f"Erro ao enviar mensagem: {e}")
            self.entry_chat.delete(0, tk.END)

    def poll_server(self):
        last_board = None
        last_chat = []
        while self.running:
            try:
                with self.polling_lock:
                    state = self.server.get_game_state(self.player_id)
                if state['board'] != last_board:
                    self.update_board(state['board'])
                    last_board = state['board']
                if state['phase'] != self.phase:
                    self.phase = state['phase']
                    self.display_message(f"Fase atual: {self.phase}")
                # Exibe todas as mensagens novas do chat
                for msg in state['chat']:
                    if msg not in last_chat:
                        self.display_message(msg)
                last_chat = state['chat'][:]
                # Atualiza info de turno
                is_my_turn = (state['current_player'] == self.symbol)
                if is_my_turn != self.last_turn_state:
                    if is_my_turn:
                        self.display_message("Sua vez!")
                    self.last_turn_state = is_my_turn
                # Libera interface para jogar só se for o turno do jogador
                self.awaiting_server = not is_my_turn
                if state['winner']:
                    self.display_message(state['winner'])
                    self.running = False
                    break
                if state['resigned'][self.player_id]:
                    self.display_message("Você desistiu.")
                    self.running = False
                    break
                time.sleep(1)
            except Exception as e:
                self.display_message(f"Erro de conexão: {e}")
                time.sleep(2)  # Espera e tenta novamente
                continue

    def resign(self):
        self.server.resign(self.player_id)
        self.display_message("Solicitando desistência...")
        self.running = False
        self.master.quit()

def main():
    root = tk.Tk()
    client = SeegaClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
