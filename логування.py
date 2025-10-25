import sys
import re
from pathlib import Path
from typing import Optional
from loguru import logger

# Глобальна змінна для відстеження чи відкрита гра
_game_active = False

def game_print(message: str):
    """
    Універсальна функція для виведення в консоль І одночасного запису в партія.log
    Замінює всі print() в грі.
    
    Консоль: з емодзі та ANSI кодами
    Файл: без емодзі та без ANSI кодів
    """
    global _game_active
    
    # Виводимо в консоль з форматуванням та емодзі
    print(message)
    
    # Якщо гра активна, пишемо в файл
    if _game_active:
        # Видаляємо ANSI escape коди
        clean_message = re.sub(r'\033\[[0-9;]*m', '', message)
        
        # Видаляємо емодзі та варіаційні селектори
        # Спочатку видаляємо варіаційні селектори (FE0E, FE0F) які роблять емодзі кольоровими
        clean_message = re.sub(r'[\uFE0E\uFE0F]', '', clean_message)
        
        # Потім видаляємо самі емодзі
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # емоції
            "\U0001F300-\U0001F5FF"  # символи & піктограми
            "\U0001F680-\U0001F6FF"  # транспорт & символи карти
            "\U0001F1E0-\U0001F1FF"  # прапори (iOS)
            "\U00002700-\U000027BF"  # Dingbats
            "\U0001F900-\U0001F9FF"  # Додаткові символи та піктограми
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002600-\U000026FF"  # Різноманітні символи
            "\U0001F700-\U0001F77F"  # Алхімічні символи
            "\U0001F780-\U0001F7FF"  # Геометричні форми Extended
            "\U0001F800-\U0001F8FF"  # Додаткові стрілки-C
            "\U00002B50"             # зірка ⭐
            "\U0000231A-\U0000231B"  # годинники
            "\U000025AA-\U000025FB"  # квадрати
            "\U00002934-\U00002935"  # стрілки
            "\U0001F004"             # маджонг
            "\U0001F0CF"             # джокер
            "\U0001F170-\U0001F251"  # enclosed characters
            "\U0000203C-\U00003299"  # різні символи
            "]+", 
            flags=re.UNICODE
        )
        clean_message = emoji_pattern.sub('', clean_message)
        
        # Видаляємо зайві пробіли що залишилися після емодзі
        clean_message = re.sub(r'\s+', ' ', clean_message)
        clean_message = clean_message.strip()
        
        # Пишемо в файл
        logger.bind(PARTY=True).info(clean_message)

def activate_game_logging():
    """Активує запис гри в файл"""
    global _game_active
    _game_active = True

def deactivate_game_logging():
    """Деактивує запис гри в файл"""
    global _game_active
    _game_active = False

def setup_logger():
    logger.remove()
    log_dir = Path(__file__).parent / "логи"
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        sys.stdout,
        format="<red>{message}</red>",
        level="ERROR",
        colorize=True
    )
    
    logger.add(
        log_dir / "помилки.log", 
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8"
    )
    
    logger.add(
        log_dir / "партія.log",
        format="{message}",
        level="INFO",
        rotation="10 MB", 
        retention="60 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "PARTY" in record["extra"]
    )
    
    return logger

game_logger = setup_logger()

current_game_session = None
move_counter = 0
current_player = None
game_counter = 0
pgn_moves = []  # Список ходів для PGN
current_turn_logged = False  # Чи було вже залоговано заголовок поточного ходу
pending_events = []  # Накопичувач подій для поточного ходу

def convert_coords_to_chess_notation(row: int, col: int) -> str:
    """Конвертує координати (row, col) в шахову нотацію типу A1, B2"""
    # row: 1-20, col: 1-20
    # A-T (20 літер) для колонок, 1-20 для рядків
    cols = "ABCDEFGHIJKLMNOPQRST"
    chess_col = cols[col - 1] if 1 <= col <= 20 else "?"
    chess_row = str(21 - row) if 1 <= row <= 20 else "?"
    return f"{chess_col}{chess_row}"

def get_pgn_move_type(move_type: str, special_info: str = "") -> str:
    """Визначає тип ходу для PGN з розширеними механіками"""
    special_lower = special_info.lower()
    move_type_lower = move_type.lower()
    
    # Спеціальні механіки (перевіряємо і move_type, і special_info)
    if "подвійний хід" in special_lower or "подвійний хід" in move_type_lower or "double move" in special_lower:
        return "xD"
    elif "пропуск ходу" in special_lower or "skip turn" in special_lower:
        return "--"
    elif "захист щитом" in special_lower or "shield protection" in special_lower:
        return "+"
    elif "активація здібності" in special_lower or "special ability" in special_lower:
        return "*"
    elif "туманність" in special_lower or "fog" in special_lower:
        return "~"
    elif "посилення ока" in special_lower or "eye enhancement" in special_lower:
        return "(E)"
    elif "дія тріумфатора" in special_lower or "triumphator action" in special_lower:
        return "(T)"
    # Атаки з спеціальними ефектами
    elif "паралізація" in special_lower or "paralysis" in special_lower:
        return "xP"
    elif "воскресіння" in special_lower or "resurrection" in special_lower:
        return "xR"  
    elif "телепортація" in special_lower or "teleport" in special_lower or "телепортується" in move_type_lower:
        return "xT"
    elif "обмін" in special_lower or "обмін" in move_type_lower or "swap" in special_lower:
        return "xS"
    elif move_type == "атакує":
        return "x"
    else:
        return ""

