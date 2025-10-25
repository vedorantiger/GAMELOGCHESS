# -*- coding: utf-8 -*-
from PyQt6.QtGui import QColor
from enum import Enum, IntEnum

# --- Розміри дошки ---
# ЄДИНА СИСТЕМА КООРДИНАТ: 22x20 (включає туманності та мітки)
BOARD_ROWS = 22
BOARD_COLS = 20

# Позиції туманностей в єдиній системі координат
NEBULAS = {
    "top_left": (0, 0),#ігрова клітинка, яка стає доступна після відкритя
    "top_right": (0, 19),#ігрова клітинка, яка стає доступна після відкритя
    "bottom_left": (21, 0),#ігрова клітинка, яка стає доступна після відкритя
    "bottom_right": (21, 19)#ігрова клітинка, яка стає доступна після відкритя
}

# Позиції таймерів (поза основною дошкою)
TIMER_CELLS = {
    "top_left_timer": (0, -1),#не ігрова клітинка, яка показує таймер для туманності (0, 0)
    "top_right_timer": (0, 20), #не ігрова клітинка, яка показує таймер для туманності (0, 19)
    "bottom_left_timer": (21, -1), #не ігрова клітинка, яка показує таймер для туманності (21, 0)
    "bottom_right_timer": (21, 20)#не ігрова клітинка, яка показує таймер для туманності (21, 19)
}

# Мітки для координат
LETTERS_BOTTOM = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']
NUMBERS_LEFT = [str(i) for i in range(20, 0, -1)]

class PieceType(IntEnum):
    EMPTY = 0
    PAWN = 1
    ROOK = 2
    KNIGHT = 3
    BISHOP = 4
    QUEEN = 5
    KING = 6
    LIGHTNING = 7
    MOON = 8
    TEMPLE = 9
    ARISTOCRAT = 10
    RIDER = 11
    TRIUMPHATOR = 12
    FURY = 13
    EYE = 14
    SHIELD = 15

class PieceColor(IntEnum):
    WHITE = 1
    BLACK = -1

class CellType(Enum):
    STANDARD = 0
    NEBULA = 1
    LABEL = 2

# ID діапазони для фігур
WHITE_ID_START = 1000
WHITE_ID_END = 1099
BLACK_ID_START = 2000
BLACK_ID_END = 2099

# --- Кольори дошки та фігур ---
DARK_SQUARE_COLOR = QColor(0, 0, 0)
LIGHT_SQUARE_COLOR = QColor(255, 255, 255)
BACKGROUND_COLOR = QColor(255, 255, 255)
BLACK_BORDER_COLOR = QColor(0, 0, 0)

# --- Кольори для різних типів ходів ---
ATTACK_DOT_COLOR = QColor(255, 0, 0)      # Червона для атак
MOVE_DOT_COLOR = QColor(0, 127, 255)      # Синя для звичайних ходів (включаючи вхід у туманність)
SWAP_DOT_COLOR = QColor(200, 200, 200, 200)  # Сіра для обмінів
TELEPORT_DOT_COLOR = QColor(148, 0, 211)  # Фіолетова для телепортації

# --- Налаштування контурів клітинок ---
CELL_BORDER_OPTIONS = [
    "На всіх клітинках",
    "Не малювати", 
    "Тільки на білих",
    "Тільки на чорних"
]
DEFAULT_CELL_BORDER_OPTION = "На всіх клітинках"

# --- Спеціальні ефекти ---
PARALYSIS_COLOR = QColor(255, 0, 0, 50)
RESURRECTION_COLOR_GREEN = QColor(76, 175, 80)
RESURRECTION_COLOR_GRAY = QColor(128, 128, 128)
EYE_ENHANCEMENT_COLOR = QColor(0, 255, 0, 180) # Green for Eye enhancement
MOON_HIGHLIGHT_COLOR = QColor(255, 255, 0)

FOG_RING_WHITE_COLOR = QColor(255, 255, 255, 255)
FOG_RING_BLACK_COLOR = QColor(0, 0, 0, 255)

