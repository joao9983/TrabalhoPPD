class Board:
    EMPTY = '.'
    PLAYER1 = 'X'
    PLAYER2 = 'O'

    def __init__(self):
        self.size = 5
        self.board = [[self.EMPTY for _ in range(self.size)] for _ in range(self.size)]
        self.board[2][2] = ' '  # casa central vazia
        self.phase = 'placement'
        self.pieces = {self.PLAYER1: 0, self.PLAYER2: 0}
        self.max_pieces = 12
        self.current_player = self.PLAYER1

    def print_board(self):
        for row in self.board:
            print(" ".join(row))
        print()

    def place_piece(self, x, y):
        if self.phase != 'placement':
            return False, "Fase de movimentação iniciada."

        if not self._is_valid_cell(x, y):
            return False, "Posição inválida."

        if self.board[y][x] != self.EMPTY:
            return False, "Casa já ocupada."

        self.board[y][x] = self.current_player
        self.pieces[self.current_player] += 1

        if self._placement_complete():
            self.phase = 'movement'

        self._switch_turn()
        return True, "Peça colocada com sucesso."

    def _placement_complete(self):
        return all(p == self.max_pieces for p in self.pieces.values())

    def _switch_turn(self):
        self.current_player = self.PLAYER2 if self.current_player == self.PLAYER1 else self.PLAYER1

    def _is_valid_cell(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size and not (x == 2 and y == 2)

    def move_piece(self, from_x, from_y, to_x, to_y):
        if self.phase != 'movement':
            return False, "Ainda estamos na fase de colocação."

        if not self._is_valid_cell(from_x, from_y) or not self._is_valid_cell(to_x, to_y):
            return False, "Posição fora do tabuleiro."

        if self.board[from_y][from_x] != self.current_player:
            return False, "Você só pode mover suas próprias peças."

        if self.board[to_y][to_x] != self.EMPTY:
            return False, "Destino inválido (não está vazio)."

        if not self._is_adjacent(from_x, from_y, to_x, to_y):
            return False, "Movimento deve ser para uma casa adjacente (sem diagonais)."

        # Realiza o movimento
        self.board[to_y][to_x] = self.current_player
        self.board[from_y][from_x] = self.EMPTY

        # Verifica captura
        self._check_captures(to_x, to_y)

        # Verifica fim de jogo
        winner = self._check_winner()
        if winner:
            return True, f"Fim de jogo! Jogador {winner} venceu!"

        self._switch_turn()
        return True, "Movimento realizado com sucesso."

    def _is_adjacent(self, x1, y1, x2, y2):
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)

    def _check_captures(self, x, y):
        opp = self.PLAYER2 if self.current_player == self.PLAYER1 else self.PLAYER1
        directions = [(-1,0), (1,0), (0,-1), (0,1)]  # esquerda, direita, cima, baixo

        for dx, dy in directions:
            nx = x + dx
            ny = y + dy
            px = x + 2 * dx
            py = y + 2 * dy
            if self._in_bounds(px, py):
                if self.board[ny][nx] == opp and self.board[py][px] == self.current_player:
                    self.board[ny][nx] = self.EMPTY  # captura!

    def _check_winner(self):
        pieces_p1 = sum(row.count(self.PLAYER1) for row in self.board)
        pieces_p2 = sum(row.count(self.PLAYER2) for row in self.board)
        if pieces_p1 == 0:
            return self.PLAYER2
        elif pieces_p2 == 0:
            return self.PLAYER1
        return None

    def _in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size
    
    def __str__(self):
        return "\n".join(" ".join(row) for row in self.board)