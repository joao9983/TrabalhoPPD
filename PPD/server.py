import socket
import threading
from game.board import Board

HOST = 'localhost'
PORT = 5555

clients = []
player_symbols = ['X', 'O']
game = Board()
lock = threading.Lock()

def broadcast(msg):
    for client in clients:
        try:
            client.send(msg.encode())
        except:
            pass

def send_board():
    board_str = "\n".join(" ".join(row) for row in game.board)
    broadcast(f"\nTabuleiro atual:\n{board_str}\n")

def handle_client(conn, addr, player_id):
    conn.send(f"Você é o jogador {player_symbols[player_id]}\n".encode())

    while True:
        with lock:
            if game.current_player != player_symbols[player_id]:
                conn.send("Aguarde seu turno...\n".encode())
                continue

            conn.send("Seu turno! Digite o comando (ex: place x y OU move x1 y1 x2 y2):\n".encode())
        
        try:
            msg = conn.recv(1024).decode().strip()
            if not msg:
                break

            print(f"[{addr}] {msg}")
            with lock:
                if msg.startswith("place"):
                    try:
                        _, x, y = msg.split()
                        success, response = game.place_piece(int(x), int(y))
                    except ValueError:
                        conn.send("Comando inválido. Use: place x y\n".encode())
                        continue

                elif msg.startswith("move"):
                    try:
                        _, x1, y1, x2, y2 = msg.split()
                        success, response = game.move_piece(int(x1), int(y1), int(x2), int(y2))
                    except ValueError:
                        conn.send("Comando inválido. Use: move x1 y1 x2 y2\n".encode())
                        continue

                elif msg.strip() in ["exit", "resign", "desistir"]:
                    broadcast(f"Jogador {player_symbols[player_id]} desistiu. Jogador {player_symbols[1 - player_id]} venceu!\n")
                    conn.send("Você desistiu da partida.\n".encode())

                    for c in clients:
                        try:
                            c.shutdown(socket.SHUT_RDWR)
                            c.close()
                        except:
                            pass

                    print(f"Jogador {player_symbols[player_id]} desistiu. Fim da partida.")
                    return

                else:
                    conn.send("Comando inválido.\n".encode())
                    continue

                broadcast(f"\n{response}")
                send_board()

                # ✅ Verificação de fim de jogo removida daqui!
                # Agora o fim de jogo é tratado internamente no board.move_piece()

                # Se o move_piece ou place_piece detectou fim de jogo,
                # ele já mandou no response — e podemos encerrar o servidor:
                if "Fim do jogo!" in response:
                    for c in clients:
                        try:
                            c.shutdown(socket.SHUT_RDWR)
                            c.close()
                        except:
                            pass
                    return

        except Exception as e:
            print(f"Erro com cliente {addr}: {e}")
            break

    conn.close()
    clients.remove(conn)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(2)
    print("Servidor aguardando 2 jogadores...")

    while len(clients) < 2:
        conn, addr = s.accept()
        print(f"Jogador conectado: {addr}")
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr, len(clients)-1)).start()

    print("Dois jogadores conectados. Jogo iniciado.")
    send_board()

if __name__ == "__main__":
    main()