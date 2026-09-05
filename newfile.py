import html
import random
import re

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# ============================================================
# НАСТРОЙКА
# ============================================================

TOKEN = "8874069279:AAHrLaWaDX8jPcb_-dQkfBtBrWzizWXkkbw"


# ============================================================
# ХРАНИЛИЩЕ ИГР
# ============================================================

games = {}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_name(user):
    """Красивое имя пользователя."""
    if user.username:
        return f"@{user.username}"

    name = user.first_name or "Игрок"

    if user.last_name:
        name += f" {user.last_name}"

    return name


def get_game(chat_id):
    return games.get(chat_id)


def is_group(update):
    chat = update.effective_chat

    return chat and chat.type in ("group", "supergroup")


def normalize_word(text):
    """Приводит слово к удобному виду."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def parse_comment(text):
    """
    Поддержка:
    яблоко #это пример#

    Вернёт:
    основной текст
    комментарий
    """

    text = text.strip()

    match = re.match(r"^(.*?)\s*#(.*?)#\s*$", text, re.DOTALL)

    if match:
        main_text = match.group(1).strip()
        comment = match.group(2).strip()

        return main_text, comment

    return text, None


def correct_first_letter(word, letter):
    """
    Проверяет, начинается ли слово с нужной буквы.
    Ё и Е считаем одной буквой.
    """

    if not word:
        return False

    first = word[0].lower()
    needed = letter.lower()

    if first == needed:
        return True

    if first in ("е", "ё") and needed in ("е", "ё"):
        return True

    return False


def answer_keyboard(chat_id, question_id):
    """Кнопки ответа ведущего."""

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Да",
                callback_data=f"ans:yes:{chat_id}:{question_id}",
            ),
            InlineKeyboardButton(
                "❌ Нет",
                callback_data=f"ans:no:{chat_id}:{question_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🟡 Почти",
                callback_data=f"ans:almost:{chat_id}:{question_id}",
            ),
            InlineKeyboardButton(
                "🔵 Далеко",
                callback_data=f"ans:far:{chat_id}:{question_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "💡 Подсказка",
                callback_data=f"ans:hint:{chat_id}:{question_id}",
            ),
            InlineKeyboardButton(
                "✍️ Свой ответ",
                callback_data=f"ans:custom:{chat_id}:{question_id}",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def clear_question(game):
    """Очищает текущий вопрос."""
    game["current_question_id"] = None
    game["last_question"] = None
    game["last_question_comment"] = None
    game["private_keyboard_message_id"] = None


# ============================================================
# КОМАНДЫ БОТА
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 <b>Игра «Угадай слово»</b>\n\n"
        "Здесь два игрока пытаются угадать загаданное слово.\n\n"
        "<b>Команды:</b>\n"
        "/start — запустить бота\n"
        "/game — создать новую игру\n"
        "/join — присоединиться к игре\n"
        "/word — ведущему ввести слово\n"
        "/guess слово — попытаться угадать слово\n"
        "/rules — правила игры\n"
        "/help — помощь\n"
        "/status — состояние игры\n"
        "/stop — остановить игру\n\n"
        "💡 Если вы впервые используете бота, обязательно "
        "нажмите /start в личном чате с ботом."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Помощь</b>\n\n"
        "/game — создать игру в группе\n"
        "/join — присоединиться вторым игроком\n"
        "/word — ведущему ввести секретное слово\n"
        "/guess слово — попробовать угадать слово\n"
        "/rules — посмотреть правила\n"
        "/status — посмотреть состояние игры\n"
        "/stop — остановить игру\n\n"
        "Во время игры вопросы пишутся обычным сообщением "
        "в группе.\n\n"
        "Комментарии можно писать так:\n"
        "<code>вопрос #мой комментарий#</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 <b>Правила игры</b>\n\n"
        "1️⃣ В игре участвуют два игрока.\n"
        "2️⃣ Оба выбирают чёт или нечёт.\n"
        "3️⃣ Бот бросает 🎲 кубик.\n"
        "4️⃣ Один игрок становится ведущим.\n"
        "5️⃣ Второй игрок становится угадывающим.\n"
        "6️⃣ Ведущий вводит секретное слово в личном чате.\n"
        "7️⃣ Бот выбирает случайную букву.\n"
        "8️⃣ Ведущий даёт односоставную подсказку, "
        "начинающуюся с этой буквы.\n"
        "9️⃣ Угадывающий задаёт вопросы в группе.\n"
        "🔟 Ведущий отвечает кнопками.\n\n"
        "Ответы ведущего:\n"
        "✅ Да\n"
        "❌ Нет\n"
        "🟡 Почти\n"
        "🔵 Далеко\n"
        "💡 Подсказка\n"
        "✍️ Свой ответ\n\n"
        "При необходимости можно добавить комментарий:\n"
        "<code>яблоко #слишком сложно#</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        await update.message.reply_text(
            "❌ Команду /game нужно использовать в группе."
        )
        return

    chat_id = update.effective_chat.id

    if chat_id in games:
        game = games[chat_id]

        if game["stage"] != "finished":
            await update.message.reply_text(
                "⚠️ В этой группе уже идёт игра.\n"
                "Используйте /status."
            )
            return

        await update.message.reply_text(
            "🏁 Предыдущая игра закончена.\n"
            "Сначала используйте /stop, затем /game."
        )
        return

    user = update.effective_user
    name = get_name(user)

    games[chat_id] = {
        "chat_id": chat_id,

        "player1": user.id,
        "player1_name": name,

        "player2": None,
        "player2_name": None,

        "host": None,
        "host_name": None,

        "guesser": None,
        "guesser_name": None,

        "choice": {},
        "dice": None,

        "word": None,
        "letter": None,

        "hint": None,
        "hint_comment": None,

        "question_number": 0,
        "current_question_id": None,

        "last_question": None,
        "last_question_comment": None,

        "private_keyboard_message_id": None,

        "stage": "waiting_player",
    }

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 Присоединиться",
                    callback_data=f"join:{chat_id}",
                )
            ]
        ]
    )

    await update.message.reply_text(
        f"🎮 <b>Новая игра создана!</b>\n\n"
        f"👤 Игрок 1: <b>{html.escape(name)}</b>\n\n"
        f"Нужен второй игрок.\n"
        f"Нажмите кнопку ниже или используйте /join.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        await update.message.reply_text(
            "❌ Команду /join нужно использовать в группе."
        )
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id)

    if not game:
        await update.message.reply_text(
            "❌ Сейчас нет активной игры.\n"
            "Создайте её через /game."
        )
        return

    if game["stage"] != "waiting_player":
        await update.message.reply_text(
            "❌ Сейчас присоединиться уже нельзя."
        )
        return

    user = update.effective_user

    if user.id == game["player1"]:
        await update.message.reply_text(
            "❌ Вы уже являетесь первым игроком."
        )
        return

    game["player2"] = user.id
    game["player2_name"] = get_name(user)
    game["stage"] = "waiting_choice"

    await update.message.reply_text(
        f"🎮 Второй игрок присоединился!\n\n"
        f"👤 Игрок 1: <b>{html.escape(game['player1_name'])}</b>\n"
        f"👤 Игрок 2: <b>{html.escape(game['player2_name'])}</b>\n\n"
        f"Теперь каждый должен выбрать чёт или нечёт.",
        parse_mode="HTML",
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🟢 Чёт",
                    callback_data=f"choice:even:{chat_id}",
                ),
                InlineKeyboardButton(
                    "🔴 Нечёт",
                    callback_data=f"choice:odd:{chat_id}",
                ),
            ]
        ]
    )

    await update.message.reply_text(
        "🎲 <b>Выберите:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Команда предназначена для личного чата.
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "🔐 Секретное слово нужно вводить в личном чате с ботом."
        )
        return

    # Ищем игру, где пользователь ведущий.
    game = None

    for current_game in games.values():
        if current_game.get("host") == user.id:
            game = current_game
            break

    if not game:
        await update.message.reply_text(
            "❌ Вы сейчас не являетесь ведущим ни в одной игре."
        )
        return

    if game["stage"] not in ("waiting_word", "waiting_word_input"):
        await update.message.reply_text(
            "❌ Сейчас вводить слово нельзя."
        )
        return

    game["stage"] = "waiting_word_input"

    await update.message.reply_text(
        "🤫 Напишите мне <b>секретное слово</b> одним сообщением.\n\n"
        "Не отправляйте его в группу!",
        parse_mode="HTML",
    )


async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        await update.message.reply_text(
            "❌ Угадывать слово нужно в группе."
        )
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id)

    if not game:
        await update.message.reply_text(
            "❌ Активной игры нет."
        )
        return

    if game["stage"] != "playing":
        await update.message.reply_text(
            "❌ Сейчас слово угадывать нельзя."
        )
        return

    user = update.effective_user

    if user.id != game["guesser"]:
        await update.message.reply_text(
            "❌ Только угадывающий может пытаться угадать слово."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Используйте:\n"
            "<code>/guess слово</code>",
            parse_mode="HTML",
        )
        return

    guess = normalize_word(" ".join(context.args))
    word = normalize_word(game["word"])

    if guess == word:
        game["stage"] = "finished"

        await update.message.reply_text(
            f"🎉 <b>Правильно!</b>\n\n"
            f"🔐 Загаданное слово: "
            f"<b>{html.escape(game['word'])}</b>\n\n"
            f"🏆 Победил: "
            f"<b>{html.escape(game['guesser_name'])}</b>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "❌ Неверно. Игра продолжается."
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        await update.message.reply_text(
            "ℹ️ /status работает в группе."
        )
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id)

    if not game:
        await update.message.reply_text(
            "ℹ️ Активной игры нет."
        )
        return

    stage_names = {
        "waiting_player": "ожидание второго игрока",
        "waiting_choice": "выбор чёт/нечёт",
        "rolling": "бросок кубика",
        "waiting_word": "ожидание секретного слова",
        "waiting_word_input": "ввод секретного слова",
        "waiting_hint": "ожидание первой подсказки",
        "playing": "игра идёт",
        "waiting_new_hint": "ведущий пишет новую подсказку",
        "waiting_custom": "ведущий пишет свой ответ",
        "finished": "игра закончена",
    }

    stage = stage_names.get(
        game["stage"],
        game["stage"],
    )

    text = (
        "📊 <b>Состояние игры</b>\n\n"
        f"👤 Игрок 1: <b>{html.escape(game['player1_name'])}</b>\n"
        f"👤 Игрок 2: "
        f"<b>{html.escape(game['player2_name'] or '—')}</b>\n\n"
        f"🎭 Ведущий: "
        f"<b>{html.escape(game['host_name'] or '—')}</b>\n"
        f"🔎 Угадывающий: "
        f"<b>{html.escape(game['guesser_name'] or '—')}</b>\n\n"
        f"📌 Состояние: <b>{stage}</b>"
    )

    if game.get("letter"):
        text += f"\n🔤 Буква: <b>{html.escape(game['letter'])}</b>"

    if game.get("hint"):
        text += f"\n💡 Подсказка: <b>{html.escape(game['hint'])}</b>"

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        await update.message.reply_text(
            "❌ /stop нужно использовать в группе."
        )
        return

    chat_id = update.effective_chat.id

    if chat_id not in games:
        await update.message.reply_text(
            "ℹ️ Активной игры нет."
        )
        return

    game = games[chat_id]

    # Удаляем клавиатуру у сообщения ведущего, если она существует.
    try:
        if game.get("private_keyboard_message_id"):
            await context.bot.edit_message_reply_markup(
                chat_id=game["host"],
                message_id=game["private_keyboard_message_id"],
                reply_markup=None,
            )
    except Exception:
        pass

    del games[chat_id]

    await update.message.reply_text(
        "🛑 <b>Игра остановлена.</b>\n\n"
        "Можно начать новую через /game.",
        parse_mode="HTML",
    )


# ============================================================
# CALLBACK: ПРИСОЕДИНЕНИЕ
# ============================================================

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    try:
        _, chat_id_text = query.data.split(":")
        chat_id = int(chat_id_text)
    except Exception:
        return

    game = get_game(chat_id)

    if not game:
        await query.answer(
            "Игра уже закончилась.",
            show_alert=True,
        )
        return

    if game["stage"] != "waiting_player":
        await query.answer(
            "Присоединиться уже нельзя.",
            show_alert=True,
        )
        return

    user = query.from_user

    if user.id == game["player1"]:
        await query.answer(
            "Вы уже игрок №1.",
            show_alert=True,
        )
        return

    game["player2"] = user.id
    game["player2_name"] = get_name(user)
    game["stage"] = "waiting_choice"

    await query.edit_message_text(
        f"🎮 <b>Второй игрок присоединился!</b>\n\n"
        f"👤 Игрок 1: <b>{html.escape(game['player1_name'])}</b>\n"
        f"👤 Игрок 2: <b>{html.escape(game['player2_name'])}</b>\n\n"
        f"Теперь выберите чёт или нечёт.",
        parse_mode="HTML",
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🟢 Чёт",
                    callback_data=f"choice:even:{chat_id}",
                ),
                InlineKeyboardButton(
                    "🔴 Нечёт",
                    callback_data=f"choice:odd:{chat_id}",
                ),
            ]
        ]
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text="🎲 <b>Выберите:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ============================================================
# CALLBACK: ЧЁТ / НЕЧЁТ
# ============================================================

async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    try:
        _, choice, chat_id_text = query.data.split(":")
        chat_id = int(chat_id_text)
    except Exception:
        await query.answer(
            "Ошибка.",
            show_alert=True,
        )
        return

    game = get_game(chat_id)

    if not game:
        await query.answer(
            "Игра закончилась.",
            show_alert=True,
        )
        return

    user = query.from_user

    if user.id not in (
        game["player1"],
        game["player2"],
    ):
        await query.answer(
            "Вы не участник этой игры.",
            show_alert=True,
        )
        return

    if game["stage"] != "waiting_choice":
        await query.answer(
            "Сейчас выбирать нельзя.",
            show_alert=True,
        )
        return

    if user.id in game["choice"]:
        await query.answer(
            "Вы уже сделали выбор.",
            show_alert=True,
        )
        return

    game["choice"][user.id] = choice

    await query.answer(
        "Выбор принят!",
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎲 {html.escape(get_name(user))} "
            f"выбрал "
            f"<b>{'чёт' if choice == 'even' else 'нечёт'}</b>."
        ),
        parse_mode="HTML",
    )

    if len(game["choice"]) < 2:
        return

    # ========================================================
    # Оба выбрали -> бросаем кубик
    # ========================================================

    game["stage"] = "rolling"

    dice_message = await context.bot.send_dice(
        chat_id=chat_id,
        emoji="🎲",
    )

    dice_value = dice_message.dice.value

    game["dice"] = dice_value

    # Чётное число = even
    result = "even" if dice_value % 2 == 0 else "odd"

    # Игрок, который выбрал выпавший вариант, становится ведущим.
    players = [
        game["player1"],
        game["player2"],
    ]

    winners = [
        player_id
        for player_id in players
        if game["choice"].get(player_id) == result
    ]

    if len(winners) == 1:
        host_id = winners[0]
    elif len(winners) == 2:
        # Оба угадали вариант.
        # Выбираем случайно.
        host_id = random.choice(winners)
    else:
        # Никто не угадал — выбираем случайно.
        host_id = random.choice(players)

    guesser_id = (
        game["player2"]
        if host_id == game["player1"]
        else game["player1"]
    )

    game["host"] = host_id
    game["guesser"] = guesser_id

    host_name = (
        game["player1_name"]
        if host_id == game["player1"]
        else game["player2_name"]
    )

    guesser_name = (
        game["player1_name"]
        if guesser_id == game["player1"]
        else game["player2_name"]
    )

    game["host_name"] = host_name
    game["guesser_name"] = guesser_name

    game["stage"] = "waiting_word"

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🎲 <b>Результат броска:</b> "
            f"{dice_value}\n\n"
            f"🎭 Ведущий: <b>{html.escape(host_name)}</b>\n"
            f"🔎 Угадывающий: <b>{html.escape(guesser_name)}</b>\n\n"
            "🤫 Ведущий, откройте личный чат с ботом "
            "и используйте /word."
        ),
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=host_id,
            text=(
                "🎭 <b>Вы стали ведущим!</b>\n\n"
                "Теперь введите секретное слово.\n"
                "Используйте команду /word."
            ),
            parse_mode="HTML",
        )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Я не смог написать ведущему в личку.\n"
                "Ведущий должен открыть личный чат с ботом "
                "и нажать /start."
            ),
        )


# ============================================================
# ЛИЧНЫЕ СООБЩЕНИЯ
# ============================================================

async def private_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Здесь обрабатываются сообщения ведущего в личке:

    waiting_word_input -> секретное слово
    waiting_new_hint   -> новая подсказка
    waiting_custom     -> свой ответ
    """

    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text.strip()

    # Ищем игру, где пользователь является ведущим.
    game = None

    for current_game in games.values():
        if current_game.get("host") == user.id:
            game = current_game
            break

    if not game:
        return

    # ========================================================
    # ВВОД СЕКРЕТНОГО СЛОВА
    # ========================================================

    if game["stage"] == "waiting_word_input":
        word, comment = parse_comment(text)

        if not word:
            await update.message.reply_text(
                "❌ Слово не может быть пустым.\n"
                "Попробуйте ещё раз."
            )
            return

        # Секретное слово желательно одним словом.
        if len(word.split()) != 1:
            await update.message.reply_text(
                "❌ Секретное слово должно состоять из одного слова."
            )
            return

        game["word"] = word

        # Случайная буква из слова.
        game["letter"] = random.choice(list(word))

        game["stage"] = "waiting_hint"

        await update.message.reply_text(
            f"🔐 Слово принято.\n\n"
            f"🔤 Нужная буква: "
            f"<b>{html.escape(game['letter'])}</b>\n\n"
            f"💡 Теперь напишите <b>в группе</b> "
            f"одно слово-подсказку, начинающееся "
            f"с этой буквы.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # НОВАЯ ПОДСКАЗКА
    # ========================================================

    if game["stage"] == "waiting_new_hint":
        hint, comment = parse_comment(text)

        if len(hint.split()) != 1:
            await update.message.reply_text(
                "❌ Подсказка должна состоять из одного слова.\n"
                "Попробуйте ещё раз."
            )
            return

        if not correct_first_letter(
            hint,
            game["letter"],
        ):
            await update.message.reply_text(
                f"❌ Подсказка должна начинаться "
                f"с буквы «{game['letter']}».\n\n"
                f"Напишите другую подсказку."
            )
            return

        game["hint"] = hint
        game["hint_comment"] = comment
        game["stage"] = "playing"

        text_to_group = (
            "💡 <b>Новая подсказка от ведущего:</b>\n\n"
            f"<b>{html.escape(hint)}</b>"
        )

        if comment:
            text_to_group += (
                f"\n\n💬 <i>{html.escape(comment)}</i>"
            )

        await context.bot.send_message(
            chat_id=game["chat_id"],
            text=text_to_group,
            parse_mode="HTML",
        )

        clear_question(game)

        await update.message.reply_text(
            "✅ Новая подсказка отправлена в группу."
        )

        return

    # ========================================================
    # СВОЙ ОТВЕТ
    # ========================================================

    if game["stage"] == "waiting_custom":
        answer, comment = parse_comment(text)

        if not answer:
            await update.message.reply_text(
                "❌ Ответ не может быть пустым.\n"
                "Попробуйте ещё раз."
            )
            return

        game["stage"] = "playing"

        text_to_group = (
            "✍️ <b>Ответ ведущего:</b>\n\n"
            f"{html.escape(answer)}"
        )

        if comment:
            text_to_group += (
                f"\n\n💬 <i>{html.escape(comment)}</i>"
            )

        await context.bot.send_message(
            chat_id=game["chat_id"],
            text=text_to_group,
            parse_mode="HTML",
        )

        clear_question(game)

        await update.message.reply_text(
            "✅ Ваш ответ отправлен в группу."
        )

        return


# ============================================================
# ПЕРВАЯ ПОДСКАЗКА В ГРУППЕ
# ============================================================

async def process_first_hint(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game,
):
    text = update.message.text.strip()

    hint, comment = parse_comment(text)

    if len(hint.split()) != 1:
        await update.message.reply_text(
            "❌ Подсказка должна состоять из одного слова."
        )
        return

    if not correct_first_letter(
        hint,
        game["letter"],
    ):
        await update.message.reply_text(
            f"❌ Подсказка должна начинаться "
            f"с буквы «{game['letter']}»."
        )
        return

    game["hint"] = hint
    game["hint_comment"] = comment
    game["stage"] = "playing"

    text_to_send = (
        "💡 <b>Первая подсказка:</b>\n\n"
        f"<b>{html.escape(hint)}</b>"
    )

    if comment:
        text_to_send += (
            f"\n\n💬 <i>{html.escape(comment)}</i>"
        )

    await update.message.reply_text(
        text_to_send,
        parse_mode="HTML",
    )


# ============================================================
# ВОПРОС УГАДЫВАЮЩЕГО
# ============================================================

async def process_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game,
):
    user = update.effective_user
    text = update.message.text.strip()

    # Если уже есть вопрос, ждём ответа ведущего.
    if game["current_question_id"] is not None:
        await update.message.reply_text(
            "⏳ Сначала дождитесь ответа ведущего "
            "на предыдущий вопрос."
        )
        return

    question, comment = parse_comment(text)

    if not question:
        return

    game["question_number"] += 1

    question_id = game["question_number"]

    game["current_question_id"] = question_id
    game["last_question"] = question
    game["last_question_comment"] = comment

    # --------------------------------------------------------
    # Публикуем вопрос в группе
    # --------------------------------------------------------

    group_text = (
        f"❓ <b>Вопрос №{question_id}</b>\n\n"
        f"{html.escape(question)}"
    )

    if comment:
        group_text += (
            f"\n\n💬 <i>{html.escape(comment)}</i>"
        )

    await context.bot.send_message(
        chat_id=game["chat_id"],
        text=group_text,
        parse_mode="HTML",
    )

    # --------------------------------------------------------
    # Отправляем ведущему вопрос + кнопки в личку
    # --------------------------------------------------------

    private_text = (
        f"❓ <b>Вопрос №{question_id}</b>\n\n"
        f"{html.escape(question)}"
    )

    if comment:
        private_text += (
            f"\n\n💬 <i>{html.escape(comment)}</i>"
        )

    private_text += (
        "\n\n👇 <b>Выберите ответ:</b>"
    )

    try:
        private_message = await context.bot.send_message(
            chat_id=game["host"],
            text=private_text,
            parse_mode="HTML",
            reply_markup=answer_keyboard(
                game["chat_id"],
                question_id,
            ),
        )

        game["private_keyboard_message_id"] = (
            private_message.message_id
        )

    except Exception:
        await context.bot.send_message(
            chat_id=game["chat_id"],
            text=(
                "⚠️ Не удалось отправить кнопки ведущему в личку.\n"
                "Ведущий должен открыть бота и нажать /start."
            ),
        )