def start_new_game(mode: str, white_player: str, black_player: str):
    global current_game_session, move_counter, current_player, game_counter, pgn_moves, current_turn_logged, pending_events
    
    # ВИПРАВЛЕНО: Знаходимо останній номер гри у файлі логів
    log_file = Path(__file__).parent / "логи" / "партія.log"
    game_counter = 1  # За замовчуванням
    
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Шукаємо всі записи "Запуск гри №X"
                import re
                matches = re.findall(r'Запуск гри №(\d+)', content)
                if matches:
                    # Беремо найбільший номер і додаємо 1
                    last_game_number = max(int(num) for num in matches)
                    game_counter = last_game_number + 1
        except:
            game_counter = 1
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    current_game_session = {
        'mode': mode,
        'white_player': white_player,
        'black_player': black_player,
        'start_time': timestamp,
        'moves': []
    }
    
    move_counter = 0
    pgn_moves = []  # Скидаємо PGN ходи
    current_player = "білий"
    current_turn_logged = False  # Скидаємо стан логування
    pending_events = []  # Очищаємо накопичувач подій
    
    # ДОДАЄМО ВІДСТУПИ між іграми (окрім першої)
    if game_counter > 1:
        logger.bind(PARTY=True).info("")
        logger.bind(PARTY=True).info("")
        logger.bind(PARTY=True).info("")
    
    logger.bind(PARTY=True).info(f"Запуск гри №{game_counter}")
    logger.bind(PARTY=True).info(f"Вибрано режим гри: {mode}")
    
    if (white_player == "Людина" and black_player == "Людина") or (white_player == "Гравець_1" and black_player == "Гравець_2"):
        game_type = "Людина проти Людини (білі - гравець_1, чорні - гравець_2)"
    elif white_player == "Людина" and black_player == "ШІ":
        game_type = "Людина проти ШІ (білі - людина, чорні - ШІ)"
    elif white_player == "ШІ" and black_player == "Людина":
        game_type = "ШІ проти Людини (білі - ШІ, чорні - людина)"
    else:
        game_type = "ШІ проти ШІ"
    
    logger.bind(PARTY=True).info(f"Тип партії: {game_type}")
    logger.bind(PARTY=True).info(f"Дата: {timestamp}")
    logger.bind(PARTY=True).info("")

def log_move_to_party(piece_name: str, piece_color: str, piece_id: int, from_pos: str, to_pos: str, 
                     from_coords: tuple, to_coords: tuple, move_type: str = "ходить", 
                     captured_piece: Optional[str] = None, captured_id: Optional[int] = None,
                     special_info: str = ""):
    global current_player, move_counter, current_game_session, pgn_moves
    
    if not current_game_session:
        return
    
    # ВИПРАВЛЕНО: Підтримка різних типів ходів
    if move_type == "атакує" and captured_piece:
        move_text = f"{piece_color} {piece_name} id({piece_id}) з {from_pos} ({from_coords[0]}, {from_coords[1]}) атакує {captured_piece} id({captured_id}) на {to_pos} ({to_coords[0]}, {to_coords[1]})"
    elif move_type == "здійснив священний обмін з" and captured_piece:
        move_text = f"{piece_color} {piece_name} id({piece_id}) здійснив священний обмін з {captured_piece} id({captured_id})"
        if special_info:
            move_text += f"\n   {special_info}"
    elif move_type == "обмінявся з" and captured_piece:
        move_text = f"{piece_color} {piece_name} id({piece_id}) обмінявся з {captured_piece} id({captured_id})"
        if special_info:
            move_text += f"\n   {special_info}"
    elif move_type == "телепортується":
        move_text = f"{piece_color} {piece_name} id({piece_id}) телепортується з {from_pos} на {to_pos}"
        if special_info:
            move_text += f" ({special_info})"
    elif move_type == "подвійний хід (частина 1/2)":
        # НОВИЙ ТИП: Перший хід подвійного ходу Місяця
        move_text = f"{piece_color} {piece_name} id({piece_id}) ходить з {from_pos} на {to_pos}"
        if special_info:
            move_text = special_info  # Використовуємо точний текст з special_info
        else:
            move_text += f"\nПерший хід подвійного ходу Місяцем id({piece_id}) {from_pos} на {to_pos}"
    else:
        move_text = f"{piece_color} {piece_name} id({piece_id}) ходить з {from_pos} ({from_coords[0]}, {from_coords[1]}) на {to_pos} ({to_coords[0]}, {to_coords[1]})"
    
    # Логуємо цей хід як початок нового ходу гравця
    log_party_event(move_text, increment_move=True)
    
    # ДОДАЄМО PGN хід
    pgn_move_type = get_pgn_move_type(move_type, special_info)
    pgn_move = f"{from_pos}{pgn_move_type}{to_pos}"
    pgn_moves.append(pgn_move)

def log_error(message: str, exception: Optional[Exception] = None):
    try:
        if exception:
            import traceback
            error_details = traceback.format_exc()
            game_logger.error(f"{message}: {str(exception)}\n{error_details}")
        else:
            game_logger.error(message)
    except Exception as e:
        print(f"LOGGING ERROR: {message}: {e}")

