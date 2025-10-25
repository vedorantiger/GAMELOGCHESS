# -*- coding: utf-8 -*-

"""from typing import Dict

Модуль оцінки позиції для ШІ гри "Вершителі часу"from налаштування import PieceType, PieceColor

from логування import game_logger

Цей модуль відповідає за оцінку ігрових позицій та визначення переваги гравців.

Використовується алгоритмом пошуку (minimax/alpha-beta) для вибору найкращих ходів.

class PositionEvaluator:

Архітектура:    """

- PositionEvaluator: головний клас оцінки    ОНОВЛЕНІ ОЦІНКИ ФІГУР на основі детального аналізу правил та здібностей

- PIECE_VALUES: базові оцінки фігур    

- Методи оцінки: матеріал, позиція, мобільність, безпека короля, спеціальні здібності    Базова шкала: Пішак = 1.0

    

TODO для майбутньої реалізації:    Критерії оцінки:

1. Позиційна оцінка (центр, розвиток, структура пішаків)    - Мобільність (кількість можливих ходів)

2. Мобільність фігур (кількість можливих ходів)    - Атакуюча сила (радіус атаки, патерни)

3. Безпека короля (атаки навколо, імунні зони)    - Спеціальні здібності (унікальні механіки)

4. Контроль туманностей і телепортації    - Стратегічна цінність (вплив на гру)

5. Оцінка паралізованих фігур    - Захисна функція