# ============================================================
# ОБРАБОТКА КНОПОК ОТВЕТА
# ============================================================

async def answer_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    try:
        _, answer_type, chat_id_text, question_id_text = (
            query.data.split(":")
        )

        chat_id = int(chat_id_text)
        question_id = int(question_id_text)

    except Exception:
        await query.answer(
            "Ошибка данных.",
            show_alert=True,
        )
        return

    game = get_game(chat_id)

    if not game:
        await query.answer(
            "Игра закончилась.",
            show_alert=True,
        )
        return

    user = query.from_user

    # Кнопки работают только в личке ведущего.
    if query.message.chat.type != "private":
        await query.answer(
            "Эти кнопки работают только в личке ведущего.",
            show_alert=True,
        )
        return

    if user.id != game["host"]:
        await query.answer(
            "Только ведущий может отвечать.",
            show_alert=True,
        )
        return

    if game["current_question_id"] != question_id:
        await query.answer(
            "Этот вопрос уже обработан.",
            show_alert=True,
        )
        return

    if game["stage"] != "playing":
        await query.answer(
            "Сейчас ответить нельзя.",
            show_alert=True,
        )
        return

    # ========================================================
    # СРАЗУ УБИРАЕМ КНОПКИ
    # ========================================================

    try:
        await query.edit_message_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    game["private_keyboard_message_id"] = None

    # ========================================================
    # ДА
    # ========================================================

    if answer_type == "yes":
        game["stage"] = "finished"

        await query.answer("Игра окончена!")

        question_text = game.get("last_question") or ""

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 <b>ДА!</b>\n\n"
                f"❓ Вопрос: {html.escape(question_text)}\n\n"
                f"🔐 Загаданное слово:\n"
                f"<b>{html.escape(game['word'])}</b>\n\n"
                f"🏆 Угадал: "
                f"<b>{html.escape(game['guesser_name'])}</b>"
            ),
            parse_mode="HTML",
        )

        clear_question(game)

        return

    # ========================================================
    # НЕТ
    # ========================================================

    if answer_type == "no":
        await query.answer("Ответ отправлен.")

        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ <b>Нет.</b>",
            parse_mode="HTML",
        )

        clear_question(game)
        game["stage"] = "playing"

        return

    # ========================================================
    # ПОЧТИ
    # ========================================================

    if answer_type == "almost":
        await query.answer("Ответ отправлен.")

        await context.bot.send_message(
            chat_id=chat_id,
            text="🟡 <b>Почти.</b>",
            parse_mode="HTML",
        )

        clear_question(game)
        game["stage"] = "playing"

        return

    # ========================================================
    # ДАЛЕКО
    # ========================================================

    if answer_type == "far":
        await query.answer("Ответ отправлен.")

        await context.bot.send_message(
            chat_id=chat_id,
            text="🔵 <b>Далеко.</b>",
            parse_mode="HTML",
        )

        clear_question(game)
        game["stage"] = "playing"

        return

    # ========================================================
    # ПОДСКАЗКА
    # ========================================================

    if answer_type == "hint":
        await query.answer("Жду новую подсказку.")

        game["stage"] = "waiting_new_hint"

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "💡 <b>Ведущий готовит новую подсказку.</b>\n\n"
                "Подождите немного."
            ),
            parse_mode="HTML",
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "💡 <b>Введите новую подсказку.</b>\n\n"
                f"Она должна состоять из одного слова "
                f"и начинаться с буквы "
                f"<b>{html.escape(game['letter'])}</b>.\n\n"
                "Можно добавить комментарий:\n"
                "<code>слово #комментарий#</code>"
            ),
            parse_mode="HTML",
        )

        return

    # ========================================================
    # СВОЙ ОТВЕТ
    # ========================================================

    if answer_type == "custom":
        await query.answer("Жду ваш ответ.")

        game["stage"] = "waiting_custom"

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✍️ <b>Ведущий пишет свой ответ.</b>\n\n"
                "Подождите немного."
            ),
            parse_mode="HTML",
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "✍️ <b>Напишите свой ответ.</b>\n\n"
                "Я автоматически отправлю его в группу.\n\n"
                "Можно добавить комментарий:\n"
                "<code>Ответ #ваш комментарий#</code>"
            ),
            parse_mode="HTML",
        )

        return


