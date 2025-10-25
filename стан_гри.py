# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple, Optional
from дошка import Board
from розташування_фігур import Piece, Move, get_initial_piece_positions
from правила_фігур import MoveCalculator
from налаштування import (
    PieceType, PieceColor,
    LETTERS_BOTTOM, NUMBERS_LEFT,
    PIECE_NAMES_UA, NEBULAS
)
from логування import game_logger, game_print, log_error, end_game

def coordinates_to_chess_notation(row: int, col: int) -> str:
    """Конвертує координати в шахову нотацію"""
    if 0 <= col - 1 < len(LETTERS_BOTTOM):
        letter = LETTERS_BOTTOM[col - 1]
    else:
        letter = chr(ord('A') + col - 1)
    
    # Перевертаємо номер рядка для правильної нотації
    chess_row = 21 - row
    return f"{letter}{chess_row}"

def get_color_name_ua(piece_color: PieceColor) -> str:
    return "білий" if piece_color == PieceColor.WHITE else "чорний"

def get_color_name_ua_with_gender(piece_color: PieceColor, piece_type: PieceType) -> str:
    feminine_pieces = {PieceType.QUEEN, PieceType.ROOK, PieceType.FURY, PieceType.LIGHTNING}
    if piece_type in feminine_pieces:
        return "біла" if piece_color == PieceColor.WHITE else "чорна"
    else:
        return "білий" if piece_color == PieceColor.WHITE else "чорний"

def is_nebula_coordinates(row: int, col: int) -> bool:
    for nebula_name, (neb_row, neb_col) in NEBULAS.items():
        if neb_row == row and neb_col == col:
            return True
    return False

def get_nebula_name(row: int, col: int) -> Optional[str]:
    for nebula_name, (neb_row, neb_col) in NEBULAS.items():
        if neb_row == row and neb_col == col:
            return nebula_name
    return None

def get_nebula_emoji_name(nebula_name: str) -> str:
    nebula_names_ua = {
        "top_left": "верхня ліва",
        "top_right": "верхня права", 
        "bottom_left": "нижня ліва",
        "bottom_right": "нижня права"
    }
    return nebula_names_ua.get(nebula_name, nebula_name)

