# client.py
import socket
import threading

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(2048).decode()
            if not msg:
                break
            print(msg)
        except:
            print("Conexão encerrada pelo servidor.")
            break

def main():
    host = 'localhost'
    port = 5555

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

    while True:
        try:
            msg = input()
            if not msg.strip():
                continue
            if msg.strip().lower() == "exit":
                s.send(msg.encode())
                break
            s.send(msg.encode())
        except:
            print("Erro ao enviar mensagem.")
            break

    s.close()

if __name__ == "__main__":
    main()