def log_party_event(message: str, increment_move: bool = False):
    """
    Логує подію партії. 
    increment_move: якщо True, це означає початок нового ходу гравця
    """
    global move_counter, current_player, current_turn_logged, pending_events
    
    if increment_move:
        # Спочатку виводимо всі накопичені події від попереднього ходу
        _flush_pending_events()
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # ВИПРАВЛЕНО: Використовуємо move_counter який синхронізується з turn_number
        move_counter += 1
        move_num = move_counter
        
        # Визначаємо гравця по номеру ходу
        if move_num % 2 == 1:  # Непарні ходи - білий гравець
            current_player = "білий"
            player_title = "Білого"
        else:  # Парні ходи - чорний гравець
            current_player = "чорний"
            player_title = "Чорного"
        
        header = f"** {timestamp}, Хід {player_title} Гравця - номер ходу {move_num}: **"
        logger.bind(PARTY=True).info(header)
        current_turn_logged = True
        
        # Додаємо основну подію ходу
        logger.bind(PARTY=True).info(message)
        
    else:
        # Це додаткова подія в рамках поточного ходу - виводимо одразу
        if current_turn_logged:
            logger.bind(PARTY=True).info(message)
        else:
            # Якщо заголовок ходу ще не виведено, додаємо в накопичувач
            pending_events.append(message)

def _flush_pending_events():
    """Виводить всі накопичені події поточного ходу"""
    global pending_events, current_turn_logged
    
    for event in pending_events:
        logger.bind(PARTY=True).info(event)
    
    pending_events = []
    current_turn_logged = False

def log_party_event_immediate(message: str):
    """
    Логує подію НЕГАЙНО в поточний хід, без буферизації.
    Використовується для воскресінь, туманностей та інших подій,
    які мають з'явитися в лозі ОДРАЗУ під поточним заголовком ходу.
    """
    logger.bind(PARTY=True).info(message)

def log_game_event(message: str):
    logger.bind(PARTY=True).info(message)

def log_move(player: str, move: str, position: str = ""):
    pass

def log_game_action(action: str, details: str = ""):
    pass

def log_teleportation(piece_name: str, piece_color: str, piece_id: int, from_pos: str, to_pos: str, 
                     from_coords: tuple, to_coords: tuple):
    """Логування телепортації через туманності"""
    log_move_to_party(piece_name, piece_color, piece_id, from_pos, to_pos, 
                     from_coords, to_coords, "телепортується", 
                     special_info="телепортація")

def log_resurrection(piece_name: str, piece_color: str, piece_id: int, position: str, coords: tuple):
    """Логування воскресіння фігури"""
    log_move_to_party(piece_name, piece_color, piece_id, "---", position, 
                     (0, 0), coords, "воскресає", 
                     special_info="воскресіння")

def log_paralysis(attacker_name: str, attacker_color: str, attacker_id: int, 
                 victim_name: str, victim_color: str, victim_id: int,
                 from_pos: str, to_pos: str, from_coords: tuple, to_coords: tuple):
    """Логування паралізації"""
    log_move_to_party(attacker_name, attacker_color, attacker_id, from_pos, to_pos, 
                     from_coords, to_coords, "паралізує", 
                     f"{victim_color} {victim_name}", victim_id,
                     special_info="паралізація")

def log_position_swap(piece1_name: str, piece1_color: str, piece1_id: int,
                     piece2_name: str, piece2_color: str, piece2_id: int,
                     pos1: str, pos2: str, coords1: tuple, coords2: tuple):
    """Логування обміну позиціями"""
    log_move_to_party(piece1_name, piece1_color, piece1_id, pos1, pos2, 
                     coords1, coords2, "міняється місцями з", 
                     f"{piece2_color} {piece2_name}", piece2_id,
                     special_info="обмін")

def generate_pgn_string(result: str = "*") -> str:
    """Генерує PGN рядок для поточної гри"""
    global current_game_session, pgn_moves, game_counter
    
    if not current_game_session:
        return ""
    
    from datetime import datetime
    game_date = datetime.strptime(current_game_session['start_time'], "%Y-%m-%d %H:%M:%S").strftime("%Y.%m.%d")
    
    # PGN заголовки
    pgn_header = f"""[Event "{current_game_session['mode']}"]
[Site "Тренувальний датасет"]
[Date "{game_date}"]
[Round "{game_counter}"]
[White "{current_game_session['white_player']}"]
[Black "{current_game_session['black_player']}"]
[Result "{result}"]

"""
    
    # PGN ходи - кожен хід окремо з номером
    if not pgn_moves:
        return pgn_header + f"{result}\n"
    
    # Форматуємо ходи з номерами (кожен хід на окремому рядку)
    move_pairs = []
    for i, move in enumerate(pgn_moves):
        move_num = i + 1
        # Визначаємо колір гравця за номером ходу
        if move_num % 2 == 1:  # Непарні ходи - білий
            formatted_move = f"{(move_num + 1) // 2}. {move}"
            move_pairs.append(formatted_move)
        else:  # Парні ходи - чорний  
            formatted_move = f"{move_num // 2}... {move}"
            move_pairs.append(formatted_move)
    
    # Розбиваємо рядки по 3 ходи для читабельності
    lines = []
    for i in range(0, len(move_pairs), 3):
        line = " ".join(move_pairs[i:i+3])
        lines.append(line)
    
    pgn_moves_text = " \n".join(lines) + f" {result}\n"
    
    return pgn_header + pgn_moves_text