class GameState:
    def __init__(self):
        self.board = Board()
        self.current_player = PieceColor.WHITE
        self.turn_number = 1
        self.selected_piece = None
        self.possible_moves = []
        self.possible_attacks = []
        self.possible_teleports = []
        
        self.move_calculator = MoveCalculator(self.board)
        self.move_calculator.set_game_state(self)
        
        self.move_history = []
        self.captured_pieces = {"white": [], "black": []}
        
        self.paralysis_selection = None  # {'triumphator_pos': (r,c), 'target_pos': (r,c)}
        self.paralyzed_pieces = {}  # {(row, col): {'duration': int, 'piece_id': int}}
        self.moon_double_move = None
        
        self.nebula_blocked = {
            "top_left": True,
            "top_right": True, 
            "bottom_left": True,
            "bottom_right": True
        }
        
        self.resurrected_pawns = {"white": 0, "black": 0}
        self.resurrection_available = {"white": 0, "black": 0}
        self.nebulas_activated = {"white": False, "black": False}
        self.nebula_piece_timers = {}
        self.recently_resurrected_pieces = set()

        # Eye enhancement attributes
        self.eye_enhancement_used = {"white": False, "black": False}
        self.triumphant_eye_links = {}
        self.eye_enhancement_selection = None
        
        # Система полювання на душі Всадником
        self.hunted_souls = {
            "white": {PieceType.KNIGHT: False, PieceType.BISHOP: False, PieceType.RIDER: False},
            "black": {PieceType.KNIGHT: False, PieceType.BISHOP: False, PieceType.RIDER: False}
        }
        self.performed_resurrection = {"white": False, "black": False}  # Одне воскресіння всадником на всю гру (НАЗАВЖДІ)
        self.soul_corners = []  # Список куточків для воскресіння: [(row, col, piece_type, is_green, player_color)]
        
        # Система Аристократа - дипломатичний обмін
        self.aristocrat_exchanges = []  # Список можливих обмінів: [(row, col)]
        
        # Система Місяця - подвійний хід
        self.moon_double_move_active = {"white": False, "black": False}  # Активація подвійного ходу
        self.moon_double_move_used = {"white": False, "black": False}  # Використання подвійного ходу (один раз за гру)
        self.moon_double_move_first_piece = None  # ID фігури, що зробила перший хід
        
        # Система Храму - священний обмін
        self.temple_swap_used = {
            "black_left": False,    # Храм на позиції (1, 1) - ID 2000
            "black_right": False,   # Храм на позиції (1, 18) - ID 2017
            "white_left": False,    # Храм на позиції (20, 1) - ID 1030
            "white_right": False    # Храм на позиції (20, 18) - ID 1047
        }
        self.temple_swap_selection = None  # {'temple_pos': (r,c), 'temple_id': str}
        
        # Статус завершення гри
        self.game_over = False
        self.winner = None  # 'white', 'black', або 'draw' (для пату)
        self.game_over_reason = None  # 'checkmate', 'stalemate', тощо
        
        self._setup_initial_position()
    
    def _setup_initial_position(self):
        initial_positions = get_initial_piece_positions()
        for row, col, piece_type, piece_color, piece_id in initial_positions:
            if 1 <= row <= 20 and 1 <= col <= 18:
                piece = Piece(piece_type, piece_color, piece_id)
                self.board.set_piece(row, col, piece)
        
        # Setup Triumphant-Eye links
        self.triumphant_eye_links = {
            1004: [1000, 1001],
            1005: [1002, 1003],
            2036: [2042, 2043],
            2037: [2044, 2045],
        }

    def get_piece_at(self, row: int, col: int) -> Optional[Piece]:
        piece = self.board.get_piece_at(row, col)
        if piece and not piece.is_empty():
            return piece
        return None
    
    def is_nebula_blocked(self, row: int, col: int) -> bool:
        for nebula_name, (nebula_row, nebula_col) in NEBULAS.items():
            if nebula_row == row and nebula_col == col:
                return self.nebula_blocked.get(nebula_name, False)
        return False
    
    def unlock_nebula(self, nebula_name: str):
        if nebula_name in self.nebula_blocked:
            self.nebula_blocked[nebula_name] = False
    
    def get_nebula_ring_color(self, row: int, col: int, current_player_color: PieceColor) -> Optional[PieceColor]:
        if self.is_nebula_blocked(row, col):
            return PieceColor.BLACK if current_player_color == PieceColor.WHITE else PieceColor.WHITE
        return None
    
    def select_piece(self, row: int, col: int) -> bool:
        if self.paralysis_selection:
            return self._handle_paralysis_landing_selection(row, col)

        # Eye enhancement тепер обробляється в графіка_інтерфейсу.py через _handle_enhancement_click()
        # Тут ми просто блокуємо звичайний вибір фігур під час посилення
        if self.eye_enhancement_selection:
            return False

        if (row, col) in self.paralyzed_pieces:
            game_print("❌ Ця фігура паралізована!")
            return False

        piece = self.get_piece_at(row, col)
            
        if piece is None or piece.color != self.current_player:
            self.clear_selection()
            # Очищаємо вибір Храму, якщо клікаємо на порожню клітинку або ворожу фігуру
            self.temple_swap_selection = None
            return False
        
        # Якщо вибираємо не Храм, очищаємо попередній вибір обміну
        if piece.type != PieceType.TEMPLE:
            self.temple_swap_selection = None
        
        if piece.id in self.recently_resurrected_pieces:
            return False
        
        # Перевірка подвійного ходу Місяця
        color_key = "white" if piece.color == PieceColor.WHITE else "black"
        if self.moon_double_move_active[color_key]:
            if self.moon_double_move_first_piece is not None:
                # Другий хід - можна вибрати тільки Місяць
                if piece.type != PieceType.MOON:
                    game_print("🌙 Під час подвійного ходу можна вибрати тільки Місяць!")
                    return False
        
        supported_pieces = [
            PieceType.PAWN, PieceType.ROOK, PieceType.KNIGHT, 
            PieceType.BISHOP, PieceType.QUEEN, PieceType.KING,
            PieceType.SHIELD, PieceType.FURY, PieceType.TEMPLE,
            PieceType.ARISTOCRAT, PieceType.RIDER, PieceType.MOON,
            PieceType.LIGHTNING, PieceType.TRIUMPHATOR, PieceType.EYE
        ]
        
        if piece.type not in supported_pieces:
            return False
        
        self.selected_piece = (row, col)
        self.possible_moves, self.possible_attacks, self.possible_teleports = self.move_calculator.get_possible_moves(piece, row, col)
        
        # Додаткова логіка для Храму - показуємо можливості священного обміну
        if piece.type == PieceType.TEMPLE:
            temple_id = self.get_temple_id(row, col)
            if temple_id and not self.temple_swap_used.get(temple_id, False):
                # Храм ще не використав свій обмін
                self.temple_swap_selection = {
                    'temple_pos': (row, col),
                    'temple_id': temple_id
                }
                # Можливі обміни будуть відображені як спеціальні крапки в графічному інтерфейсі
        
        return True

    def _handle_paralysis_landing_selection(self, row: int, col: int) -> bool:
        """Обробляє вибір місця приземлення після ініціації паралічу"""
        if not self.paralysis_selection:
            return False
        
        triumphator_pos = self.paralysis_selection['triumphator_pos']
        target_pos = self.paralysis_selection['target_pos']
        
        landing_squares = self.move_calculator.get_paralysis_landing_squares(
            target_pos[0], target_pos[1]
        )
        
        if (row, col) not in landing_squares:
            self.paralysis_selection = None
            return False
        
        self._execute_paralysis(triumphator_pos, target_pos, (row, col))
        
        self.paralysis_selection = None
        self.clear_selection()
        
        self.switch_player()
        return True

    def make_move(self, to_row: int, to_col: int) -> bool:
        if self.selected_piece is None:
            return False
        
        from_row, from_col = self.selected_piece
        piece = self.board.get_piece_at(from_row, from_col)
        
        if piece and piece.type == PieceType.TRIUMPHATOR:
            if (to_row, to_col) in self.possible_attacks:
                self.paralysis_selection = {
                    'triumphator_pos': (from_row, from_col),
                    'target_pos': (to_row, to_col)
                }
                self.clear_selection()
                return True
        
        # КРИТИЧНО: Обробка обміну Аристократа - він НЕ ВБИВАЄ, а МІНЯЄТЬСЯ!
        if piece and piece.type == PieceType.ARISTOCRAT:
            # Перевірка обміну з ворожою фігурою (червона крапка)
            if (to_row, to_col) in self.possible_attacks:
                target_piece = self.board.get_piece_at(to_row, to_col)
                if target_piece and not target_piece.is_empty():
                    # Це обмін з ворожою фігурою - НЕ атака!
                    return self.execute_aristocrat_exchange(from_row, from_col, to_row, to_col)
            
            # Перевірка обміну з союзною фігурою (сіра крапка)
            for move_item in self.possible_moves:
                if isinstance(move_item, tuple) and len(move_item) == 3 and move_item[2] == 'swap':
                    move_row, move_col, _ = move_item
                    if (to_row, to_col) == (move_row, move_col):
                        # Це обмін з союзною фігурою - НЕ звичайний хід!
                        return self.execute_aristocrat_exchange(from_row, from_col, to_row, to_col)
            
            # Якщо дійшли сюди - це звичайний хід Аристократа на пусту клітинку
        
        # Обробка священного обміну Храму
        if piece and piece.type == PieceType.TEMPLE:
            # Перевіряємо, чи це спроба обміну з союзною фігурою
            if self.temple_swap_selection:
                swap_targets = self.get_temple_swap_targets(from_row, from_col)
                if (to_row, to_col) in swap_targets:
                    # Виконуємо священний обмін
                    result = self.execute_temple_swap(from_row, from_col, to_row, to_col)
                    self.temple_swap_selection = None
                    return result
        
        # Перевірка звичайних ходів (враховуючи формат з 'swap', але виключаючи обміни)
        is_regular_move = False
        is_swap_move = False
        
        for move_item in self.possible_moves:
            if isinstance(move_item, tuple):
                if len(move_item) == 3 and move_item[2] == 'swap':
                    move_row, move_col, _ = move_item
                    if (to_row, to_col) == (move_row, move_col):
                        is_swap_move = True
                        break
                elif len(move_item) >= 2:
                    move_row, move_col = move_item[0], move_item[1]
                    if (to_row, to_col) == (move_row, move_col):
                        is_regular_move = True
                        break
            else:
                if (to_row, to_col) == move_item:
                    is_regular_move = True
                    break
        
        # Якщо це обмін (swap) і не Аристократ - щось не так
        if is_swap_move and piece.type != PieceType.ARISTOCRAT:
            return False
        
        # Для Аристократа обміни вже оброблені вище, тут тільки звичайні ходи
        is_attack = (to_row, to_col) in self.possible_attacks
        is_teleport = (to_row, to_col) in self.possible_teleports
        
        if not (is_regular_move or is_attack or is_teleport):
            return False
        
        if is_teleport:
            return self._handle_teleport_move(from_row, from_col, to_row, to_col)
        else:
            # КРИТИЧНО: is_attack тут означає РЕАЛЬНУ атаку, а не обмін!
            # Для Аристократа обміни вже оброблені вище
            return self._handle_regular_move(from_row, from_col, to_row, to_col, is_attack)

    def _execute_paralysis(self, triumphator_pos: Tuple[int, int], 
                           target_pos: Tuple[int, int], 
                           landing_pos: Tuple[int, int]):
        """Виконує параліч цілі"""
        triumphator = self.board.get_piece_at(triumphator_pos[0], triumphator_pos[1])
        target = self.board.get_piece_at(target_pos[0], target_pos[1])
        
        if not triumphator or not target:
            return
        
        duration = self._calculate_paralysis_duration(triumphator)
        
        self.board.move_piece(triumphator_pos[0], triumphator_pos[1], 
                              landing_pos[0], landing_pos[1])
        
        self.paralyzed_pieces[target_pos] = {
            'duration': duration,
            'piece_id': target.id,
            'color': target.color
        }
        
        triumphator_color = get_color_name_ua(triumphator.color)
        target_color = get_color_name_ua(target.color)
        target_name = PIECE_NAMES_UA.get(target.type, "невідома")
        
        # Показуємо фактичну кількість пропущених ходів (duration - 1, бо duration включає поточний хід)
        turns_to_skip = duration - 1
        game_print(f"⚡ {triumphator_color} Тріумфатор паралізував {target_color} {target_name} на {turns_to_skip} ходів!")

    def _calculate_paralysis_duration(self, triumphator: Piece) -> int:
        """
        Розраховує тривалість паралічу на основі стану Очей.
        Duration = кількість ходів, які гравець ПРОПУСТИТЬ.
        Для пропуску 1 ходу потрібно duration = 2 (бо таймер зменшується на початку кожного ходу цього гравця).
        """
        linked_eyes = self.triumphant_eye_links.get(triumphator.id, [])
        
        living_eyes = 0
        for eye_id in linked_eyes:
            if self.board.find_piece_position(eye_id):
                living_eyes += 1
        
        # Якщо є живі очі: пропуск 1 ходу (duration=2)
        # Якщо немає очей: пропуск 2 ходів (duration=3)
        return 2 if living_eyes > 0 else 3

    def _handle_teleport_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Обробляє телепортацію між туманностями"""
        piece = self.board.get_piece_at(from_row, from_col)
        
        from_nebula = get_nebula_name(from_row, from_col)
        to_nebula = get_nebula_name(to_row, to_col)
        
        penalty = 1 if from_row != to_row else 0
        
        piece_name = PIECE_NAMES_UA.get(piece.type, "невідома")
        piece_color = get_color_name_ua_with_gender(piece.color, piece.type)
        from_nebula_ua = get_nebula_emoji_name(from_nebula) if from_nebula else "невідома"
        to_nebula_ua = get_nebula_emoji_name(to_nebula) if to_nebula else "невідома"
        
        move_log = f"💫 {piece_color} {piece_name} id({piece.id}) з {from_nebula_ua} туманності ({from_row}, {from_col}) телепортується на {to_nebula_ua} туманність ({to_row}, {to_col})"
        penalty_text = " (з штрафом часу -1)" if penalty else " (без штрафу часу)"
        move_log += penalty_text
        
        game_print(move_log)
        
        self.board.move_piece(from_row, from_col, to_row, to_col)
        self.teleport_piece(piece.id, (from_row, from_col), (to_row, to_col))
        
        move = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            is_nebula_teleport=True,
            teleport_penalty=penalty
        )
        self.move_history.append(move)
        
        self.switch_player()
        return True

    def _handle_regular_move(self, from_row: int, from_col: int, to_row: int, to_col: int, is_attack: bool) -> bool:
        """Обробляє звичайні ходи та атаки"""
        piece = self.board.get_piece_at(from_row, from_col)
        captured_piece = self.board.get_piece_at(to_row, to_col) if is_attack else None
        
        is_pawn_back_move = False
        if piece.type == PieceType.PAWN and not is_attack:
            direction = -1 if piece.color == PieceColor.WHITE else 1
            if (to_row - from_row) == -direction:
                is_pawn_back_move = True
                self.move_calculator.register_pawn_back_move(piece.id)
        
        move = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            is_capture=is_attack,
            is_pawn_back_move=is_pawn_back_move
        )
        self.move_history.append(move)
        
        if captured_piece and not captured_piece.is_empty():
            if captured_piece.color == PieceColor.WHITE:
                self.captured_pieces["white"].append(captured_piece)
            else:
                self.captured_pieces["black"].append(captured_piece)
                
            if captured_piece.type == PieceType.PAWN:
                self.update_resurrection_availability(captured_piece.color)
        
        # ВИПРАВЛЕНО: Імпорт логування на початку функції
        
        piece_name = PIECE_NAMES_UA.get(piece.type, "невідома")
        piece_color = get_color_name_ua_with_gender(piece.color, piece.type)
        from_chess = coordinates_to_chess_notation(from_row, from_col)
        to_chess = coordinates_to_chess_notation(to_row, to_col)
        
        from_is_nebula = is_nebula_coordinates(from_row, from_col)
        to_is_nebula = is_nebula_coordinates(to_row, to_col)
        
        if from_is_nebula:
            from_nebula_name = get_nebula_name(from_row, from_col)
            from_nebula_emoji = get_nebula_emoji_name(from_nebula_name) if from_nebula_name else ""
            from_desc = f"{from_nebula_emoji} туманності ({from_row}, {from_col})"
        else:
            from_desc = f"{from_chess} ({from_row}, {from_col})"
        
        timer_reset = ""
        if from_is_nebula and not to_is_nebula:
            timer_reset = ", таймер обнуляється"
        
        if is_attack and captured_piece:
            captured_name = PIECE_NAMES_UA.get(captured_piece.type, "невідома")
            captured_color = get_color_name_ua_with_gender(captured_piece.color, captured_piece.type)
            
            if to_is_nebula:
                nebula_name = get_nebula_name(to_row, to_col)
                nebula_emoji_name = get_nebula_emoji_name(nebula_name) if nebula_name else ""
                to_desc = f"{nebula_emoji_name} туманність 🌀({to_row}, {to_col}), присвоєно час 5"
            else:
                to_desc = f"{to_chess} ({to_row}, {to_col})"
            
            game_print(f"⚔️ {piece_color} {piece_name} id({piece.id}) з {from_desc} атакує {captured_color} {captured_name} id({captured_piece.id}) на {to_desc}{timer_reset}")
        else:
            if to_is_nebula:
                nebula_name = get_nebula_name(to_row, to_col)
                nebula_emoji_name = get_nebula_emoji_name(nebula_name) if nebula_name else ""
                to_desc = f"{nebula_emoji_name} туманність 🌀({to_row}, {to_col}), присвоєно час 5"
            else:
                to_desc = f"{to_chess} ({to_row}, {to_col})"
                
            game_print(f"🏃 {piece_color} {piece_name} id({piece.id}) ходить з {from_desc} на {to_desc}{timer_reset}")

        # ═══ МЕХАНІКА ЕЛЕКТРИЧНОГО ПАРАЛІЧУ БЛИСКАВКИ ═══
        # Якщо захоплюється Блискавка, атакуюча фігура паралізується на 1 хід
        # Виняток: Король не паралізується
        # Особливе правило: Блискавка, що вбиває іншу блискавку, теж знищується
        lightning_paralysis_applied = False
        lightning_mutual_destruction = False
        if is_attack and captured_piece and captured_piece.type == PieceType.LIGHTNING:
            # Якщо атакуюча фігура - Король, нічого не відбувається
            if piece.type == PieceType.KING:
                pass
            # Якщо атакуюча фігура - теж Блискавка, обидві знищуються
            elif piece.type == PieceType.LIGHTNING:
                lightning_mutual_destruction = True
                attacker_name = PIECE_NAMES_UA.get(piece.type, "фігура")
                attacker_color = get_color_name_ua_with_gender(piece.color, piece.type)
                target_color = get_color_name_ua_with_gender(captured_piece.color, captured_piece.type)
                game_print(f"⚡💥💥 {attacker_color} блискавка id({piece.id}) атакує {target_color} блискавку id({captured_piece.id})!")
                game_print(f"   💀💀 Обидві блискавки знищуються в електричному вибуху!")
                # Логування взаємного знищення блискавок
            # Інші фігури паралізуються
            else:
                lightning_paralysis_applied = True
                attacker_name = PIECE_NAMES_UA.get(piece.type, "фігура")
                attacker_color = get_color_name_ua_with_gender(piece.color, piece.type)
                game_print(f"⚡💥 {attacker_color} {attacker_name} id({piece.id}) захопив Блискавку і отримав електричний шок!")
                to_notation = coordinates_to_chess_notation(to_row, to_col)
                game_print(f"   ⛔ {attacker_name} на {to_notation} ({to_row}, {to_col}) паралізована на 1 хід!")
                
                # Логування паралізації від Блискавки
        self.board.move_piece(from_row, from_col, to_row, to_col)
        
        # Взаємне знищення блискавок - видаляємо атакуючу блискавку після ходу
        if lightning_mutual_destruction:
            destroyed_piece = self.board.get_piece_at(to_row, to_col)
            if destroyed_piece:
                self.board.clear_square(to_row, to_col)
                game_print(f"   ⚡ {get_color_name_ua_with_gender(destroyed_piece.color, destroyed_piece.type)} блискавка id({destroyed_piece.id}) на {coordinates_to_chess_notation(to_row, to_col)} знищена")
        
        # Застосовуємо параліч ПІСЛЯ переміщення фігури на нову позицію
        if lightning_paralysis_applied:
            self.paralyzed_pieces[(to_row, to_col)] = {
                'duration': 2,  # duration=2 для пропуску 1 повного ходу
                'piece_id': piece.id,
                'color': piece.color
            }
        
        self._process_move_side_effects(piece, from_row, from_col, to_row, to_col, captured_piece)
        
        enhancement_triggered = self._check_eye_enhancement(piece, to_row)

        if enhancement_triggered:
            return True

        # Обробка подвійного ходу Місяця - КРИТИЧНО: перший хід ОБОВ'ЯЗКОВО має бути Місяцем!
        color_key = "white" if piece.color == PieceColor.WHITE else "black"
        
        # Перевіряємо, чи активовано подвійний хід для цього кольору
        if self.moon_double_move_active[color_key]:
            if piece.type == PieceType.MOON:
                # Хід Місяцем - дозволяємо подвійний хід
                if self.moon_double_move_first_piece is None:
                    # Перший хід Місяцем
                    self.moon_double_move_first_piece = piece.id
                    moon_notation = coordinates_to_chess_notation(to_row, to_col)
                    from_notation = coordinates_to_chess_notation(from_row, from_col)
                    game_print(f"🌙 Перший хід подвійного ходу Місяцем id({piece.id}) {from_notation} на {moon_notation} ({to_row}, {to_col}). Зробіть другий хід будь-яким Місяцем!")
                    color_name_ua = "білий" if piece.color == PieceColor.WHITE else "чорний"
                    move_text = f"{color_name_ua} місяць id({piece.id}) ходить з {from_notation} на {moon_notation}\nПерший хід подвійного ходу Місяцем id({piece.id}) {from_notation} на {moon_notation}"
                    # Додаємо PGN хід
                    from логування import pgn_moves
                    pgn_move = f"{from_notation}xD{moon_notation}"
                    pgn_moves.append(pgn_move)
                    
                    # НЕ перемикаємо гравця
                    self.clear_selection()
                    return True
                else:
                    # Другий хід Місяцем - завершуємо подвійний хід
                    moon_notation = coordinates_to_chess_notation(to_row, to_col)
                    from_notation = coordinates_to_chess_notation(from_row, from_col)
                    game_print(f"🌙 Другий хід подвійного ходу Місяцем id({piece.id}) {from_notation} на {moon_notation} ({to_row}, {to_col}). Подвійний хід завершено!")
                    
                    # НЕ вимикаємо moon_double_move_active - він залишається назавжди!
                    self.moon_double_move_first_piece = None
                    self.switch_player()
                    return True
            else:
                # Якщо вже зроблено перший хід місяцем, другий ОБОВ'ЯЗКОВО має бути місяцем!
                if self.moon_double_move_first_piece is not None:
                    game_print("❌ Помилка: Після ходу місяцем другий хід має бути також місяцем!")
                    return False
                
                # Якщо перший хід ще не зроблено - пропускаємо подвійний хід на цей раз
                self.moon_double_move_first_piece = None  # Скидаємо стан
                # moon_double_move_active залишається True - можливість НЕ втрачається!
                self.switch_player()
                return True
        
        # Стара логіка для сумісності (якщо не Місяць або немає активного подвійного ходу)
        if piece.type == PieceType.MOON and self.moon_double_move is None:
            self.moon_double_move = (to_row, to_col)
        else:
            self.switch_player()
        
        return True

    def _process_move_side_effects(self, piece: Piece, from_row: int, from_col: int, to_row: int, to_col: int, captured_piece: Optional[Piece]):
        """Обробляє побічні ефекти ходу"""
        
        from_is_nebula = is_nebula_coordinates(from_row, from_col)
        to_is_nebula = is_nebula_coordinates(to_row, to_col)

        if from_is_nebula and not to_is_nebula:
            if piece.id in self.nebula_piece_timers:
                del self.nebula_piece_timers[piece.id]
        elif not from_is_nebula and to_is_nebula:
            self.enter_nebula(piece.id, (to_row, to_col))

        if captured_piece and captured_piece.type in [PieceType.SHIELD, PieceType.FURY]:
            self._handle_capture_of_shield_or_fury(captured_piece, to_row, to_col)
        
        # Система полювання на душі Всадником
        if captured_piece and piece.type == PieceType.RIDER:
            self._handle_soul_hunting(piece, captured_piece)
        
        # Система активації подвійного ходу Місяця при знищенні обох Аристократів
        if captured_piece and captured_piece.type == PieceType.ARISTOCRAT:
            self._check_aristocrat_death_for_moon_activation(captured_piece)

    def _check_eye_enhancement(self, piece: Piece, to_row: int) -> bool:
        """Перевіряє та запускає механіку посилення Ока."""
        if piece.type != PieceType.EYE:
            return False

        color_key = "white" if piece.color == PieceColor.WHITE else "black"
        final_rank = 1 if piece.color == PieceColor.WHITE else 20

        if to_row == final_rank and not self.eye_enhancement_used[color_key]:
            player_eyes = self.board.get_all_pieces_of_type(PieceType.EYE, piece.color)
            
            if len(player_eyes) >= 4:
                game_print("👁️ Око досягло фінальної лінії! Оберіть 3 з 4 Очей для посилення.")
                self.eye_enhancement_selection = {
                    "player": piece.color,
                    "selectable_eyes": [pos for pos in player_eyes],
                    "selected_pos": []
                }
                return True
            elif player_eyes:
                game_print("👁️ Око досягло фінальної лінії! Всі ваші Ока посилено автоматично.")
                for r, c in player_eyes:
                    eye_to_enhance = self.get_piece_at(r, c)
                    if eye_to_enhance:
                        eye_to_enhance.is_enhanced = True
                        chess_pos = coordinates_to_chess_notation(r, c)
                        game_print(f"👁️ Око ID {eye_to_enhance.id} на {chess_pos} ({r}, {c}) було посилено автоматично!")
                self.eye_enhancement_used[color_key] = True
                self.switch_player()
                return True
        
        return False

    def _handle_capture_of_shield_or_fury(self, captured_piece: Piece, row: int, col: int):
        """Обробляє захоплення щита або фурії з прив'язкою"""
        
        if captured_piece.type == PieceType.SHIELD:
            self._log_unprotected_pieces(row, col, captured_piece.color)

        self.move_calculator.update_board(self.board)
        additional_casualties = self.move_calculator.handle_shield_fury_bond(captured_piece, row, col)
        
        for casualty_pos in additional_casualties:
            casualty_piece = self.board.get_piece_at(casualty_pos[0], casualty_pos[1])
            if casualty_piece:
                casualty_color = get_color_name_ua(casualty_piece.color)
                casualty_name = PIECE_NAMES_UA.get(casualty_piece.type)
                casualty_chess = coordinates_to_chess_notation(casualty_pos[0], casualty_pos[1])
                game_print(f"💥 Додаткова втрата: {casualty_color} {casualty_name} id({casualty_piece.id}) знищено на {casualty_chess} ({casualty_pos[0]}, {casualty_pos[1]})!")
                
                # Логування додаткової втрати до партії
                # КРИТИЧНО: Фізично видаляємо фігуру з дошки!
                self.board.clear_square(casualty_pos[0], casualty_pos[1])
                
                # Додаємо до списку захоплених фігур
                if casualty_piece.color == PieceColor.WHITE:
                    self.captured_pieces["white"].append(casualty_piece)
                else:
                    self.captured_pieces["black"].append(casualty_piece)

    def _handle_soul_hunting(self, rider: Piece, captured_piece: Piece):
        """Обробляє полювання Всадника на душі (кінь, офіцер, всадник)"""
        target_types = [PieceType.KNIGHT, PieceType.BISHOP, PieceType.RIDER]
        
        if captured_piece.type not in target_types:
            return
        
        color_key = "white" if rider.color == PieceColor.WHITE else "black"
        
        # Вполювати душу
        if not self.hunted_souls[color_key][captured_piece.type]:
            self.hunted_souls[color_key][captured_piece.type] = True
            
            captured_name = PIECE_NAMES_UA.get(captured_piece.type, "невідома")
            rider_name = PIECE_NAMES_UA.get(rider.type, "всадник")
            rider_color = get_color_name_ua(rider.color)
            
            game_print(f"👻 {rider_color} {rider_name} id({rider.id}) вполював душу {captured_name}!")
            
            # Оновлюємо куточки для воскресіння
            self._update_soul_corners()
    
    def _update_soul_corners(self):
        """Оновлює куточки для воскресіння на стартових позиціях"""
        self.soul_corners = []
        
        # Стартові позиції для білих та чорних
        start_positions = {
            PieceType.KNIGHT: {"white": [(20, 6), (20, 13)], "black": [(1, 6), (1, 13)]},
            PieceType.BISHOP: {"white": [(20, 8), (20, 11)], "black": [(1, 8), (1, 11)]},
            PieceType.RIDER: {"white": [(20, 3), (20, 16)], "black": [(1, 3), (1, 16)]}
        }
        
        for color in ["white", "black"]:
            player_color = PieceColor.WHITE if color == "white" else PieceColor.BLACK
            
            # Перевірка: чи використав гравець вже воскресіння
            if self.performed_resurrection[color]:
                continue
            
            # Перевірка: чи є живі всадники у гравця
            rider_count = len(self.board.get_all_pieces_of_type(PieceType.RIDER, player_color))
            if rider_count == 0:
                continue
            
            # Перевіряємо кожен тип вполюваної душі
            for piece_type in [PieceType.KNIGHT, PieceType.BISHOP, PieceType.RIDER]:
                if not self.hunted_souls[color][piece_type]:
                    continue
                
                # Перевіряємо умови для зеленого куточка
                is_green = False
                if piece_type == PieceType.RIDER:
                    # Для всадника: рівно 1 всадник залишився
                    is_green = rider_count == 1
                else:
                    # Для коня та офіцера: втрачена ОДНА фігура (залишилася 1 з 2-х)
                    piece_count = len(self.board.get_all_pieces_of_type(piece_type, player_color))
                    is_green = piece_count == 1  # Було 2, залишилася 1 - можна воскрешати
                
                # Додаємо куточки на стартові позиції
                for row, col in start_positions[piece_type][color]:
                    # Перевіряємо, чи клітинка вільна
                    if self.board.is_square_empty(row, col):
                        self.soul_corners.append((row, col, piece_type, is_green, player_color))

    def _log_unprotected_pieces(self, shield_row: int, shield_col: int, shield_color: PieceColor):
        """Логує фігури, що втратили захист після знищення щита"""
        shield_zone = self.move_calculator._get_shield_zone(shield_row, shield_col)
        unprotected_pieces = []
        
        for r, c in shield_zone:
            if (r, c) == (shield_row, shield_col): 
                continue
            
            piece_on_cell = self.board.get_piece_at(r, c)
            if piece_on_cell and not piece_on_cell.is_empty() and piece_on_cell.color == shield_color:
                pos = self.board.find_piece_position(piece_on_cell.id)
                if pos:
                    chess_notation = coordinates_to_chess_notation(pos[0], pos[1])
                    piece_name = PIECE_NAMES_UA.get(piece_on_cell.type)
                    unprotected_pieces.append(f"{piece_name} id({piece_on_cell.id}) на {chess_notation} ({pos[0]}, {pos[1]})")
        
        if unprotected_pieces:
            pieces_str = ", ".join(unprotected_pieces)
            game_print(f"🛡️ Фігури, що втратили захист: {pieces_str}")
            # Логування втрати захисту
    def switch_player(self):
        """Перемикає гравця на наступний хід"""
        self.clear_selection()
        self.moon_double_move = None
        
        self.recently_resurrected_pieces.clear()
        
        # Оновлюємо куточки для воскресіння душ
        self._update_soul_corners()
        
        # Оновлюємо таймери паралічу ПЕРЕД перемиканням гравця
        # Таймери зменшуються для поточного гравця (того, хто щойно походив)
        self._update_paralysis_timers()
        
        # Завершуємо логування поточного ходу
        from логування import finish_current_turn
        finish_current_turn()
        
        self.current_player = PieceColor.BLACK if self.current_player == PieceColor.WHITE else PieceColor.WHITE
        self._update_paralysis_timers()
        
        # Збільшуємо номер ходу після кожного ходу (не тільки білих)
        self.turn_number += 1
        
        if self.move_calculator:
            self.move_calculator.update_board(self.board)
            
            attacker_pos = self.move_calculator._is_king_in_check(self.current_player)
            if attacker_pos:
                attacker_piece = self.board.get_piece_at(attacker_pos[0], attacker_pos[1])
                king_pos = self.move_calculator._find_king(self.current_player)
                king_piece = self.board.get_piece_at(king_pos[0], king_pos[1])

                if attacker_piece and king_piece:
                    attacker_name = PIECE_NAMES_UA.get(attacker_piece.type, "невідома")
                    attacker_color = get_color_name_ua_with_gender(attacker_piece.color, attacker_piece.type)
                    attacker_notation = coordinates_to_chess_notation(attacker_pos[0], attacker_pos[1])
                    king_notation = coordinates_to_chess_notation(king_pos[0], king_pos[1])

                    game_print(f"♚️ Шах! {attacker_color} {attacker_name} id({attacker_piece.id}) з {attacker_notation} ({attacker_pos[0]}, {attacker_pos[1]}) ставить шах королю id({king_piece.id}) на {king_notation} ({king_pos[0]}, {king_pos[1]})")
                    
                    # Логування шаху
            # Перевірка мату
            if self.move_calculator.is_checkmate(self.current_player):
                self.game_over = True
                self.winner = 'white' if self.current_player == PieceColor.BLACK else 'black'
                self.game_over_reason = 'checkmate'
                winner_name = 'Білі' if self.winner == 'white' else 'Чорні'
                loser_name = 'Чорні' if self.winner == 'white' else 'Білі'
                game_print(f"")
                game_print(f"{'='*60}")
                game_print(f"👑 МАТ! {winner_name} перемогли!")
                game_print(f"♔ {loser_name} король у безвихідній ситуації!")
                game_print(f"{'='*60}")
                game_print(f"")
                
                # Логування завершення гри
                end_game(f"закінчена гра - МАТ, переміг {winner_name}")
                return
            
            # Перевірка пату
            if self.move_calculator.is_stalemate(self.current_player):
                self.game_over = True
                self.winner = 'draw'
                self.game_over_reason = 'stalemate'
                current_name = 'Білі' if self.current_player == PieceColor.WHITE else 'Чорні'
                game_print(f"")
                game_print(f"{'='*60}")
                game_print(f"🤝 ПАТ! Нічия!")
                game_print(f"♔ {current_name} король не під шахом, але немає легальних ходів!")
                game_print(f"{'='*60}")
                game_print(f"")
                
                # Логування пату
                end_game("закінчена гра - ПАТ, нічия")
                return

        self._update_nebula_timers()

        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        game_print(f"\033[1m{current_time}, Хід {'Білого' if self.current_player == PieceColor.WHITE else 'Чорного'} Гравця - номер ходу {self.turn_number}:\033[0m")

        for piece_id, timer_info in self.nebula_piece_timers.items():
            pos = self.board.find_piece_position(piece_id)
            if pos:
                piece = self.board.get_piece_at(pos[0], pos[1])
                if piece and piece.color == self.current_player:
                    nebula_name = get_nebula_name(pos[0], pos[1])
                    if nebula_name:
                        emoji = get_nebula_emoji_name(nebula_name)
                        color_name = get_color_name_ua_with_gender(piece.color, piece.type)
                        piece_name = PIECE_NAMES_UA.get(piece.type, "невідома")
                        game_print(f"🌀 {color_name} {piece_name} id({piece.id}) що стоїть на {emoji} Туманності ({pos[0]}, {pos[1]}) має таймер - {timer_info['timer']}.")

    def _update_paralysis_timers(self):
        """
        Оновлює таймери паралічу для ПОТОЧНОГО гравця (того, хто щойно ПОХОДИВ).
        Викликається ПЕРЕД switch_player(), тому current_player - це гравець, який завершує хід.
        Зменшуємо duration для фігур current_player після того, як він походив.
        
        Логіка: 
        - Білий паралізує чорного (duration=2)
        - Чорний ходить іншою фігурою → duration зменшується до 1 (король все ще паралізований)
        - Білий ходить
        - Чорний ходить іншою фігурою → duration зменшується до 0 (параліч знято)
        """
        pieces_to_unparalyze = []
        # Ітеруємо по копії, оскільки словник може змінюватися
        for pos, paralysis_info in list(self.paralyzed_pieces.items()):
            # Зменшуємо лічильник тільки для фігур поточного гравця (який щойно походив)
            if paralysis_info.get('color') == self.current_player:
                paralysis_info['duration'] -= 1
                if paralysis_info['duration'] < 1:
                    pieces_to_unparalyze.append(pos)
        
        for pos in pieces_to_unparalyze:
            if pos in self.paralyzed_pieces:
                del self.paralyzed_pieces[pos]
                game_print(f"✅ Фігура на {coordinates_to_chess_notation(pos[0], pos[1])} більше не паралізована")
    
    def _update_nebula_timers(self):
        """Оновлює таймери фігур у туманностях"""
        pieces_to_remove = []
        for piece_id, timer_info in list(self.nebula_piece_timers.items()):
            piece = self.board.get_piece_by_id(piece_id)
            if not piece or piece.color != self.current_player:
                continue
                
            timer_info["timer"] -= 1
            
            if timer_info["timer"] <= 0:
                piece_pos = self.board.find_piece_position(piece_id)
                
                nebula_name_str = ""
                nebula_coords_str = ""
                if piece_pos:
                    neb_name_raw = get_nebula_name(piece_pos[0], piece_pos[1])
                    if neb_name_raw:
                        nebula_name_str = get_nebula_emoji_name(neb_name_raw)
                    nebula_coords_str = f"({piece_pos[0]}, {piece_pos[1]})"

                piece_name = PIECE_NAMES_UA.get(piece.type, "невідома")
                message = f"💀 фігура {piece_name} id({piece.id}) знищена в туманості {nebula_name_str} {nebula_coords_str} за браком часу."
                game_print(message)

                if piece_pos:
                    self.board.clear_square(piece_pos[0], piece_pos[1])
                pieces_to_remove.append(piece_id)

        for piece_id in pieces_to_remove:
            if piece_id in self.nebula_piece_timers:
                del self.nebula_piece_timers[piece_id]
    
    def add_paralysis(self, row: int, col: int, duration: int):
        """Додає параліч на фігуру"""
        self.paralyzed_pieces[(row, col)] = duration
    
    def get_current_player_name(self) -> str:
        return "Білі" if self.current_player == PieceColor.WHITE else "Чорні"
    
    def clear_selection(self):
        self.selected_piece = None
        self.possible_moves = []
        self.possible_attacks = []
        self.possible_teleports = []
        # temple_swap_selection НЕ очищається тут - він зберігається до використання обміну
    
    def is_piece_selected(self) -> bool:
        return self.selected_piece is not None
    
    def get_selected_position(self) -> Optional[Tuple[int, int]]:
        return self.selected_piece
    
    def reset_game(self):
        """Скидає гру до початкового стану"""
        self.board = Board()
        self.current_player = PieceColor.WHITE
        self.turn_number = 1
        self.selected_piece = None
        self.possible_moves = []
        self.possible_attacks = []
        self.possible_teleports = []
        self.move_history = []
        self.captured_pieces = {"white": [], "black": []}
        self.paralyzed_pieces = {}
        self.paralysis_mode_data = None
        self.moon_double_move = None
        self.nebula_blocked = {
            "top_left": True,
            "top_right": True, 
            "bottom_left": True,
            "bottom_right": True
        }
        self.resurrected_pawns = {"white": 0, "black": 0}
        self.resurrection_available = {"white": 0, "black": 0}
        self.nebulas_activated = {"white": False, "black": False}
        self.nebula_piece_timers = {}
        self.recently_resurrected_pieces = set()
        
        self.eye_enhancement_used = {"white": False, "black": False}
        self.triumphant_eye_links = {}
        self.eye_enhancement_selection = None
        
        # Скидання системи Храму
        self.temple_swap_used = {
            "black_left": False,
            "black_right": False,
            "white_left": False,
            "white_right": False
        }
        self.temple_swap_selection = None
        
        # Скидання системи Місяця
        self.moon_double_move_active = {"white": False, "black": False}
        self.moon_double_move_used = {"white": False, "black": False}
        self.moon_double_move_first_piece = None
        
        # Скидання системи Всадника
        self.hunted_souls = {
            "white": {PieceType.KNIGHT: False, PieceType.BISHOP: False, PieceType.RIDER: False},
            "black": {PieceType.KNIGHT: False, PieceType.BISHOP: False, PieceType.RIDER: False}
        }
        self.performed_resurrection = {"white": False, "black": False}
        self.soul_corners = []
        
        self._setup_initial_position()
        
        self.move_calculator.update_board(self.board)
        self.move_calculator.set_game_state(self)
        self.move_calculator.reset_pawn_back_moves()
    
    def save_game(self, filename: str):
        pass
    
    def load_game(self, filename: str):
        pass
    
    def undo_move(self):
        if not self.move_history:
            return False
        return False
    
    def get_game_info(self) -> dict:
        return {
            "current_player": self.get_current_player_name(),
            "move_count": len(self.move_history),
            "captured_white": len(self.captured_pieces["white"]),
            "captured_black": len(self.captured_pieces["black"]),
            "paralyzed_count": len(self.paralyzed_pieces)
        }
    
    def update_resurrection_availability(self, captured_color: PieceColor):
        """Оновлює доступність воскресіння для гравця"""
        color_name = "white" if captured_color == PieceColor.WHITE else "black"
        if self.resurrected_pawns[color_name] < 2:
            self.resurrection_available[color_name] += 1

    def can_resurrect_pawn(self, color: PieceColor) -> bool:
        """Перевіряє чи може гравець воскресити пішака"""
        color_name = "white" if color == PieceColor.WHITE else "black"
        return (
            self.resurrection_available[color_name] > 0 and 
            self.resurrected_pawns[color_name] < 2
        )

    def resurrect_pawn(self, row: int, col: int, color: PieceColor) -> bool:
        """Воскрешає пішака на вказану позицію"""
        color_name_ua = "білий" if color == PieceColor.WHITE else "чорний"
        
        if not self.can_resurrect_pawn(color):
            return False

        color_key = "white" if color == PieceColor.WHITE else "black"
        self.resurrection_available[color_key] -= 1

        if not self.board.is_square_empty(row, col):
            self.resurrection_available[color_key] += 1
            return False
        
        if color == PieceColor.WHITE:
            base_id = 1050
            piece_id = base_id + self.resurrected_pawns["white"]
        else:
            base_id = 2050
            piece_id = base_id + self.resurrected_pawns["black"]
        
        pawn = Piece(PieceType.PAWN, color, piece_id)
        self.board.set_piece(row, col, pawn)
        
        self.recently_resurrected_pieces.add(piece_id)
        self.resurrected_pawns[color_key] += 1
        
        is_free_action = self.resurrected_pawns[color_key] == 1
        
        chess_position = coordinates_to_chess_notation(row, col)
        attempt = self.resurrected_pawns[color_key]
        
        if attempt == 1:
            action_detail = "(хід не затрачено, заборона руху поточної фігури)"
        else:
            action_detail = "(хід затрачено)"
            
        game_print(f"⚰️ Гравець {color_name_ua} воскресив пішака ID {piece_id} позицією {chess_position} ({int(row)}, {int(col)}) спроб {attempt}/2 {action_detail}")
        # Воскресіння виводиться ОДРАЗУ в поточний хід
        if self.resurrected_pawns[color_key] == 2:
            self.activate_nebulas(color)
            return False
        
        return is_free_action
    
    def resurrect_soul(self, row: int, col: int, piece_type: PieceType, color: PieceColor):
        """Воскрешає душу (кінь, офіцер, всадник) через Всадника"""
        color_key = "white" if color == PieceColor.WHITE else "black"
        color_name_ua = "білий" if color == PieceColor.WHITE else "чорний"
        piece_name = PIECE_NAMES_UA.get(piece_type, "невідома")
        
        # Генеруємо ID для воскрешеної фігури
        if color == PieceColor.WHITE:
            base_id = {
                PieceType.KNIGHT: 1100,
                PieceType.BISHOP: 1110,
                PieceType.RIDER: 1120
            }[piece_type]
        else:
            base_id = {
                PieceType.KNIGHT: 2100,
                PieceType.BISHOP: 2110,
                PieceType.RIDER: 2120
            }[piece_type]
        
        # Рахуємо, скільки вже воскрешено цього типу
        existing_count = len([p for p in self.board.get_all_pieces_of_type(piece_type, color)])
        piece_id = base_id + existing_count
        
        # Створюємо фігуру
        resurrected_piece = Piece(piece_type, color, piece_id)
        self.board.set_piece(row, col, resurrected_piece)
        
        # Позначаємо, що воскресіння використано
        self.performed_resurrection[color_key] = True
        
        # Оновлюємо куточки (всі зникнуть)
        self._update_soul_corners()
        
        chess_position = coordinates_to_chess_notation(row, col)
        game_print(f"👻 Гравець {color_name_ua} воскресив {piece_name} ID {piece_id} на позиції {chess_position} ({row}, {col}) через Всадника!")
        # Переключаємо хід
        self.switch_player()

    def activate_nebulas(self, color: PieceColor):
        """Активує туманності для гравця після другого воскресіння"""
        color_name = "білий" if color == PieceColor.WHITE else "чорний"
        color_key = "white" if color == PieceColor.WHITE else "black"
        self.nebulas_activated[color_key] = True
        
        if color == PieceColor.WHITE:
            self.nebula_blocked["bottom_left"] = False
            self.nebula_blocked["bottom_right"] = False
            game_print(f"🌀 Туманності активовані для гравця {color_name} - відкрито (21,0) та (21,19)")
        else:
            self.nebula_blocked["top_left"] = False
            self.nebula_blocked["top_right"] = False
            game_print(f"🌀 Туманності активовані для гравця {color_name} - відкрито (0,0) та (0,19)")
    def enter_nebula(self, piece_id: int, nebula_pos: Tuple[int, int]):
        self.nebula_piece_timers[piece_id] = {
            "timer": 5,
            "nebula_pos": nebula_pos
        }
    def teleport_piece(self, piece_id: int, from_nebula: Tuple[int, int], to_nebula: Tuple[int, int]) -> bool:
        if piece_id not in self.nebula_piece_timers:
            return False
        
        penalty = 0
        if from_nebula[0] != to_nebula[0]:
            penalty = 1
        
        timer_info = self.nebula_piece_timers[piece_id]
        timer_info["timer"] -= penalty
        timer_info["nebula_pos"] = to_nebula
        
        # ВИДАЛЕНО дублювання: логування телепортації тепер у _handle_teleport_move()

        if timer_info["timer"] <= 0:
            piece_pos = self.board.find_piece_position(piece_id)
            piece = self.board.get_piece_at(piece_pos[0], piece_pos[1]) if piece_pos else None
            
            from_nebula_name = get_nebula_emoji_name(get_nebula_name(from_nebula[0], from_nebula[1]))
            to_nebula_name = get_nebula_emoji_name(get_nebula_name(to_nebula[0], to_nebula[1]))

            if piece_pos:
                self.board.clear_square(piece_pos[0], piece_pos[1])

            if piece:
                piece_name = PIECE_NAMES_UA.get(piece.type, "невідома")
                message = f"💀💫 фігура {piece_name} id({piece.id}) загинула в телепортації з туманності {from_nebula_name} ({from_nebula[0]}, {from_nebula[1]}) в {to_nebula_name} ({to_nebula[0]}, {to_nebula[1]}), знищена в телепортації за штрафом."
                game_print(message)
            else:
                message = f"💀💫 фігура з id({piece_id}) знищена в телепортації за штрафом."
                game_print(message)

            if piece_id in self.nebula_piece_timers:
                del self.nebula_piece_timers[piece_id]
            return False
        
        return True

    def _can_aristocrat_exchange_with(self, from_row: int, from_col: int, to_row: int, to_col: int) -> Tuple[bool, str]:
        """
        Перевіряє можливість обміну Аристократа з фігурою на цільовій позиції.
        Використовує перевірки з MoveCalculator._can_aristocrat_exchange
        """
        aristocrat = self.board.get_piece_at(from_row, from_col)
        target_piece = self.board.get_piece_at(to_row, to_col)
        
        if not aristocrat or aristocrat.type != PieceType.ARISTOCRAT:
            return False, "Не Аристократ"
        
        if not target_piece or target_piece.is_empty():
            return False, "Цільова клітинка порожня"
        
        # Використовуємо метод з MoveCalculator для валідації
        is_aristocrat_in_nebula = is_nebula_coordinates(from_row, from_col)
        can_exchange = self.move_calculator._can_aristocrat_exchange(
            aristocrat, from_row, from_col, to_row, to_col, is_aristocrat_in_nebula
        )
        
        if not can_exchange:
            return False, "Обмін заборонений правилами"
        
        return True, "OK"
    
    def _check_aristocrat_death_for_moon_activation(self, captured_aristocrat: Piece):
        """
        Перевіряє, чи знищено обох Аристократів одного кольору.
        Якщо так - активує подвійний хід для Місяців цього кольору (назавжди).
        """
        color_key = "white" if captured_aristocrat.color == PieceColor.WHITE else "black"
        
        # Перевіряємо, чи вже активовано подвійний хід (щоб не виводити повідомлення двічі)
        if self.moon_double_move_active[color_key]:
            return
        
        # Підраховуємо живих Аристократів цього кольору
        alive_aristocrats = self.board.get_all_pieces_of_type(PieceType.ARISTOCRAT, captured_aristocrat.color)
        
        # Якщо обидва Аристократи знищені - активуємо подвійний хід назавжди
        if len(alive_aristocrats) == 0:
            self.moon_double_move_active[color_key] = True
            color_name = "білих" if captured_aristocrat.color == PieceColor.WHITE else "чорних"
            game_print(f"🌙 АКТИВОВАНО: Подвійний хід Місяців для {color_name}! Обидва Аристократи знищені.")
            game_print(f"   📢 Кожен хід {color_name} може бути подвійним (місяць → місяць) до кінця гри!")
            
            # Логування активації подвійного ходу
    def execute_aristocrat_exchange(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """
        Виконує дипломатичний обмін Аристократа з іншою фігурою.
        Обидві фігури миттєво міняються місцями.
        """
        aristocrat = self.board.get_piece_at(from_row, from_col)
        target_piece = self.board.get_piece_at(to_row, to_col)
        
        if not aristocrat or not target_piece:
            return False
        
        # Перевірка можливості обміну
        can_exchange, reason = self._can_aristocrat_exchange_with(from_row, from_col, to_row, to_col)
        
        if not can_exchange:
            game_print(f"⚠️ Обмін неможливий: {reason}")
            return False
        
        # КРИТИЧНО: Справжній обмін місцями - зберігаємо обидві фігури!
        # 1. Зберігаємо копії обох фігур
        aristocrat_copy = Piece(aristocrat.type, aristocrat.color, aristocrat.id)
        target_copy = Piece(target_piece.type, target_piece.color, target_piece.id)
        
        # Зберігаємо стан is_enhanced якщо є
        if hasattr(aristocrat, 'is_enhanced'):
            aristocrat_copy.is_enhanced = aristocrat.is_enhanced
        if hasattr(target_piece, 'is_enhanced'):
            target_copy.is_enhanced = target_piece.is_enhanced
        
        # 2. Очищаємо обидві клітинки
        self.board.clear_square(from_row, from_col)
        self.board.clear_square(to_row, to_col)
        
        # 3. Ставимо фігури на нові місця (ОБМІН!)
        self.board.set_piece(from_row, from_col, target_copy)      # Ціль на місце Аристократа
        self.board.set_piece(to_row, to_col, aristocrat_copy)      # Аристократ на місце цілі
        
        # ═══ МЕХАНІКА ЕЛЕКТРИЧНОГО ПАРАЛІЧУ ДЛЯ АРИСТОКРАТА ═══
        # Перевіряємо параліч ПЕРЕД логуванням, але ПІСЛЯ обміну
        lightning_shock = (target_piece.type == PieceType.LIGHTNING and 
                          target_piece.color != aristocrat.color)
        
        # Логування
        aristocrat_color = get_color_name_ua_with_gender(aristocrat.color, aristocrat.type)
        target_color = get_color_name_ua_with_gender(target_piece.color, target_piece.type)
        aristocrat_name = PIECE_NAMES_UA.get(aristocrat.type, "аристократ")
        target_name = PIECE_NAMES_UA.get(target_piece.type, "фігура")
        
        from_notation = coordinates_to_chess_notation(from_row, from_col)
        to_notation = coordinates_to_chess_notation(to_row, to_col)
        
        game_print(f"🔄 {aristocrat_color} {aristocrat_name} id({aristocrat.id}) обмінявся з {target_color} {target_name} id({target_piece.id})")
        game_print(f"   {from_notation} ({from_row}, {from_col}) ⇄ {to_notation} ({to_row}, {to_col})")
        
        # Застосовуємо параліч ПІСЛЯ обміну та логування
        if lightning_shock:
            # Паралізуємо Аристократа (який тепер на to_row, to_col)
            self.paralyzed_pieces[(to_row, to_col)] = {
                'duration': 2,  # duration=2 для пропуску 1 повного ходу
                'piece_id': aristocrat.id,
                'color': aristocrat.color
            }
            game_print(f"⚡💥 {aristocrat_color} {aristocrat_name} id({aristocrat.id}) отримав електричний шок від Блискавки!")
            game_print(f"   ⛔ {aristocrat_name} на {to_notation} ({to_row}, {to_col}) паралізований на 1 хід!")
            
            # Логування паралізації
        # Очищення вибору та передача ходу
        self.clear_selection()
        self.switch_player()
        
        return True

    def get_temple_id(self, row: int, col: int) -> Optional[str]:
        """
        Визначає ID храму за ID фігури (не за позицією, бо храм може рухатися).
        Повертає: 'black_left', 'black_right', 'white_left', 'white_right' або None
        """
        temple = self.board.get_piece_at(row, col)
        if not temple or temple.type != PieceType.TEMPLE:
            return None
        
        # Зіставлення ID фігури з ключем храму
        temple_id_map = {
            2000: "black_left",    # Чорний лівий храм (початкова позиція A20)
            2017: "black_right",   # Чорний правий храм (початкова позиція R20)
            1030: "white_left",    # Білий лівий храм (початкова позиція A1)
            1047: "white_right"    # Білий правий храм (початкова позиція R1)
        }
        
        return temple_id_map.get(temple.id)
    
    def get_temple_swap_targets(self, temple_row: int, temple_col: int) -> List[Tuple[int, int]]:
        """
        Повертає список позицій союзних фігур, з якими храм може обмінятися.
        """
        temple = self.board.get_piece_at(temple_row, temple_col)
        if not temple or temple.type != PieceType.TEMPLE:
            return []
        
        temple_id = self.get_temple_id(temple_row, temple_col)
        if not temple_id or self.temple_swap_used.get(temple_id, False):
            return []
        
        swap_targets = []
        all_pieces = self.board.get_all_pieces_of_color(temple.color)
        
        for target_row, target_col in all_pieces:
            # Пропускаємо сам храм
            if (target_row, target_col) == (temple_row, temple_col):
                continue
            
            # Перевіряємо можливість обміну
            can_swap, _ = self.can_temple_swap_with(temple_row, temple_col, target_row, target_col)
            if can_swap:
                swap_targets.append((target_row, target_col))
        
        return swap_targets
    
    def can_temple_swap_with(self, temple_row: int, temple_col: int, 
                             target_row: int, target_col: int) -> Tuple[bool, str]:
        """
        Перевіряє, чи може храм обмінятися з фігурою на target позиції.
        Повертає: (можливість обміну, причина відмови)
        """
        temple = self.board.get_piece_at(temple_row, temple_col)
        target = self.board.get_piece_at(target_row, target_col)
        
        if not temple or not target:
            return False, "Немає фігур"
        
        if temple.color != target.color:
            return False, "Неможливо обмінятися з ворожою фігурою"
        
        # Перевірка використання обміну
        temple_id = self.get_temple_id(temple_row, temple_col)
        if not temple_id:
            return False, "Храм не на стартовій позиції"
        
        if self.temple_swap_used.get(temple_id, False):
            return False, "Храм вже використав свій обмін"
        
        temple_in_nebula = is_nebula_coordinates(temple_row, temple_col)
        target_in_nebula = is_nebula_coordinates(target_row, target_col)
        
        # Перевірка обмежень для Короля
        if target.type == PieceType.KING:
            # Король не може опинитися в туманності
            if temple_in_nebula:
                return False, "Король не може опинитися в туманності"
            
            # Король не може опинитися в союзній імунній зоні
            in_ally_zone, _ = self.move_calculator._is_in_any_shield_zone(temple_row, temple_col, temple.color)
            if in_ally_zone:
                return False, "Король не може опинитися в союзній імунній зоні"
        
        # Перевірка обмежень для Щита
        if target.type == PieceType.SHIELD:
            # Щит не може опинитися в туманності
            if temple_in_nebula:
                return False, "Щит не може опинитися в туманності"
            
            # Храм в зоні дії союзного Щита не може мінятися з іншими Щитами
            # (щоб уникнути накладання захисту)
            temple_in_ally_shield, _ = self.move_calculator._is_in_any_shield_zone(temple_row, temple_col, temple.color)
            if temple_in_ally_shield:
                return False, "Храм в зоні дії Щита не може мінятися з іншими Щитами"
        
        # Перевірка обмежень для Фурії
        if target.type == PieceType.FURY:
            # Фурія не може опинитися в союзній імунній зоні
            in_ally_zone, _ = self.move_calculator._is_in_any_shield_zone(temple_row, temple_col, temple.color)
            if in_ally_zone:
                return False, "Фурія не може опинитися в союзній імунній зоні"
        
        # Перевірка обмежень для Храму (куди він піде)
        # Храм не може опинитися в ворожій імунній зоні
        enemy_color = PieceColor.BLACK if temple.color == PieceColor.WHITE else PieceColor.WHITE
        in_enemy_zone, _ = self.move_calculator._is_in_any_shield_zone(target_row, target_col, enemy_color)
        if in_enemy_zone:
            # Якщо ціль знаходиться в ворожій зоні і може там бути (Король, Око, Фурія, Аристократ)
            # але Храм туди не може, то обмін неможливий
            if target.type not in [PieceType.KING, PieceType.EYE, PieceType.FURY, PieceType.ARISTOCRAT]:
                return False, "Храм не може опинитися в ворожій імунній зоні"
            else:
                return False, "Храм не може обмінятися з фігурою в ворожій імунній зоні"
        
        return True, ""
    
    def execute_temple_swap(self, temple_row: int, temple_col: int, 
                           target_row: int, target_col: int) -> bool:
        """
        Виконує священний обмін Храму з союзною фігурою.
        Обидві фігури миттєво міняються місцями.
        """
        temple = self.board.get_piece_at(temple_row, temple_col)
        target = self.board.get_piece_at(target_row, target_col)
        
        if not temple or not target:
            return False
        
        # Перевірка можливості обміну
        can_swap, reason = self.can_temple_swap_with(temple_row, temple_col, target_row, target_col)
        
        if not can_swap:
            game_print(f"⚠️ Обмін неможливий: {reason}")
            return False
        
        # Отримуємо ID храму
        temple_id = self.get_temple_id(temple_row, temple_col)
        if not temple_id:
            return False
        
        # КРИТИЧНО: Справжній обмін місцями - зберігаємо обидві фігури!
        # 1. Зберігаємо копії обох фігур
        temple_copy = Piece(temple.type, temple.color, temple.id)
        target_copy = Piece(target.type, target.color, target.id)
        
        # Зберігаємо стан is_enhanced якщо є
        if hasattr(temple, 'is_enhanced'):
            temple_copy.is_enhanced = temple.is_enhanced
        if hasattr(target, 'is_enhanced'):
            target_copy.is_enhanced = target.is_enhanced
        
        # 2. Очищаємо обидві клітинки
        self.board.clear_square(temple_row, temple_col)
        self.board.clear_square(target_row, target_col)
        
        # 3. Ставимо фігури на нові місця (ОБМІН!)
        self.board.set_piece(temple_row, temple_col, target_copy)  # Ціль на місце Храму
        self.board.set_piece(target_row, target_col, temple_copy)  # Храм на місце цілі
        
        # Логування
        temple_color = get_color_name_ua_with_gender(temple.color, temple.type)
        target_color = get_color_name_ua_with_gender(target.color, target.type)
        temple_name = PIECE_NAMES_UA.get(temple.type, "храм")
        target_name = PIECE_NAMES_UA.get(target.type, "фігура")
        
        temple_notation = coordinates_to_chess_notation(temple_row, temple_col)
        target_notation = coordinates_to_chess_notation(target_row, target_col)
        
        game_print(f"⛪ {temple_color} {temple_name} id({temple.id}) здійснив священний обмін з {target_color} {target_name} id({target.id})")
        game_print(f"   {temple_notation} ({temple_row}, {temple_col}) ⇄ {target_notation} ({target_row}, {target_col})")
        
        # Позначаємо, що храм використав свій обмін
        self.temple_swap_used[temple_id] = True
        game_print(f"   ✝️ Храм id({temple.id}) на {temple_notation} ({temple_row}, {temple_col}) використав свій священний обмін (більше недоступний)")
        # Очищення вибору Храму та передача ходу
        self.temple_swap_selection = None  # Очищаємо стан вибору обміну
        self.clear_selection()
        self.switch_player()
        
        return True


