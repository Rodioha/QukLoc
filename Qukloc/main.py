import os
import telebot
import requests
from model import get_class
from config import token
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_nearby_places, get_place_info, find_main_place_by_partial_name

# Инициализация бота
bot = telebot.TeleBot(token)

# Определяем абсолютные пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# Создаем папку для изображений если её нет
os.makedirs(IMAGES_DIR, exist_ok=True)

# Функция для создания главной инлайн-клавиатуры
def create_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Поиск по фото", callback_data="photo_search"),
        InlineKeyboardButton("📍 Интересные места", callback_data="interesting_places"),
        InlineKeyboardButton("❓ Помощь", callback_data="help")
    )
    return keyboard

# Функция для создания клавиатуры после анализа фото
def create_photo_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📍 Места поблизости", callback_data="nearby"),
        InlineKeyboardButton("🆕 Новое фото", callback_data="new_photo"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message):
    welcome_text = (
        "Привет! 👋\n\n"
        "Я бот QukLoc для идентификации локаций Мурманской области. Вот что я умею:\n\n"
        "🔍 *Поиск по фото* - определю достопримечательность по вашему фото\n"
        "📍 *Интересные места* - покажу популярные места Кольского полуострова\n"
        "❓ *Помощь* - расскажу как мной пользоваться\n\n"
        "Выберите действие:"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    if not message.photo:
        return bot.send_message(message.chat.id, "Вы забыли загрузить картинку :(")

    try:
        bot.send_message(message.chat.id, "🔍 Анализирую изображение...")
        
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = file_info.file_path.split('/')[-1]
        
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        result = get_class(model_path="./keras_model.h5", labels_path="labels.txt", image_path=file_name)
        
        bot.send_message(
            message.chat.id, 
            f"🎯 *Результат анализа:* {result}\n\nЧто хотите сделать дальше?",
            parse_mode='Markdown',
            reply_markup=create_photo_keyboard()
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при обработке фото: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data == "photo_search":
            bot.answer_callback_query(call.id, "Готов к загрузке фото!")
            bot.send_message(
                call.message.chat.id,
                "📸 Пришлите фото достопримечательности Мурманской области, и я попробую её определить!"
            )
            
        elif call.data == "interesting_places":
            bot.answer_callback_query(call.id, "Ищем интересные места...")
            bot.send_message(
                call.message.chat.id,
                "🗺️ *Популярные места Мурманской области:*\n\n"
                "Водопад Большой Янискенгас\n"
                "Кандалакша и Окрестности\n"
                "Терский Берег\n"
                "Лапландский Заповедник\n"
                "Хибины и город Кировск\n"
                "Ловозерские Тундры и Сейдозеро\n"
                "Мурманск\n"
                "Териберка\n"
                "Остров Кильдин\n"
                "Полуостров Рыбачий\n"
                "Загрузите фото места или выберите поиск по фото",
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
            
        elif call.data == "help":
            bot.answer_callback_query(call.id, "Открываем справку")
            help_text = (
                "ℹ️ *Как пользоваться ботом QukLoc:*\n\n"
                "1. *Поиск по фото* - отправьте фото достопримечательности Мурманской области\n"
                "2. *Интересные места* - посмотрите популярные места Кольского полуострова\n"
                "3. *После анализа фото* вы получите дополнительное меню\n\n"
                "Для начала работы выберите действие в меню ниже 👇"
            )
            bot.send_message(
                call.message.chat.id,
                help_text,
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
            
        elif call.data == "nearby":
            bot.answer_callback_query(call.id, "Ищем интересные места...")
            
            previous_message = call.message.text
            if "Результат анализа:" in previous_message:
                current_place = previous_message.split("Результат анализа:")[1].strip().split(" (")[0]
                
                # Используем функцию для поиска полного названия
                full_place_name = find_main_place_by_partial_name(current_place)
                if full_place_name:
                    current_place = full_place_name
            else:
                current_place = "Мурманская область"
            
            # Используем функцию из database.py
            places = get_nearby_places(current_place)
            
            # Создаем клавиатуру с кнопками для каждого места
            keyboard = InlineKeyboardMarkup(row_width=1)
            for place in places:
                keyboard.add(InlineKeyboardButton(f"📍 {place['name']}", callback_data=f"place_{place['name']}"))
            
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_photo"))
            
            bot.send_message(
                call.message.chat.id,
                f"🏛️ *Интересные места рядом:*\n\n"
                "Выберите место для получения информации:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
                   
        elif call.data == "new_photo":
            bot.answer_callback_query(call.id, "Готов к загрузке нового фото")
            bot.send_message(
                call.message.chat.id,
                "📸 Загрузите новое фото достопримечательности для анализа.\n\n"
                "Я определю объект и предоставлю информацию о нем.",
                reply_markup=create_photo_keyboard()
            )
            
        elif call.data.startswith("place_"):
            bot.answer_callback_query(call.id, "🔄 Загружаем информацию...")
            
            place_name = call.data.replace("place_", "")
            place_info = get_place_info(place_name)
            
            photo_path = place_info.get("photo")
            photo_sent = False
            
            if photo_path:
                # Преобразуем относительный путь в абсолютный
                if photo_path.startswith("../"):
                    relative_path = photo_path[3:]  # Убираем ../
                    absolute_photo_path = os.path.join(BASE_DIR, relative_path)
                else:
                    absolute_photo_path = os.path.join(IMAGES_DIR, photo_path)
                
                # Проверяем существование файла
                if os.path.exists(absolute_photo_path):
                    try:
                        with open(absolute_photo_path, 'rb') as photo_file:
                            bot.send_photo(
                                call.message.chat.id,
                                photo_file,
                                caption=f"🏛️ *{place_info['name']}*\n\n{place_info['description']}",
                                parse_mode='Markdown'
                            )
                            photo_sent = True
                    except Exception as file_error:
                        # Ошибка чтения файла
                        error_msg = f"❌ Ошибка при загрузке фото: {str(file_error)}"
                        bot.send_message(
                            call.message.chat.id,
                            f"🏛️ *{place_info['name']}*\n\n{place_info['description']}\n\n{error_msg}",
                            parse_mode='Markdown'
                        )
                else:
                    # Файл не найден - показываем путь для отладки
                    bot.send_message(
                        call.message.chat.id,
                        f"🏛️ *{place_info['name']}*\n\n{place_info['description']}\n\n"
                        f"❌ Фото временно недоступно\n"
                        f"Файл не найден по пути: `{absolute_photo_path}`",
                        parse_mode='Markdown'
                    )
            
            # Если фото не было отправлено, отправляем только текст
            if not photo_sent:
                bot.send_message(
                    call.message.chat.id,
                    f"🏛️ *{place_info['name']}*\n\n{place_info['description']}",
                    parse_mode='Markdown'
                )
            
            # Клавиатура для дальнейших действий
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(

                InlineKeyboardButton("🔙 Назад", callback_data="back_to_photo")
            )
            
            bot.send_message(
                call.message.chat.id,
                "Что дальше?",
                reply_markup=keyboard
            )
            
        elif call.data.startswith("info_"):
            place_name = call.data.replace("info_", "")
            place_info = get_place_info(place_name)
            
            facts_text = (
                f"📚 *Дополнительная информация о {place_info['name']}:*\n\n"
                f"{place_info['description']}\n\n"
                f"*Историческая справка:*\n"
                f"Место имеет богатую историю и культурное значение для Мурманской области."
            )
            
            bot.send_message(
                call.message.chat.id,
                facts_text,
                parse_mode='Markdown',
                reply_markup=create_photo_keyboard()
            )
            
        elif call.data == "back_to_photo":
            bot.answer_callback_query(call.id, "Возвращаемся")
            bot.send_message(
                call.message.chat.id,
                "Выберите действие:",
                reply_markup=create_photo_keyboard()
            )
            
        elif call.data == "back_to_main":
            bot.answer_callback_query(call.id, "Возвращаемся в главное меню")
            bot.send_message(
                call.message.chat.id,
                "Главное меню:",
                reply_markup=create_main_keyboard()
            )
                
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")
        bot.send_message(
            call.message.chat.id,
            f"⚠️ *Ошибка:*\n\n`{str(e)}`\n Попробуйте выбрать другое действие.",
            parse_mode='Markdown'
        )

if __name__ == "__main__":
    print("Бот QukLoc запущен...")
    bot.polling(none_stop=True)