# -*- coding: utf-8 -*-
import numpy as np
from typing import List, Tuple, Optional, Set, Dict
from налаштування import (
    BOARD_ROWS, BOARD_COLS, PieceType, PieceColor, CellType, NEBULAS
)
from розташування_фігур import Piece
from логування import game_logger


class Board:
    def __init__(self):
        self.rows = BOARD_ROWS  # 22
        self.cols = BOARD_COLS  # 20
        
        # ОПТИМІЗАЦІЯ: Використовуємо int16 замість int32 (економія пам'яті)
        self.mailbox = np.zeros((self.rows, self.cols), dtype=np.int16)
        
        # ОПТИМІЗАЦІЯ: Компактні бітборди (використовуємо int для великих чисел)
        self.bitboards = {
            PieceColor.WHITE: {piece_type: 0 for piece_type in PieceType},
            PieceColor.BLACK: {piece_type: 0 for piece_type in PieceType}
        }
        
        # Загальні бітборди
        self.all_pieces = {
            PieceColor.WHITE: 0,
            PieceColor.BLACK: 0
        }
        
        # ОПТИМІЗАЦІЯ: O(1) доступ до фігур та позицій
        self.pieces_by_id = {}
        self.position_by_id = {}  # ID -> (row, col) для O(1) пошуку!
        
        # ОПТИМІЗАЦІЯ: Кеш для швидких запитів
        self._pieces_cache = {
            PieceColor.WHITE: {},
            PieceColor.BLACK: {}
        }
        self._cache_valid = False
        
        # Стани туманностей
        self.nebula_states = {
            name: {"active": True, "owner": None, "timer": 0}
            for name in NEBULAS.keys()
        }
        
        # ОПТИМІЗАЦІЯ: Zobrist хешування для швидкого порівняння позицій
        self._init_zobrist()
        self.position_hash = np.uint64(0)
        
        game_logger.info("Ініціалізовано оптимізовану дошку з NumPy, бітбордами та кешуванням")
    
    def _init_zobrist(self):
        """Ініціалізація Zobrist таблиці для хешування"""
        np.random.seed(42)  # Для відтворюваності
        self.zobrist_table = np.random.randint(
            0, 2**32, (self.rows, self.cols, 3000), dtype=np.uint32
        )
    
    def _update_hash(self, row: int, col: int, piece_id: int, is_adding: bool):
        """Оновлює Zobrist хеш позиції"""
        if piece_id > 0 and piece_id < 3000:
            hash_value = self.zobrist_table[row, col, piece_id]
            self.position_hash ^= hash_value
    
    def position_to_bit(self, row: int, col: int) -> int:
        """Конвертує позицію (row, col) в біт для бітборда"""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return row * self.cols + col
        return -1
    
    def bit_to_position(self, bit: int) -> Tuple[int, int]:
        """Конвертує біт назад у позицію (row, col)"""
        row = bit // self.cols
        col = bit % self.cols
        return (row, col)
    
    def get_piece_at(self, row: int, col: int) -> Optional[Piece]:
        """Отримує фігуру на заданій позиції"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return None
        
        piece_id = self.mailbox[row, col]
        if piece_id == 0:
            # Повертаємо порожню фігуру
            return Piece(PieceType.EMPTY, PieceColor.WHITE, 0)
        
        return self.pieces_by_id.get(piece_id, Piece(PieceType.EMPTY, PieceColor.WHITE, 0))
    
    def set_piece(self, row: int, col: int, piece: Piece):
        """Встановлює фігуру на заданій позиції"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        
        # Спочатку очищуємо клітинку
        self.clear_square(row, col)
        
        # Якщо це порожня фігура, залишаємо клітинку порожньою
        if piece.is_empty():
            return
        
        # Встановлюємо фігуру
        self.mailbox[row, col] = piece.id
        self.pieces_by_id[piece.id] = piece
        self.position_by_id[piece.id] = (row, col)  # Оновлюємо позицію
        
        # Оновлюємо бітборди
        bit = self.position_to_bit(row, col)
        if bit >= 0:
            self.bitboards[piece.color][piece.type] |= (1 << bit)
            self.all_pieces[piece.color] |= (1 << bit)
        
        # Оновлюємо хеш
        self._update_hash(row, col, piece.id, True)
        
        # Інвалідуємо кеш
        self._cache_valid = False
    
    def clear_square(self, row: int, col: int):
        """Очищує клітинку від фігури"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        
        piece_id = self.mailbox[row, col]
        if piece_id == 0:
            return  # Клітинка вже порожня
        
        # Отримуємо фігуру для оновлення бітбордів
        piece = self.pieces_by_id.get(piece_id)
        if piece:
            bit = self.position_to_bit(row, col)
            if bit >= 0:
                # Видаляємо з бітбордів
                mask = ~(1 << bit)
                self.bitboards[piece.color][piece.type] &= mask
                self.all_pieces[piece.color] &= mask
            
            # Оновлюємо хеш
            self._update_hash(row, col, piece_id, False)
        
        # Очищуємо клітинку
        self.mailbox[row, col] = 0
        if piece_id in self.pieces_by_id:
            del self.pieces_by_id[piece_id]
        if piece_id in self.position_by_id:
            del self.position_by_id[piece_id]
        
        # Інвалідуємо кеш
        self._cache_valid = False
    
    def move_piece(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Переміщує фігуру - АТОМАРНА ОПЕРАЦІЯ"""
        piece = self.get_piece_at(from_row, from_col)
        if not piece or piece.is_empty():
            return False
        
        # Зберігаємо ID для швидкості
        piece_id = piece.id
        
        # Очищуємо цільову клітинку
        self.clear_square(to_row, to_col)
        
        # ОПТИМІЗАЦІЯ: Прямі операції з mailbox
        self.mailbox[to_row, to_col] = piece_id
        self.mailbox[from_row, from_col] = 0
        
        # Оновлюємо позицію O(1)
        self.position_by_id[piece_id] = (to_row, to_col)
        
        # Оновлюємо бітборди одною операцією
        from_bit = self.position_to_bit(from_row, from_col)
        to_bit = self.position_to_bit(to_row, to_col)
        
        if from_bit >= 0 and to_bit >= 0:
            move_mask = (1 << from_bit) | (1 << to_bit)
            self.bitboards[piece.color][piece.type] ^= move_mask
            self.all_pieces[piece.color] ^= move_mask
        
        # Оновлюємо хеш
        self._update_hash(from_row, from_col, piece_id, False)
        self._update_hash(to_row, to_col, piece_id, True)
        
        return True
    
    def get_piece_by_id(self, piece_id: int) -> Optional[Piece]:
        """Отримує фігуру за її ID"""
        return self.pieces_by_id.get(piece_id)
    
    def find_piece_position(self, piece_id: int) -> Optional[Tuple[int, int]]:
        """Знаходить позицію фігури за її ID (O(1) пошук)"""
        return self.position_by_id.get(piece_id)
    
    def is_square_empty(self, row: int, col: int) -> bool:
        """Перевіряє, чи порожня клітинка"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return False
        return self.mailbox[row, col] == 0
    
    def is_square_occupied_by_color(self, row: int, col: int, color: PieceColor) -> bool:
        """Перевіряє, чи зайнята клітинка фігурою певного кольору"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return False
        
        bit = self.position_to_bit(row, col)
        if bit < 0:
            return False
        
        return bool(self.all_pieces[color] & (1 << bit))
    
    def get_all_pieces_of_type(self, piece_type: PieceType, color: PieceColor) -> List[Tuple[int, int]]:
        """Отримує всі позиції фігур певного типу та кольору"""
        positions = []
        bitboard = self.bitboards[color][piece_type]
        
        # Ітеруємо по бітборду
        while bitboard:
            # Знаходимо найнижчий встановлений біт
            bit = (bitboard & -bitboard).bit_length() - 1
            positions.append(self.bit_to_position(bit))
            # Видаляємо цей біт
            bitboard &= bitboard - 1
        
        return positions
    
    def get_all_pieces_of_color(self, color: PieceColor) -> List[Tuple[int, int]]:
        """Отримує всі позиції фігур певного кольору"""
        positions = []
        bitboard = self.all_pieces[color]
        
        while bitboard:
            bit = (bitboard & -bitboard).bit_length() - 1
            positions.append(self.bit_to_position(bit))
            bitboard &= bitboard - 1
        
        return positions
    
    def get_all_pieces(self) -> List[Tuple[int, int, Piece]]:
        """Отримує всі фігури на дошці"""
        pieces = []
        for row in range(self.rows):
            for col in range(self.cols):
                piece = self.get_piece_at(row, col)
                if piece and not piece.is_empty():
                    pieces.append((row, col, piece))
        return pieces
    
    def is_nebula(self, row: int, col: int) -> bool:
        """Перевіряє, чи є позиція туманністю"""
        for name, (neb_row, neb_col) in NEBULAS.items():
            if neb_row == row and neb_col == col:
                return True
        return False
    
    def get_nebula_at(self, row: int, col: int) -> Optional[str]:
        """Отримує назву туманності на позиції"""
        for name, (neb_row, neb_col) in NEBULAS.items():
            if neb_row == row and neb_col == col:
                return name
        return None
    
    def activate_nebula(self, nebula_name: str, owner: PieceColor, timer: int = 3):
        """Активує туманність для певного гравця"""
        if nebula_name in self.nebula_states:
            self.nebula_states[nebula_name] = {
                "active": True,
                "owner": owner,
                "timer": timer
            }
            game_logger.info(f"Туманність {nebula_name} активована для {owner.name} на {timer} ходів")
    
    def deactivate_nebula(self, nebula_name: str):
        """Деактивує туманність"""
        if nebula_name in self.nebula_states:
            self.nebula_states[nebula_name] = {
                "active": False,
                "owner": None,
                "timer": 0
            }
            game_logger.info(f"Туманність {nebula_name} деактивована")
    
    def update_nebula_timers(self):
        """Оновлює таймери туманностей"""
        for name, state in self.nebula_states.items():
            if state["active"] and state["timer"] > 0:
                state["timer"] -= 1
                if state["timer"] == 0:
                    self.deactivate_nebula(name)
    
    def can_use_nebula(self, nebula_name: str, color: PieceColor) -> bool:
        """Перевіряє, чи може гравець використовувати туманність"""
        if nebula_name not in self.nebula_states:
            return False
        
        state = self.nebula_states[nebula_name]
        return state["active"] and state["owner"] == color
    
    def count_pieces(self, piece_type: PieceType, color: PieceColor) -> int:
        """Підраховує кількість фігур певного типу та кольору"""
        bitboard = self.bitboards[color][piece_type]
        return bin(bitboard).count('1')