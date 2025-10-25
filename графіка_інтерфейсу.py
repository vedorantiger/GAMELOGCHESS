from PyQt6.QtWidgets import (
    QApplication, QStackedWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QGridLayout,
    QComboBox, QSlider, QGroupBox, QScrollArea,
    QSizePolicy, QSpacerItem, QFrame, QTabWidget, QRadioButton, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette, QBrush, QPainter, QColor, QPen
import sys
import datetime
from pathlib import Path
from налаштування import (
    TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, MENU_FONT_SIZE,
    BUTTON_FONT_SIZE, SMALL_TEXT_FONT_SIZE,
    UNIVERSAL_BUTTON_HEIGHT, BUTTON_WIDTH_LARGE,
    BUTTON_WIDTH_MEDIUM, BUTTON_WIDTH_SMALL,
    SIDEBAR_BUTTON_HEIGHT, SIDEBAR_BUTTON_WIDTH,
    BOARD_THEMES, DEFAULT_BOARD_THEME_INDEX,
    BUTTON_PRIMARY_COLOR, BUTTON_TEXT_COLOR,
    BUTTON_HOVER_COLOR, BUTTON_BORDER_COLOR
)
from логування import game_logger, game_print, activate_game_logging, start_new_game
from стан_гри import GameState, PieceColor, is_nebula_coordinates, coordinates_to_chess_notation
from правила_фігур import MoveCalculator
from графіка_гри import BoardWidget
from дошка import PieceType

class TitleWithBackground(QWidget):
    def __init__(self, text, font_size=TITLE_FONT_SIZE):
        super().__init__()
        self.text = text
        self.font_size = font_size
        
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        self.setFont(font)
        
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(text)
        
        horizontal_padding = 30
        vertical_padding = 20
        self.setFixedHeight(text_rect.height() + vertical_padding * 2)
        self.setMinimumWidth(text_rect.width() + horizontal_padding * 2)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        font = QFont("Arial", self.font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(self.text)
        
        widget_rect = self.rect()
        
        background_color = QColor(255, 255, 255, 120)
        painter.setBrush(QBrush(background_color))
        
        border_color = QColor(255, 255, 255, 180)
        painter.setPen(QPen(border_color, 2))
        
        corner_radius = 15
        from PyQt6.QtCore import QRect
        background_rect = QRect(5, 5, widget_rect.width() - 10, widget_rect.height() - 10)
        painter.drawRoundedRect(background_rect, corner_radius, corner_radius)
        
        text_rect_for_draw = QRect(0, 0, widget_rect.width(), widget_rect.height())
        
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    offset_rect = QRect(text_rect_for_draw.x() + dx, text_rect_for_draw.y() + dy, 
                                      text_rect_for_draw.width(), text_rect_for_draw.height())
                    painter.drawText(offset_rect, Qt.AlignmentFlag.AlignCenter, self.text)
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(text_rect_for_draw, Qt.AlignmentFlag.AlignCenter, self.text)

class StyledButton(QPushButton):
    def __init__(self, text: str, width: int = BUTTON_WIDTH_MEDIUM,
                 height: int = UNIVERSAL_BUTTON_HEIGHT, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(width, height)
        self._apply_style()

    def _apply_style(self):
        style = f"""
            QPushButton {{
                background-color: {BUTTON_PRIMARY_COLOR};
                color: {BUTTON_TEXT_COLOR};
                border: 1px solid {BUTTON_BORDER_COLOR};
                border-radius: 5px;
                padding: 5px;
                font-size: {BUTTON_FONT_SIZE}px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER_COLOR};
            }}
            QPushButton:disabled {{
                background-color: #d3d3d3;
                color: #808080;
                border-color: #a0a0a0;
            }}
        """
        self.setStyleSheet(style)

class BoardThemeSelector(QWidget):
    theme_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.selected_theme = DEFAULT_BOARD_THEME_INDEX
        self.mini_boards = []
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = TitleWithBackground("Оберіть тему дошки", 16)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(1)

        for i, theme in enumerate(BOARD_THEMES):
            row = i // 10
            col = i % 10
            mini_board = self._create_mini_board(theme, i)
            self.mini_boards.append(mini_board)
            grid_layout.addWidget(mini_board, row, col)

        grid_widget.setLayout(grid_layout)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)
        self.setLayout(layout)

    def _create_mini_board(self, theme, index):
        container = QWidget()
        container.setFixedSize(70, 70)
        container.setCursor(Qt.CursorShape.PointingHandCursor)
        container.setToolTip(theme["name"])
        
        container.theme = theme
        container.index = index
        container.parent_selector = self
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        
        mini_board = QWidget()
        mini_board.setFixedSize(60, 60)
        
        container._update_style = lambda: self._update_mini_board_style(container)
        container._update_style()
        
        def on_enter(event):
            if container.index != self.selected_theme:
                container.is_hovered = True
                container._update_style()
            
        def on_leave(event):
            container.is_hovered = False
            container._update_style()
            
        def on_click(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.set_theme(container.index)
        
        container.enterEvent = on_enter
        container.leaveEvent = on_leave
        container.mousePressEvent = on_click
        container.is_hovered = False
        
        def paint_board(event):
            painter = QPainter(mini_board)
            cell_size = 26
            start_x = 4
            start_y = 4
            light_color = QColor(*theme["light"])
            dark_color = QColor(*theme["dark"])

            for row in range(2):
                for col in range(2):
                    x = start_x + col * cell_size
                    y = start_y + row * cell_size
                    is_dark = (row + col) % 2 == 0
                    color = dark_color if is_dark else light_color
                    painter.fillRect(x, y, cell_size, cell_size, color)

                    painter.setPen(QColor(0, 0, 0))
                    painter.drawRect(x, y, cell_size, cell_size)
        
        mini_board.paintEvent = paint_board
        layout.addWidget(mini_board)
        
        return container

    def _update_mini_board_style(self, container):
        is_selected = container.index == self.selected_theme
        is_hovered = getattr(container, 'is_hovered', False)
        
        if is_selected:
            style = """
                QWidget {
                    border: 3px solid #FF9800;
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.95);
                }
            """
        elif is_hovered:
            style = """
                QWidget {
                    border: 3px solid #4CAF50;
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.85);
                }
            """
        else:
            style = """
                QWidget {
                    border: 3px solid transparent;
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.7);
                }
            """
        container.setStyleSheet(style)

    def set_theme(self, index):
        self.selected_theme = index
        for mini_board in self.mini_boards:
            if hasattr(mini_board, '_update_style'):
                mini_board._update_style()
        self.theme_changed.emit(index)
        game_logger.info(f"Вибрана тема дошки: {BOARD_THEMES[index]['name']}")

    def update_selection_display(self):
        for mini_board in self.mini_boards:
            if hasattr(mini_board, '_update_style'):
                mini_board._update_style()

class BackgroundSelector(QWidget):
    background_changed = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.selected_background = "1.jpg"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("Вибір фону програми")
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Виберіть фон, який буде відображатися у всій програмі під дошкою та меню")
        desc.setFont(QFont("Segoe UI", 14))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        backgrounds = []

        bg_path = Path("ресурси/зображення/фони")
        if bg_path.exists():
            for bg_file in sorted(bg_path.glob("*.jpg")):
                backgrounds.append((bg_file.name, bg_file.stem.title(), str(bg_file)))
            for bg_file in sorted(bg_path.glob("*.png")):
                backgrounds.append((bg_file.name, bg_file.stem.title(), str(bg_file)))

        for i, (bg_id, name, path) in enumerate(backgrounds):
            row = i // 4
            col = i % 4
            card = self._create_background_card(bg_id, name, path)
            grid_layout.addWidget(card, row, col)

        grid_widget.setLayout(grid_layout)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        back_btn = StyledButton("Назад", BUTTON_WIDTH_SMALL)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def _create_background_card(self, bg_id, name, path):
        class BackgroundCard(QFrame):
            def __init__(self, parent_selector, bg_id, name, path):
                super().__init__()
                self.parent_selector = parent_selector
                self.bg_id = bg_id
                self.bg_name = name
                self.bg_path = path
                self.setFixedSize(200, 150)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self._setup_ui()
                self._update_style()

            def _setup_ui(self):
                layout = QVBoxLayout()
                layout.setContentsMargins(10, 10, 10, 10)
                layout.setSpacing(8)

                self.preview = QLabel()
                self.preview.setFixedSize(180, 100)
                self.preview.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")

                if self.bg_path:
                    pixmap = QPixmap(self.bg_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(180, 100,
                                                    Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation)
                        self.preview.setPixmap(scaled_pixmap)
                        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

                layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)

                label = QLabel(self.bg_name)
                label.setFont(QFont("Segoe UI", 10))
                label.setStyleSheet("color: #333333;")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(label)

                self.setLayout(layout)

            def _update_style(self):
                is_selected = self.bg_id == self.parent_selector.selected_background
                if is_selected:
                    style = "border: 3px solid #007bff; border-radius: 8px; background-color: #e7f3ff;"
                else:
                    style = "border: 1px solid #cccccc; border-radius: 8px; background-color: #f8f9fa;"
                self.setStyleSheet(style)

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.parent_selector.set_background(self.bg_id)

        return BackgroundCard(self, bg_id, name, path)

    def set_background(self, bg_id):
        self.selected_background = bg_id
        for widget in self.findChildren(QFrame):
            if hasattr(widget, '_update_style'):
                widget._update_style()
        self.background_changed.emit(bg_id)
        game_logger.info(f"Вибрано фон: {bg_id}")

class GameInfoPanel(QWidget):
    settings_requested = pyqtSignal()
    new_game_requested = pyqtSignal()
    hint_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    menu_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(210)
        self._init_ui()
        self._start_timer()
        self.game_start_time = 0
        self.white_time = 0
        self.black_time = 0
        self.turn_start_time = 0

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 38, 0, 38)
        layout.setSpacing(6)

        self.info_labels = {}
        info_items = [
            ("game_time", "Час гри: 00:00"),
            ("current_turn", "Хід: білі"),
            ("white_time", "Час ходу білих: 00:00"),
            ("black_time", "Час ходу чорних: 00:00"),
            ("possible_moves", "Можливі ходи: 0"),
            ("possible_attacks", "Можливі атаки: 0")
        ]

        for key, text in info_items:
            label = QLabel(text)
            label.setFixedSize(210, 28)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont("Arial", 10))
            label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #dcdcdc; border-radius: 4px;")
            self.info_labels[key] = label
            layout.addWidget(label)

        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer)

        self.new_game_btn = StyledButton("Нова гра", 210, 28)
        self.settings_btn = StyledButton("Налаштування", 210, 28)
        self.hint_btn = StyledButton("Підказка", 210, 28)
        self.undo_btn = StyledButton("Повернути хід", 210, 28)
        self.menu_btn = StyledButton("Назад у меню", 210, 28)

        buttons = [
            (self.new_game_btn, self.new_game_requested),
            (self.settings_btn, self.settings_requested),
            (self.hint_btn, self.hint_requested),
            (self.undo_btn, self.undo_requested),
            (self.menu_btn, self.menu_requested)
        ]

        for btn, signal in buttons:
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)

        self.hint_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.setLayout(layout)

    def _start_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_times)
        self.timer.start(1000)
        import time
        self.game_start_time = time.time()
        self.turn_start_time = time.time()

    def _update_times(self):
        import time
        current_time = time.time()
        game_duration = int(current_time - self.game_start_time)
        game_time_str = f"{game_duration // 60:02d}:{game_duration % 60:02d}"
        self.info_labels["game_time"].setText(f"Час гри: {game_time_str}")
        
        # Підрахунок часу ходу поточного гравця
        if hasattr(self, 'current_player_turn') and hasattr(self, 'turn_start_time'):
            turn_duration = int(current_time - self.turn_start_time)
            turn_time_str = f"{turn_duration // 60:02d}:{turn_duration % 60:02d}"
            if self.current_player_turn == "Білі":
                self.white_time += 1  # Додаємо секунду до часу білих
                white_time_str = f"{self.white_time // 60:02d}:{self.white_time % 60:02d}"
                self.info_labels["white_time"].setText(f"Час ходу білих: {white_time_str}")
            elif self.current_player_turn == "Чорні":
                self.black_time += 1  # Додаємо секунду до часу чорних
                black_time_str = f"{self.black_time // 60:02d}:{self.black_time % 60:02d}"
                self.info_labels["black_time"].setText(f"Час ходу чорних: {black_time_str}")

    def update_turn(self, current_player: str):
        import time
        self.info_labels["current_turn"].setText(f"Хід: {current_player}")
        self.current_player_turn = current_player
        self.turn_start_time = time.time()

    def update_move_counts(self, moves: int, attacks: int):
        self.info_labels["possible_moves"].setText(f"Можливі ходи: {moves}")
        self.info_labels["possible_attacks"].setText(f"Можливі атаки: {attacks}")

    def reset_timers(self):
        import time
        self.game_start_time = time.time()
        self.turn_start_time = time.time()
        self.white_time = 0
        self.black_time = 0
        self.current_player_turn = "Білі"  # Гра починається з білих

class MainMenuScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.buttons = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = TitleWithBackground("ВЕРШИТЕЛІ ЧАСУ")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(50)

        button_texts = ["Нова гра", "Завантажити гру", "Налаштування", "Правила", "Вихід"]
        for text in button_texts:
            btn = StyledButton(text, BUTTON_WIDTH_LARGE)
            self.buttons[text] = btn
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(10)
        
        self.buttons["Завантажити гру"].setEnabled(False)
        self.buttons["Правила"].setEnabled(False)
        self.setLayout(layout)

class GameModeSelectionScreen(QWidget):
    mode_selected = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = TitleWithBackground("Виберіть режим гри", SUBTITLE_FONT_SIZE)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)

        modes = [
            ("Людина проти Людини", "pvp"),
            ("Людина проти ШІ", "pve"),
            ("ШІ проти ШІ", "eve")
        ]
        for text, mode in modes:
            btn = StyledButton(text, BUTTON_WIDTH_LARGE)
            btn.clicked.connect(lambda checked, m=mode: self.mode_selected.emit(m))
            if mode == "eve":
                btn.setEnabled(False)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(10)
        
        layout.addSpacing(30)
        back_btn = StyledButton("Назад", BUTTON_WIDTH_SMALL)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

class ColorSelectionScreen(QWidget):
    color_selected = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = TitleWithBackground("Виберіть колір", SUBTITLE_FONT_SIZE)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)

        colors = ["Білі", "Чорні", "Випадково"]
        for color in colors:
            btn = StyledButton(color, BUTTON_WIDTH_LARGE)
            btn.clicked.connect(lambda checked, c=color: self._on_color_selected(c))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(10)
        
        layout.addSpacing(30)
        back_btn = StyledButton("Назад", BUTTON_WIDTH_SMALL)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def _on_color_selected(self, color: str):
        if color == "Випадково":
            import random
            color = random.choice(["Білі", "Чорні"])
        self.color_selected.emit(color)