# ============================================================
# СООБЩЕНИЯ В ГРУППЕ
# ============================================================

async def group_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_group(update):
        return

    # Команды обрабатываются отдельно.
    if update.message.text.startswith("/"):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if not game:
        return

    # ========================================================
    # ПЕРВАЯ ПОДСКАЗКА
    # ========================================================

    if game["stage"] == "waiting_hint":
        if user.id != game["host"]:
            return

        await process_first_hint(
            update,
            context,
            game,
        )

        return

    # ========================================================
    # ОЖИДАНИЕ НОВОЙ ПОДСКАЗКИ
    # ========================================================

    if game["stage"] == "waiting_new_hint":
        # ВАЖНО:
        # Новая подсказка теперь вводится в личке.
        return

    # ========================================================
    # ОЖИДАНИЕ КАСТОМНОГО ОТВЕТА
    # ========================================================

    if game["stage"] == "waiting_custom":
        # ВАЖНО:
        # Свой ответ теперь вводится в личке.
        return

    # ========================================================
    # ИГРА ИДЁТ
    # ========================================================

    if game["stage"] != "playing":
        return

    if user.id != game["guesser"]:
        return

    await process_question(
        update,
        context,
        game,
    )


# ============================================================
# МЕНЮ КОМАНД TELEGRAM
# ============================================================