def end_game(status: str = "не закінчена гра"):
    """Завершує логування гри зі статусом і PGN"""
    global current_game_session
    
    if current_game_session:
        # Визначаємо результат для PGN
        if "МАТ" in status and "Білі" in status:
            pgn_result = "1-0"
        elif "МАТ" in status and "Чорні" in status:
            pgn_result = "0-1"
        elif "ПАТ" in status or "нічия" in status:
            pgn_result = "1/2-1/2"
        else:
            pgn_result = "*"
        
        logger.bind(PARTY=True).info(f"Статус: {status}")
        logger.bind(PARTY=True).info("")
        logger.bind(PARTY=True).info("")
        
        # Генеруємо PGN з текстових логів
        pgn_string = _generate_pgn_from_logs(pgn_result)
        logger.bind(PARTY=True).info(pgn_string)
        
        # Додаємо коментарі з розширеними механіками
        logger.bind(PARTY=True).info("")
        logger.bind(PARTY=True).info("Коментарі (розширена нотація):")
        logger.bind(PARTY=True).info("Координати: A-T (20 колонок), 1-20 (20 рядків), ВЛ-верхня ліва (0,0), ВП-верхня права (0,19), НЛ-нижня ліва (21,0), НП-нижня права (21,19)")
        logger.bind(PARTY=True).info("Типи дій: x-атака, xP-паралізація з таймером(n), xR{тип}-воскресіння (P-пішак,N-кінь,B-слон,R-тура,Q-королева,K-король,Ri-всадник,Sh-щит,Fu-фурія,Te-храм,Ar-аристократ,Mo-місяць,Ey-око,Li-блискавка,Tr-тріумфатор), xT-телепортація, xTD-телепортація з загибеллю, xS-священний обмін, xD-подвійний хід місяця")
        logger.bind(PARTY=True).info("Туманності: ~-вхід в туманність, ВЛ(n)-фігура в верхній лівій з таймером n, ВП(n)-верхня права, НЛ(n)-нижня ліва, НП(n)-нижня права, FD-загибель за браком часу, ВЛ xTВП-телепортація з ВЛ в ВП, xTD-телепортація з загибеллю")
        logger.bind(PARTY=True).info("Спеціальні: *M-активація подвійних ходів місяців, +позиція-додаткова втрата фігури, -позиції-втрата захисту, DD-взаємне знищення блискавок")
        logger.bind(PARTY=True).info("Шахи та мати: +-шах, #-мат, =-пат")
        logger.bind(PARTY=True).info("Результати: *-не завершено, 1-0-перемога білих, 0-1-перемога чорних, 1/2-1/2-нічия")
        
        current_game_session = None