class SettingsScreen(QWidget):
    back_requested = pyqtSignal()
    background_requested = pyqtSignal()
    board_theme_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = TitleWithBackground("Налаштування", SUBTITLE_FONT_SIZE)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(192, 192, 192, 0.5);
                background-color: transparent;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: rgba(240, 240, 240, 0.8);
                border: 1px solid rgba(192, 192, 192, 0.7);
                padding: 10px 20px;
                margin-right: 2px;
                border-radius: 5px 5px 0px 0px;
                color: black;
            }
            QTabBar::tab:selected {
                background-color: rgba(255, 255, 255, 0.9);
                border-bottom-color: rgba(255, 255, 255, 0.9);
                color: black;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: rgba(224, 224, 224, 0.9);
                color: black;
            }
        """)

        board_tab = self._create_board_tab()
        self.tab_widget.addTab(board_tab, "Дошка")

        background_tab = self._create_background_tab()
        self.tab_widget.addTab(background_tab, "Фони")

        misc_tab = self._create_misc_tab()
        self.tab_widget.addTab(misc_tab, "Різне")

        layout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        back_btn = StyledButton("Назад", BUTTON_WIDTH_SMALL)
        back_btn.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(back_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _create_board_tab(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = TitleWithBackground("Палітра кольорів дошки", 16)
        layout.addWidget(title)

        self.theme_selector = BoardThemeSelector()
        self.theme_selector.theme_changed.connect(self.board_theme_changed.emit)
        layout.addWidget(self.theme_selector)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_background_tab(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = TitleWithBackground("Вибір фону програми", 16)
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(10)

        self.background_cards = []
        self.selected_background_file = None

        self._create_background_grid(scroll_layout)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        widget.setLayout(layout)
        
        self._update_background_selection_styles()
        
        return widget

    def _create_background_grid(self, parent_layout):
        from pathlib import Path
        
        backgrounds_path = Path(__file__).parent / "ресурси" / "зображення" / "фони"
        
        background_files = []
        seen_names = set()
        
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        
        for file_path in backgrounds_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                name_without_ext = file_path.stem
                if name_without_ext not in seen_names:
                    background_files.append(file_path)
                    seen_names.add(name_without_ext)
        
        def numeric_sort_key(file_path):
            try:
                return int(file_path.stem)
            except ValueError:
                return float('inf')
        
        background_files.sort(key=numeric_sort_key)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        for i, bg_file in enumerate(background_files):
            row = i // 5
            col = i % 5
            
            background_card = self._create_background_card(bg_file)
            grid_layout.addWidget(background_card, row, col)
            
            self.background_cards.append(background_card)
        
        grid_widget = QWidget()
        grid_widget.setLayout(grid_layout)
        
        parent_layout.addWidget(grid_widget)
        
        parent_layout.addStretch()

    def _create_background_card(self, bg_file):
        card_widget = QWidget()
        card_widget.setFixedSize(240, 200)
        
        card_widget.bg_file = bg_file
        
        card_widget.setStyleSheet("""
            QWidget {
                border: 3px solid transparent;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
            }
            QWidget:hover {
                border-color: #4CAF50;
                background-color: rgba(255, 255, 255, 0.95);
            }
        """)
        
        layout = QVBoxLayout(card_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        image_label = QLabel()
        image_label.setFixedSize(220, 160)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #eee;
                background-color: rgba(249, 249, 249, 0.9);
                border-radius: 4px;
            }
        """)
        
        try:
            pixmap = QPixmap(str(bg_file))
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    220, 160,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                image_label.setText("❌")
                image_label.setStyleSheet("""
                    QLabel {
                        border: 1px solid #ffcccc;
                        background-color: #ffeeee;
                        border-radius: 4px;
                        color: #cc0000;
                        font-size: 40px;
                    }
                """)
                
        except Exception as e:
            image_label.setText("⚠️")
            image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ffcccc;
                    background-color: #fff8e1;
                    border-radius: 4px;
                    color: #ff9800;
                    font-size: 40px;
                }
            """)
        
        layout.addWidget(image_label)
        
        name_label = QLabel(bg_file.stem)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("""
            QLabel {
                border: none;
                font-size: 14px;
                color: #666;
                background: transparent;
                font-weight: bold;
            }
        """)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        def on_click(event):
            self._select_background(bg_file)
            
        card_widget.mousePressEvent = on_click
        card_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        
        card_widget.setToolTip(f"Клікніть для вибору фону: {bg_file.name}")
        
        return card_widget

    def _select_background(self, bg_file):
        background_name = bg_file.name
        game_logger.info(f"Вибрано фон: {background_name}")
        
        self.selected_background_file = bg_file.name
        
        for card in self.background_cards:
            if hasattr(card, 'bg_file') and card.bg_file.name == background_name:
                card.setStyleSheet("""
                    QWidget {
                        border: 3px solid #FF9800;
                        border-radius: 8px;
                        background-color: rgba(255, 255, 255, 0.95);
                    }
                    QWidget:hover {
                        border-color: #FF9800;
                        background-color: rgba(255, 255, 255, 0.98);
                    }
                """)
            else:
                card.setStyleSheet("""
                    QWidget {
                        border: 3px solid transparent;
                        border-radius: 8px;
                        background-color: rgba(255, 255, 255, 0.9);
                    }
                    QWidget:hover {
                        border-color: #4CAF50;
                        background-color: rgba(255, 255, 255, 0.95);
                    }
                """)
        
        widget = self
        while widget and not isinstance(widget, QStackedWidget):
            widget = widget.parent()
        
        if widget and hasattr(widget, '_apply_background'):
            widget._apply_background(background_name)
            if hasattr(widget, 'settings'):
                widget.settings.setValue("background_name", background_name)
                widget.current_background_name = background_name

    def _update_background_selection_styles(self):
        if not hasattr(self, 'background_cards') or not self.background_cards:
            return
            
        current_background = None
        widget = self
        while widget and not isinstance(widget, QStackedWidget):
            widget = widget.parent()
        
        if widget and hasattr(widget, 'settings'):
            current_background = widget.settings.value("background_name", "")
        
        for card in self.background_cards:
            if hasattr(card, 'bg_file'):
                if card.bg_file.name == current_background:
                    card.setStyleSheet("""
                        QWidget {
                            border: 3px solid #FF9800;
                            border-radius: 8px;
                            background-color: rgba(255, 255, 255, 0.95);
                        }
                        QWidget:hover {
                            border-color: #FF9800;
                            background-color: rgba(255, 255, 255, 0.98);
                        }
                    """)
                else:
                    card.setStyleSheet("""
                        QWidget {
                            border: 3px solid transparent;
                            border-radius: 8px;
                            background-color: rgba(255, 255, 255, 0.9);
                        }
                        QWidget:hover {
                            border-color: #4CAF50;
                            background-color: rgba(255, 255, 255, 0.95);
                        }
                    """)

    def _create_misc_tab(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = TitleWithBackground("Додаткові налаштування", 16)
        layout.addWidget(title)

        border_group = QGroupBox("Контури клітинок дошки")
        border_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: transparent;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: white;
                background-color: transparent;
            }
        """)
        border_layout = QVBoxLayout(border_group)
        border_layout.setSpacing(10)

        description = QLabel("Виберіть, на яких клітинках малювати протилежний контур:")
        description.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        description.setWordWrap(True)
        border_layout.addWidget(description)

        from налаштування import CELL_BORDER_OPTIONS, DEFAULT_CELL_BORDER_OPTION
        self.border_radio_buttons = []
        
        current_border_option = DEFAULT_CELL_BORDER_OPTION
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings()
            current_border_option = settings.value("cell_border_option", DEFAULT_CELL_BORDER_OPTION)
        except:
            pass
        
        for option in CELL_BORDER_OPTIONS:
            radio = QRadioButton(option)
            radio.setStyleSheet("""
                QRadioButton {
                    color: white;
                    font-size: 13px;
                    background-color: transparent;
                    spacing: 8px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 2px solid #888;
                    background-color: transparent;
                }
                QRadioButton::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #4CAF50;
                }
                QRadioButton::indicator:hover {
                    border: 2px solid #4CAF50;
                }
            """)
            
            if option == current_border_option:
                radio.setChecked(True)
            
            radio.toggled.connect(self._on_border_option_changed)
            
            self.border_radio_buttons.append(radio)
            border_layout.addWidget(radio)

        layout.addWidget(border_group)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _on_border_option_changed(self):
        selected_option = None
        for radio in self.border_radio_buttons:
            if radio.isChecked():
                selected_option = radio.text()
                break
        
        if selected_option:
            game_logger.info(f"Змінено налаштування контурів: {selected_option}")
            
            try:
                from PyQt6.QtCore import QSettings
                settings = QSettings()
                settings.setValue("cell_border_option", selected_option)
                settings.sync()
                
                main_window = self.window()
                if hasattr(main_window, 'board_widget'):
                    main_window.board_widget.update()
                elif hasattr(main_window, 'game_screen') and hasattr(main_window.game_screen, 'board_widget'):
                    main_window.game_screen.board_widget.update()
            except Exception as e:
                game_print(f"Помилка при збереженні налаштування контурів: {e}")
        
    def set_current_theme(self, index: int):
        self.theme_selector.set_theme(index)