# --- Кольори тексту ---
LABEL_TEXT_COLOR = QColor(0, 0, 0)
TIMER_TEXT_COLOR = QColor(255, 0, 0)
WHITE_COLOR = QColor(255, 255, 255)
RED_SEMI_TRANSPARENT = QColor(255, 0, 0, 180)
RED_SOLID = QColor(255, 0, 0)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# --- Теми дошки ---
BOARD_THEMES = [
    {"name": "Класична монохромність", "light": hex_to_rgb("#F8F8F8"), "dark": hex_to_rgb("#6C6C6C")},
    {"name": "Оливковий сад", "light": hex_to_rgb("#EBECD0"), "dark": hex_to_rgb("#739552")},
    {"name": "Піщана дюна", "light": hex_to_rgb("#D0B486"), "dark": hex_to_rgb("#815833")},
    {"name": "Сталева елегантність", "light": hex_to_rgb("#687182"), "dark": hex_to_rgb("#2C313F")},
    {"name": "Медова карамель", "light": hex_to_rgb("#EDD6B0"), "dark": hex_to_rgb("#B88762")},
    {"name": "Морський бриз", "light": hex_to_rgb("#D4DFE5"), "dark": hex_to_rgb("#779AAF")},
    {"name": "Кавова гармонія", "light": hex_to_rgb("#B99E79"), "dark": hex_to_rgb("#725239")},
    {"name": "Небесна далечінь", "light": hex_to_rgb("#F0F1F0"), "dark": hex_to_rgb("#7598AE")},
    {"name": "Срібний туман", "light": hex_to_rgb("#DBE5E6"), "dark": hex_to_rgb("#9AA1A1")},
    {"name": "Кам'яна фортеця", "light": hex_to_rgb("#B4B0A9"), "dark": hex_to_rgb("#5D5B59")},
    {"name": "Бурштинове сонце", "light": hex_to_rgb("#F1CDA3"), "dark": hex_to_rgb("#C46D37")},
    {"name": "Весняний сад", "light": hex_to_rgb("#F3F3F4"), "dark": hex_to_rgb("#6A9B41")},
    {"name": "Пергаментний манускрипт", "light": hex_to_rgb("#C6C0AA"), "dark": hex_to_rgb("#66615C")},
    {"name": "Аметистова мрія", "light": hex_to_rgb("#F0F1F0"), "dark": hex_to_rgb("#8476BA")},
    {"name": "Місячне сяйво", "light": hex_to_rgb("#D9E4E8"), "dark": hex_to_rgb("#696867")},
    {"name": "Смарагдовий ліс", "light": hex_to_rgb("#E9E8E5"), "dark": hex_to_rgb("#316448")},
    {"name": "Горіхова деревина", "light": hex_to_rgb("#C59C65"), "dark": hex_to_rgb("#6B3926")},
    {"name": "Теракотова кераміка", "light": hex_to_rgb("#E6C39F"), "dark": hex_to_rgb("#875230")},
    {"name": "Балтійське море", "light": hex_to_rgb("#EAE9D2"), "dark": hex_to_rgb("#4B7399")},
    {"name": "Рожевий зефір", "light": hex_to_rgb("#FEFFFE"), "dark": hex_to_rgb("#FBD9E1")},
    {"name": "Вишневий контраст", "light": hex_to_rgb("#C74C51"), "dark": hex_to_rgb("#303030")},
    {"name": "Дубова кора", "light": hex_to_rgb("#A2A2A2"), "dark": hex_to_rgb("#AC8F6D")},
    {"name": "Платинова витонченість", "light": hex_to_rgb("#D8D9D8"), "dark": hex_to_rgb("#A8A9A8")},
    {"name": "Графітовий мінімалізм", "light": hex_to_rgb("#BFC0C0"), "dark": hex_to_rgb("#554D49")},
    {"name": "Золотий мед", "light": hex_to_rgb("#FAE4AE"), "dark": hex_to_rgb("#D18815")},
    {"name": "Вугільна елегантність", "light": hex_to_rgb("#8B8A89"), "dark": hex_to_rgb("#696867")},
    {"name": "Пшенична нива", "light": hex_to_rgb("#E1DEC0"), "dark": hex_to_rgb("#BBA469")},
    {"name": "Корал рифу", "light": hex_to_rgb("#F5DBC3"), "dark": hex_to_rgb("#BB5746")},
    {"name": "Пустельний пісок", "light": hex_to_rgb("#CEC0B2"), "dark": hex_to_rgb("#C3AD9A")},
    {"name": "Абрикосовий нектар", "light": hex_to_rgb("#EDCBA5"), "dark": hex_to_rgb("#D8A46D")},
    {"name": "Лазурна хмара", "light": hex_to_rgb("#F2F6FA"), "dark": hex_to_rgb("#5596F2")},
    {"name": "Рожева орхідея", "light": hex_to_rgb("#F5F0F1"), "dark": hex_to_rgb("#EC94A4")},
    {"name": "Абсолютний контраст", "light": hex_to_rgb("#FFFFFF"), "dark": hex_to_rgb("#000000")},
    {"name": "Лавандове поле", "light": hex_to_rgb("#E8E3F5"), "dark": hex_to_rgb("#7B68A6")},
    {"name": "Малахітова розкіш", "light": hex_to_rgb("#D4F1E8"), "dark": hex_to_rgb("#2E7D6B")},
    {"name": "Марсіанський захід", "light": hex_to_rgb("#FFE5D9"), "dark": hex_to_rgb("#E85D4E")},
    {"name": "Північне сяйво", "light": hex_to_rgb("#E0F4FF"), "dark": hex_to_rgb("#4A90A4")},
    {"name": "Шоколадний трюфель", "light": hex_to_rgb("#D7C4B7"), "dark": hex_to_rgb("#3E2723")},
    {"name": "Сакура в цвіту", "light": hex_to_rgb("#FFE8ED"), "dark": hex_to_rgb("#D47B93")},
    {"name": "Бірюзова лагуна", "light": hex_to_rgb("#E0F5F3"), "dark": hex_to_rgb("#00897B")},
    {"name": "Вінтажний папір", "light": hex_to_rgb("#F5E6D3"), "dark": hex_to_rgb("#8B6F47")},
    {"name": "Індиго ніч", "light": hex_to_rgb("#E8EAF6"), "dark": hex_to_rgb("#3F51B5")},
    {"name": "Оксамитова троянда", "light": hex_to_rgb("#FFDDE1"), "dark": hex_to_rgb("#AD1457")},
    {"name": "Цитрусовий фреш", "light": hex_to_rgb("#FFF9E6"), "dark": hex_to_rgb("#FF9800")},
    {"name": "Вулканічний попіл", "light": hex_to_rgb("#ECEFF1"), "dark": hex_to_rgb("#455A64")},
    {"name": "Королівський пурпур", "light": hex_to_rgb("#F3E5F5"), "dark": hex_to_rgb("#6A1B9A")},
    {"name": "Оливкова гілка", "light": hex_to_rgb("#F0F4C3"), "dark": hex_to_rgb("#689F38")},
    {"name": "Полярна ніч", "light": hex_to_rgb("#FAFAFA"), "dark": hex_to_rgb("#37474F")},
    {"name": "Золотий янтар", "light": hex_to_rgb("#FFF8E1"), "dark": hex_to_rgb("#FFA000")},
    {"name": "Космічна глибина", "light": hex_to_rgb("#E1E2E1"), "dark": hex_to_rgb("#1A237E")},
]