def _generate_pgn_from_logs(result: str = "*") -> str:
    """Генерує PGN з текстових логів партії"""
    log_file = Path(__file__).parent / "логи" / "партія.log"
    
    if not log_file.exists():
        return f"[Event \"Людина проти Людини\"]\n[Result \"{result}\"]\n\n{result}"
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Знаходимо останню гру (від останнього "Запуск гри")
        games = content.split("Запуск гри №")
        if len(games) < 2:
            return f"[Event \"Людина проти Людини\"]\n[Result \"{result}\"]\n\n{result}"
        
        last_game = games[-1]
        
        # Витягуємо інформацію про гру
        mode_match = re.search(r'Тип партії: (.+)', last_game)
        date_match = re.search(r'Дата: (\d{4}-\d{2}-\d{2})', last_game)
        
        mode = mode_match.group(1) if mode_match else "Людина проти Людини"
        date = date_match.group(1).replace('-', '.') if date_match else "2025.10.25"
        
        # Мапінг туманностей
        fog_map = {
            'верхня ліва': 'ВЛ', 'верхня права': 'ВП',
            'нижня ліва': 'НЛ', 'нижня права': 'НП'
        }
        
        # Парсимо ходи з логів
        moves = {}  # Словник {номер_ходу: список_ходів}
        lines = last_game.split('\n')
        current_turn = 0
        skip_lines = 0
        fog_timers = {}  # {номер_ходу: (туманність, таймер)}
        fog_deaths = {}  # {номер_ходу: тип_смерті}
        check_markers = {}  # {номер_ходу: '+' для шаху або '#' для мату}
        
        for i, line in enumerate(lines):
            if skip_lines > 0:
                skip_lines -= 1
                continue
            
            # Визначаємо номер ходу
            turn_match = re.search(r'номер ходу (\d+):', line)
            if turn_match:
                current_turn = int(turn_match.group(1))
                if current_turn not in moves:
                    moves[current_turn] = []
                continue
            
            if current_turn == 0:
                continue
            
            # Перевірка шаху, мату та пату
            if 'Шах!' in line and current_turn > 0:
                # Шах ставиться в ПОТОЧНОМУ ході (не попередньому!)
                # Але якщо це новий хід (щойно почався), то це від попереднього
                # Перевіряємо, чи є вже хід записаний у current_turn
                if current_turn in moves and moves[current_turn]:
                    # Є хід у поточному ході - шах від нього
                    check_markers[current_turn] = '+'
                else:
                    # Немає ходу - шах від попереднього ходу
                    check_markers[current_turn - 1] = '+'
                continue
            
            if 'МАТ!' in line and current_turn > 0:
                # Мат означає, що попередній хід був матуючим
                check_markers[current_turn - 1] = '#'
                continue
            
            if 'ПАТ!' in line and current_turn > 0:
                # Пат означає, що попередній хід призвів до пату
                check_markers[current_turn - 1] = '='
                continue
            
            # Відстежуємо таймери туманностей
            timer_match = re.search(r'що стоїть на ([а-я]+ [а-я]+) Туманності .+ має таймер - (\d+)', line)
            if timer_match:
                fog_name = timer_match.group(1)
                timer = int(timer_match.group(2))
                fog_short = fog_map.get(fog_name, fog_name)
                fog_timers[current_turn] = (fog_short, timer)
                continue
            
            # Відстежуємо смерті в туманностях
            if 'загинула в телепортації' in line:
                fog_deaths[current_turn] = 'teleport'
                continue
            if 'знищена в туманості' in line and 'за браком часу' in line:
                fog_deaths[current_turn] = 'timeout'
                continue
            
            # Ігноруємо воскресіння без затрати ходу
            if 'воскресив' in line and 'хід не затрачено' in line:
                continue
            
            # Ігноруємо активацію туманностей та зняття паралізації
            if 'Туманності активовані' in line or 'більше не паралізована' in line:
                continue
            
            # Відстежуємо взаємне знищення блискавок
            if 'Обидві блискавки знищуються' in line:
                # Це частина атаки, яка вже була записана
                # Додамо маркер DD (double destruction) до попередньої атаки
                if current_turn in moves and moves[current_turn]:
                    last_move_idx = len(moves[current_turn]) - 1
                    if last_move_idx >= 0 and 'x' in moves[current_turn][last_move_idx]:
                        # Додаємо маркер взаємного знищення
                        moves[current_turn][last_move_idx] += 'DD'
                continue
            
            # Відстежуємо втрату захисту (відбувається в тому ж ході, що й атака)
            # Це буде додано до поточної атаки, що знищила щит/фурію
            if 'втратили захист' in line:
                # Збираємо позиції фігур, що втратили захист
                unprotected_positions = []
                protection_line = line
                # Шукаємо всі позиції у рядку
                pos_matches = re.findall(r'на ([A-T]\d+)', protection_line)
                if pos_matches and current_turn in moves and moves[current_turn]:
                    # Додаємо маркер втрати захисту до ПОТОЧНОГО ходу
                    last_move_idx = len(moves[current_turn]) - 1
                    if last_move_idx >= 0:
                        # Додаємо позиції без захисту
                        protection_str = '-' + ','.join(pos_matches)
                        moves[current_turn][last_move_idx] += protection_str
                continue
            
            # 1. Паралізація (від будь-якої фігури)
            # Може бути від:
            # - Тріумфатора (здібність)
            # - Блискавки (при вбивстві)
            # - Аристократа після обміну з блискавкою
            if 'паралізував' in line or 'паралізована на' in line:
                paralysis_recorded = False
                target_pos = None
                paralysis_turns = 1
                
                # Варіант 1: Тріумфатор паралізував
                if 'Тріумфатор паралізував' in line:
                    # Витягуємо кількість ходів
                    turns_match = re.search(r'на (\d+) ходів', line)
                    if turns_match:
                        paralysis_turns = int(turns_match.group(1))
                    
                    # Шукаємо хід тріумфатора в цьому ході
                    for j in range(i-1, max(0, i-5), -1):
                        prev_line = lines[j]
                        if 'номер ходу' in prev_line and str(current_turn) not in prev_line:
                            break
                        triumphator_move = re.search(r'[Тт]ріумфатор id\(\d+\) ходить з ([A-T]\d+).+ на ([A-T]\d+)', prev_line)
                        if triumphator_move:
                            from_pos = triumphator_move.group(1)
                            to_pos = triumphator_move.group(2)
                            moves[current_turn] = [f"{from_pos} xP{to_pos}({paralysis_turns})"]
                            paralysis_recorded = True
                            break
                    
                    # Якщо не знайшли руху, шукаємо останню позицію тріумфатора
                    if not paralysis_recorded:
                        # Шукаємо позицію цільової фігури з попереднього ходу
                        for j in range(i-5, i):
                            if j >= 0 and j < len(lines):
                                prev_line = lines[j]
                                if f'номер ходу {current_turn - 1}' in prev_line:
                                    for k in range(j+1, min(len(lines), j+5)):
                                        pos_line = lines[k]
                                        if 'номер ходу' in pos_line:
                                            break
                                        pos_match = re.search(r'на ([A-T]\d+)', pos_line)
                                        if pos_match:
                                            target_pos = pos_match.group(1)
                        
                        # Шукаємо останню позицію тріумфатора
                        color_match = re.search(r'(білий|чорний|біла|чорна) [Тт]ріумфатор', line)
                        if color_match:
                            color = color_match.group(1)
                            triumphator_pos = None
                            for j in range(i-1, max(0, i-50), -1):
                                search_line = lines[j]
                                tr_pos_match = re.search(rf'{color} [Тт]ріумфатор id\(\d+\).*?на ([A-T]\d+)', search_line)
                                if tr_pos_match:
                                    triumphator_pos = tr_pos_match.group(1)
                                    break
                            
                            if triumphator_pos and target_pos:
                                moves[current_turn] = [f"{triumphator_pos} xP{target_pos}({paralysis_turns})"]
                                paralysis_recorded = True
                
                # Варіант 2: Паралізація від блискавки або іншої фігури
                elif 'паралізована на' in line:
                    # Витягуємо кількість ходів
                    turns_match = re.search(r'паралізована на (\d+) хід', line)
                    if turns_match:
                        paralysis_turns = int(turns_match.group(1))
                    
                    # Витягуємо позицію з цього ж рядка
                    pos_match = re.search(r'на ([A-T]\d+)', line)
                    if pos_match:
                        target_pos = pos_match.group(1)
                        # Шукаємо атаку, що призвела до паралізації (вбивство блискавки)
                        for j in range(i-1, max(0, i-5), -1):
                            prev_line = lines[j]
                            if 'номер ходу' in prev_line and str(current_turn) not in prev_line:
                                break
                            attack_match = re.search(r'id\(\d+\) з ([A-T]\d+) .+ атакує .+ на ([A-T]\d+)', prev_line)
                            if attack_match:
                                from_pos = attack_match.group(1)
                                to_pos = attack_match.group(2)
                                # Додаємо паралізацію до атаки
                                moves[current_turn] = [f"{from_pos} x{to_pos}P({paralysis_turns})"]
                                paralysis_recorded = True
                                break
                
                if not paralysis_recorded and target_pos:
                    # Якщо нічого не знайшли, просто запишемо паралізацію
                    moves[current_turn] = [f"xP{target_pos}({paralysis_turns})"]
                
                continue
            
            # 2. Воскресіння (що затрачують хід)
            # Варіант 1: звичайні воскресіння "позицією"
            res_match = re.search(r'Гравець (?:білий|чорний) воскресив (пішака|коня|офіцера|тура|всадника|слона|королеву|короля|щита|фурію|храм|аристократа|місяць|око|блискавку|тріумфатора) .+ позицією ([A-T]\d+) .+ \(хід затрачено\)', line)
            if res_match:
                piece_type = res_match.group(1)
                pos = res_match.group(2)
                # Мапінг типів фігур на короткі позначки
                piece_map = {
                    'пішака': 'P', 'коня': 'N', 'офіцера': 'B', 'тура': 'R', 
                    'всадника': 'Ri', 'слона': 'B', 'королеву': 'Q', 'короля': 'K',
                    'щита': 'Sh', 'фурію': 'Fu', 'храм': 'Te', 'аристократа': 'Ar',
                    'місяць': 'Mo', 'око': 'Ey', 'блискавку': 'Li', 'тріумфатора': 'Tr'
                }
                piece_short = piece_map.get(piece_type, 'P')
                moves[current_turn].append(f"{pos} xR{piece_short}")
                continue
            
            # Варіант 2: воскресіння всадників "на позиції"
            res_rider_match = re.search(r'Гравець (?:білий|чорний) воскресив (всадник) .+ на позиції ([A-T]\d+)', line)
            if res_rider_match:
                pos = res_rider_match.group(2)
                moves[current_turn] = [f"{pos} xRRi"]
                continue
            
            # 3. Телепортація
            teleport_match = re.search(r'з ([а-я]+ [а-я]+) [Тт]уманності .+ телепортується на ([а-я]+ [а-я]+) [Тт]уманність', line)
            if teleport_match:
                from_fog = fog_map.get(teleport_match.group(1), teleport_match.group(1))
                to_fog = fog_map.get(teleport_match.group(2), teleport_match.group(2))
                # Перевіряємо чи була смерть
                death_marker = 'D' if current_turn in fog_deaths and fog_deaths[current_turn] == 'teleport' else ''
                move_str = f"{from_fog} xT{death_marker}{to_fog}"
                moves[current_turn] = [move_str]
                continue
            
            # 4. Священний обмін (храм і аристократ)
            # Храм: "здійснив священний обмін"
            # Аристократ: "обмінявся"
            if ('здійснив священний обмін' in line or 'обмінявся' in line) and i + 1 < len(lines):
                next_line = lines[i + 1]
                swap_coords = re.findall(r'([A-T]\d+)', next_line)
                if len(swap_coords) >= 2:
                    # Перевіряємо чи є паралізація від блискавки після обміну
                    paralysis_timer = 1  # за замовчуванням
                    paralysis_detected = False
                    for j in range(i+1, min(len(lines), i+5)):
                        check_line = lines[j]
                        if 'отримав електричний шок від Блискавки' in check_line:
                            paralysis_detected = True
                            timer_match = re.search(r'на (\d+) хід', check_line)
                            if timer_match:
                                paralysis_timer = int(timer_match.group(1))
                            break
                    
                    if paralysis_detected:
                        moves[current_turn] = [f"{swap_coords[0]} xS{swap_coords[1]}P({paralysis_timer})"]
                    else:
                        moves[current_turn] = [f"{swap_coords[0]} xS{swap_coords[1]}"]
                    skip_lines = 5 if paralysis_detected else 2
                continue
            
            # 5. Активація подвійного ходу місяців
            if 'АКТИВОВАНО: Подвійний хід Місяців' in line and i > 0:
                # Шукаємо останню атаку слона
                for j in range(i-1, max(0, i-3), -1):
                    prev_line = lines[j]
                    attack_match = re.search(r'слон id\(\d+\) з ([A-T]\d+).+ атакує .+ на ([A-T]\d+)', prev_line)
                    if attack_match:
                        from_pos = attack_match.group(1)
                        to_pos = attack_match.group(2)
                        moves[current_turn] = [f"{from_pos} x{to_pos}*M"]
                        break
                continue
            
            # 6. Подвійні ходи місяців
            double_move_first = re.search(r'Перший хід подвійного ходу Місяцем.+ ([A-T]\d+) на ([A-T]\d+)', line)
            if double_move_first:
                from_pos = double_move_first.group(1)
                to_pos = double_move_first.group(2)
                # Шукаємо другий хід
                for j in range(i+1, min(len(lines), i+5)):
                    next_line = lines[j]
                    double_move_second = re.search(r'Другий хід подвійного ходу Місяцем.+ ([A-T]\d+) на ([A-T]\d+)', next_line)
                    if double_move_second:
                        to_pos2 = double_move_second.group(2)
                        moves[current_turn] = [f"{from_pos} {to_pos} xD {to_pos} {to_pos2}"]
                        skip_lines = 5
                        break
                continue
            
            # 7. Атака з додатковою втратою
            if 'Додаткова втрата:' in line and i > 0:
                shield_match = re.search(r'щит id\(\d+\) знищено на ([A-T]\d+)', line)
                if shield_match:
                    shield_pos = shield_match.group(1)
                    # Шукаємо атаку перед цим (будь-яка фігура може атакувати)
                    for j in range(i-1, max(0, i-3), -1):
                        prev_line = lines[j]
                        attack_match = re.search(r'id\(\d+\) з ([A-T]\d+).+ атакує .+ на ([A-T]\d+)', prev_line)
                        if attack_match:
                            from_pos = attack_match.group(1)
                            to_pos = attack_match.group(2)
                            moves[current_turn] = [f"{from_pos} x{to_pos}+{shield_pos}"]
                            break
                continue
            
            # 8. Звичайні ходи та атаки
            # Спочатку перевіряємо вхід у туманність з координат (з "на туманність")
            fog_entry_from_coord_match = re.search(r'id\(\d+\) ходить з ([A-T]\d+) .+ на ([а-я]+ [а-я]+) туманність', line)
            if fog_entry_from_coord_match:
                from_pos = fog_entry_from_coord_match.group(1)
                to_fog = fog_entry_from_coord_match.group(2)
                to_pos = fog_map.get(to_fog, to_fog)
                to_pos += '~'  # Позначка входу в туманність
                
                if not moves[current_turn]:
                    move_str = f"{from_pos} {to_pos}"
                    moves[current_turn].append(move_str)
                continue
            
            # Атака З туманності НА координати
            fog_attack_match = re.search(r'з ([а-я]+ [а-я]+) [Тт]уманності .+ атакує .+ на ([A-T]\d+)', line)
            if fog_attack_match:
                from_fog = fog_attack_match.group(1)
                to_pos = fog_attack_match.group(2)
                from_pos = fog_map.get(from_fog, from_fog)
                
                if not moves[current_turn]:
                    move_str = f"{from_pos} x{to_pos}"
                    moves[current_turn].append(move_str)
                continue
            
            # Спочатку пробуємо атаки (вищий пріоритет)
            attack_match = re.search(r'id\(\d+\) з ([A-T]\d+) .+ атакує .+ на ([A-T]\d+)', line)
            if attack_match:
                from_pos = attack_match.group(1)
                to_pos = attack_match.group(2)
                
                # Перевіряємо чи не була вже записана атака з спец-ефектом
                if not moves[current_turn]:
                    move_str = f"{from_pos} x{to_pos}"
                    moves[current_turn].append(move_str)
                continue
            
            # Потім звичайні ходи
            simple_move_match = re.search(r'id\(\d+\) ходить з ([A-T]\d+) .+ на ([A-T]\d+)', line)
            if simple_move_match:
                from_pos = simple_move_match.group(1)
                to_pos = simple_move_match.group(2)
                
                # Перевіряємо чи не була вже записана
                if not moves[current_turn]:
                    move_str = f"{from_pos} {to_pos}"
                    moves[current_turn].append(move_str)
                continue
                
        # Додаємо інформацію про таймери та смерті
        for turn in sorted(fog_timers.keys()):
            if turn in moves and moves[turn]:
                # Додаємо відмітку про таймер на ПОЧАТКУ ходу
                fog_short, timer = fog_timers[turn]
                timer_str = f"{fog_short}({timer})"
                moves[turn].insert(0, timer_str)
        
        for turn in fog_deaths:
            if fog_deaths[turn] == 'timeout' and turn in moves:
                # Додаємо позначку про смерть після ходу
                moves[turn].append('FD')
        
        # Додаємо маркери шахів, матів та патів
        for turn in check_markers:
            if turn in moves and moves[turn]:
                marker = check_markers[turn]
                # Додаємо маркер до останнього елемента ходу
                last_move_idx = len(moves[turn]) - 1
                moves[turn][last_move_idx] = moves[turn][last_move_idx] + marker
        
        # Формуємо PGN
        pgn_header = f"""[Event "{mode}"]
[Site "Тренувальний датасет"]
[Date "{date}"]
[Round "1"]
[White "Гравець_1"]
[Black "Гравець_2"]
[Result "{result}"]
"""
        
        # Форматуємо ходи
        formatted_moves = []
        for turn_num in sorted(moves.keys()):
            if moves[turn_num]:
                move_str = ' '.join(moves[turn_num])
                formatted_moves.append(f"{turn_num}. {move_str}")
        
        # Розбиваємо по 3 ходи на рядок
        pgn_lines = []
        for i in range(0, len(formatted_moves), 3):
            pgn_lines.append(' '.join(formatted_moves[i:i+3]))
        
        pgn_body = '\n'.join(pgn_lines) if pgn_lines else ""
        
        return f"{pgn_header}\n{pgn_body} {result}"
        
    except Exception as e:
        logger.error(f"Помилка генерації PGN: {e}")
        return f"[Event \"Людина проти Людини\"]\n[Result \"{result}\"]\n\n{result}"

