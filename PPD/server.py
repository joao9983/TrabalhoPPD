import socket
import threading
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

from game.board import Board


HOST = ''

class SeegaRPCServer:
    def __init__(self):
        self.clients = []  # Lista de clientes conectados (apenas para controle)
        self.player_symbols = ['X', 'O']
        self.game = Board()
        self.lock = threading.Lock()
        self.chat_log = []
        self.resigned = [False, False]

    def join_game(self):
        """Retorna o id do jogador (0 ou 1) e símbolo."""
        with self.lock:
            if len(self.clients) < 2:
                player_id = len(self.clients)
                self.clients.append(player_id)
                return player_id, self.player_symbols[player_id]
            else:
                return -1, ""

    def get_game_state(self, player_id):
        """Retorna o tabuleiro, fase, jogador atual, mensagens de chat e status."""
        with self.lock:
            board_str = "\n".join(" ".join(row) for row in self.game.board)
            return {
                'board': board_str,
                'phase': self.game.phase,
                'current_player': self.game.current_player,
                'chat': self.chat_log[-10:],
                'winner': self._get_winner(),
                'resigned': self.resigned.copy(),
            }

    def place_piece(self, player_id, x, y):
        with self.lock:
            if self.game.current_player != self.player_symbols[player_id]:
                return False, "Aguarde seu turno..."
            success, response = self.game.place_piece(x, y)
            # NÃO chama self._switch_turn() aqui!
            return success, response

    def move_piece(self, player_id, x1, y1, x2, y2):
        with self.lock:
            if self.game.current_player != self.player_symbols[player_id]:
                return False, "Aguarde seu turno..."
            success, response = self.game.move_piece(x1, y1, x2, y2)
            # NÃO chama self._switch_turn() aqui!
            return success, response

    def send_chat(self, player_id, msg):
        with self.lock:
            symbol = self.player_symbols[player_id]
            chat_msg = f"[Chat] Jogador {symbol}: {msg}"
            self.chat_log.append(chat_msg)
            return True

    def resign(self, player_id):
        with self.lock:
            self.resigned[player_id] = True
            return True

    def get_chat(self):
        """Retorna as últimas 10 mensagens do chat."""
        with self.lock:
            return self.chat_log[-10:]

    def _get_winner(self):
        winner, reason = self.game._check_winner()
        if winner:
            return f"Jogador {winner} venceu! {reason} Fim do jogo!"
        if any(self.resigned):
            idx = self.resigned.index(True)
            return f"Jogador {self.player_symbols[1-idx]} venceu por desistência!"
        return None

# --- Servidor principal ---
def main():
    server = SimpleXMLRPCServer((HOST, 8000), allow_none=True, logRequests=True)
    server.register_introspection_functions()
    seega = SeegaRPCServer()
    server.register_instance(seega)
    print("Servidor XML-RPC aguardando conexões na porta 8000...")
    server.serve_forever()

if __name__ == "__main__":
    main()