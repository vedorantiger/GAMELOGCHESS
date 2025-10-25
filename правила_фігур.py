from typing import List, Tuple, Optional, Set
from налаштування import (
    PieceType, PieceColor, BOARD_ROWS, BOARD_COLS, NEBULAS
)
from розташування_фігур import Piece, Move, is_valid_position
from логування import game_logger


def get_path_cells(from_row: int, from_col: int, to_row: int, to_col: int) -> List[Tuple[int, int]]:
    path = []
    row_direction = 0 if from_row == to_row else (1 if to_row > from_row else -1)
    col_direction = 0 if from_col == to_col else (1 if to_col > from_col else -1)
    
    current_row = from_row + row_direction
    current_col = from_col + col_direction
    
    while (current_row, current_col) != (to_row, to_col):
        if 1 <= current_row <= 20 and 1 <= current_col <= 18:
            path.append((current_row, current_col))
        current_row += row_direction
        current_col += col_direction
    
    return path


def get_knight_deltas() -> List[Tuple[int, int]]:
    return [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]


def is_in_shield_zone(row: int, col: int, shield_row: int, shield_col: int) -> bool:
    return abs(row - shield_row) <= 1 and abs(col - shield_col) <= 1


def is_in_nebula(row: int, col: int, nebulas) -> bool:
    for name, (neb_row, neb_col) in nebulas.items():
        if neb_row == row and neb_col == col:
            return True
    return False


