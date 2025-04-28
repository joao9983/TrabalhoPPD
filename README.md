# Seega - Trabalho PPD

Este projeto implementa o jogo Seega com comunicação via sockets, incluindo interface gráfica e chat.

## Estrutura do Projeto

PPD/
    client_ui.py      # Cliente com interface gráfica (Tkinter)
    client.py         # Cliente de terminal
    game/
        board.py      # Lógica do jogo Seega
    server.py         # Servidor do jogo
    test.py           # Testes da lógica do tabuleiro
README.md

## Pré-requisitos

- Python 3.8 ou superior
- (Opcional) virtualenv para criar ambientes virtuais

## Criando o Ambiente Virtual

No terminal, execute:

    python -m venv venv

Ative o ambiente virtual:

- Windows:
      venv\Scripts\activate
- Linux/macOS:
      source venv/bin/activate

## Instalando Dependências

O único requisito extra é o Tkinter (usado na interface gráfica), que já vem com a maioria das instalações do Python.  
Se necessário, instale o Tkinter:

- Ubuntu/Debian:
      sudo apt-get install python3-tk
- Windows:  
  Tkinter já está incluído no instalador oficial do Python.

## Executando o Servidor

Abra um terminal na pasta PPD e execute:

    python server.py

O servidor aguardará dois jogadores conectarem.

## Executando o Cliente de Terminal

Abra outro terminal (com o ambiente ativado) e execute:

    python client.py

Repita em outro terminal para o segundo jogador.

## Executando o Cliente com Interface Gráfica

Abra outro terminal (com o ambiente ativado) e execute:

    python client_ui.py

Repita em outro terminal para o segundo jogador.

## Comandos do Cliente

- Colocar peça:  
  place x y  
  Exemplo: place 1 2
- Mover peça:  
  move x1 y1 x2 y2  
  Exemplo: move 1 2 1 3
- Desistir:  
  exit
- Chat:  
  chat mensagem  
  Exemplo: chat Olá!

Na interface gráfica, basta clicar nas casas do tabuleiro e usar o campo de chat.

## Testando a Lógica do Jogo

Para rodar testes simples da lógica do tabuleiro:

    python test.py

## Observações

- O servidor e os clientes devem ser executados na mesma máquina (localhost) por padrão.
- Para jogar em máquinas diferentes, altere o valor de host em client.py e client_ui.py para o IP do servidor.

---

Qualquer dúvida, entre em contato!