from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor, QFont, QPixmap
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QRect, QRectF, QPoint
from pathlib import Path
from typing import Set, Tuple, Optional, Dict
from налаштування import (
    BOARD_ROWS, BOARD_COLS,
    NEBULAS, LETTERS_BOTTOM, NUMBERS_LEFT,
    LIGHT_SQUARE_COLOR, DARK_SQUARE_COLOR, BACKGROUND_COLOR,
    BLACK_BORDER_COLOR, ATTACK_DOT_COLOR, MOVE_DOT_COLOR, SWAP_DOT_COLOR,
    TELEPORT_DOT_COLOR,
    PARALYSIS_COLOR, RESURRECTION_COLOR_GREEN, RESURRECTION_COLOR_GRAY,
    MOON_HIGHLIGHT_COLOR, LABEL_TEXT_COLOR, TIMER_TEXT_COLOR,
    WHITE_COLOR, RED_SEMI_TRANSPARENT, RED_SOLID,
    CELL_MARGIN, MIN_CELL_SIZE, DOT_SIZE_RATIO, CORNER_SIZE_RATIO,
    PARALYSIS_INDICATOR_SIZE_RATIO, FOG_RING_SIZE_RATIO, FOG_RING_WIDTH_RATIO,
    BOARD_THEMES, DEFAULT_BOARD_THEME_INDEX,
    PieceType, PieceColor, PIECE_FILE_MAP, EYE_ENHANCEMENT_COLOR
)
from логування import game_logger