class MoveCalculator:
    def __init__(self, board):
        self.board = board
        self.pawns_used_back_move = set()
        self.game_state = None  # Встановлюється через set_game_state
        self._shield_zones_cache = {}
        self._shield_positions_cache = {}
        self._cache_turn = -1
        self._moves_cache = {}  # Кеш для можливих ходів

    def update_board(self, board):
        self.board = board
        self._clear_cache()

    def set_game_state(self, game_state):
        self.game_state = game_state

    def register_pawn_back_move(self, pawn_id: int):
        self.pawns_used_back_move.add(pawn_id)

    def has_pawn_used_back_move(self, pawn_id: int) -> bool:
        return pawn_id in self.pawns_used_back_move

    def reset_pawn_back_moves(self):
        self.pawns_used_back_move.clear()

    def _clear_cache(self):
        self._shield_zones_cache.clear()
        self._shield_positions_cache.clear()
        self._cache_turn = -1
        self._moves_cache.clear()

    def get_possible_moves(self, piece: Piece, row: int, col: int, filter_legal: bool = True) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:
        # Кешування за позицією та станом дошки
        cache_key = (piece.id, row, col, self.board.position_hash, filter_legal)
        if cache_key in self._moves_cache:
            return self._moves_cache[cache_key]

        # КРИТИЧНО: Паралізовані фігури не можуть ходити!
        if self.game_state and (row, col) in self.game_state.paralyzed_pieces:
            result = [], [], []
            self._moves_cache[cache_key] = result
            return result

        if piece.is_empty():
            result = [], [], []
        else:
            move_methods = {
                PieceType.PAWN: self._get_pawn_moves,
                PieceType.ROOK: self._get_rook_moves,
                PieceType.KNIGHT: self._get_knight_moves,
                PieceType.BISHOP: self._get_bishop_moves,
                PieceType.QUEEN: self._get_queen_moves,
                PieceType.KING: self._get_king_moves,
                PieceType.FURY: self._get_fury_moves,
                PieceType.SHIELD: self._get_shield_moves,
                PieceType.TEMPLE: self._get_temple_moves,
                PieceType.ARISTOCRAT: self._get_aristocrat_moves,
                PieceType.RIDER: self._get_rider_moves,
                PieceType.LIGHTNING: self._get_lightning_moves,
                PieceType.MOON: self._get_moon_moves,
                PieceType.TRIUMPHATOR: self._get_triumphator_moves,
                PieceType.EYE: self._get_eye_moves
            }
            
            moves, attacks = [], []
            teleports = []
            
            # Отримуємо стандартні ходи для фігури
            method = move_methods.get(piece.type)
            if method:
                moves, attacks = method(piece, row, col)

            # Якщо фігура в туманності, додаємо можливість телепортації
            if self._is_in_nebula(row, col):
                teleport_moves, _ = self._get_nebula_teleports(piece, row, col)
                teleports.extend(teleport_moves)

            if filter_legal:
                moves = self._filter_legal_moves(piece, row, col, moves)
                attacks = self._filter_legal_moves(piece, row, col, attacks)
                teleports = self._filter_legal_moves(piece, row, col, teleports)
            
            result = moves, attacks, teleports

        self._moves_cache[cache_key] = result
        return result

    def _get_nebula_teleports(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Отримує можливі телепортації між туманностями"""
        teleports = []
        
        if piece.type == PieceType.KING:
            return [], []
        
        if not self.game_state:
            return [], []
        
        for name, (neb_row, neb_col) in NEBULAS.items():
            if neb_row == row and neb_col == col:
                continue
            
            color_name = "white" if piece.color == PieceColor.WHITE else "black"
            if (self.game_state.nebulas_activated.get(color_name, False) or 
                self.game_state.nebulas_activated.get("white" if piece.color == PieceColor.BLACK else "black", False)):
                if (not self.game_state.is_nebula_blocked(neb_row, neb_col) and 
                    self._is_empty(neb_row, neb_col) and 
                    self._is_valid_square(neb_row, neb_col)):
                    teleports.append((neb_row, neb_col))
        
        return teleports, []

    def _is_valid_square(self, row: int, col: int) -> bool:
        if is_valid_position(row, col):
            return True
        
        for nebula_name, (neb_row, neb_col) in NEBULAS.items():
            if neb_row == row and neb_col == col:
                if self.game_state and not self.game_state.is_nebula_blocked(row, col):
                    return True
        
        return False

    def _is_empty(self, row: int, col: int) -> bool:
        if not self._is_valid_square(row, col):
            return False
        return self.board.is_square_empty(row, col)

    def _is_enemy(self, row: int, col: int, color: PieceColor) -> bool:
        if not self._is_valid_square(row, col):
            return False
        piece = self.board.get_piece_at(row, col)
        return piece is not None and not piece.is_empty() and piece.color != color

    def _is_ally(self, row: int, col: int, color: PieceColor) -> bool:
        if not self._is_valid_square(row, col):
            return False
        piece = self.board.get_piece_at(row, col)
        return piece is not None and not piece.is_empty() and piece.color == color

    def _can_attack_target(self, attacker: Piece, target_row: int, target_col: int) -> bool:
        if not self._is_enemy(target_row, target_col, attacker.color):
            return False
        
        # Атакувати фігуру В ТУМАННОСТІ (ззовні): НЕМОЖЛИВО.
        if self._is_in_nebula(target_row, target_col):
            return False
        
        if self._is_protected_by_shield(target_row, target_col):
            if attacker.type in [PieceType.KING, PieceType.EYE, PieceType.FURY]:
                return True
            else:
                return False
        return True

    def _get_shield_positions(self, color: PieceColor) -> List[Tuple[int, int]]:
        cache_key = color
        if cache_key in self._shield_positions_cache:
            return self._shield_positions_cache[cache_key]
        shields = self.board.get_all_pieces_of_type(PieceType.SHIELD, color)
        self._shield_positions_cache[cache_key] = shields
        return shields

    def _get_shield_zone(self, shield_row: int, shield_col: int) -> Set[Tuple[int, int]]:
        cache_key = (shield_row, shield_col)
        if cache_key in self._shield_zones_cache:
            return self._shield_zones_cache[cache_key]
        zone = set()
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r = shield_row + dr
                c = shield_col + dc
                if self._is_valid_square(r, c):
                    zone.add((r, c))
        self._shield_zones_cache[cache_key] = zone
        return zone

    def _is_in_shield_zone(self, row: int, col: int, shield_row: int, shield_col: int) -> bool:
        return is_in_shield_zone(row, col, shield_row, shield_col)

    def _is_in_any_shield_zone(self, row: int, col: int, color: PieceColor) -> Tuple[bool, Optional[Tuple[int, int]]]:
        for shield_row, shield_col in self._get_shield_positions(color):
            if self._is_in_shield_zone(row, col, shield_row, shield_col):
                return True, (shield_row, shield_col)
        return False, None

    def _is_protected_by_shield(self, row: int, col: int) -> bool:
        if not self._is_valid_square(row, col):
            return False
        piece = self.board.get_piece_at(row, col)
        if not piece or piece.is_empty():
            return False
        in_zone, _ = self._is_in_any_shield_zone(row, col, piece.color)
        return in_zone

    def _shield_zones_overlap(self, shield1_row: int, shield1_col: int, shield2_row: int, shield2_col: int) -> bool:
        zone1 = self._get_shield_zone(shield1_row, shield1_col)
        zone2 = self._get_shield_zone(shield2_row, shield2_col)
        return bool(zone1 & zone2)

    def _is_nebula_position(self, row: int, col: int) -> bool:
        return self.board.is_nebula(row, col)

    def _shield_zone_contains_nebula(self, shield_row: int, shield_col: int) -> bool:
        zone = self._get_shield_zone(shield_row, shield_col)
        for zone_row, zone_col in zone:
            if self._is_nebula_position(zone_row, zone_col):
                return True
        return False

    def _can_shield_move_to(self, shield_row: int, shield_col: int, target_row: int, target_col: int) -> bool:
        if self._is_nebula_position(target_row, target_col):
            return False
        if self._shield_zone_contains_nebula(target_row, target_col):
            return False
        
        all_shields = self.board.get_all_pieces_of_type(PieceType.SHIELD, PieceColor.WHITE)
        all_shields.extend(self.board.get_all_pieces_of_type(PieceType.SHIELD, PieceColor.BLACK))
        
        for row, col in all_shields:
            if (row, col) != (shield_row, shield_col):
                if self._shield_zones_overlap(target_row, target_col, row, col):
                    return False
        return True

    def _can_shield_move_to_position(self, piece: Piece, target_row: int, target_col: int) -> bool:
        """
        Перевіряє, чи може щит переміститися на вказану позицію.
        Щит НЕ може притягнути в свою зону фігури, які не можуть там бути.
        Але якщо фігура ВЖЕ в зоні старого положення щита - це OK.
        """
        # Отримуємо стару та нову зони щита
        current_row, current_col = self.board.find_piece_position(piece.id) or (target_row, target_col)
        old_zone = self._get_shield_zone(current_row, current_col)
        new_zone = self._get_shield_zone(target_row, target_col)
        
        # Перевіряємо фігури в НОВІЙ зоні
        for zone_row, zone_col in new_zone:
            zone_piece = self.board.get_piece_at(zone_row, zone_col)
            if zone_piece and not zone_piece.is_empty():
                # Союзні Король/Фурія не можуть бути в зоні
                if zone_piece.color == piece.color and zone_piece.type in [PieceType.KING, PieceType.FURY]:
                    return False
                
                # Якщо ворожа фігура ВЖЕ в старій зоні - це OK (вона там була до ходу)
                if (zone_row, zone_col) in old_zone:
                    continue
                
                # Якщо ворожа фігура НЕ в старій зоні - перевіряємо, чи може вона бути в зоні щита
                # Король, Око, Фурія, Аристократ - можуть заходити в зону щита
                if zone_piece.color != piece.color and zone_piece.type not in [PieceType.KING, PieceType.EYE, PieceType.FURY, PieceType.ARISTOCRAT]:
                    return False  # ПРИТЯГУЄМО заборонену фігуру - ЗАБОРОНЕНО!
        
        return True

    def handle_shield_fury_bond(self, captured_piece: Piece, capture_row: int, capture_col: int) -> List[Tuple[int, int]]:
        additional_casualties = []
        if captured_piece.type == PieceType.SHIELD:
            fury_pairs = {2039: 2038, 2041: 2040, 1007: 1006, 1009: 1008}
            fury_id = fury_pairs.get(captured_piece.id)
            if fury_id:
                fury_pos = self.board.find_piece_position(fury_id)
                if fury_pos:
                    additional_casualties.append(fury_pos)
                    game_logger.info(f"Прив'язка: Щит знищено → Фурія також вмирає!")
        elif captured_piece.type == PieceType.FURY:
            shield_pairs = {2038: 2039, 2040: 2041, 1006: 1007, 1008: 1009}
            shield_id = shield_pairs.get(captured_piece.id)
            if shield_id:
                shield_pos = self.board.find_piece_position(shield_id)
                if shield_pos:
                    additional_casualties.append(shield_pos)
                    game_logger.info(f"Прив'язка: Фурія знищена → Щит також вмирає!")
        return additional_casualties

    def _can_enter_shield_zone(self, piece: Piece, target_row: int, target_col: int) -> bool:
        ally_in_zone, _ = self._is_in_any_shield_zone(target_row, target_col, piece.color)
        enemy_color = PieceColor.BLACK if piece.color == PieceColor.WHITE else PieceColor.WHITE
        enemy_in_zone, _ = self._is_in_any_shield_zone(target_row, target_col, enemy_color)
        
        if ally_in_zone:
            if piece.type == PieceType.KING or piece.type == PieceType.FURY:
                return False
            return True
        
        if enemy_in_zone:
            # Король, Око, Фурія та АРИСТОКРАТ можуть заходити в зону ворожого щита
            if piece.type in [PieceType.KING, PieceType.EYE, PieceType.FURY, PieceType.ARISTOCRAT]:
                return True
            return False
        
        return True

    def _is_path_blocked_by_enemy_shield(self, piece: Piece, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        if piece.type in [PieceType.KING, PieceType.EYE, PieceType.FURY]:
            return False
        
        enemy_color = PieceColor.BLACK if piece.color == PieceColor.WHITE else PieceColor.WHITE
        path_cells = self._get_path_cells(from_row, from_col, to_row, to_col)
        
        for path_row, path_col in path_cells:
            in_enemy_zone, _ = self._is_in_any_shield_zone(path_row, path_col, enemy_color)
            if in_enemy_zone:
                return True
        return False

    def _get_path_cells(self, from_row: int, from_col: int, to_row: int, to_col: int) -> List[Tuple[int, int]]:
        return get_path_cells(from_row, from_col, to_row, to_col)

    def _is_valid_move(self, piece: Piece, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        if not self._is_valid_square(to_row, to_col):
            return False
        if self._is_ally(to_row, to_col, piece.color):
            return False
        if self.game_state and self.game_state.is_nebula_blocked(to_row, to_col) and piece.type != PieceType.QUEEN:
            return False
        if not self._can_enter_shield_zone(piece, to_row, to_col):
            return False
        if piece.type == PieceType.SHIELD:
            if not self._can_shield_move_to(from_row, from_col, to_row, to_col):
                return False
        return True

    def _is_valid_attack(self, piece: Piece, target_row: int, target_col: int) -> bool:
        return self._can_attack_target(piece, target_row, target_col)

    def _is_in_nebula(self, row: int, col: int) -> bool:
        return is_in_nebula(row, col, NEBULAS)

    def _get_nebula_name_at(self, row: int, col: int) -> Optional[str]:
        for name, (neb_row, neb_col) in NEBULAS.items():
            if neb_row == row and neb_col == col:
                return name
        return None

    def _get_pawn_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        direction = -1 if piece.color == PieceColor.WHITE else 1
        
        new_row = row + direction
        if self._is_valid_square(new_row, col) and self._is_empty(new_row, col):
            if self._is_valid_move(piece, row, col, new_row, col):
                moves.append((new_row, col))
                
                # Початкові ряди: 19 для білих, 2 для чорних
                is_starting_position = (piece.color == PieceColor.WHITE and row == 19) or (piece.color == PieceColor.BLACK and row == 2)
                if is_starting_position:
                    double_row = row + 2 * direction
                    if self._is_valid_square(double_row, col) and self._is_empty(double_row, col):
                        if self._is_valid_move(piece, row, col, double_row, col):
                            moves.append((double_row, col))
        
        if piece.id not in self.pawns_used_back_move:
            back_row = row - direction
            if self._is_valid_square(back_row, col) and self._is_empty(back_row, col):
                if self._is_valid_move(piece, row, col, back_row, col):
                    moves.append((back_row, col))
        
        for dc in [-1, 1]:
            attack_col = col + dc
            if self._is_valid_square(new_row, attack_col) and self._is_valid_attack(piece, new_row, attack_col):
                attacks.append((new_row, attack_col))
        
        return moves, attacks

    def _get_rook_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            for i in range(1, max(BOARD_ROWS, BOARD_COLS)):
                new_row = row + dr * i
                new_col = col + dc * i
                
                if not self._is_valid_square(new_row, new_col):
                    break
                
                if self._is_path_blocked_by_enemy_shield(piece, row, col, new_row, new_col):
                    break
                
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))
                    break
                else:
                    break
        
        return moves, attacks

    def _get_knight_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        knight_moves = get_knight_deltas()
        
        for dr, dc in knight_moves:
            new_row = row + dr
            new_col = col + dc
            
            if self._is_valid_square(new_row, new_col):
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))
        
        return moves, attacks

    def _get_bishop_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            for i in range(1, max(BOARD_ROWS, BOARD_COLS)):
                new_row = row + dr * i
                new_col = col + dc * i
                
                if not self._is_valid_square(new_row, new_col):
                    break
                
                if self._is_path_blocked_by_enemy_shield(piece, row, col, new_row, new_col):
                    break
                
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))
                    break
                else:
                    break
        
        return moves, attacks

    def _get_queen_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        rook_moves, rook_attacks = self._get_rook_moves(piece, row, col)
        bishop_moves, bishop_attacks = self._get_bishop_moves(piece, row, col)
        return rook_moves + bishop_moves, rook_attacks + bishop_attacks

    def _get_king_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        king_moves = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1)
        ]
        
        for dr, dc in king_moves:
            new_row = row + dr
            new_col = col + dc
            
            if self._is_in_nebula(new_row, new_col):
                continue

            if self._is_valid_square(new_row, new_col):
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))
        
        return moves, attacks

    def _get_fury_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        
        attack_directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1)
        ]
        
        for dr, dc in attack_directions:
            new_row = row + dr
            new_col = col + dc
            if self._is_valid_square(new_row, new_col):
                if self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))
        
        for distance in [1, 2, 3]:
            for dc in [-1, 1]:
                new_row = row
                new_col = col + dc * distance
                if self._is_in_nebula(new_row, new_col):
                    continue
                if self._is_valid_square(new_row, new_col):
                    path_clear = True
                    for i in range(1, distance + 1):
                        check_col = col + dc * i
                        if not self._is_empty(row, check_col):
                            path_clear = False
                            break
                    if path_clear and self._is_empty(new_row, new_col):
                        if self._is_valid_move(piece, row, col, new_row, new_col):
                            moves.append((new_row, new_col))
        
        for distance in [1, 2]:
            for dr in [-1, 1]:
                new_row = row + dr * distance
                new_col = col
                if self._is_in_nebula(new_row, new_col):
                    continue
                if self._is_valid_square(new_row, new_col):
                    path_clear = True
                    for i in range(1, distance + 1):
                        check_row = row + dr * i
                        if not self._is_empty(check_row, col):
                            path_clear = False
                            break
                    if path_clear and self._is_empty(new_row, new_col):
                        if self._is_valid_move(piece, row, col, new_row, new_col):
                            moves.append((new_row, new_col))
        
        return moves, attacks

    def _get_shield_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []
        shield_moves = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1)
        ]
        
        for dr, dc in shield_moves:
            new_row = row + dr
            new_col = col + dc
            if (self._is_valid_square(new_row, new_col) and
                self._is_empty(new_row, new_col) and
                self._is_valid_move(piece, row, col, new_row, new_col) and
                self._can_shield_move_to_position(piece, new_row, new_col)):
                moves.append((new_row, new_col))
        
        return moves, attacks

    def _get_temple_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Храм:
        1. Звичайні ходи на 1 клітинку ортогонально (як король, але тільки прямо)
        2. Стрибки:
           - Вертикально: 2-3 клітинки
           - Горизонтально: 2 клітинки
           - Може перестрибувати максимум 1 ворожу фігуру
        3. Священний обмін: один раз за гру може обмінятися з союзною фігурою
           (обробляється окремо через спеціальний маркер)
        """
        moves = []
        attacks = []
        
        # ═══ ЧАСТИНА 1: ЗВИЧАЙНІ ХОДИ (1 клітинка ортогонально) ═══
        king_directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1)  # Тільки ортогонально
        ]
        
        for dr, dc in king_directions:
            new_row = row + dr
            new_col = col + dc
            
            if not self._is_valid_square(new_row, new_col):
                continue
            
            # Храм не може входити в ворожі імунні зони
            if not self._can_enter_shield_zone(piece, new_row, new_col):
                continue
            
            target_piece = self.board.get_piece_at(new_row, new_col)
            if not target_piece or target_piece.is_empty():
                moves.append((new_row, new_col))
            elif target_piece.color != piece.color:
                if self._can_attack_target(piece, new_row, new_col):
                    attacks.append((new_row, new_col))
        
        # ═══ ЧАСТИНА 2: СТРИБКИ ═══
        jump_directions = [
            (-3, 0), (3, 0),   # Вертикаль 3 клітинки
            (-2, 0), (2, 0),   # Вертикаль 2 клітинки
            (0, -2), (0, 2)    # Горизонталь 2 клітинки
        ]
        
        for dr, dc in jump_directions:
            new_row = row + dr
            new_col = col + dc
            
            if not self._is_valid_square(new_row, new_col):
                continue
            
            # Перевірка шляху (максимум 1 ворог)
            enemies_on_path = 0
            path_blocked = False
            steps = max(abs(dr), abs(dc))
            
            for i in range(1, steps):
                path_row = row + (1 if dr > 0 else -1 if dr < 0 else 0) * i
                path_col = col + (1 if dc > 0 else -1 if dc < 0 else 0) * i
                
                # Перевірка імунітету на шляху
                if not self._can_enter_shield_zone(piece, path_row, path_col):
                    path_blocked = True
                    break
                
                path_piece = self.board.get_piece_at(path_row, path_col)
                if path_piece and not path_piece.is_empty():
                    if path_piece.color != piece.color:
                        enemies_on_path += 1
                        if enemies_on_path > 1:
                            path_blocked = True
                            break
                    else:
                        # Союзна фігура блокує шлях
                        path_blocked = True
                        break
            
            if path_blocked:
                continue
            
            # Перевірка цільової клітинки
            if not self._can_enter_shield_zone(piece, new_row, new_col):
                continue
            
            target_piece = self.board.get_piece_at(new_row, new_col)
            if not target_piece or target_piece.is_empty():
                moves.append((new_row, new_col))
            elif target_piece.color != piece.color:
                if self._can_attack_target(piece, new_row, new_col):
                    attacks.append((new_row, new_col))
        
        return moves, attacks

    def _get_aristocrat_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Аристократ:
        1. Ортогональні стрибки на 2 клітинки (вертикаль/горизонталь)
        2. Діагональні ходи на 1-3 клітинки
        3. Повертає (moves, enemy_exchanges + ally_exchanges)
           - attacks = ворожі обміни (червоні крапки)
           - moves включає союзні обміни (сірі крапки через спеціальне позначення)
        
        Обмеження для обміну:
        - НЕ може обмінюватися з Оком
        - Спеціальні перевірки для Щита, Короля, Фурії
        - Перевірка зон щитів та туманностей
        """
        moves = []
        enemy_exchanges = []  # Червоні крапки - обмін з ворожими фігурами
        
        # Поточна позиція Аристократа
        current_pos = (row, col)
        is_aristocrat_in_nebula = self._is_in_nebula(row, col)
        
        # === ЧАСТИНА 1: Ортогональні стрибки на 2 клітинки ===
        orthogonal_jumps = [
            (-2, 0), (2, 0), (0, -2), (0, 2)
        ]
        
        for dr, dc in orthogonal_jumps:
            new_row = row + dr
            new_col = col + dc
            
            if not self._is_valid_square(new_row, new_col):
                continue
            
            # Вільна клітинка - звичайний хід
            if self._is_empty(new_row, new_col):
                if self._is_valid_move(piece, row, col, new_row, new_col):
                    moves.append((new_row, new_col))
            else:
                # Зайнята - перевірка на можливість обміну
                if self._can_aristocrat_exchange(piece, row, col, new_row, new_col, is_aristocrat_in_nebula):
                    target_piece = self.board.get_piece_at(new_row, new_col)
                    if target_piece and target_piece.color != piece.color:
                        # Ворожа фігура - червона крапка
                        enemy_exchanges.append((new_row, new_col))
                    else:
                        # Союзна фігура - додаємо як спеціальний хід (сіра крапка)
                        moves.append((new_row, new_col, 'swap'))  # Помічаємо як обмін
        
        # === ЧАСТИНА 2: Діагональні ходи на 1-3 клітинки ===
        diagonal_directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in diagonal_directions:
            for distance in range(1, 4):  # 1-3 клітинки
                new_row = row + dr * distance
                new_col = col + dc * distance
                
                if not self._is_valid_square(new_row, new_col):
                    break
                
                # Перевірка шляху (без перестрибування)
                path_cells = self._get_path_cells(row, col, new_row, new_col)
                if any(not self._is_empty(r, c) for r, c in path_cells):
                    break
                
                # Вільна клітинка - звичайний хід
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                else:
                    # Зайнята - перевірка на можливість обміну
                    if self._can_aristocrat_exchange(piece, row, col, new_row, new_col, is_aristocrat_in_nebula):
                        target_piece = self.board.get_piece_at(new_row, new_col)
                        if target_piece and target_piece.color != piece.color:
                            # Ворожа фігура - червона крапка
                            enemy_exchanges.append((new_row, new_col))
                        else:
                            # Союзна фігура - додаємо як спеціальний хід (сіра крапка)
                            moves.append((new_row, new_col, 'swap'))  # Помічаємо як обмін
                    break  # Зупиняємо промінь
        
        # Повертаємо ворожі обміни як "атаки" (червоні крапки)
        # Союзні обміни вже в moves з міткою 'swap'
        return moves, enemy_exchanges
    
    def _can_aristocrat_exchange(self, aristocrat: Piece, from_row: int, from_col: int, 
                                  to_row: int, to_col: int, is_aristocrat_in_nebula: bool) -> bool:
        """
        Перевіряє, чи може Аристократ обмінятися з фігурою на вказаній позиції.
        Враховує всі спеціальні правила та обмеження.
        """
        target_piece = self.board.get_piece_at(to_row, to_col)
        
        if not target_piece or target_piece.is_empty():
            return False
        
        # === ЗАБОРОНА 1: НЕ може обмінюватися з Оком ===
        if target_piece.type == PieceType.EYE:
            return False
        
        # Перевірки позицій
        is_target_in_nebula = self._is_in_nebula(to_row, to_col)
        
        # Перевірка зон щитів на обох позиціях
        aristocrat_in_ally_shield, _ = self._is_in_any_shield_zone(from_row, from_col, aristocrat.color)
        aristocrat_in_enemy_shield, _ = self._is_in_any_shield_zone(from_row, from_col, 
            PieceColor.BLACK if aristocrat.color == PieceColor.WHITE else PieceColor.WHITE)
        
        target_in_ally_shield, _ = self._is_in_any_shield_zone(to_row, to_col, target_piece.color)
        target_in_enemy_shield, _ = self._is_in_any_shield_zone(to_row, to_col,
            PieceColor.BLACK if target_piece.color == PieceColor.WHITE else PieceColor.WHITE)
        
        # === ПЕРЕВІРКА 2: ЩИТИ ===
        if target_piece.type == PieceType.SHIELD:
            # Обмін зі СОЮЗНИМ Щитом
            if target_piece.color == aristocrat.color:
                # Щит не може опинитися в туманності
                if is_aristocrat_in_nebula:
                    return False
                # Щит не може опинитися в зоні іншого союзного щита
                if aristocrat_in_ally_shield:
                    return False
                
                # КРИТИЧНА ПЕРЕВІРКА: Щит переміститься на місце Аристократа
                # Перевіряємо зону навколо НОВОЇ позиції щита (місце Аристократа)
                # ПРАВИЛО: Союзний Щит НЕ може створювати зону навколо союзних Короля/Фурії
                # (але ворожі Король/Фурія МОЖУТЬ заходити в зону союзного Щита!)
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = from_row + dr, from_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        if (check_row, check_col) == (to_row, to_col):
                            continue  # Пропускаємо позицію самого Щита
                        
                        check_piece = self.board.get_piece_at(check_row, check_col)
                        if check_piece and not check_piece.is_empty():
                            # ТІЛЬКИ союзні Король/Фурія не можуть бути в зоні союзного Щита
                            if check_piece.color == aristocrat.color:  # Та ж команда
                                if check_piece.type in [PieceType.KING, PieceType.FURY]:
                                    return False  # Заборонено!
            else:
                # Обмін з ВОРОЖИМ Щитом
                # Ворожий Щит не може опинитися поряд з Фурією або союзними фігурами Аристократа
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = from_row + dr, from_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        if (check_row, check_col) == (to_row, to_col):
                            continue
                        
                        check_piece = self.board.get_piece_at(check_row, check_col)
                        if check_piece and not check_piece.is_empty():
                            # Ворожий Щит не може бути поряд з Фурією або союзними фігурами
                            if check_piece.type == PieceType.FURY:
                                return False
                            if check_piece.color == aristocrat.color:
                                return False
        
        # === ПЕРЕВІРКА 3: КОРОЛЬ ===
        if target_piece.type == PieceType.KING:
            # Король не може опинитися в туманності
            if is_aristocrat_in_nebula:
                return False
            # СОЮЗНИЙ Король не може опинитися в зоні СОЮЗНОГО щита
            # (ворожий Король МОЖЕ опинитися в зоні союзного щита Аристократа!)
            if target_piece.color == aristocrat.color and aristocrat_in_ally_shield:
                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 1: Король не може опинитися в зоні ІНШОГО союзного щита
            # Перевіряємо, чи на позиції Аристократа (куди переміститься Король) є зона союзного щита
            if target_piece.color == aristocrat.color:
                # Перевіряємо всі клітинки 3×3 навколо позиції Аристократа
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = from_row + dr, from_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        
                        shield = self.board.get_piece_at(check_row, check_col)
                        if shield and shield.type == PieceType.SHIELD:
                            # Якщо це союзний щит - Король не може туди потрапити!
                            if shield.color == target_piece.color:
                                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 2: Аристократ не може зайти на позицію Короля, якщо там зона союзного щита
            # Перевіряємо, чи на позиції Короля (куди переміститься Аристократ) є зона союзного щита КОРОЛЯ
            if target_piece.color != aristocrat.color:  # Ворожий Король
                # Перевіряємо всі клітинки 3×3 навколо позиції Короля
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = to_row + dr, to_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        if (check_row, check_col) == (from_row, from_col):
                            continue  # Пропускаємо позицію самого Аристократа
                        
                        shield = self.board.get_piece_at(check_row, check_col)
                        if shield and shield.type == PieceType.SHIELD:
                            # Якщо це союзний щит КОРОЛЯ - обмін заборонений!
                            if shield.color == target_piece.color:
                                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 3: ВОРОЖИЙ Аристократ в зоні щита не може обмінятися з Королем того ж кольору
            # Якщо Аристократ заходить в зону ворожого щита, він не може обмінятися з Королем цього кольору
            if target_piece.color != aristocrat.color:  # Ворожий Король
                # Перевіряємо, чи Аристократ в зоні щита того ж кольору, що і Король
                in_zone, _ = self._is_in_any_shield_zone(from_row, from_col, target_piece.color)
                if in_zone:
                    return False  # ВОРОЖИЙ Аристократ в зоні щита не може обмінятися з Королем!
        
        # === ПЕРЕВІРКА 4: ФУРІЯ ===
        if target_piece.type == PieceType.FURY:
            # СОЮЗНА Фурія не може опинитися в зоні СОЮЗНОГО щита
            # (ворожа Фурія МОЖЕ опинитися в зоні союзного щита Аристократа!)
            if target_piece.color == aristocrat.color and aristocrat_in_ally_shield:
                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 1: Фурія не може опинитися в зоні ІНШОГО союзного щита
            # Перевіряємо, чи на позиції Аристократа (куди переміститься Фурія) є зона союзного щита
            if target_piece.color == aristocrat.color:
                # Перевіряємо всі клітинки 3×3 навколо позиції Аристократа
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = from_row + dr, from_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        
                        shield = self.board.get_piece_at(check_row, check_col)
                        if shield and shield.type == PieceType.SHIELD:
                            # Якщо це союзний щит - Фурія не може туди потрапити!
                            if shield.color == target_piece.color:
                                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 2: Аристократ не може зайти на позицію Фурії, якщо там зона союзного щита
            # Перевіряємо, чи на позиції Фурії (куди переміститься Аристократ) є зона союзного щита ФУРІЇ
            if target_piece.color != aristocrat.color:  # Ворожа Фурія
                # Перевіряємо всі клітинки 3×3 навколо позиції Фурії
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        check_row, check_col = to_row + dr, to_col + dc
                        if not self._is_valid_square(check_row, check_col):
                            continue
                        if (check_row, check_col) == (from_row, from_col):
                            continue  # Пропускаємо позицію самого Аристократа
                        
                        shield = self.board.get_piece_at(check_row, check_col)
                        if shield and shield.type == PieceType.SHIELD:
                            # Якщо це союзний щит ФУРІЇ - обмін заборонений!
                            if shield.color == target_piece.color:
                                return False
            
            # КРИТИЧНА ПЕРЕВІРКА 3: ВОРОЖИЙ Аристократ в зоні щита не може обмінятися з Фурією того ж кольору
            # Якщо Аристократ заходить в зону ворожого щита, він не може обмінятися з Фурією цього кольору
            if target_piece.color != aristocrat.color:  # Ворожа Фурія
                # Перевіряємо, чи Аристократ в зоні щита того ж кольору, що і Фурія
                in_zone, _ = self._is_in_any_shield_zone(from_row, from_col, target_piece.color)
                if in_zone:
                    return False  # ВОРОЖИЙ Аристократ в зоні щита не може обмінятися з Фурією!
        
        # === ПЕРЕВІРКА 5: Аристократ в туманності ===
        if is_aristocrat_in_nebula:
            # Аристократ в туманності не може обмінятися зі Щитом або Королем
            if target_piece.type in [PieceType.SHIELD, PieceType.KING]:
                return False
        
        # === ПЕРЕВІРКА 6: Аристократ в зоні СОЮЗНОГО щита ===
        if aristocrat_in_ally_shield:
            # Не може обмінятися з СОЮЗНИМИ Королем або Фурією 
            # (бо вони не можуть бути в союзній зоні щита)
            # ВОРОЖІ Король/Фурія МОЖУТЬ заходити в зону союзного щита!
            if target_piece.color == aristocrat.color:
                if target_piece.type in [PieceType.KING, PieceType.FURY]:
                    return False
        
        # === ПЕРЕВІРКА 7: Загальна перевірка зон щитів ===
        # ТІЛЬКИ союзні фігури не можуть опинитися в союзній зоні щита
        # Ворожі фігури МОЖУТЬ заходити в зону союзного щита!
        if aristocrat_in_ally_shield and target_piece.color == aristocrat.color:
            # Союзна фігура не може опинитися в союзній зоні щита
            if target_piece.type in [PieceType.KING, PieceType.FURY]:
                return False
        
        # Аристократ не може опинитися в ворожій йому зоні щита
        # (але це стосується лише випадку, якщо Аристократ переходить на місце ворожої фігури)
        if target_in_enemy_shield:
            # Перевіряємо, чи це зона ворожого щита для Аристократа
            shield_color = None
            for sr in range(-1, 2):
                for sc in range(-1, 2):
                    check_r, check_c = to_row + sr, to_col + sc
                    if self._is_valid_square(check_r, check_c):
                        shield = self.board.get_piece_at(check_r, check_c)
                        if shield and shield.type == PieceType.SHIELD:
                            shield_color = shield.color
                            break
            # Якщо це ворожий щит для Аристократа - заборонено
            if shield_color and shield_color != aristocrat.color:
                return False
        
        # === ПЕРЕВІРКА 8: Туманності ===
        # Якщо ціль в туманності, і це Щит або Король - заборонено
        if is_target_in_nebula:
            if aristocrat.type in [PieceType.SHIELD, PieceType.KING]:
                return False
        
        # Якщо всі перевірки пройдено - обмін можливий
        return True

    def _get_rider_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Всадник: комбінація коня + офіцера з перестрибуванням
        1. Ходи коня: L-подібні стрибки (8 позицій)
        2. Ходи офіцера: діагоналі з можливістю перестрибнути ОДНУ союзну фігуру
        """
        moves = []
        attacks = []
        
        # === ЧАСТИНА 1: Ходи коня (L-подібні стрибки) ===
        knight_deltas = get_knight_deltas()
        for dr, dc in knight_deltas:
            new_row, new_col = row + dr, col + dc
            
            if not self._is_valid_square(new_row, new_col):
                continue
                
            if self._is_empty(new_row, new_col):
                if self._is_valid_move(piece, row, col, new_row, new_col):
                    moves.append((new_row, new_col))
            elif self._is_enemy(new_row, new_col, piece.color):
                if self._is_valid_attack(piece, new_row, new_col):
                    attacks.append((new_row, new_col))
        
        # === ЧАСТИНА 2: Ходи офіцера з перестрибуванням (діагоналі) ===
        diagonal_directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in diagonal_directions:
            jumped_ally = False  # Чи перестрибнули союзника на цьому променю
            
            for distance in range(1, max(BOARD_ROWS, BOARD_COLS)):
                new_row = row + dr * distance
                new_col = col + dc * distance
                
                if not self._is_valid_square(new_row, new_col):
                    break
                
                # Перевіряємо, що на поточній клітинці
                current_cell_has_enemy = self._is_enemy(new_row, new_col, piece.color)
                current_cell_has_ally = self._is_ally(new_row, new_col, piece.color)
                current_cell_empty = self._is_empty(new_row, new_col)
                
                if jumped_ally:
                    # Вже перестрибнули союзника - можемо тільки на порожні клітинки
                    if current_cell_empty:
                        if self._is_valid_move(piece, row, col, new_row, new_col):
                            moves.append((new_row, new_col))
                    elif current_cell_has_enemy:
                        # Атакуємо ворога після перестрибування союзника
                        if self._is_valid_attack(piece, new_row, new_col):
                            attacks.append((new_row, new_col))
                        break  # Зупиняємо промінь після атаки
                    else:
                        # Другий союзник - блокуємо промінь
                        break
                else:
                    # Ще не перестрибнули союзника
                    if current_cell_empty:
                        # Порожня клітинка - додаємо рух
                        if self._is_valid_move(piece, row, col, new_row, new_col):
                            moves.append((new_row, new_col))
                    elif current_cell_has_ally:
                        # Перший союзник - позначаємо і продовжуємо
                        jumped_ally = True
                        # НЕ додаємо цю клітинку (не можна ставати на союзника)
                    elif current_cell_has_enemy:
                        # Ворог - атакуємо і зупиняємо промінь
                        if self._is_valid_attack(piece, new_row, new_col):
                            attacks.append((new_row, new_col))
                        break
        
        return moves, attacks

    def _get_lightning_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Блискавка:
        1. Діагональні ходи на 1-2 клітинки (ТІЛЬКИ на вільні клітинки, не атакує по діагоналі)
        2. L-подібні атаки: стрибок через 2 діагональні + 1 перпендикулярно
        3. Електричний параліч: фігура, що захопила Блискавку, паралізується на 1 хід
           (виняток: Король і Блискавка не паралізуються)
        """
        moves = []
        attacks = []
        
        # Діагональні напрямки
        diag_directions = [
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]
        
        for dr, dc in diag_directions:
            # ═══ ЧАСТИНА 1: ДІАГОНАЛЬНІ ХОДИ (1-2 клітинки) ═══
            for i in range(1, 3):  # 1 та 2 клітинки
                diag_row = row + dr * i
                diag_col = col + dc * i
                
                if not self._is_valid_square(diag_row, diag_col):
                    continue
                
                # Блискавка НЕ може входити в імунні зони (щитів)
                if not self._can_enter_shield_zone(piece, diag_row, diag_col):
                    continue
                
                target_piece = self.board.get_piece_at(diag_row, diag_col)
                if not target_piece or target_piece.is_empty():
                    # ТІЛЬКИ НА ВІЛЬНІ КЛІТИНКИ (не атакує по діагоналі)
                    moves.append((diag_row, diag_col))
                else:
                    # Якщо клітинка зайнята - зупиняємось у цьому напрямку
                    break
            
            # ═══ ЧАСТИНА 2: L-ПОДІБНІ АТАКИ ═══
            # Стрибок через 2 діагональні клітинки
            diag_row_2 = row + dr * 2
            diag_col_2 = col + dc * 2
            
            if not self._is_valid_square(diag_row_2, diag_col_2):
                continue
            
            # Два варіанти L-форми від діагональної точки
            # L-1: 3 кроки по ряду, 1 по колонці
            # L-2: 1 крок по ряду, 3 по колонці
            l_attack_points = [
                (row + 3 * dr, col + dc),     # L-1
                (row + dr, col + 3 * dc)      # L-2
            ]
            
            for attack_row, attack_col in l_attack_points:
                if not self._is_valid_square(attack_row, attack_col):
                    continue
                
                # Перевірка імунітету (виняток для короля)
                if not self._can_enter_shield_zone(piece, attack_row, attack_col):
                    target_piece = self.board.get_piece_at(attack_row, attack_col)
                    # Виняток: може атакувати короля в імунній зоні
                    if target_piece and target_piece.type == PieceType.KING and target_piece.color != piece.color:
                        attacks.append((attack_row, attack_col))
                    continue
                
                target_piece = self.board.get_piece_at(attack_row, attack_col)
                if not target_piece or target_piece.is_empty():
                    # L-хід на вільну клітинку - позначаємо як "атакуючий хід" (синя крапка з червоним контуром)
                    # Це дозволяє гравцю зрозуміти, що це атакуюча позиція
                    moves.append((attack_row, attack_col, 'attack_potential'))
                elif target_piece.color != piece.color:
                    # L-атака ворожої фігури
                    if self._can_attack_target(piece, attack_row, attack_col):
                        attacks.append((attack_row, attack_col))
        
        return moves, attacks

    def _get_moon_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Місяць:
        1. Стрибки на 2 клітинки (тільки ортогонально: вертикаль/горизонталь)
        2. Механіка обходу: НЕ може стрибати через зайняту клітинку,
           але може обійти перешкоду через бічні (перпендикулярні) клітинки
        3. Якщо хоча б одна бічна клітинка вільна - стрибок можливий
        """
        moves = []
        attacks = []
        
        # Напрямки стрибка на 2 клітинки (тільки ортогонально)
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        
        for dr, dc in directions:
            final_row = row + dr
            final_col = col + dc
            
            # Перевірка доступності кінцевої клітинки
            if not self._is_valid_square(final_row, final_col):
                continue
            
            # КЛЮЧОВИЙ МОМЕНТ: Клітинка через яку стрибаємо (середня)
            middle_row = row + (1 if dr > 0 else -1 if dr < 0 else 0)
            middle_col = col + (1 if dc > 0 else -1 if dc < 0 else 0)
            
            # СИСТЕМА ОБХОДУ: Клітинки обходу (перпендикулярні до напрямку стрибка)
            detour_squares = []
            if dr != 0:  # Вертикальний стрибок - обхід по горизонталі
                detour_squares = [
                    (middle_row, col - 1),  # Ліворуч від середньої клітинки
                    (middle_row, col + 1)   # Праворуч від середньої клітинки
                ]
            else:  # Горизонтальний стрибок - обхід по вертикалі
                detour_squares = [
                    (row - 1, middle_col),  # Вище від середньої клітинки
                    (row + 1, middle_col)   # Нижче від середньої клітинки
                ]
            
            # КРИТИЧНА ПЕРЕВІРКА: Чи є хоча б одна вільна клітинка для обходу
            valid_detour_found = False
            for detour_row, detour_col in detour_squares:
                # Перевіряємо доступність клітинки обходу
                if not self._is_valid_square(detour_row, detour_col):
                    continue
                
                # Перевіряємо, чи вільна клітинка
                if self._is_empty(detour_row, detour_col):
                    valid_detour_found = True
                    break
            
            # Якщо немає шляху для обходу - стрибок неможливий
            if not valid_detour_found:
                continue
            
            # ФІНАЛЬНА ОБРОБКА: Перевірка цільової клітинки
            if not self._is_valid_move(piece, row, col, final_row, final_col):
                # Спеціальний випадок: можна атакувати короля навіть в імунній зоні
                target_piece = self.board.get_piece_at(final_row, final_col)
                if target_piece and target_piece.type == PieceType.KING and target_piece.color != piece.color:
                    attacks.append((final_row, final_col))
                continue
            
            # Перевірка цільової клітинки
            if self._is_empty(final_row, final_col):
                # Хід на вільну клітинку
                moves.append((final_row, final_col))
            elif self._is_enemy(final_row, final_col, piece.color):
                # Атака ворожої фігури
                if self._is_valid_attack(piece, final_row, final_col):
                    attacks.append((final_row, final_col))
            # Не можна стрибати на союзну фігуру
        
        return moves, attacks

    def _get_triumphator_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Отримує можливі ходи та цілі для паралічу Тріумфатора"""
        moves = []
        paralysis_targets = []
        
        # Рухи Тріумфатора:
        # - Діагоналі: 1-2 клітинки
        # - Горизонталі: 1-2 клітинки  
        # - Вертикалі: 1-3 клітинки
        
        # Діагональні рухи (1-2 клітинки)
        for dr, dc in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            for distance in [1, 2]:
                new_row = row + dr * distance
                new_col = col + dc * distance
                
                if not self._is_valid_square(new_row, new_col):
                    break
                    
                # Перевірка шляху
                path = self._get_path_cells(row, col, new_row, new_col)
                path_blocked = any(not self._is_empty(r, c) for r, c in path)
                if path_blocked:
                    break
                    
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    # Перевірка, чи можна паралізувати цю ціль
                    if self._can_paralyze_target(new_row, new_col):
                        paralysis_targets.append((new_row, new_col))
                    break
                else:
                    break
        
        # Горизонтальні рухи (1-2 клітинки)
        for dc in [-1, 1]:
            for distance in [1, 2]:
                new_row = row
                new_col = col + dc * distance
                
                if not self._is_valid_square(new_row, new_col):
                    break
                    
                path = self._get_path_cells(row, col, new_row, new_col)
                if any(not self._is_empty(r, c) for r, c in path):
                    break
                    
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    # Перевірка, чи можна паралізувати цю ціль
                    if self._can_paralyze_target(new_row, new_col):
                        paralysis_targets.append((new_row, new_col))
                    break
                else:
                    break
        
        # Вертикальні рухи: вперед 1-3 клітинки, назад 1-2 клітинки
        for dr in [-1, 1]:
            # Визначаємо напрямок руху відносно кольору фігури
            is_forward = (dr == -1 and piece.color == PieceColor.WHITE) or (dr == 1 and piece.color == PieceColor.BLACK)
            max_distance = 3 if is_forward else 2  # Вперед 3, назад 2
            
            for distance in range(1, max_distance + 1):
                new_row = row + dr * distance
                new_col = col
                
                if not self._is_valid_square(new_row, new_col):
                    break
                    
                path = self._get_path_cells(row, col, new_row, new_col)
                if any(not self._is_empty(r, c) for r, c in path):
                    break
                    
                if self._is_empty(new_row, new_col):
                    if self._is_valid_move(piece, row, col, new_row, new_col):
                        moves.append((new_row, new_col))
                elif self._is_enemy(new_row, new_col, piece.color):
                    # Перевірка, чи можна паралізувати цю ціль
                    if self._can_paralyze_target(new_row, new_col):
                        paralysis_targets.append((new_row, new_col))
                    break
                else:
                    break
        
        # Тріумфатор повертає paralysis_targets як "атаки"
        # але вони будуть оброблятися спеціально
        return moves, paralysis_targets
    
    def _can_paralyze_target(self, target_row: int, target_col: int) -> bool:
        """
        Перевіряє, чи може Тріумфатор паралізувати фігуру на вказаній позиції.
        Тріумфатор НЕ може паралізувати:
        - Щит
        - Блискавку
        - Будь-які фігури, що знаходяться в зоні захисту Щита
        """
        target_piece = self.board.get_piece_at(target_row, target_col)
        
        # Перевірка, чи є ціль
        if not target_piece or target_piece.is_empty():
            return False
        
        # Не можна паралізувати Щит
        if target_piece.type == PieceType.SHIELD:
            return False
        
        # Не можна паралізувати Блискавку
        if target_piece.type == PieceType.LIGHTNING:
            return False
        
        # Не можна паралізувати фігури, захищені Щитом
        if self._is_protected_by_shield(target_row, target_col):
            return False
        
        return True

    def get_paralysis_landing_squares(self, target_row: int, target_col: int) -> List[Tuple[int, int]]:
        """Отримує можливі клітинки для приземлення після паралічу"""
        landing_squares = []
        
        # Діагональні клітинки навколо цілі
        for dr, dc in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            new_row = target_row + dr
            new_col = target_col + dc
            
            if self._is_valid_square(new_row, new_col) and self._is_empty(new_row, new_col):
                landing_squares.append((new_row, new_col))
        
        return landing_squares

    def _get_eye_moves(self, piece: Piece, row: int, col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        moves = []
        attacks = []

        # --- Атака (завжди по прямих лініях) ---
        attack_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        attack_range = 2 if piece.is_enhanced else 1

        for dr, dc in attack_directions:
            if piece.is_enhanced:
                # Посилене Око: може атакувати НА ВИБІР на 1 або 2 клітинки
                # Перевіряємо обидві клітинки незалежно
                for i in [1, 2]:
                    new_row, new_col = row + dr * i, col + dc * i
                    
                    if not self._is_valid_square(new_row, new_col):
                        continue  # Пропускаємо цю відстань, але перевіряємо іншу
                    
                    if self._is_enemy(new_row, new_col, piece.color):
                        if self._is_valid_attack(piece, new_row, new_col):
                            attacks.append((new_row, new_col))
            else:
                # Звичайне Око: атакує тільки на 1 клітинку
                new_row, new_col = row + dr, col + dc
                
                if not self._is_valid_square(new_row, new_col):
                    continue
                
                if self._is_enemy(new_row, new_col, piece.color):
                    if self._is_valid_attack(piece, new_row, new_col):
                        attacks.append((new_row, new_col))

        # --- Рух (завжди по діагоналях) ---
        move_directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        if piece.is_enhanced:
            # Посилений рух: до 3 клітинок з можливістю "прослизнути" через одного ворога
            for dr, dc in move_directions:
                enemy_on_path = False  # Чи є ворог на шляху цього променя
                for i in range(1, 4):
                    new_row, new_col = row + dr * i, col + dc * i

                    if not self._is_valid_square(new_row, new_col):
                        break

                    # Перевіряємо, що на поточній клітинці
                    current_cell_has_enemy = self._is_enemy(new_row, new_col, piece.color)
                    current_cell_has_ally = self._is_ally(new_row, new_col, piece.color)
                    current_cell_empty = self._is_empty(new_row, new_col)

                    # Якщо вже був ворог раніше на променю
                    if enemy_on_path:
                        # Дозволяємо рух тільки на порожні клітинки після першого ворога
                        if current_cell_empty:
                            if self._is_valid_move(piece, row, col, new_row, new_col):
                                moves.append((new_row, new_col))
                        else:
                            # Другий ворог або союзник - блокуємо промінь
                            break
                    else:
                        # Ще не зустрічали ворога на променю
                        if current_cell_empty:
                            # Порожня клітинка - додаємо рух
                            if self._is_valid_move(piece, row, col, new_row, new_col):
                                moves.append((new_row, new_col))
                        elif current_cell_has_ally:
                            # Союзник - блокуємо промінь
                            break
                        elif current_cell_has_enemy:
                            # Перший ворог - позначаємо і продовжуємо (не можна атакувати, але можна перестрибнути)
                            enemy_on_path = True
                            # НЕ додаємо цю клітинку в moves (не можна атакувати при русі)
                            # Продовжуємо цикл для перевірки наступних клітинок
        else:
            # Звичайний рух: 1 або 2 клітинки, шлях вільний
            for dr, dc in move_directions:
                for i in range(1, 3):
                    new_row, new_col = row + dr * i, col + dc * i

                    if not self._is_valid_square(new_row, new_col):
                        break

                    path = self._get_path_cells(row, col, new_row, new_col)
                    is_path_blocked = any(not self._is_empty(r, c) for r, c in path)
                    
                    if is_path_blocked:
                        break

                    if self._is_empty(new_row, new_col):
                        if self._is_valid_move(piece, row, col, new_row, new_col):
                            moves.append((new_row, new_col))
                    else: # Клітинка не порожня, зупиняємо промінь
                        break

        return moves, attacks

    def _filter_legal_moves(self, piece: Piece, from_row: int, from_col: int, moves: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        legal_moves = []
        for move_item in moves:
            marker = None
            # Обробка формату з міткою ('swap', 'attack_potential', тощо)
            if isinstance(move_item, tuple) and len(move_item) == 3:
                to_row, to_col, marker = move_item
            elif isinstance(move_item, tuple) and len(move_item) >= 2:
                to_row, to_col = move_item[0], move_item[1]
            else:
                continue
            
            original_piece = self.board.get_piece_at(to_row, to_col)
            
            self.board.move_piece(from_row, from_col, to_row, to_col)
            
            if self._is_king_in_check(piece.color) is None:
                # Зберігаємо оригінальний формат з маркером
                if marker:
                    legal_moves.append((to_row, to_col, marker))
                else:
                    legal_moves.append((to_row, to_col))
            
            self.board.clear_square(to_row, to_col)
            self.board.set_piece(from_row, from_col, piece)
            if original_piece and not original_piece.is_empty():
                self.board.set_piece(to_row, to_col, original_piece)
        
        return legal_moves

    def _is_king_in_check(self, color: PieceColor) -> Optional[Tuple[int, int]]:
        """Перевіряє, чи є король у шаху, і повертає позицію атакуючої фігури."""
        king_pos = self._find_king(color)
        if not king_pos:
            return None
        
        king_row, king_col = king_pos
        enemy_color = PieceColor.BLACK if color == PieceColor.WHITE else PieceColor.WHITE

        # Перевірка атак ковзаючих фігур (тура, слон, ферзь та їх аналоги)
        sliding_attackers = {PieceType.ROOK, PieceType.QUEEN}
        # АРИСТОКРАТ НЕ ВБИВАЄ - НЕ СТАВИТЬ ШАХ!
        diagonal_attackers = {PieceType.BISHOP, PieceType.QUEEN}
        
        # 8 напрямків: 4 прямих, 4 діагональних
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            for i in range(1, max(BOARD_ROWS, BOARD_COLS)):
                r, c = king_row + dr * i, king_col + dc * i

                if not self._is_valid_square(r, c):
                    break

                piece = self.board.get_piece_at(r, c)
                if piece and not piece.is_empty():
                    if piece.color == enemy_color:
                        # Перевірка для прямих напрямків
                        if (dr == 0 or dc == 0) and piece.type in sliding_attackers:
                            return (r, c)
                        # Перевірка для діагональних напрямків
                        if (dr != 0 and dc != 0) and piece.type in diagonal_attackers:
                            return (r, c)
                    # Промінь блоковано, виходимо з внутрішнього циклу
                    break

        # Перевірка атак фігур, що стрибають (кінь та аналоги)
        # ТРІУМФАТОР НЕ ВБИВАЄ - НЕ СТАВИТЬ ШАХ!
        knight_attackers = {PieceType.KNIGHT, PieceType.RIDER, PieceType.MOON}
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in knight_moves:
            r, c = king_row + dr, king_col + dc
            if self._is_valid_square(r, c):
                piece = self.board.get_piece_at(r, c)
                if piece and piece.color == enemy_color and piece.type in knight_attackers:
                    return (r, c)

        # Перевірка атак пішаків
        pawn_direction = 1 if color == PieceColor.WHITE else -1
        for dc in [-1, 1]:
            r, c = king_row - pawn_direction, king_col + dc
            if self._is_valid_square(r, c):
                piece = self.board.get_piece_at(r, c)
                if piece and piece.color == enemy_color and piece.type == PieceType.PAWN:
                    return (r, c)
        
        # Перевірка атак Блискавки (L-подібні атаки)
        # Блискавка атакує L-подібним патерном: 3 діагональ + 1 перпендикуляр АБО 1 діагональ + 3 перпендикуляр
        diag_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in diag_directions:
            # Два варіанти L-форми
            lightning_l_points = [
                (king_row + 3 * dr, king_col + dc),      # L-1: 3 по діагоналі, 1 перпендикулярно
                (king_row + dr, king_col + 3 * dc)       # L-2: 1 по діагоналі, 3 перпендикулярно
            ]
            
            for r, c in lightning_l_points:
                if self._is_valid_square(r, c):
                    piece = self.board.get_piece_at(r, c)
                    if piece and piece.color == enemy_color and piece.type == PieceType.LIGHTNING:
                        return (r, c)

        # Перевірка атак короля, фурії, звичайного Ока (атакують як король на 1 клітинку)
        king_like_attackers = {PieceType.KING, PieceType.FURY}
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                r, c = king_row + dr, king_col + dc
                if self._is_valid_square(r, c):
                    piece = self.board.get_piece_at(r, c)
                    if piece and piece.color == enemy_color:
                        # Король і Фурія - завжди атакують на 1 клітинку
                        if piece.type in king_like_attackers:
                            return (r, c)
                        # Звичайне Око - атакує ортогонально на 1 клітинку
                        if piece.type == PieceType.EYE and not piece.is_enhanced and (dr == 0 or dc == 0):
                            return (r, c)
        
        # Перевірка атак посиленого Ока (ортогонально на 1-2 клітинки)
        if True:  # Завжди перевіряємо посилене Око
            eye_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            for dr, dc in eye_directions:
                for distance in [1, 2]:
                    r, c = king_row + dr * distance, king_col + dc * distance
                    if self._is_valid_square(r, c):
                        piece = self.board.get_piece_at(r, c)
                        if piece and piece.color == enemy_color and piece.type == PieceType.EYE and piece.is_enhanced:
                            return (r, c)
                        # Якщо клітинка зайнята іншою фігурою, зупиняємо перевірку в цьому напрямку
                        if piece and not piece.is_empty():
                            break
        
        # Перевірка атак Храму (ортогонально 1 + стрибки 2-3/2)
        # Перевірка ортогональних атак на 1 клітинку
        temple_directions_1 = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dr, dc in temple_directions_1:
            r, c = king_row + dr, king_col + dc
            if self._is_valid_square(r, c):
                piece = self.board.get_piece_at(r, c)
                if piece and piece.color == enemy_color and piece.type == PieceType.TEMPLE:
                    return (r, c)
        
        # Перевірка стрибків Храму (2-3 вертикально, 2 горизонтально)
        temple_jump_directions = [
            (-3, 0), (3, 0),   # Вертикаль 3
            (-2, 0), (2, 0),   # Вертикаль 2
            (0, -2), (0, 2)    # Горизонталь 2
        ]
        for dr, dc in temple_jump_directions:
            r, c = king_row + dr, king_col + dc
            if self._is_valid_square(r, c):
                piece = self.board.get_piece_at(r, c)
                if piece and piece.color == enemy_color and piece.type == PieceType.TEMPLE:
                    # Перевірка, що на шляху максимум 1 ворог (сам король)
                    # Храм може перестрибнути максимум 1 ворога
                    enemies_on_path = 0
                    path_clear = True
                    steps = max(abs(dr), abs(dc))
                    
                    for i in range(1, steps):
                        path_row = king_row + (1 if dr > 0 else -1 if dr < 0 else 0) * i
                        path_col = king_col + (1 if dc > 0 else -1 if dc < 0 else 0) * i
                        path_piece = self.board.get_piece_at(path_row, path_col)
                        
                        if path_piece and not path_piece.is_empty():
                            if path_piece.color != enemy_color:
                                # Ворог (король) на шляху
                                enemies_on_path += 1
                                if enemies_on_path > 1:
                                    path_clear = False
                                    break
                            else:
                                # Союзна для Храму фігура блокує
                                path_clear = False
                                break
                    
                    if path_clear and enemies_on_path <= 1:
                        return (r, c)

        return None

    def _find_king(self, color: PieceColor) -> Optional[Tuple[int, int]]:
        king_positions = self.board.get_all_pieces_of_type(PieceType.KING, color)
        return king_positions[0] if king_positions else None

    def is_checkmate(self, color: PieceColor) -> bool:
        """
        Перевіряє, чи є мат для вказаного кольору.
        Мат настає коли:
        1. Король під шахом І немає жодного легального ходу
        2. Король паралізований І під шахом (не може рухатися, щоб захиститися)
        """
        # Перевірка шаху
        if self._is_king_in_check(color) is None:
            return False
        
        # Знаходимо короля
        king_pos = self._find_king(color)
        if not king_pos:
            return False
        
        # КРИТИЧНО: Якщо король паралізований І під шахом - це МАТ!
        if self.game_state and king_pos in self.game_state.paralyzed_pieces:
            paralysis_info = self.game_state.paralyzed_pieces[king_pos]
            # Перевіряємо, що паралізований саме король цього кольору
            if paralysis_info.get('color') == color:
                print(f"⚡👑 МАТ! Король паралізований і під шахом!")
                return True
        
        # Стандартна перевірка - чи є хоча б один легальний хід
        all_pieces = self.board.get_all_pieces_of_color(color)
        for row, col in all_pieces:
            piece = self.board.get_piece_at(row, col)
            if piece and not piece.is_empty():
                moves, attacks, teleports = self.get_possible_moves(piece, row, col)
                if moves or attacks or teleports:
                    return False
        
        return True

    def is_stalemate(self, color: PieceColor) -> bool:
        if self._is_king_in_check(color) is not None:
            return False
        
        all_pieces = self.board.get_all_pieces_of_color(color)
        for row, col in all_pieces:
            piece = self.board.get_piece_at(row, col)
            if piece and not piece.is_empty():
                moves, attacks, teleports = self.get_possible_moves(piece, row, col)
                if moves or attacks or teleports:
                    return False
        
        return True

    def get_resurrection_positions(self, color: PieceColor) -> List[Tuple[int, int]]:
        """Повертає позиції для воскресіння пішаків."""
        positions = []
        # Білі пішаки воскресають на своєму стартовому ряду (19), чорні - на своєму (2).
        resurrection_row = 19 if color == PieceColor.WHITE else 2
        
        # Пряме використання координат без зсувів - ігрова зона 1-18
        for col in range(1, 19):
            if self.board.is_square_empty(resurrection_row, col):
                positions.append((resurrection_row, col))
        
        return positions

    def is_resurrection_row(self, row: int, color: PieceColor) -> bool:
        """Перевіряє, чи є ряд рядом воскресіння для пішака."""
        # Білі пішаки воскресають на своєму стартовому ряду (19), чорні - на своєму (2).
        resurrection_row = 19 if color == PieceColor.WHITE else 2
        return row == resurrection_row


class MoveValidator:
    def __init__(self, board):
        self.board = board
        self.calculator = MoveCalculator(board)

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int,
                      current_player: PieceColor) -> bool:
        if not self._is_valid_square(from_row, from_col) or not self._is_valid_square(to_row, to_col):
            return False
        
        piece = self.board.get_piece_at(from_row, from_col)
        if not piece or piece.is_empty() or piece.color != current_player:
            return False
        
        moves, attacks, teleports = self.calculator.get_possible_moves(piece, from_row, from_col)
        return (to_row, to_col) in moves or (to_row, to_col) in attacks or (to_row, to_col) in teleports

    def _is_valid_square(self, row: int, col: int) -> bool:
        return is_valid_position(row, col)
