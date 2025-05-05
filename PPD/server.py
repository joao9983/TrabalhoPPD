import socket
import threading
import time

from game.board import Board


HOST = ''

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
    conn.send(f"Você é o jogador {player_symbols[player_id]}.\n".encode())  # Mensagem indicando o jogador
    print(f"[DEBUG] Mensagem enviada para {addr}: Você é o jogador {player_symbols[player_id]}.")

    if player_symbols[player_id] != game.current_player:
        conn.send("Aguardue pelo outro jogador...\n".encode())

    while True:
        try:
            msg = conn.recv(1024).decode().strip()
            if not msg:
                break

            print(f"[{addr}] {msg}")

            with lock:
                if msg.startswith("chat "):
                    chat_msg = msg[5:].strip()
                    if chat_msg:
                        for c in clients:
                            try:
                                c.send(f"[Chat] Jogador {player_symbols[player_id]}: {chat_msg}\n".encode())
                            except:
                                pass
                        conn.send("Mensagem enviada!\n".encode())
                    else:
                        conn.send("Mensagem de chat vazia.\n".encode())
                    continue  # Chat tratado, volta pro loop!

                # Daqui para baixo, só comandos de jogo (place/move/exit) respeitam turno
                if game.current_player != player_symbols[player_id]:
                    conn.send("Aguarde seu turno...\n".encode())
                    continue

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

                # Manda resposta apenas para quem jogou
                conn.send(f"\n🎮 {response}\n".encode())

                # Atualiza o tabuleiro para ambos
                send_board()

                if "Fim do jogo!" in response:
                    broadcast(f"🏁 Fim do jogo!\n")
                    for c in clients:
                        try:
                            c.shutdown(socket.SHUT_RDWR)
                            c.close()
                        except:
                            pass
                    return
                
                # Manda aviso para o adversário
                other_player_id = 1 - player_id
                other_conn = clients[other_player_id]
                try:
                    other_conn.send("\n🎯 Seu adversário jogou. Sua vez!\n".encode())
                    print(f"[DEBUG] Mensagem enviada para jogador {player_symbols[other_player_id]}: Sua vez!")
                except:
                    pass
                
        except Exception as e:
            print(f"Erro com cliente {addr}: {e}")
            break

    conn.close()
    clients.remove(conn)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, 0))  # Porta automática
    port = s.getsockname()[1]
    with open("server_port.txt", "w") as f:
        f.write(str(port))
    s.listen(2)
    print(f"Servidor aguardando 2 jogadores na porta {port}...")

    while len(clients) < 2:
        conn, addr = s.accept()
        print(f"Jogador conectado: {addr}")
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr, len(clients)-1)).start()

    print("Dois jogadores conectados. Jogo iniciado.")
    broadcast(f"Jogo iniciado! Jogador {game.current_player} começa a partida.\n")  # Envia mensagem para ambos
    print(f"[DEBUG] Mensagem de início enviada: Jogador {game.current_player} começa a partida.")
    send_board()

if __name__ == "__main__":
    main()