def finish_current_turn():
    """Завершує поточний хід і виводить всі накопичені події"""
    _flush_pending_events()

def log_double_move(piece_name: str, from_row: int, from_col: int, to_row: int, to_col: int, is_second_move: bool = False):
    """Логує подвійний хід Moon фігури"""
    from_pos = convert_coords_to_chess_notation(from_row, from_col)
    to_pos = convert_coords_to_chess_notation(to_row, to_col)
    
    move_part = "перший" if not is_second_move else "другий"
    log_party_event(f"{piece_name} здійснює {move_part} хід подвійного ходу: {from_pos} → {to_pos}")
    
    if is_second_move:
        # Для PGN додаємо спеціальний маркер подвійного ходу
        pgn_move = f"M{to_pos}xD"
        pgn_moves.append(pgn_move)

def log_skip_turn(reason: str, affected_player: str = ""):
    """Логує пропуск ходу через паралізацію або інші причини"""
    if affected_player:
        log_party_event(f"{affected_player} пропускає хід ({reason})")
    else:
        log_party_event(f"Хід пропущено ({reason})")
    
    # Для PGN додаємо маркер пропуску ходу
    pgn_moves.append("--")

def log_shield_protection(protected_piece: str, shield_pos: str, attack_blocked: bool = True):
    """Логує захист щитом"""
    if attack_blocked:
        log_party_event(f"{protected_piece} захищений щитом на {shield_pos} - атака заблокована")
    else:
        log_party_event(f"{protected_piece} під захистом щита на {shield_pos}")

