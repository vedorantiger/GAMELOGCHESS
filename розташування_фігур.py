# -*- coding: utf-8 -*-
"""
Модуль фігур для гри "Вершителі часу"
15 типів фігур + їх стартові позиції

ID розподіл:
- Білі фігури: 1000-1099
- Чорні фігури: 2000-2099
- Усього фігур: 92 (46 білих + 46 чорних)

Єдина система координат: 22x20
Ігрові клітинки: рядки 1-20, колонки 1-18
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from налаштування import (
    PieceType, PieceColor, 
    WHITE_ID_START, WHITE_ID_END, 
    BLACK_ID_START, BLACK_ID_END
)


class Piece:
    """Клас для представлення фігури"""
    
    def __init__(self, piece_type: PieceType, piece_color: PieceColor, piece_id: int = 0):
        # Валідація вхідних параметрів
        if not isinstance(piece_type, PieceType):
            raise ValueError(f"piece_type має бути PieceType, отримано {type(piece_type)}")
        if not isinstance(piece_color, PieceColor):
            raise ValueError(f"piece_color має бути PieceColor, отримано {type(piece_color)}")
        if not isinstance(piece_id, int) or piece_id < 0:
            raise ValueError(f"piece_id має бути невід'ємним int, отримано {piece_id}")
            
        self.type = piece_type
        self.color = piece_color
        self.id = piece_id
        self.is_enhanced = False

    def __repr__(self):
        return f"Piece({self.type.name}, {self.color.name}, id={self.id})"
    
    def __eq__(self, other):
        if not isinstance(other, Piece):
            return False
        return self.type == other.type and self.color == other.color and self.id == other.id
    
    def __hash__(self):
        """Хеш для можливості використання в множинах та словниках"""
        return hash((self.type, self.color, self.id))
    
    def is_empty(self) -> bool:
        """Перевірити, чи є фігура порожньою"""
        return self.type == PieceType.EMPTY
    
    def is_white(self) -> bool:
        """Перевірити, чи є фігура білою"""
        return self.color == PieceColor.WHITE
    
    def is_black(self) -> bool:
        """Перевірити, чи є фігура чорною"""
        return self.color == PieceColor.BLACK


@dataclass(slots=True, frozen=True)
class Move:
    """Клас для представлення ходу"""
    from_square: int
    to_square: int
    is_capture: bool = False
    promotion_piece: Optional[PieceType] = None
    is_castling: bool = False
    is_en_passant: bool = False
    is_pawn_double_move: bool = False
    is_pawn_back_move: bool = False
    is_pawn_resurrection: bool = False
    is_nebula_teleport: bool = False
    special_move_flag: Optional[str] = None  # 'TEMPLE_SWAP', 'ARISTOCRAT_EXCHANGE_ALLY', etc.
    teleport_penalty: int = 0

    def __str__(self):
        return f"Move({self.from_square} -> {self.to_square}, type={self.special_move_flag or 'NORMAL'})"


def get_initial_piece_positions() -> List[Tuple[int, int, PieceType, PieceColor, int]]:
    """
    Повертає початкові позиції всіх фігур на дошці зі СТАТИЧНИМИ ID
    Формат: (row, col, piece_type, piece_color, piece_id)
    
    Єдина система координат 22x20:
    - Ігрові клітинки: рядки 1-20, колонки 1-18
    - Туманності: (0,0), (0,19), (21,0), (21,19)
    """
    
    # === ЧОРНІ ФІГУРИ ===
    # Чорні фігури (ряд 1) - ID 2000-2017
    black_back_row = [
        (1, 1, PieceType.TEMPLE, PieceColor.BLACK, 2000),
        (1, 2, PieceType.ARISTOCRAT, PieceColor.BLACK, 2001),
        (1, 3, PieceType.RIDER, PieceColor.BLACK, 2002),
        (1, 4, PieceType.ROOK, PieceColor.BLACK, 2003),
        (1, 5, PieceType.LIGHTNING, PieceColor.BLACK, 2004),
        (1, 6, PieceType.KNIGHT, PieceColor.BLACK, 2005),
        (1, 7, PieceType.MOON, PieceColor.BLACK, 2006),
        (1, 8, PieceType.BISHOP, PieceColor.BLACK, 2007),
        (1, 9, PieceType.QUEEN, PieceColor.BLACK, 2008),
        (1, 10, PieceType.KING, PieceColor.BLACK, 2009),
        (1, 11, PieceType.BISHOP, PieceColor.BLACK, 2010),
        (1, 12, PieceType.MOON, PieceColor.BLACK, 2011),
        (1, 13, PieceType.KNIGHT, PieceColor.BLACK, 2012),
        (1, 14, PieceType.LIGHTNING, PieceColor.BLACK, 2013),
        (1, 15, PieceType.ROOK, PieceColor.BLACK, 2014),
        (1, 16, PieceType.RIDER, PieceColor.BLACK, 2015),
        (1, 17, PieceType.ARISTOCRAT, PieceColor.BLACK, 2016),
        (1, 18, PieceType.TEMPLE, PieceColor.BLACK, 2017),
    ]
    
    # Чорні пішаки (ряд 2) - ID 2018-2035
    black_pawns = [
        (2, col, PieceType.PAWN, PieceColor.BLACK, 2017 + col) 
        for col in range(1, 19)
    ]
    
    # Чорні спеціальні фігури - ID 2036-2047
    black_special = [
        (4, 5, PieceType.TRIUMPHATOR, PieceColor.BLACK, 2036),
        (4, 14, PieceType.TRIUMPHATOR, PieceColor.BLACK, 2037),
        # Фурії та Щити з фіксованими парними ID
        (4, 8, PieceType.FURY, PieceColor.BLACK, 2038),      # H17 
        (4, 6, PieceType.SHIELD, PieceColor.BLACK, 2039),    # F17 ↔ H17
        (4, 11, PieceType.FURY, PieceColor.BLACK, 2040),     # K17
        (4, 13, PieceType.SHIELD, PieceColor.BLACK, 2041),   # M17 ↔ K17
        # Очі
        (5, 3, PieceType.EYE, PieceColor.BLACK, 2042),
        (5, 7, PieceType.EYE, PieceColor.BLACK, 2043),
        (5, 12, PieceType.EYE, PieceColor.BLACK, 2044),
        (5, 16, PieceType.EYE, PieceColor.BLACK, 2045),
    ]
    
    # === БІЛІ ФІГУРИ ===
    # Білі спеціальні фігури - ID 1000-1011
    white_special = [
        (16, 3, PieceType.EYE, PieceColor.WHITE, 1000),
        (16, 7, PieceType.EYE, PieceColor.WHITE, 1001),
        (16, 12, PieceType.EYE, PieceColor.WHITE, 1002),
        (16, 16, PieceType.EYE, PieceColor.WHITE, 1003),
        (17, 5, PieceType.TRIUMPHATOR, PieceColor.WHITE, 1004),
        (17, 14, PieceType.TRIUMPHATOR, PieceColor.WHITE, 1005),
        # Фурії та Щити з фіксованими парними ID
        (17, 8, PieceType.FURY, PieceColor.WHITE, 1006),     # H4
        (17, 6, PieceType.SHIELD, PieceColor.WHITE, 1007),   # F4 ↔ H4
        (17, 11, PieceType.FURY, PieceColor.WHITE, 1008),    # K4
        (17, 13, PieceType.SHIELD, PieceColor.WHITE, 1009),  # M4 ↔ K4
    ]
    
    # Білі пішаки (ряд 19) - ID 1012-1029
    white_pawns = [
        (19, col, PieceType.PAWN, PieceColor.WHITE, 1011 + col) 
        for col in range(1, 19)
    ]
    
    # Білі фігури (ряд 20) - ID 1030-1047
    white_back_row = [
        (20, 1, PieceType.TEMPLE, PieceColor.WHITE, 1030),
        (20, 2, PieceType.ARISTOCRAT, PieceColor.WHITE, 1031),
        (20, 3, PieceType.RIDER, PieceColor.WHITE, 1032),
        (20, 4, PieceType.ROOK, PieceColor.WHITE, 1033),
        (20, 5, PieceType.LIGHTNING, PieceColor.WHITE, 1034),
        (20, 6, PieceType.KNIGHT, PieceColor.WHITE, 1035),
        (20, 7, PieceType.MOON, PieceColor.WHITE, 1036),
        (20, 8, PieceType.BISHOP, PieceColor.WHITE, 1037),
        (20, 9, PieceType.KING, PieceColor.WHITE, 1038),
        (20, 10, PieceType.QUEEN, PieceColor.WHITE, 1039),
        (20, 11, PieceType.BISHOP, PieceColor.WHITE, 1040),
        (20, 12, PieceType.MOON, PieceColor.WHITE, 1041),
        (20, 13, PieceType.KNIGHT, PieceColor.WHITE, 1042),
        (20, 14, PieceType.LIGHTNING, PieceColor.WHITE, 1043),
        (20, 15, PieceType.ROOK, PieceColor.WHITE, 1044),
        (20, 16, PieceType.RIDER, PieceColor.WHITE, 1045),
        (20, 17, PieceType.ARISTOCRAT, PieceColor.WHITE, 1046),
        (20, 18, PieceType.TEMPLE, PieceColor.WHITE, 1047),
    ]
    
    # Об'єднуємо всі позиції
    all_positions = []
    all_positions.extend(black_back_row)
    all_positions.extend(black_pawns)
    all_positions.extend(black_special)
    all_positions.extend(white_special)
    all_positions.extend(white_pawns)
    all_positions.extend(white_back_row)
    
    return all_positions


def get_piece_by_id(piece_id: int, positions: List[Tuple[int, int, PieceType, PieceColor, int]]) -> Optional[Tuple[int, int, PieceType, PieceColor, int]]:
    """Знайти фігуру за її ID"""
    # Швидка перевірка діапазону
    if not (WHITE_ID_START <= piece_id <= WHITE_ID_END or BLACK_ID_START <= piece_id <= BLACK_ID_END):
        return None
    
    # Лінійний пошук
    for pos in positions:
        if pos[4] == piece_id:  # pos[4] - це piece_id
            return pos
    return None


def get_fury_shield_partner_id(piece_id: int) -> Optional[int]:
    """Отримати ID партнера для Фурії або Щита"""
    # Чорні пари: Фурія(2038)↔Щит(2039), Фурія(2040)↔Щит(2041)
    # Білі пари: Фурія(1006)↔Щит(1007), Фурія(1008)↔Щит(1009)
    fury_shield_pairs = {
        # Чорні пари
        2038: 2039,  # H17 Фурія ↔ F17 Щит
        2039: 2038,  # F17 Щит ↔ H17 Фурія
        2040: 2041,  # K17 Фурія ↔ M17 Щит
        2041: 2040,  # M17 Щит ↔ K17 Фурія
        # Білі пари
        1006: 1007,  # H4 Фурія ↔ F4 Щит
        1007: 1006,  # F4 Щит ↔ H4 Фурія
        1008: 1009,  # K4 Фурія ↔ M4 Щит
        1009: 1008,  # M4 Щит ↔ K4 Фурія
    }
    
    return fury_shield_pairs.get(piece_id)


def is_fury_shield_pair(id1: int, id2: int) -> bool:
    """Перевірити, чи є дві фігури парою Фурія↔Щит"""
    partner_id = get_fury_shield_partner_id(id1)
    return partner_id == id2


def is_valid_position(row: int, col: int) -> bool:
    """
    Перевіряє, чи знаходиться позиція в межах ігрової зони.
    Єдина система координат 22x20:
    - Ігрові клітинки: рядки 1-20, колонки 1-18
    - Туманності: (0,0), (0,19), (21,0), (21,19) - поза ігровою зоною
    """
    return (1 <= row <= 20 and 1 <= col <= 18)


def validate_piece_positions(positions: List[Tuple[int, int, PieceType, PieceColor, int]]) -> List[str]:
    """
    Валідувати список позицій фігур
    Повертає список помилок (порожній список якщо все ОК)
    """
    errors = []
    
    # Перевірка унікальності ID
    ids = [pos[4] for pos in positions]
    if len(ids) != len(set(ids)):
        errors.append("Знайдені дублікати ID")
    
    # Перевірка позицій на дошці
    for i, (row, col, piece_type, color, piece_id) in enumerate(positions):
        if not is_valid_position(row, col):
            errors.append(f"Позиція {i}: ({row}, {col}) поза межами ігрової зони")
        
        # Перевірка діапазону ID
        if color == PieceColor.WHITE and not (WHITE_ID_START <= piece_id <= WHITE_ID_END):
            errors.append(f"Позиція {i}: Білий ID {piece_id} поза діапазоном")
        elif color == PieceColor.BLACK and not (BLACK_ID_START <= piece_id <= BLACK_ID_END):
            errors.append(f"Позиція {i}: Чорний ID {piece_id} поза діапазоном")
    
    return errors


# Кешування початкових позицій для оптимізації
_CACHED_INITIAL_POSITIONS = None

def get_initial_positions_cached() -> List[Tuple[int, int, PieceType, PieceColor, int]]:
    """Отримати початкові позиції з кешуванням"""
    global _CACHED_INITIAL_POSITIONS
    if _CACHED_INITIAL_POSITIONS is None:
        _CACHED_INITIAL_POSITIONS = get_initial_piece_positions()
    return _CACHED_INITIAL_POSITIONS