DEFAULT_BOARD_THEME_INDEX = 0

# --- Розміри та відступи ---
CELL_MARGIN = 1
MIN_CELL_SIZE = 10

DOT_SIZE_RATIO = 0.5
CORNER_SIZE_RATIO = 0.6
PARALYSIS_INDICATOR_SIZE_RATIO = 0.5
FOG_RING_SIZE_RATIO = 0.4
FOG_RING_WIDTH_RATIO = 0.08

# --- Шрифти UI ---
UI_FONT_FAMILY = "Segoe UI"

TITLE_FONT_SIZE = 48
SUBTITLE_FONT_SIZE = 28
MENU_FONT_SIZE = 18
BUTTON_FONT_SIZE = 16
SMALL_TEXT_FONT_SIZE = 14

# --- Розміри UI елементів ---
UI_BACKGROUND_COLOR = "#f8f9fa"

INFO_PANEL_WIDTH = 210
INFO_LABEL_HEIGHT = 28
INFO_BUTTON_HEIGHT = 28
INFO_SPACING = 6
INFO_SEPARATOR_HEIGHT = 20

INFO_LABEL_BACKGROUND = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f0f0, stop:1 #e0e0e0)"
INFO_LABEL_BORDER = "1px solid #ccc"
INFO_LABEL_TEXT_COLOR = "#333"

# --- Налаштування тем ---
THEME_GRID_COLS = 10
THEME_MINI_BOARD_SIZE = 60
THEME_MINI_CELL_SIZE = 26

THEME_NORMAL_BG = "#f8f8f8"
THEME_NORMAL_BORDER = "2px solid #333333"
THEME_HOVER_BG = "#FFFFE0"
THEME_HOVER_BORDER = "5px solid #FF4500"
THEME_SELECTED_BG = "#FFE4B5"
THEME_SELECTED_BORDER = "6px solid #FF8C00"
THEME_SELECTED_RADIUS = "4px"