class BoardWidget(QWidget):
    cell_clicked = pyqtSignal(int, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.pieces = {}
        self._cell_size = 30
        self._offset_x = 0
        self._offset_y = 0
        self.attack_dots = set()
        self.move_dots = set()
        self.attack_move_dots = set()  # Нові крапки для ходів з можливістю атаки (сині з червоним контуром)
        self.swap_dots = set()
        self.teleport_dots = set()
        self.paralyzed_cells = {}
        self.paralysis_landing_dots = set()
        self.resurrection_corners = {}
        self.soul_corners = {}  # Куточки для воскресіння душ: {(row, col): (piece_type, is_green, color)}
        self.eye_enhancement_corners = {} # For Eye enhancement
        self.highlighted_moons = set()
        self.king_in_check_position = None  # Позиція короля під шахом для жовтої рамки
        self.fog_cells = {}
        self.shield_positions = set()
        self.selected_piece_position = None
        self.current_theme_index = DEFAULT_BOARD_THEME_INDEX
        self.light_square_color = QColor(*BOARD_THEMES[self.current_theme_index]["light"])
        self.dark_square_color = QColor(*BOARD_THEMES[self.current_theme_index]["dark"])
        self._svg_cache = {}
        self.nebula_ownership = {
            "top_left": "black",
            "top_right": "white",
            "bottom_left": "white",
            "bottom_right": "black"
        }
        self.nebula_timers = {}
        self.game_state = None
        game_logger.info("Ініціалізовано BoardWidget")

    def set_board_theme(self, theme_index: int):
        if 0 <= theme_index < len(BOARD_THEMES):
            self.current_theme_index = theme_index
            theme = BOARD_THEMES[theme_index]
            self.light_square_color = QColor(*theme["light"])
            self.dark_square_color = QColor(*theme["dark"])
            self.update()
            game_logger.info(f"Встановлено тему дошки: {theme['name']}")

    def set_game_state(self, game_state):
        self.game_state = game_state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._calculate_board_dimensions()
        self._draw_board(painter)
        self._draw_labels(painter)
        self._draw_nebulas(painter)
        self._draw_timers(painter)
        self._draw_pieces(painter)
        self._draw_visual_effects(painter)

    def _calculate_board_dimensions(self):
        top_margin = 15
        bottom_margin = 2
        min_horizontal_margin = 20
        
        available_width = self.width() - min_horizontal_margin
        available_height = self.height() - (top_margin + bottom_margin)
        
        cell_width = (available_width - BOARD_COLS * 2 * CELL_MARGIN) // BOARD_COLS
        cell_height = (available_height - BOARD_ROWS * 2 * CELL_MARGIN) // BOARD_ROWS
        
        self._cell_size = max(MIN_CELL_SIZE, min(cell_width, cell_height))
        
        grid_width = BOARD_COLS * (self._cell_size + 2 * CELL_MARGIN)
        grid_height = BOARD_ROWS * (self._cell_size + 2 * CELL_MARGIN)
        
        self._offset_x = (self.width() - grid_width) // 2
        self._offset_y = top_margin

    def _draw_board(self, painter):
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                self._draw_square(painter, row, col)

    def _draw_square(self, painter, row: int, col: int):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        cell_rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
        
        if self._is_label_cell(row, col):
            return
        
        if self._is_nebula_cell(row, col):
            is_dark = (row + col) % 2 == 0
            color = self.dark_square_color if is_dark else self.light_square_color
            painter.fillRect(cell_rect, color)
        else:
            is_dark = (row + col) % 2 == 0
            color = self.dark_square_color if is_dark else self.light_square_color
            painter.fillRect(cell_rect, color)
        
        border_option = self._get_border_option()
        should_draw_border = False
        
        if border_option == "На всіх клітинках":
            should_draw_border = True
        elif border_option == "Не малювати":
            should_draw_border = False
        elif border_option == "Тільки на білих":
            should_draw_border = not is_dark
        elif border_option == "Тільки на чорних":
            should_draw_border = is_dark
        
        if should_draw_border:
            if is_dark:
                border_color = self.light_square_color
            else:
                border_color = self.dark_square_color
            
            inner_rect = QRect(cell_rect.x() + 1, cell_rect.y() + 1, 
                              cell_rect.width() - 2, cell_rect.height() - 2)
            painter.setPen(QPen(border_color, 1))
            painter.drawRect(inner_rect)

    def _get_border_option(self):
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings()
            from налаштування import DEFAULT_CELL_BORDER_OPTION
            return settings.value("cell_border_option", DEFAULT_CELL_BORDER_OPTION)
        except:
            from налаштування import DEFAULT_CELL_BORDER_OPTION
            return DEFAULT_CELL_BORDER_OPTION

    def _is_label_cell(self, row: int, col: int) -> bool:
        return (row == 0 or row == BOARD_ROWS - 1 or
                col == 0 or col == BOARD_COLS - 1) and \
               (row, col) not in NEBULAS.values() and \
            not self._is_timer_cell(row, col)

    def _is_nebula_cell(self, row: int, col: int) -> bool:
        return (row, col) in NEBULAS.values()

    def _is_timer_cell(self, row: int, col: int) -> bool:
        timer_positions = [
            (0, -1), (0, 20),
            (21, -1), (21, 20)
        ]
        return (row, col) in timer_positions

    def _draw_labels(self, painter):
        font = QFont("Arial", max(8, self._cell_size // 4))
        painter.setFont(font)
        
        circle_color = QColor(255, 255, 255, 120)
        painter.setBrush(QBrush(circle_color))
        painter.setPen(QPen(Qt.GlobalColor.transparent))
        
        for col in range(1, BOARD_COLS - 1):
            if col - 1 < len(LETTERS_BOTTOM):
                letter = LETTERS_BOTTOM[col - 1]
                x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
                y_bottom = self._offset_y + (BOARD_ROWS - 1) * (self._cell_size + 2 * CELL_MARGIN)
                rect_bottom = QRect(x + CELL_MARGIN, y_bottom + CELL_MARGIN, self._cell_size, self._cell_size)
                
                circle_radius = min(self._cell_size // 3, 15)
                circle_center_x = rect_bottom.center().x()
                circle_center_y = rect_bottom.center().y()
                painter.drawEllipse(circle_center_x - circle_radius, circle_center_y - circle_radius, 
                                  circle_radius * 2, circle_radius * 2)
                
                painter.setPen(QPen(LABEL_TEXT_COLOR))
                painter.drawText(rect_bottom, Qt.AlignmentFlag.AlignCenter, letter)
                painter.setPen(QPen(Qt.GlobalColor.transparent))
        
        for row in range(1, BOARD_ROWS - 1):
            if row - 1 < len(NUMBERS_LEFT):
                number = NUMBERS_LEFT[row - 1]
                x = self._offset_x
                y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
                rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
                
                circle_radius = min(self._cell_size // 3, 15)
                circle_center_x = rect.center().x()
                circle_center_y = rect.center().y()
                painter.drawEllipse(circle_center_x - circle_radius, circle_center_y - circle_radius, 
                                  circle_radius * 2, circle_radius * 2)
                
                painter.setPen(QPen(LABEL_TEXT_COLOR))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, number)
                painter.setPen(QPen(Qt.GlobalColor.transparent))

    def _draw_nebulas(self, painter):
        for name, (row, col) in NEBULAS.items():
            if self.game_state and self.game_state.is_nebula_blocked(row, col):
                x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
                y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
                ring_size = int(self._cell_size * FOG_RING_SIZE_RATIO)
                ring_width = max(2, int(self._cell_size * FOG_RING_WIDTH_RATIO))
                ring_x = x + CELL_MARGIN + (self._cell_size - ring_size) // 2
                ring_y = y + CELL_MARGIN + (self._cell_size - ring_size) // 2
                owner = self.nebula_ownership.get(name, "white")
                if owner == "white":
                    ring_color = self.dark_square_color
                else:
                    ring_color = self.light_square_color
                painter.setBrush(QBrush(Qt.GlobalColor.transparent))
                painter.setPen(QPen(ring_color, ring_width))
                painter.drawEllipse(ring_x, ring_y, ring_size, ring_size)

    def _draw_timers(self, painter):
        timer_positions = {
            "top_left": (0, -1),
            "top_right": (0, 20),
            "bottom_left": (21, -1),
            "bottom_right": (21, 20)
        }
        painter.setPen(QPen(BLACK_BORDER_COLOR, 1))
        font = QFont("Arial", max(8, self._cell_size // 4), QFont.Weight.Bold)
        painter.setFont(font)
        for name, (row, col) in timer_positions.items():
            if col == -1:
                x = self._offset_x - (self._cell_size + 2 * CELL_MARGIN)
            elif col == 20:
                x = self._offset_x + BOARD_COLS * (self._cell_size + 2 * CELL_MARGIN)
            else:
                x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
            y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
            timer_rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
            painter.setBrush(QBrush(WHITE_COLOR))
            painter.setPen(QPen(BLACK_BORDER_COLOR, 1))
            painter.drawRect(timer_rect)
            painter.setPen(QPen(TIMER_TEXT_COLOR))
            
            timer_value = self.nebula_timers.get(name, "--")
            painter.drawText(timer_rect, Qt.AlignmentFlag.AlignCenter, str(timer_value))

    def _draw_visual_effects(self, painter):
        for row, col in self.move_dots:
            self._draw_move_dot(painter, row, col, MOVE_DOT_COLOR)
        
        # Малюємо крапки ходу з можливістю атаки (сині з червоним контуром)
        for row, col in self.attack_move_dots:
            self._draw_attack_move_dot(painter, row, col)
        
        for row, col in self.attack_dots:
            self._draw_move_dot(painter, row, col, ATTACK_DOT_COLOR)
        
        for row, col in self.teleport_dots:
            self._draw_teleport_dot(painter, row, col)
        
        # Малюємо індикатор паралічу ПЕРЕД сірими крапками
        for (row, col), paralysis_info in self.paralyzed_cells.items():
            self._draw_paralyzed_cell(painter, row, col, paralysis_info['duration'])
        
        # Малюємо сірі крапки обміну ПІСЛЯ паралічу, щоб вони були поверх
        for row, col in self.swap_dots:
            self._draw_move_dot(painter, row, col, SWAP_DOT_COLOR)
    
        for row, col in self.paralysis_landing_dots:
            self._draw_paralysis_landing_dot(painter, row, col)

        for (row, col), color in self.resurrection_corners.items():
            self._draw_resurrection_corner(painter, row, col, color)

        for (row, col), color in self.eye_enhancement_corners.items():
            self._draw_enhancement_corner(painter, row, col, color)

        for row, col in self.highlighted_moons:
            self._draw_moon_highlight(painter, row, col)

        # Малюємо жовту рамку навколо короля під шахом
        if self.king_in_check_position:
            row, col = self.king_in_check_position
            self._draw_king_in_check(painter, row, col)

        for (row, col), player_color in self.fog_cells.items():
            self._draw_fog_ring(painter, row, col, player_color)

        for row, col in self.shield_positions:
            self._draw_shield_zone(painter, row, col)

    def _draw_move_dot(self, painter, row: int, col: int, color: QColor):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        dot_size = int(self._cell_size * DOT_SIZE_RATIO)
        dot_x = x + CELL_MARGIN + (self._cell_size - dot_size) // 2
        dot_y = y + CELL_MARGIN + (self._cell_size - dot_size) // 2
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(BLACK_BORDER_COLOR, 2))
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
    
    def _draw_attack_move_dot(self, painter, row: int, col: int):
        """Малює синю крапку ходу з червоним контуром всередині (для Блискавки)"""
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        dot_size = int(self._cell_size * DOT_SIZE_RATIO)
        dot_x = x + CELL_MARGIN + (self._cell_size - dot_size) // 2
        dot_y = y + CELL_MARGIN + (self._cell_size - dot_size) // 2
        
        # Малюємо синю крапку (як звичайний хід)
        painter.setBrush(QBrush(MOVE_DOT_COLOR))
        painter.setPen(QPen(BLACK_BORDER_COLOR, 2))
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
        
        # Малюємо червоний контур всередині (менший розмір)
        inner_size = int(dot_size * 0.6)  # 60% від розміру крапки
        inner_x = dot_x + (dot_size - inner_size) // 2
        inner_y = dot_y + (dot_size - inner_size) // 2
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))  # Без заливки
        painter.setPen(QPen(ATTACK_DOT_COLOR, 2))  # Червоний контур
        painter.drawEllipse(inner_x, inner_y, inner_size, inner_size)

    def _draw_teleport_dot(self, painter, row: int, col: int):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        
        dot_size = int(self._cell_size * DOT_SIZE_RATIO)
        dot_x = x + CELL_MARGIN + (self._cell_size - dot_size) // 2
        dot_y = y + CELL_MARGIN + (self._cell_size - dot_size) // 2
        
        ring_size = int(dot_size * 1.5)
        ring_x = dot_x - (ring_size - dot_size) // 2
        ring_y = dot_y - (ring_size - dot_size) // 2
        
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.setPen(QPen(TELEPORT_DOT_COLOR, 3))
        painter.drawEllipse(ring_x, ring_y, ring_size, ring_size)
        
        painter.setBrush(QBrush(TELEPORT_DOT_COLOR))
        painter.setPen(QPen(BLACK_BORDER_COLOR, 2))
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

    def _draw_paralyzed_cell(self, painter, row: int, col: int, duration: int):
        """Малює візуалізацію паралізованої клітинки"""
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        cell_rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
        
        # Малюємо напівпрозорий червоний фон
        painter.fillRect(cell_rect, QColor(255, 0, 0, 80))
        
        # Розмір індикатора (кружечок у верхньому лівому куті)
        indicator_size = max(16, int(self._cell_size * 0.3))
        
        # Позиція кружечка в верхньому лівому куті клітинки
        indicator_x = x + CELL_MARGIN + 2
        indicator_y = y + CELL_MARGIN + 2
        
        # Малюємо червоний кружечок
        painter.setBrush(QBrush(QColor(200, 0, 0)))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(indicator_x, indicator_y, indicator_size, indicator_size)
        
        # Малюємо число всередині кружечка (1 або 2)
        font_size = max(10, int(indicator_size * 0.6))
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        text_rect = QRect(indicator_x, indicator_y, indicator_size, indicator_size)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(duration))

    def _draw_paralysis_landing_dot(self, painter, row: int, col: int):
        """Малює спеціальну точку для вибору місця приземлення"""
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        
        dot_size = int(self._cell_size * 0.4)
        dot_x = x + CELL_MARGIN + (self._cell_size - dot_size) // 2
        dot_y = y + CELL_MARGIN + (self._cell_size - dot_size) // 2
        
        painter.setBrush(QBrush(QColor(255, 215, 0)))
        painter.setPen(QPen(QColor(255, 140, 0), 3))
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

    def _draw_moon_highlight(self, painter, row: int, col: int):
        """Малює жовту рамку навколо підсиленого місяця (без трикутника)"""
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        cell_rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
        
        # Малюємо тільки жовту рамку навколо клітинки
        painter.setPen(QPen(MOON_HIGHLIGHT_COLOR, 3))
        painter.setBrush(QBrush())
        painter.drawRect(cell_rect)

    def _draw_king_in_check(self, painter, row: int, col: int):
        """Малює жовту рамку навколо короля під шахом"""
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        cell_rect = QRect(x + CELL_MARGIN, y + CELL_MARGIN, self._cell_size, self._cell_size)
        
        # Малюємо жовту рамку навколо клітинки короля
        painter.setPen(QPen(MOON_HIGHLIGHT_COLOR, 3))
        painter.setBrush(QBrush())
        painter.drawRect(cell_rect)

    def _draw_resurrection_corner(self, painter, row: int, col: int, color: str):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        corner_size = int(self._cell_size * CORNER_SIZE_RATIO)
        
        if row <= 10:
            corner_x = x + CELL_MARGIN
            corner_y = y + CELL_MARGIN + self._cell_size - corner_size
            points = [
                QPoint(corner_x, corner_y + corner_size),
                QPoint(corner_x, corner_y),
                QPoint(corner_x + corner_size, corner_y + corner_size)
            ]
        else:
            corner_x = x + CELL_MARGIN + self._cell_size - corner_size
            corner_y = y + CELL_MARGIN
            points = [
                QPoint(corner_x, corner_y),
                QPoint(corner_x + corner_size, corner_y),
                QPoint(corner_x + corner_size, corner_y + corner_size)
            ]
        
        if color == "gray":
            corner_color = RESURRECTION_COLOR_GRAY
        else:
            corner_color = RESURRECTION_COLOR_GREEN
        
        painter.setBrush(QBrush(corner_color))
        painter.setPen(QPen(corner_color))
        painter.drawPolygon(points)
        painter.setBrush(QBrush())
        painter.setPen(QPen(BLACK_BORDER_COLOR, 2))
        painter.drawPolygon(points)

    def _draw_enhancement_corner(self, painter, row: int, col: int, color: str):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        corner_size = int(self._cell_size * CORNER_SIZE_RATIO)
        
        corner_x = x + CELL_MARGIN
        corner_y = y + CELL_MARGIN
        points = [
            QPoint(corner_x, corner_y),
            QPoint(corner_x + corner_size, corner_y),
            QPoint(corner_x, corner_y + corner_size)
        ]
        
        corner_color = QColor(color)
        
        painter.setBrush(QBrush(corner_color))
        painter.setPen(QPen(corner_color))
        painter.drawPolygon(points)
        painter.setBrush(QBrush())
        painter.setPen(QPen(BLACK_BORDER_COLOR, 1))
        painter.drawPolygon(points)

    def _draw_fog_ring(self, painter, row: int, col: int, player_color: str):
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        ring_size = int(self._cell_size * FOG_RING_SIZE_RATIO)
        ring_width = max(2, int(self._cell_size * FOG_RING_WIDTH_RATIO))
        ring_x = x + CELL_MARGIN + (self._cell_size - ring_size) // 2
        ring_y = y + CELL_MARGIN + (self._cell_size - ring_size) // 2
        ring_color = self.dark_square_color if player_color == "white" else self.light_square_color
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.setPen(QPen(ring_color, ring_width))
        painter.drawEllipse(ring_x, ring_y, ring_size, ring_size)

    def _draw_shield_zone(self, painter, shield_row: int, shield_col: int):
        start_row = max(1, shield_row - 1)
        end_row = min(20, shield_row + 1)
        start_col = max(1, shield_col - 1)
        end_col = min(18, shield_col + 1)
        start_x = self._offset_x + start_col * (self._cell_size + 2 * CELL_MARGIN)
        start_y = self._offset_y + start_row * (self._cell_size + 2 * CELL_MARGIN)
        end_x = self._offset_x + end_col * (self._cell_size + 2 * CELL_MARGIN)
        end_y = self._offset_y + end_row * (self._cell_size + 2 * CELL_MARGIN)
        zone_width = end_x - start_x + self._cell_size + 2 * CELL_MARGIN
        zone_height = end_y - start_y + self._cell_size + 2 * CELL_MARGIN
        zone_x = start_x - CELL_MARGIN
        zone_y = start_y - CELL_MARGIN
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.setBrush(QBrush())
        painter.drawRect(zone_x, zone_y, zone_width, zone_height)

    def _get_svg_renderer(self, piece_name: str, color: str) -> Optional[QSvgRenderer]:
        folder_name = "білі" if color == "білі" else "чорні"
        cache_key = f"{piece_name}_{folder_name}"
        if cache_key not in self._svg_cache:
            svg_path = Path(__file__).parent / f"ресурси/зображення/фігури/{folder_name}/{piece_name}.svg"
            if svg_path.exists():
                renderer = QSvgRenderer(str(svg_path))
                if renderer.isValid():
                    self._svg_cache[cache_key] = renderer
                else:
                    game_logger.warning(f"Неможливо завантажити SVG: {svg_path}")
                    return None
            else:
                game_logger.warning(f"SVG файл не знайдено: {svg_path}")
                return None
        return self._svg_cache.get(cache_key)

    def _draw_pieces(self, painter):
        for (row, col), piece_info in self.pieces.items():
            self._draw_piece(painter, row, col, piece_info)

    def _draw_piece(self, painter, row: int, col: int, piece_info: dict):
        if "type" not in piece_info:
            return
        piece_type = piece_info["type"]
        piece_color = piece_info["color"]
        piece_name = PIECE_FILE_MAP.get(piece_type, "pawn.svg").replace(".svg", "")
        color = "білі" if piece_color == PieceColor.WHITE else "чорні"
        renderer = self._get_svg_renderer(piece_name, color)
        if not renderer:
            return
        x = self._offset_x + col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + row * (self._cell_size + 2 * CELL_MARGIN)
        is_selected = self.selected_piece_position == (row, col)
        piece_size = int(self._cell_size * 0.8 * (1.4 if is_selected else 1.0))
        piece_x = x + CELL_MARGIN + (self._cell_size - piece_size) // 2
        piece_y = y + CELL_MARGIN + (self._cell_size - piece_size) // 2
        piece_rect = QRectF(piece_x, piece_y, piece_size, piece_size)
        renderer.render(painter, piece_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mouse_pos = event.position().toPoint()
            clicked_cell = self._get_cell_under_mouse(mouse_pos)
            if clicked_cell:
                row, col = clicked_cell
                self.cell_clicked.emit(row, col, mouse_pos)

    def is_click_on_resurrection_corner(self, mouse_pos, cell_row: int, cell_col: int) -> bool:
        if (cell_row, cell_col) not in self.resurrection_corners:
            return False
        
        mx, my = mouse_pos.x(), mouse_pos.y()
        x = self._offset_x + cell_col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + cell_row * (self._cell_size + 2 * CELL_MARGIN)
        corner_size = int(self._cell_size * CORNER_SIZE_RATIO)
        
        if cell_row <= 10:
            # Нижній лівий куточок для чорних (трикутник)
            corner_x = x + CELL_MARGIN
            corner_y = y + CELL_MARGIN + self._cell_size - corner_size
            rel_x = mx - corner_x
            rel_y = my - corner_y
            # СТРОГО перевірка трикутника
            return (rel_x >= 0 and rel_y >= 0 and 
                   rel_x <= corner_size and rel_y <= corner_size and
                   rel_y >= corner_size - rel_x)
        else:
            # Верхній правий куточок для білих (трикутник)
            corner_x = x + CELL_MARGIN + self._cell_size - corner_size
            corner_y = y + CELL_MARGIN
            rel_x = mx - corner_x
            rel_y = my - corner_y
            # СТРОГО перевірка трикутника
            return (rel_x >= 0 and rel_y >= 0 and
                   rel_x <= corner_size and rel_y <= corner_size and
                   rel_x >= corner_size - rel_y)

    def is_click_on_enhancement_corner(self, mouse_pos, cell_row: int, cell_col: int) -> bool:
        if (cell_row, cell_col) not in self.eye_enhancement_corners:
            return False
        
        mx, my = mouse_pos.x(), mouse_pos.y()
        x = self._offset_x + cell_col * (self._cell_size + 2 * CELL_MARGIN)
        y = self._offset_y + cell_row * (self._cell_size + 2 * CELL_MARGIN)
        corner_size = int(self._cell_size * CORNER_SIZE_RATIO)

        corner_x = x + CELL_MARGIN
        corner_y = y + CELL_MARGIN
        rel_x = mx - corner_x
        rel_y = my - corner_y
        return (rel_x >= 0 and rel_y >= 0 and rel_x <= corner_size and rel_y <= corner_size and (rel_x + rel_y) <= corner_size)

    def _get_cell_under_mouse(self, mouse_pos):
        if not mouse_pos:
            return None
        mx, my = mouse_pos.x(), mouse_pos.y()
        grid_width = BOARD_COLS * (self._cell_size + 2 * CELL_MARGIN)
        grid_height = BOARD_ROWS * (self._cell_size + 2 * CELL_MARGIN)
        if not (self._offset_x <= mx < self._offset_x + grid_width and
                self._offset_y <= my < self._offset_y + grid_height):
            return None
        slot_size = self._cell_size + 2 * CELL_MARGIN
        col = int((mx - self._offset_x) // slot_size)
        row = int((my - self._offset_y) // slot_size)
        if 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS:
            is_label = (row == 0 or row == BOARD_ROWS - 1 or
                        col == 0 or col == BOARD_COLS - 1) and \
                (row, col) not in NEBULAS.values() and \
                not self._is_timer_cell(row, col)
            if not is_label:
                return (row, col)
        return None

    def update_pieces_from_board(self, board):
        self.pieces = {}
        self.shield_positions.clear()
        
        all_pieces = board.get_all_pieces()
        for row, col, piece in all_pieces:
            self.pieces[(row, col)] = {
                'type': piece.type,
                'color': piece.color,
                'id': piece.id
            }
            if piece.type == PieceType.SHIELD:
                self.shield_positions.add((row, col))

    def update_from_game_state(self, game_state):
        """Оновити візуалізацію на основі стану гри"""
        self.paralyzed_cells = game_state.paralyzed_pieces.copy()
        
        if game_state.paralysis_selection:
            target_pos = game_state.paralysis_selection['target_pos']
            landing_squares = game_state.move_calculator.get_paralysis_landing_squares(
                target_pos[0], target_pos[1]
            )
            self.paralysis_landing_dots = set(landing_squares)
        else:
            self.paralysis_landing_dots.clear()
        
        # Підсвічуємо місяці, якщо активовано подвійний хід
        self.highlighted_moons.clear()
        current_player = game_state.current_player
        color_key = "white" if current_player == PieceColor.WHITE else "black"
        
        # Підсвічуємо місяці, якщо подвійний хід активовано (назавжди після загибелі аристократів)
        if game_state.moon_double_move_active[color_key]:
            # Знаходимо всі місяці поточного гравця
            # get_all_pieces_of_type повертає список позицій (row, col)
            moon_positions = game_state.board.get_all_pieces_of_type(PieceType.MOON, current_player)
            for row, col in moon_positions:
                self.highlighted_moons.add((row, col))
        
        self.update()

    def update_resurrection_corners(self, game_state):
        if not game_state or not game_state.move_calculator:
            return
        
        self.resurrection_corners.clear()
        
        current_player = game_state.current_player
        
        # Воскресіння пішаків
        if game_state.can_resurrect_pawn(current_player):
            positions = game_state.move_calculator.get_resurrection_positions(current_player)
            for row, col in positions:
                self.add_resurrection_corner(row, col, "green")
        
        # Воскресіння через Всадника (душі коня, офіцера, всадника)
        for row, col, piece_type, is_green, piece_color in game_state.soul_corners:
            # Показуємо куточки тільки для поточного гравця
            if piece_color == current_player:
                color = "green" if is_green else "gray"
                self.add_resurrection_corner(row, col, color)

    def update_eye_enhancement_corners(self, game_state):
        self.eye_enhancement_corners.clear()
        if game_state and game_state.eye_enhancement_selection:
            selection_data = game_state.eye_enhancement_selection
            if selection_data["player"] == game_state.current_player:
                for r, c in selection_data["selectable_eyes"]:
                    if (r, c) in selection_data["selected_pos"]:
                        self.eye_enhancement_corners[(r, c)] = EYE_ENHANCEMENT_COLOR.lighter(150).name()
                    else:
                        self.eye_enhancement_corners[(r, c)] = EYE_ENHANCEMENT_COLOR.name()
        self.update()


    def update_nebula_timers(self, game_state):
        if not game_state:
            return
        
        self.nebula_timers.clear()
        
        for piece_id, timer_info in game_state.nebula_piece_timers.items():
            timer_value = timer_info.get("timer", 0)
            nebula_pos = timer_info.get("nebula_pos")
            
            if nebula_pos:
                for nebula_name, (neb_row, neb_col) in NEBULAS.items():
                    if (neb_row, neb_col) == nebula_pos:
                        timer_name = {
                            "top_left": "top_left",
                            "top_right": "top_right", 
                            "bottom_left": "bottom_left",
                            "bottom_right": "bottom_right"
                        }.get(nebula_name)
                        
                        if timer_name:
                            self.nebula_timers[timer_name] = timer_value
                        break
        
        self.update()

    def add_attack_dot(self, row: int, col: int):
        self.attack_dots.add((row, col))
        self.update()

    def add_move_dot(self, row: int, col: int):
        self.move_dots.add((row, col))
        self.update()
    
    def add_attack_move_dot(self, row: int, col: int):
        """Додає крапку ходу з можливістю атаки (синя з червоним контуром)"""
        self.attack_move_dots.add((row, col))
        self.update()

    def add_swap_dot(self, row: int, col: int):
        self.swap_dots.add((row, col))
        self.update()

    def add_teleport_dot(self, row: int, col: int):
        self.teleport_dots.add((row, col))
        self.update()

    def set_cell_paralyzed(self, row: int, col: int, duration: int):
        self.paralyzed_cells[(row, col)] = duration
        self.update()

    def remove_cell_paralysis(self, row: int, col: int):
        self.paralyzed_cells.pop((row, col), None)
        self.update()

    def add_resurrection_corner(self, row: int, col: int, color: str = "green"):
        self.resurrection_corners[(row, col)] = color
        self.update()

    def remove_resurrection_corner(self, row: int, col: int):
        self.resurrection_corners.pop((row, col), None)
        self.update()

    def set_moon_highlighted(self, row: int, col: int, active: bool = True):
        if active:
            self.highlighted_moons.add((row, col))
        else:
            self.highlighted_moons.discard((row, col))
        self.update()

    def set_fog_ring(self, row: int, col: int, player_color: str):
        self.fog_cells[(row, col)] = player_color
        self.update()

    def remove_fog_ring(self, row: int, col: int):
        self.fog_cells.pop((row, col), None)
        self.update()

    def set_nebula_owner(self, nebula_name: str, owner: str):
        if nebula_name in self.nebula_ownership:
            self.nebula_ownership[nebula_name] = owner
            self.update()

    def set_king_in_check(self, row: int, col: int):
        """Встановлює позицію короля під шахом для відображення жовтої рамки"""
        self.king_in_check_position = (row, col)
        self.update()

    def clear_king_in_check(self):
        """Очищає позицію короля під шахом"""
        self.king_in_check_position = None
        self.update()

    def clear_all_visual_effects(self):
        self.attack_dots.clear()
        self.move_dots.clear()
        self.swap_dots.clear()
        self.teleport_dots.clear()
        self.paralyzed_cells.clear()
        self.paralysis_landing_dots.clear()
        self.resurrection_corners.clear()
        self.eye_enhancement_corners.clear()
        self.highlighted_moons.clear()
        self.king_in_check_position = None
        self.fog_cells.clear()
        self.shield_positions.clear()
        self.nebula_timers.clear()
        self.update()

    def clear_move_indicators(self):
        self.attack_dots.clear()
        self.move_dots.clear()
        self.attack_move_dots.clear()  # Очищаємо нові крапки
        self.swap_dots.clear()
        self.teleport_dots.clear()
        self.update()

    def set_selected_piece(self, row: int, col: int):
        self.selected_piece_position = (row, col) if row is not None else None
        self.update()

    def clear_selected_piece(self):
        self.selected_piece_position = None
