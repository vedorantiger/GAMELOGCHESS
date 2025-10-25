
from typing import Tuple, Optional
from налаштування import PieceType, PieceColor
from розташування_фігур import Move
from логування import game_logger


class ChessAI:
    def __init__(self, depth: int = 3):

        self.depth = depth
        self.evaluator = None
        game_logger.info(f"Ініціалізовано ШІ з глибиною пошуку {depth}")

    def get_best_move(self, game_state, color: PieceColor) -> Optional[Move]:

        game_logger.warning("ШІ ще не реалізовано - повертаємо випадковий хід")
        
        # Правильно перебираємо всі фігури через API дошки
        all_pieces = game_state.board.get_all_pieces_of_color(color)
        
        for row, col in all_pieces:
            piece = game_state.board.get_piece_at(row, col)
            if piece and not piece.is_empty() and piece.color == color:
                moves, attacks = game_state.move_calculator.get_possible_moves(piece, row, col)
                if moves:
                    return Move(
                        from_square=(row, col),
                        to_square=moves[0],
                        is_capture=False
                    )
                if attacks:
                    return Move(
                        from_square=(row, col),
                        to_square=attacks[0],
                        is_capture=True
                    )
        return None

    def minimax(self, game_state, depth: int, alpha: float, beta: float,
                maximizing_player: bool) -> float:

        return 0.0

    def set_difficulty(self, level: int):

        if 1 <= level <= 5:
            self.depth = level * 2
            game_logger.info(f"Встановлено рівень складності ШІ: {level} (глибина: {self.depth})")
        else:
            game_logger.warning(f"Некоректний рівень складності: {level}")