# --- Налаштування фонів ---
BACKGROUND_CARD_WIDTH = 200
BACKGROUND_CARD_HEIGHT = 150
BACKGROUND_PREVIEW_WIDTH = 180
BACKGROUND_PREVIEW_HEIGHT = 100
BACKGROUND_GRID_COLS = 4
BACKGROUND_CARD_SPACING = 15

BACKGROUND_NORMAL_BG = "white"
BACKGROUND_NORMAL_BORDER = "2px solid #cccccc"
BACKGROUND_HOVER_BORDER = "2px solid #4A90E2"
BACKGROUND_SELECTED_BG = "#f0f8ff"
BACKGROUND_SELECTED_BORDER = "3px solid #4A90E2"
BACKGROUND_CARD_RADIUS = "10px"

# --- Розміри кнопок ---
UNIVERSAL_BUTTON_HEIGHT = 40
BUTTON_WIDTH_LARGE = 380
BUTTON_WIDTH_MEDIUM = 300
BUTTON_WIDTH_SMALL = 200

SIDEBAR_BUTTON_HEIGHT = 28
SIDEBAR_BUTTON_WIDTH = 210
SIDEBAR_PANEL_WIDTH = 210

MAIN_MENU_BUTTON_HEIGHT = 40
MAIN_MENU_BUTTON_WIDTH = 380
BACK_BUTTON_HEIGHT = 40
BACK_BUTTON_WIDTH = 200

# --- Стилі кнопок ---
BUTTON_BORDER_RADIUS = 0
BUTTON_PADDING_VERTICAL = 8
BUTTON_PADDING_HORIZONTAL = 12
BUTTON_MARGIN = 0

BUTTON_PRIMARY_COLOR = "#ffffff"
BUTTON_PRIMARY_GRADIENT_END = "#ffffff"
BUTTON_TEXT_COLOR = "#000000"
BUTTON_BORDER_COLOR = "#000000"

BUTTON_HOVER_COLOR = "rgba(135, 206, 235, 0.8)"
BUTTON_HOVER_GRADIENT_END = "rgba(135, 206, 235, 0.8)"
BUTTON_HOVER_TEXT_COLOR = "#000000"
BUTTON_HOVER_BORDER_COLOR = "#000000"

BUTTON_PRESSED_COLOR = "#e0e0e0"
BUTTON_PRESSED_GRADIENT_END = "#e0e0e0"
BUTTON_PRESSED_TEXT_COLOR = "#000000"
BUTTON_PRESSED_BORDER_COLOR = "#000000"

BUTTON_DISABLED_COLOR = "#ffffff"
BUTTON_DISABLED_GRADIENT_END = "#ffffff"
BUTTON_DISABLED_TEXT_COLOR = "#000000"
BUTTON_DISABLED_BORDER_COLOR = "#000000"

BUTTON_FONT_FAMILY = "Arial"
BUTTON_FONT_WEIGHT = 400
BUTTON_HOVER_FONT_WEIGHT = 400

# --- Назви фігур українською ---
PIECE_NAMES_UA = {
    PieceType.PAWN: "пішак",
    PieceType.ROOK: "тура", 
    PieceType.KNIGHT: "кінь",
    PieceType.BISHOP: "слон",
    PieceType.QUEEN: "королева",
    PieceType.KING: "король",
    PieceType.TEMPLE: "храм",
    PieceType.ARISTOCRAT: "аристократ",
    PieceType.RIDER: "всадник",
    PieceType.LIGHTNING: "блискавка",
    PieceType.MOON: "місяць",
    PieceType.TRIUMPHATOR: "тріумфатор",
    PieceType.FURY: "фурія",
    PieceType.SHIELD: "щит",
    PieceType.EYE: "око"
}

# --- Відповідність фігур до файлів ---
PIECE_FILE_MAP = {
    PieceType.ARISTOCRAT: "aristocrat.svg",
    PieceType.BISHOP: "bishop.svg",
    PieceType.EYE: "eye.svg",
    PieceType.FURY: "fury.svg",
    PieceType.KING: "king.svg",
    PieceType.KNIGHT: "knight.svg",
    PieceType.LIGHTNING: "lightning.svg",
    PieceType.MOON: "moon.svg",
    PieceType.PAWN: "pawn.svg",
    PieceType.QUEEN: "queen.svg",
    PieceType.RIDER: "rider.svg",
    PieceType.ROOK: "rook.svg",
    PieceType.SHIELD: "shield.svg",
    PieceType.TEMPLE: "temple.svg",
    PieceType.TRIUMPHATOR: "triumphator.svg",
}