async def post_init(application):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("game", "Создать игру"),
        BotCommand("join", "Присоединиться"),
        BotCommand("word", "Ввести секретное слово"),
        BotCommand("guess", "Попытаться угадать"),
        BotCommand("rules", "Правила игры"),
        BotCommand("help", "Помощь"),
        BotCommand("status", "Состояние игры"),
        BotCommand("stop", "Остановить игру"),
    ]

    await application.bot.set_my_commands(commands)


# ============================================================
# ОБРАБОТЧИК ОШИБОК
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(
        "Ошибка:",
        context.error,
    )


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Команды
    application.add_handler(
        CommandHandler("start", start_command)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("rules", rules_command)
    )

    application.add_handler(
        CommandHandler("game", game_command)
    )

    application.add_handler(
        CommandHandler("join", join_command)
    )

    application.add_handler(
        CommandHandler("word", word_command)
    )

    application.add_handler(
        CommandHandler("guess", guess_command)
    )

    application.add_handler(
        CommandHandler("status", status_command)
    )

    application.add_handler(
        CommandHandler("stop", stop_command)
    )

    # Кнопка "Присоединиться"
    application.add_handler(
        CallbackQueryHandler(
            join_callback,
            pattern=r"^join:"
        )
    )

    # Кнопки "Чёт / Нечёт"
    application.add_handler(
        CallbackQueryHandler(
            choice_callback,
            pattern=r"^choice:"
        )
    )

    # Кнопки ответов ведущего
    application.add_handler(
        CallbackQueryHandler(
            answer_callback,
            pattern=r"^ans:"
        )
    )

    # Сообщения в личке
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND
            & filters.ChatType.PRIVATE,
            private_text_handler,
        )
    )

    # Сообщения в группе
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND
            & filters.ChatType.GROUPS,
            group_text_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    print("Бот запущен!")

    application.run_polling()


if __name__ == "__main__":
    main()