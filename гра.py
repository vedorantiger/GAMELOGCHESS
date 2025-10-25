#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вершителі часу - Головний файл запуску гри
Точка входу + перевірка структури файлів
"""

import os
import sys
import traceback
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Налаштування глобального логера для помилок
def setup_error_logging():
    """Налаштовує глобальну обробку помилок"""
    from логування import game_logger
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Глобальний обробник помилок"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        game_logger.error(f"Необроблена помилка: {error_msg}")
        print(f"КРИТИЧНА ПОМИЛКА: {exc_value}")
        print("Деталі записано в помилки.log")
    
    sys.excepthook = handle_exception


def check_project_structure():
    """Перевіряє наявність всіх необхідних файлів проекту"""
    message = "🔍 Перевірка структури проекту..."
    print(message)
    
    base_path = Path(__file__).parent
    
    # Список обов'язкових файлів
    required_files = [
        "гра.py",
        "налаштування.py",
        "логування.py",
        "розташування_фігур.py",
        "стан_гри.py",
        "дошка.py",
        "правила_фігур.py",
        "графіка_гри.py",
        "графіка_інтерфейсу.py",
        "штучний_інтелект/__init__.py",
        "штучний_інтелект/алгоритм.py",
        "штучний_інтелект/оцінка.py",
    ]
    
    # Перевірка файлів
    missing_files = []
    existing_files = 0
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            existing_files += 1
        else:
            missing_files.append(file_path)
    
    # Перевірка фігур
    figure_names = [
        "aristocrat.svg", "bishop.svg", "eye.svg", "fury.svg", "king.svg",
        "knight.svg", "lightning.svg", "moon.svg", "pawn.svg", "queen.svg", 
        "rider.svg", "rook.svg", "shield.svg", "temple.svg", "triumphator.svg"
    ]
    
    white_figures_path = base_path / "ресурси/зображення/фігури/білі"
    black_figures_path = base_path / "ресурси/зображення/фігури/чорні"
    
    white_count = sum(1 for f in figure_names if (white_figures_path / f).exists())
    black_count = sum(1 for f in figure_names if (black_figures_path / f).exists())
    
    # Створення директорії логів
    log_dir = base_path / "логи"
    log_dir.mkdir(exist_ok=True)
    
    # Перевірка фонів
    backgrounds_path = base_path / "ресурси" / "зображення" / "фони"
    background_count = 0
    if backgrounds_path.exists():
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        seen_names = set()
        for file_path in backgrounds_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                name_without_ext = file_path.stem
                if name_without_ext not in seen_names:
                    background_count += 1
                    seen_names.add(name_without_ext)
    
    # Виведення результатів
    total_files = len(required_files)
    message1 = f"📁 Файли проекту: {existing_files}/{total_files}"
    print(message1)
    message2 = f"♟️  Фігури: {white_count}/15 білих, {black_count}/15 чорних"
    print(message2)
    
    if missing_files:
        message3 = "⚠️  Відсутні файли:"
        print(message3)
        for file in missing_files:
            message4 = f"   ❌ {file}"
            print(message4)
    
    if missing_files or white_count < 15 or black_count < 15:
        message5 = "❌ Деякі файли відсутні. Програма може працювати некоректно."
        print(message5)
        return False
    
    message6 = "✅ Структура проекту повна та коректна!"
    print(message6)
    if background_count > 0:
        message7 = f"Знайдено фонів: {background_count} шт."
        print(message7)
    
    return True


def main():
    """Головна функція запуску гри"""
    import os
    # os.system('cls')  # Очищення терміналу для Windows
    
    try:
        # Налаштування глобального логування помилок
        setup_error_logging()
        
        # Перевірка структури
        if not check_project_structure():
            message = "🛑 Неможливо запустити гру через відсутні файли."
            print(message)
            sys.exit(1)
        
        message = "🚀 Запуск гри..."
        print(message)
        
        # Запуск Qt додатку
        app = QApplication(sys.argv)
        app.setApplicationName("Вершителі часу")
        app.setOrganizationName("TimeChess")
        
        # Створення та показ головного вікна
        from графіка_інтерфейсу import MainWindow
        window = MainWindow()
        window.showMaximized()
        
        # Запуск головного циклу
        sys.exit(app.exec())
        
    except Exception as e:
        from логування import game_logger
        game_logger.error(f"Критична помилка при запуску гри: {e}")
        game_logger.error(traceback.format_exc())
        print(f"КРИТИЧНА ПОМИЛКА: {e}")
        print("Деталі записано в помилки.log")
        sys.exit(1)


if __name__ == "__main__":
    main()