class GameScreen(QWidget):
    back_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.game_state = GameState()
        self.game_mode = None
        self.player_color = None
        self._init_ui()
        self._setup_game()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(38, 5, 5, 5)
        layout.setSpacing(10)
        
        self.board_widget = BoardWidget()
        self.board_widget.cell_clicked.connect(self._on_cell_clicked)
        layout.addWidget(self.board_widget, stretch=1)

        self.info_panel = GameInfoPanel()
        self.info_panel.new_game_requested.connect(self.reset_game_state)
        self.info_panel.settings_requested.connect(self.settings_requested.emit)
        self.info_panel.menu_requested.connect(self.back_requested.emit)
        layout.addWidget(self.info_panel)

        self.setLayout(layout)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(50)

    def _setup_game(self):
        self.board_widget.set_game_state(self.game_state)
        self.board_widget.update_pieces_from_board(self.game_state.board)
    
    def _on_cell_clicked(self, row: int, col: int, mouse_pos=None):
        # Блокуємо ВСІ кліки, якщо гра закінчена
        if self.game_state.game_over:
            return
        
        # Handle special clicks first (resurrection, enhancement)
        if mouse_pos and self._is_enhancement_corner_click(row, col, mouse_pos):
            self._handle_enhancement_click(row, col)
            return

        # Якщо активне посилення Очей, НЕ обробляємо кліки на воскресіння
        if not self.game_state.eye_enhancement_selection:
            if mouse_pos and self._is_resurrection_corner_click(row, col, mouse_pos):
                self._handle_resurrection_click(row, col)
                return

        # КРИТИЧНО: Якщо активне посилення Очей, блокуємо ВСІ звичайні кліки на фігури
        # Дозволяємо тільки кліки на куточки посилення
        if self.game_state.eye_enhancement_selection:
            # Під час посилення можна клікати ТІЛЬКИ на куточки, інакше ігноруємо клік
            return

        # If we are in the middle of a paralysis move, the next click is a landing spot
        if self.game_state.paralysis_selection:
            # This click is for the landing spot. select_piece will handle it.
            if self.game_state.select_piece(row, col):
                # The paralysis move was successful and is now complete.
                self._on_move_made()
            else:
                # The click was not a valid landing spot, paralysis is cancelled.
                self.game_state.clear_selection()
                self._clear_move_indicators()
            self._update_display()
            return

        if self.game_state.is_piece_selected():
            # A piece is selected, try to make a move.
            move_result = self.game_state.make_move(row, col)

            # Check if the move initiated paralysis
            if move_result and self.game_state.paralysis_selection:
                # Yes. Don't treat as a full move. Just update UI to show landing dots.
                # Очищаємо всі попередні індикатори (сині крапки ходу та червоні крапки паралізації)
                self._clear_move_indicators()
                # Оновлюємо відображення з новими даними (точки приземлення)
                self.board_widget.update_from_game_state(self.game_state)
            elif move_result:
                # A regular move was completed.
                self._on_move_made()
            else:
                # The move was invalid. Try to select a new piece at the clicked location.
                if self.game_state.select_piece(row, col):
                    self._on_piece_selected(row, col)
                else:
                    # Not a valid new selection either, so clear everything.
                    self.game_state.clear_selection()
                    self._clear_move_indicators()
        else:
            # No piece is selected, so this click is an attempt to select one.
            if self.game_state.select_piece(row, col):
                self._on_piece_selected(row, col)
        
        self._update_display()

    def _is_resurrection_corner_click(self, row: int, col: int, mouse_pos) -> bool:
        if not self.game_state:
            return False
        return self.board_widget.is_click_on_resurrection_corner(mouse_pos, row, col)

    def _is_enhancement_corner_click(self, row: int, col: int, mouse_pos) -> bool:
        if not self.game_state:
            return False
        return self.board_widget.is_click_on_enhancement_corner(mouse_pos, row, col)

    def _handle_enhancement_click(self, row: int, col: int):
        if not self.game_state or not self.game_state.eye_enhancement_selection:
            return
        
        # Клік саме на куточок - викликаємо toggle вибору/зняття Ока
        selection_data = self.game_state.eye_enhancement_selection
        piece = self.game_state.get_piece_at(row, col)
        
        if not piece or piece.type != PieceType.EYE or piece.color != self.game_state.current_player:
            return
        
        piece_pos = (row, col)
        
        # Перевірка, чи це Око доступне для вибору
        if piece_pos not in selection_data["selectable_eyes"]:
            return
        
        # Toggle: якщо вже вибране - знімаємо, якщо ні - додаємо
        if piece_pos in selection_data["selected_pos"]:
            selection_data["selected_pos"].remove(piece_pos)
            chess_pos = coordinates_to_chess_notation(row, col)
            game_print(f"👁️ Око ID {piece.id} на {chess_pos} ({row}, {col}) знято з вибору.")
        else:
            # Додаємо Око до вибору (максимум 3)
            if len(selection_data["selected_pos"]) < 3:
                selection_data["selected_pos"].append(piece_pos)
                chess_pos = coordinates_to_chess_notation(row, col)
                game_print(f"👁️ Око ID {piece.id} на {chess_pos} ({row}, {col}) вибрано для посилення.")
        
        # Перевірка завершення посилення - ПІСЛЯ будь-якої зміни
        if len(selection_data["selected_pos"]) == 3:
            game_print("----- Посилення завершено -----")
            for r, c in selection_data["selected_pos"]:
                eye_piece = self.game_state.get_piece_at(r, c)
                if eye_piece:
                    eye_piece.is_enhanced = True
                    chess_pos_final = coordinates_to_chess_notation(r, c)
                    game_print(f"👁️ Око ID {eye_piece.id} на {chess_pos_final} ({r}, {c}) було посилено!")

            color_key = "white" if self.game_state.current_player == PieceColor.WHITE else "black"
            self.game_state.eye_enhancement_used[color_key] = True
            self.game_state.eye_enhancement_selection = None
            self.game_state.switch_player()
        
        self._update_display()

    def _handle_resurrection_click(self, row: int, col: int):
        if not self.game_state or not self.game_state.move_calculator:
            return
        
        current_player = self.game_state.current_player
        
        # Перевірка воскресіння душ через Всадника
        soul_resurrection = self._try_soul_resurrection(row, col, current_player)
        if soul_resurrection:
            return
        
        # Стандартне воскресіння пішака
        if (not self.game_state.can_resurrect_pawn(current_player) or
            not self.game_state.move_calculator.is_resurrection_row(row, current_player) or
            not self.game_state.board.is_square_empty(row, col)):
            self.board_widget.resurrection_corners.clear()
            self.board_widget.update()
            return
        
        is_free_action = self.game_state.resurrect_pawn(row, col, current_player)
        
        # Миттєво оновлюємо фігури на дошці
        self.board_widget.update_pieces_from_board(self.game_state.board)
        
        if is_free_action:
            self.game_state.clear_selection()
            self.board_widget.clear_move_indicators()
            # Оновлюємо куточки воскресіння для можливості другого воскресіння
            self.board_widget.update_resurrection_corners(self.game_state)
        else:
            self.game_state.switch_player()
            # Очищаємо куточки після другого воскресіння
            self.board_widget.resurrection_corners.clear()
        
        # Миттєво оновлюємо відображення
        self._update_display()
        self.board_widget.update()
        # Примусово оновлюємо інтерфейс Qt
        self.board_widget.repaint()
    
    def _try_soul_resurrection(self, row: int, col: int, current_player) -> bool:
        """Спроба воскресіння душі через Всадника. Повертає True, якщо воскресіння відбулося"""
        color_key = "white" if current_player == PieceColor.WHITE else "black"
        
        # Перевірка: чи вже використав воскресіння
        if self.game_state.performed_resurrection[color_key]:
            return False
        
        # Перевірка: чи є живі всадники
        rider_count = len(self.game_state.board.get_all_pieces_of_type(PieceType.RIDER, current_player))
        if rider_count == 0:
            return False
        
        # Шукаємо куточок на цій позиції
        for corner_row, corner_col, piece_type, is_green, piece_color in self.game_state.soul_corners:
            if corner_row == row and corner_col == col and piece_color == current_player:
                # Перевірка: чи зелений куточок (готовий до воскресіння)
                if not is_green:
                    game_print(f"⚠️ Умови для воскресіння ще не виконані!")
                    return False
                
                # Перевірка: чи клітинка вільна
                if not self.game_state.board.is_square_empty(row, col):
                    game_print(f"⚠️ Клітинка зайнята!")
                    return False
                
                # ВОСКРЕСІННЯ!
                self.game_state.resurrect_soul(row, col, piece_type, current_player)
                
                # Оновлюємо відображення
                self.board_widget.update_pieces_from_board(self.game_state.board)
                self.board_widget.update_resurrection_corners(self.game_state)
                self._update_display()
                self.board_widget.update()
                self.board_widget.repaint()
                
                return True
        
        return False

    def _on_piece_selected(self, row: int, col: int):
        self.board_widget.clear_move_indicators()
        self.board_widget.set_selected_piece(row, col)
        self.board_widget.update()
        
        # Обробляємо ходи - розділяємо звичайні ходи, обміни та атакуючі ходи
        for move_item in self.game_state.possible_moves:
            if isinstance(move_item, tuple) and len(move_item) == 3:
                if move_item[2] == 'swap':
                    # Це обмін з союзною фігурою - сіра крапка
                    move_row, move_col, _ = move_item
                    self.board_widget.add_swap_dot(move_row, move_col)
                elif move_item[2] == 'attack_potential':
                    # Це L-хід Блискавки (атакуюча позиція) - синя крапка з червоним контуром
                    move_row, move_col, _ = move_item
                    self.board_widget.add_attack_move_dot(move_row, move_col)
            else:
                # Звичайний хід - синя крапка
                if isinstance(move_item, tuple) and len(move_item) >= 2:
                    move_row, move_col = move_item[0], move_item[1]
                else:
                    move_row, move_col = move_item
                self.board_widget.add_move_dot(move_row, move_col)
        
        # Атаки (включаючи обміни з ворожими фігурами) - червоні крапки
        for attack_row, attack_col in self.game_state.possible_attacks:
            self.board_widget.add_attack_dot(attack_row, attack_col)
        
        # Телепорти - фіолетові крапки
        for teleport_row, teleport_col in getattr(self.game_state, 'possible_teleports', []):
            self.board_widget.add_teleport_dot(teleport_row, teleport_col)
        
        # ДОДАТКОВО: Священний обмін Храму - сірі крапки на союзних фігурах
        piece = self.game_state.get_piece_at(row, col)
        if piece and piece.type == PieceType.TEMPLE:
            temple_id = self.game_state.get_temple_id(row, col)
            if temple_id and not self.game_state.temple_swap_used.get(temple_id, False):
                # Храм ще не використав свій обмін - показуємо сірі крапки
                swap_targets = self.game_state.get_temple_swap_targets(row, col)
                for swap_row, swap_col in swap_targets:
                    self.board_widget.add_swap_dot(swap_row, swap_col)
                temple_swaps = len(swap_targets)
            else:
                temple_swaps = 0
        else:
            temple_swaps = 0
        
        # Підрахунок ходів для інформаційної панелі
        regular_moves = sum(1 for m in self.game_state.possible_moves 
                           if not (isinstance(m, tuple) and len(m) == 3 and m[2] == 'swap'))
        swap_moves = sum(1 for m in self.game_state.possible_moves 
                        if isinstance(m, tuple) and len(m) == 3 and m[2] == 'swap')
        
        total_moves = (regular_moves + swap_moves + temple_swaps +
                      len(self.game_state.possible_attacks) + 
                      len(getattr(self.game_state, 'possible_teleports', [])))
        
        self.info_panel.update_move_counts(
            regular_moves + swap_moves + temple_swaps + len(getattr(self.game_state, 'possible_teleports', [])),
            len(self.game_state.possible_attacks)
        )

    def _on_move_made(self):
        self.board_widget.clear_move_indicators()
        self.board_widget.clear_selected_piece()
        self.board_widget.update_pieces_from_board(self.game_state.board)
        
        # Оновлюємо всі візуальні ефекти, включаючи підсвітку місяців
        self._update_display()
        
        self.board_widget.update()
        
        if self.game_state.move_calculator.is_checkmate(self.game_state.current_player):
            winner = "Чорні" if self.game_state.current_player == "WHITE" else "Білі"
        elif self.game_state.move_calculator.is_stalemate(self.game_state.current_player):
            pass  # Пат обробляється в іншому місці
        self.info_panel.update_move_counts(0, 0)
        
    def _clear_move_indicators(self):
        self.board_widget.clear_move_indicators()
        self.board_widget.clear_selected_piece()
        self.info_panel.update_move_counts(0, 0)

    def _update_display(self):
        info = self.game_state.get_game_info()
        current_player = info["current_player"]
        if not hasattr(self, '_last_player') or self._last_player != current_player:
            self.info_panel.update_turn(current_player)
            self._last_player = current_player
        
        # Update all visual state from game state
        self.board_widget.update_from_game_state(self.game_state)
        
        # Перевірка шаху та відображення жовтої рамки
        if self.game_state.move_calculator:
            actual_current_player = self.game_state.current_player  # PieceColor enum
            king_pos = self.game_state.move_calculator._find_king(actual_current_player)
            if king_pos:
                attacker_pos = self.game_state.move_calculator._is_king_in_check(actual_current_player)
                if attacker_pos:
                    # Король під шахом - показуємо жовту рамку
                    self.board_widget.set_king_in_check(king_pos[0], king_pos[1])
                else:
                    # Шаху немає - прибираємо рамку
                    self.board_widget.clear_king_in_check()
            else:
                self.board_widget.clear_king_in_check()
        else:
            self.board_widget.clear_king_in_check()
        
        # Якщо активне посилення Очей, НЕ показуємо куточки воскресіння
        if self.game_state.eye_enhancement_selection:
            # Тільки куточки посилення Очей
            self.board_widget.update_eye_enhancement_corners(self.game_state)
            # Очищаємо куточки воскресіння на час вибору
            self.board_widget.resurrection_corners.clear()
        else:
            # Звичайний режим: показуємо куточки воскресіння
            self.board_widget.update_resurrection_corners(self.game_state)
            self.board_widget.update_eye_enhancement_corners(self.game_state)
        
        self.board_widget.update_nebula_timers(self.game_state)
        self.board_widget.update()
        
        # Показуємо діалог, якщо гра закінчена
        if self.game_state.game_over and not hasattr(self, '_game_over_shown'):
            self._game_over_shown = True
            self._show_game_over_dialog()

    def _show_game_over_dialog(self):
        """Показує діалогове вікно з результатом гри"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Гра завершена!")
        
        if self.game_state.winner == 'draw':
            dialog.setIcon(QMessageBox.Icon.Information)
            dialog.setText("🤝 ПАТ! Нічия!")
            dialog.setInformativeText("Король не під шахом, але немає легальних ходів.")
        else:
            dialog.setIcon(QMessageBox.Icon.Information)
            winner_name = "Білі" if self.game_state.winner == 'white' else "Чорні"
            loser_name = "Чорні" if self.game_state.winner == 'white' else "Білі"
            dialog.setText(f"👑 МАТ! {winner_name} перемогли!")
            dialog.setInformativeText(f"{loser_name} король у безвихідній ситуації!")
        
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 14px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        dialog.exec()

    def set_game_info(self, mode: str, color: str):
        self.game_mode = mode
        self.player_color = color

    def set_board_theme(self, theme_index: int):
        self.board_widget.set_board_theme(theme_index)
        
    def reset_game_state(self):
        self.game_state.reset_game()
        self.board_widget.clear_all_visual_effects()
        self.board_widget.update_pieces_from_board(self.game_state.board)
        self.info_panel.reset_timers()
        # Скидаємо прапорець показу діалогу game over
        if hasattr(self, '_game_over_shown'):
            delattr(self, '_game_over_shown')
        self._update_display()

class MainWindow(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вершителі часу")
        self.setMinimumSize(1920, 1080)
        self.settings = QSettings("VershyteliChasu", "ChessGame")

        self.previous_screen = None
        self.current_background_name = None
        self.selected_game_mode = None
        self.selected_color = None

        self.game_modes = {
            "pvp": "Людина проти Людини",
            "pve": "Людина проти ШІ",
            "eve": "ШІ проти ШІ"
        }

        self.menu_screen = MainMenuScreen()
        self.settings_screen = SettingsScreen()
        self.game_mode_screen = GameModeSelectionScreen()
        self.color_selection_screen = ColorSelectionScreen()
        self.game_screen = GameScreen()
        self.background_selection_screen = BackgroundSelector()

        self.addWidget(self.menu_screen)
        self.addWidget(self.settings_screen)
        self.addWidget(self.game_mode_screen)
        self.addWidget(self.color_selection_screen)
        self.addWidget(self.game_screen)
        self.addWidget(self.background_selection_screen)

        self.setCurrentWidget(self.menu_screen)
        self._load_settings()
        self._connect_signals()

    def _connect_signals(self):
        self.menu_screen.buttons["Нова гра"].clicked.connect(
            lambda: self.setCurrentWidget(self.game_mode_screen))
        self.menu_screen.buttons["Налаштування"].clicked.connect(
            lambda: self._show_settings_screen())
        self.menu_screen.buttons["Вихід"].clicked.connect(QApplication.instance().quit)
        
        self.game_mode_screen.mode_selected.connect(self._on_game_mode_selected)
        self.game_mode_screen.back_requested.connect(
            lambda: self.setCurrentWidget(self.menu_screen))

        self.color_selection_screen.color_selected.connect(self._on_color_selected)
        self.color_selection_screen.back_requested.connect(
            lambda: self.setCurrentWidget(self.game_mode_screen))
            
        self.game_screen.back_requested.connect(
            lambda: self.setCurrentWidget(self.menu_screen))
        self.game_screen.settings_requested.connect(self._show_settings_screen)

        self.settings_screen.back_requested.connect(self._on_settings_back_requested)
        self.settings_screen.board_theme_changed.connect(self._on_board_theme_changed)
        
        self.background_selection_screen.back_requested.connect(
            lambda: self.setCurrentWidget(self.settings_screen))
        self.background_selection_screen.background_changed.connect(self._on_background_changed)

    def _on_game_mode_selected(self, mode: str):
        self.selected_game_mode = mode
        mode_name = self.game_modes.get(mode, mode)
        game_logger.info(f"Вибрано режим гри: {mode_name}")
        game_print(f"Вибрано режим гри: {mode_name}")
        self.setCurrentWidget(self.color_selection_screen)

    def _on_color_selected(self, color: str):
        self.selected_color = color
        game_print(f"Вибрано колір: {color}")
        mode_name = self.game_modes.get(self.selected_game_mode or "", self.selected_game_mode or "")
        
        # Визначаємо типи гравців згідно з режимом гри
        if self.selected_game_mode == "pvp":  # Людина проти Людини
            white_player = "Гравець_1"
            black_player = "Гравець_2"
        elif self.selected_game_mode == "pve":  # Людина проти ШІ
            if color == "Білі":
                white_player = "Людина"
                black_player = "ШІ"
            else:
                white_player = "ШІ"
                black_player = "Людина"
        else:  # eve - ШІ проти ШІ
            white_player = "ШІ"
            black_player = "ШІ"
        
        start_new_game(mode_name, white_player, black_player)
        activate_game_logging()  # Активуємо логування в файл
        self.game_screen.set_game_info(self.selected_game_mode, color)
        self.game_screen.reset_game_state()
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        game_print(f"\033[1m{current_time}, Хід Білого Гравця - номер ходу {self.game_screen.game_state.turn_number}:\033[0m")
        self.setCurrentWidget(self.game_screen)

    def _show_settings_screen(self):
        self.previous_screen = self.currentWidget()
        current_theme = self.settings.value("board_theme_index", DEFAULT_BOARD_THEME_INDEX, type=int)
        self.settings_screen.set_current_theme(current_theme)
        self.setCurrentWidget(self.settings_screen)
        
    def _on_settings_back_requested(self):
        if self.previous_screen:
            self.setCurrentWidget(self.previous_screen)
        else:
            self.setCurrentWidget(self.menu_screen)
        self.previous_screen = None

    def _on_board_theme_changed(self, theme_index: int):
        self.settings.setValue("board_theme_index", theme_index)
        self.game_screen.set_board_theme(theme_index)
        game_logger.info(f"Змінено тему дошки на: {BOARD_THEMES[theme_index]['name']}")
        
    def _on_background_changed(self, background_name: str):
        self.current_background_name = background_name
        self.settings.setValue("background_name", background_name)
        self._apply_background(background_name)
        game_logger.info(f"Змінено фон на: {background_name}")
        
    def _load_settings(self):
        board_theme_index = self.settings.value("board_theme_index", DEFAULT_BOARD_THEME_INDEX, type=int)
        self.settings_screen.set_current_theme(board_theme_index)
        self.game_screen.set_board_theme(board_theme_index)

        background_name = self.settings.value("background_name", "1.jpg", type=str)
        self.current_background_name = background_name
        self.background_selection_screen.selected_background = background_name
        self._apply_background(background_name)

    def _apply_background(self, background_name: str):
        background_path = Path("ресурси/зображення/фони") / background_name
        if background_path.exists():
            pixmap = QPixmap(str(background_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                palette = self.palette()
                palette.setBrush(QPalette.ColorRole.Window, QBrush(scaled_pixmap))
                self.setPalette(palette)
                self.setStyleSheet("") 

                screens = [
                    self.game_screen, self.settings_screen, self.menu_screen,
                    self.game_mode_screen, self.color_selection_screen, self.background_selection_screen
                ]
                
                for screen in screens:
                    screen_scaled_pixmap = pixmap.scaled(screen.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    screen_palette = screen.palette()
                    screen_palette.setBrush(QPalette.ColorRole.Window, QBrush(screen_scaled_pixmap))
                    screen.setPalette(screen_palette)
                    screen.setStyleSheet("")
                
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_background_name:
            self._apply_background(self.current_background_name)
    
    def closeEvent(self, event):
        """Обробка закриття вікна - логування завершення гри"""
        try:
            from логування import end_game
            end_game("не закінчена гра - закрито вікно")
        except:
            pass  # Ігноруємо помилки логування
        event.accept()