6. Оцінка спеціальних здібностей (подвійний хід, воскресіння, обмін)    """

7. Ендшпільна оцінка (король в атаці, просування пішаків)    

"""    PIECE_VALUES = {

        # === КЛАСИЧНІ ФІГУРИ ===

from typing import Dict, Optional        PieceType.PAWN: 1.0,           # Базова одиниця

from налаштування import PieceType, PieceColor        PieceType.KNIGHT: 3.2,         # L-ходи, перестрибування

from логування import game_logger        PieceType.BISHOP: 3.5,         # Діагоналі необмежено

        PieceType.ROOK: 5.5,           # Ортогоналі необмежено

        PieceType.QUEEN: 10.0,         # Комбінація Тура+Слон

class PositionEvaluator:        PieceType.KING: 1000.0,        # Безцінний (мат = програш)

    """        

    Клас для оцінки ігрових позицій.        # === УНІКАЛЬНІ ФІГУРИ (оновлені оцінки) ===

            

    Використовує багатофакторну оцінку:        # ШИТ - 3.0 (було 2.0)

    1. Матеріальний баланс (найважливіше)        # + Рухається на 1-3 ортогонально

    2. Позиційні фактори (розвиток, центр, структура)        # + Створює імунну зону 3×3 (захищає 8 клітинок!)

    3. Тактичні фактори (атаки, загрози, мобільність)        # + Блокує ворожі атаки (крім Короля)

    4. Спеціальні фактори (туманності, здібності)        # - Не атакує (тільки переміщення)

            # = Висока захисна цінність, особливо в групі

    Оцінка повертається з точки зору білих:        PieceType.SHIELD: 3.0,

    - Позитивне значення = перевага білих        

    - Негативне значення = перевага чорних        # ОКО - 3.5 (було 3.0)

    - 0 = рівна позиція        # + Атакує ортогонально на 1 (базове)

    """        # + Рухається діагонально 1-3

            # + ПОСИЛЕННЯ через Тріумфатора: атака на 1-2, може "прослизнути" через ворога

    # ============================================================================        # + Можливість стати дуже сильною в ендшпілі

    # БАЗОВІ ОЦІНКИ ФІГУР (оновлено на основі детального аналізу)        # = Середня фігура з потенціалом зростання

    # ============================================================================        PieceType.EYE: 3.5,

    # Шкала: Пішак = 1.0        

    # Оцінки враховують: мобільність, атаку, спецздібності, стратегічну цінність        # МІСЯЦЬ - 4.5 (було 4.0)

    # ============================================================================        # + Ходи коня (L-подібні)

            # + ПОДВІЙНИЙ ХІД: 1 раз за гру може зробити 2 ходи підряд!

    PIECE_VALUES = {        # + Тактична бомба (раптові комбінації)

        # === КЛАСИЧНІ ФІГУРИ ===        # + Висока мобільність

        PieceType.PAWN: 1.0,           # Базова одиниця        # = Сильна тактична фігура з game-changing здібністю

        PieceType.KNIGHT: 3.2,         # L-ходи, перестрибування        PieceType.MOON: 4.5,

        PieceType.BISHOP: 3.5,         # Діагоналі необмежено        

        PieceType.ROOK: 5.5,           # Ортогоналі необмежено        # ВСАДНИК - 5.0 (було 4.5)

        PieceType.QUEEN: 10.0,         # Тура+Слон = найсильніша        # + Комбінація Коня + Офіцера з перестрибуванням

        PieceType.KING: 1000.0,        # Безцінний (мат = програш)        # + L-ходи коня

                # + Діагоналі з перестрибуванням ОДНОГО союзника

        # === УНІКАЛЬНІ ФІГУРИ ===        # + ПОЛЮВАННЯ НА ДУШІ: може воскресити Коня/Слона/Всадника (1 раз за гру)

        PieceType.SHIELD: 3.0,         # Імунна зона 3×3, захист        # + Дуже висока мобільність

        PieceType.EYE: 3.5,            # Атака 1-2 (посилене), діагональний рух        # = Дуже сильна універсальна фігура з унікальною здібністю

        PieceType.ARISTOCRAT: 4.0,     # Дипломатичний обмін, НЕ вбиває        PieceType.RIDER: 5.0,

        PieceType.MOON: 4.5,           # L-ходи + подвійний хід (1 раз)        

        PieceType.RIDER: 5.0,          # Кінь+Офіцер + воскресіння        # ХРАМ - 5.5 (було 5.5) ✓ правильно

        PieceType.TEMPLE: 5.5,         # Стрибки + священний обмін        # + Ортогонально 1 + стрибки 2-3 вертикально, 2 горизонтально

        PieceType.LIGHTNING: 6.5,      # L-атаки + електричний параліч        # + Може перестрибнути 1 ворога

        PieceType.FURY: 7.5,           # Король+горизонталь 1-3        # + СВЯЩЕННИЙ ОБМІН: 1 раз за гру обмін з союзником (стратегічне переміщення)

        PieceType.TRIUMPHATOR: 8.5,    # Паралізація замість вбивства        # + Не входить в імунні зони

                # = Сильна фігура з унікальною мобільністю

        # === ПОРОЖНЯ КЛІТИНКА ===        PieceType.TEMPLE: 5.5,

        PieceType.EMPTY: 0.0        

    }        # БЛИСКАВКА - 6.5 (було 6.0)

            # + Діагоналі 1-2 (тільки ходи, не атаки)

    # Ваги для різних компонентів оцінки        # + L-ПОДІБНІ АТАКИ: 3 діагональ + 1 перпендикуляр (дуже унікально!)

    MATERIAL_WEIGHT = 1.0      # Матеріал (найважливіше)        # + ЕЛЕКТРИЧНИЙ ПАРАЛІЧ: хто захопить - паралізується на 2 ходи (крім Король/Блискавка)

    POSITION_WEIGHT = 0.1      # Позиція фігур        # + Високий тактичний потенціал

    MOBILITY_WEIGHT = 0.05     # Мобільність        # + Важко захопити без втрат

    KING_SAFETY_WEIGHT = 0.3   # Безпека короля        # = Дуже сильна атакуюча фігура з унікальним патерном

    CENTER_WEIGHT = 0.2        # Контроль центру        PieceType.LIGHTNING: 6.5,

    NEBULA_WEIGHT = 0.15       # Контроль туманностей        

            # АРИСТОКРАТ - 4.0 (було 4.0) ✓ правильно

    def __init__(self):        # + Діагоналі 1-3

        """Ініціалізація оцінювача з кешуванням"""        # + Ортогональні стрибки на 2

        self._cache: Dict[int, float] = {}  # Кеш для оцінки позицій (хеш → оцінка)        # + ДИПЛОМАТИЧНИЙ ОБМІН: міняється місцями з будь-якою фігурою (союзник/ворог)

        self._cache_hits = 0        # - НЕ вбиває (тільки обмін)

        self._cache_misses = 0        # + Якщо обмін з ворожою Блискавкою - паралізується

        game_logger.info("Ініціалізовано оцінювач позицій з кешуванням")        # + Обмеження: не може обміняти Короля на Короля

            # = Унікальна стратегічна фігура, але не атакує

    def evaluate_position(self, game_state) -> float:        PieceType.ARISTOCRAT: 4.0,

        """        

        Головний метод оцінки позиції.        # ФУРІЯ - 7.5 (було 9.0)

                # + Атакує на 1 у всі боки (як Король)

        Args:        # + Рухається ГОРИЗОНТАЛЬНО 1-3 клітинки

            game_state: Поточний стан гри        # - Обмежена вертикальна мобільність (тільки атака)

                    # = Сильна горизонтальна фігура, але не 9.0

        Returns:        PieceType.FURY: 7.5,

            float: Оцінка позиції (+ білі, - чорні)        

        """        # ТРІУМФАТОР - 8.5 (було 10.0)

        # Використовуємо хеш дошки для кешування        # + Діагоналі 1-2, ортогоналі 1-2, вертикаль 1-3

        board_hash = game_state.board.position_hash        # + ПАРАЛІЗАЦІЯ замість вбивства: ціль паралізується на 2-3 ходи

                # + Може паралізувати Короля (але не Блискавку/Щит)

        if board_hash in self._cache:        # + Паралізований Король під шахом = МАТ!

            self._cache_hits += 1        # + Зв'язок з Очима (посилення)

            return self._cache[board_hash]        # - НЕ вбиває (фігура залишається на дошці)

                # = Дуже сильна контрольна фігура, але не сильніша за Ферзя

        self._cache_misses += 1        PieceType.TRIUMPHATOR: 8.5,

                

        # Перевірка на мат/пат        # ПОРОЖНЯ КЛІТИНКА

        if game_state.game_over:        PieceType.EMPTY: 0.0

            if game_state.winner == 'white':    }

                score = 10000.0  # Білі виграли

            elif game_state.winner == 'black':    def __init__(self):

                score = -10000.0  # Чорні виграли        self._cache = {}  # Кеш для оцінки позицій

            else:  # 'draw'        game_logger.info("Ініціалізовано оцінювач позицій з кешуванням")

                score = 0.0  # Нічия

            self._cache[board_hash] = score    def evaluate_position(self, game_state) -> float:

            return score        # Використовуємо хеш дошки для кешування

                board_hash = game_state.board.position_hash

        # Комплексна оцінка        if board_hash in self._cache:

        score = 0.0            return self._cache[board_hash]

        

        # 1. Матеріальний баланс (найважливіше)        score = 0.0

        material_score = self._calculate_material(game_state)        material_score = self._calculate_material(game_state)

        score += material_score * self.MATERIAL_WEIGHT        position_score = self._calculate_position(game_state)

                center_score = self._calculate_center_control(game_state)

        # 2. Позиційна оцінка (TODO: реалізувати детально)        king_safety = self._calculate_king_safety(game_state)

        position_score = self._calculate_position(game_state)        score = material_score + position_score * 0.1 + center_score * 0.2 + king_safety * 0.3

        score += position_score * self.POSITION_WEIGHT        

                self._cache[board_hash] = score

        # 3. Контроль центру (TODO: реалізувати детально)        return score

        center_score = self._calculate_center_control(game_state)

        score += center_score * self.CENTER_WEIGHT    def _calculate_material(self, game_state) -> float:

                white_material = 0.0

        # 4. Безпека короля (TODO: реалізувати детально)        black_material = 0.0

        king_safety = self._calculate_king_safety(game_state)        for row in range(len(game_state.board)):

        score += king_safety * self.KING_SAFETY_WEIGHT            for col in range(len(game_state.board[row])):

                        piece = game_state.board[row][col]

        # Кешуємо результат                if not piece.is_empty():

        self._cache[board_hash] = score                    value = self.PIECE_VALUES.get(piece.type, 0)

        return score                    if piece.color == PieceColor.WHITE:

                            white_material += value

    def _calculate_material(self, game_state) -> float:                    else:

        """                        black_material += value

        Розраховує матеріальний баланс.        return white_material - black_material

        

        Базова оцінка: підраховує вартість усіх фігур на дошці.    def _calculate_position(self, game_state) -> float:

                return 0.0

        TODO для покращення:

        - Бонус за пару слонів    def _calculate_center_control(self, game_state) -> float:

        - Штраф за подвоєні пішаки        center_squares = [

        - Бонус за посилене Око            (8, 8), (8, 9), (8, 10), (8, 11),

        - Оцінка паралізованих фігур (зменшена цінність)            (9, 8), (9, 9), (9, 10), (9, 11),

                    (10, 8), (10, 9), (10, 10), (10, 11),

        Returns:            (11, 8), (11, 9), (11, 10), (11, 11)

            float: Різниця матеріалу (білі - чорні)        ]

        """        white_control = 0

        white_material = 0.0        black_control = 0

        black_material = 0.0        for row, col in center_squares:

                    piece = game_state.board[row][col]

        # Отримуємо всі фігури на дошці            if not piece.is_empty():

        all_pieces = game_state.board.get_all_pieces()                if piece.color == PieceColor.WHITE:

                            white_control += 1

        for row, col, piece in all_pieces:                else:

            if piece.is_empty():                    black_control += 1

                continue        return white_control - black_control

            

            # Базова вартість фігури    def _calculate_king_safety(self, game_state) -> float:

            value = self.PIECE_VALUES.get(piece.type, 0.0)        return 0.0

            
            # TODO: Додати бонуси/штрафи
            # - Посилене Око: +0.5
            # - Паралізована фігура: -50% цінності
            # - Фігура в туманності під таймером: -20%
            
            if piece.color == PieceColor.WHITE:
                white_material += value
            else:
                black_material += value
        
        return white_material - black_material
    
    def _calculate_position(self, game_state) -> float:
        """
        Розраховує позиційну оцінку.
        
        TODO: Реалізувати:
        - Розвиток фігур (чи вийшли з початкових позицій)
        - Структура пішаків (подвоєні, ізольовані, прохідні)
        - Відкриті лінії для тур
        - Діагоналі для слонів
        - Аванпости для коней
        - Контроль ключових полів
        
        Returns:
            float: Позиційна оцінка
        """
        # ЗАГЛУШКА: базова реалізація
        return 0.0
    
    def _calculate_center_control(self, game_state) -> float:
        """
        Розраховує контроль центру дошки.
        
        Центр: клітинки (8-11, 8-11) - 16 центральних полів
        
        TODO: Покращення:
        - Зважений контроль (атаковані клітинки)
        - Розширений центр
        - Контроль через пішаків (вища вага)
        
        Returns:
            float: Оцінка контролю центру
        """
        # ЗАГЛУШКА: базова реалізація
        center_squares = [
            (8, 8), (8, 9), (8, 10), (8, 11),
            (9, 8), (9, 9), (9, 10), (9, 11),
            (10, 8), (10, 9), (10, 10), (10, 11),
            (11, 8), (11, 9), (11, 10), (11, 11)
        ]
        
        white_control = 0
        black_control = 0
        
        for row, col in center_squares:
            piece = game_state.board.get_piece_at(row, col)
            if piece and not piece.is_empty():
                if piece.color == PieceColor.WHITE:
                    white_control += 1
                else:
                    black_control += 1
        
        return float(white_control - black_control)
    
    def _calculate_king_safety(self, game_state) -> float:
        """
        Розраховує безпеку королів.
        
        TODO: Реалізувати:
        - Щити навколо короля (імунні зони)
        - Пішакова структура біля короля
        - Відкриті лінії атак на короля
        - Наближеність ворожих фігур
        - Король під шахом (велика загроза)
        - Паралізований король (критична загроза)
        - Можливість рокіровки (немає в цій грі, але є телепортація)
        
        Returns:
            float: Оцінка безпеки королів
        """
        # ЗАГЛУШКА: базова реалізація
        return 0.0
    
    def _calculate_mobility(self, game_state) -> float:
        """
        Розраховує мобільність фігур.
        
        TODO: Реалізувати:
        - Підрахунок кількості легальних ходів для кожного кольору
        - Зважена мобільність (різні фігури мають різну вагу)
        - Мобільність в критичних зонах (центр, атака на короля)
        
        Returns:
            float: Оцінка мобільності
        """
        # ЗАГЛУШКА
        return 0.0
    
    def _calculate_special_abilities(self, game_state) -> float:
        """
        Оцінює спеціальні здібності та механіки гри.
        
        TODO: Реалізувати оцінку:
        - Туманності: контроль, блокування, телепортація
        - Паралізовані фігури: зменшена цінність
        - Доступні обміни (Храм, Аристократ): стратегічна цінність
        - Подвійний хід Місяця: доступний/використаний
        - Воскресіння Всадником: можливість повернути фігури
        - Посилені Очі: збільшена атакуюча сила
        - Душі на полюванні: прогрес до воскресіння
        
        Returns:
            float: Оцінка спеціальних здібностей
        """
        # ЗАГЛУШКА
        return 0.0
    
    def clear_cache(self):
        """Очищує кеш оцінок (викликати при новій грі)"""
        self._cache.clear()
        game_logger.info(f"Кеш очищено. Статистика: {self._cache_hits} hits, {self._cache_misses} misses")
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Повертає статистику використання кешу"""
        return {
            'size': len(self._cache),
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / max(1, self._cache_hits + self._cache_misses)
        }
