# test_move.py
from game.board import Board

b = Board()

# Pré-configuração manual para testes (fase de movimentação)
b.phase = 'movement'
b.board = [
    ['.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.'],
    ['.', '.', ' ', '.', '.'],
    ['.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.']
]
b.board[2][1] = 'X'  # jogador atual
b.board[2][2] = 'O'  # oponente
b.board[2][3] = 'X'  # jogador atual
b.current_player = 'X'

b.print_board()
success, msg = b.move_piece(2, 3, 2, 2)  # move X para capturar O
print(msg)
b.print_board()