def log_special_ability_activation(piece_name: str, ability_name: str, details: str = ""):
    """Логує активацію спеціальних здібностей фігур"""
    message = f"{piece_name} активує здібність: {ability_name}"
    if details:
        message += f" ({details})"
    log_party_event(message)
    
    # Для PGN додаємо маркер активації здібності
    piece_symbol = piece_name[0].upper()
    pgn_moves.append(f"{piece_symbol}*")

def log_fog_interaction(piece_name: str, from_row: int, from_col: int, to_row: int, to_col: int, interaction_type: str):
    """Логує взаємодію з туманністю"""
    from_pos = convert_coords_to_chess_notation(from_row, from_col)
    to_pos = convert_coords_to_chess_notation(to_row, to_col)
    
    log_party_event(f"{piece_name} {interaction_type} туманність: {from_pos} → {to_pos}")
    
    # Для PGN додаємо маркер взаємодії з туманністю
    piece_symbol = piece_name[0].upper()
    pgn_moves.append(f"{piece_symbol}{to_pos}~")

def log_eye_enhancement(enhanced_eyes: list, final_line_eye: str):
    """Логує посилення Очей після досягнення фінальної лінії"""
    enhanced_positions = [convert_coords_to_chess_notation(eye['row'], eye['col']) for eye in enhanced_eyes]
    log_party_event(f"Око на {final_line_eye} досягло фінальної лінії")
    log_party_event(f"Посилено Очі на позиціях: {', '.join(enhanced_positions)}")
    
    # Для PGN додаємо маркер посилення
    pgn_moves.append(f"E{final_line_eye}(E)")

def log_triumphator_action(action_type: str, triumphator_pos: str, target_info: str = "", details: str = ""):
    """Логує дії Тріумфатора"""
    message = f"Тріумфатор на {triumphator_pos} {action_type}"
    if target_info:
        message += f" {target_info}"
    if details:
        message += f" ({details})"
    log_party_event(message)
    
    # Для PGN додаємо маркер дії Тріумфатора
    pgn_moves.append(f"Tr{triumphator_pos}(T)")

def log_piece_enhancement(piece_name: str, enhancement_type: str, source: str = ""):
    """Логує посилення фігури через спеціальні ефекти"""
    message = f"{piece_name} отримує посилення: {enhancement_type}"
    if source:
        message += f" (від {source})"
    log_party_event(message)
