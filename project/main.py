import logging, random, sqlite3, os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = "8020241872:AAFRJb_t9Fxh2lKHI2_nUqdIbHWpnmA-cNQ"

CHALLENGES = [
    {"id": 1, "title": "Без одноразового стаканчика", "desc": "Возьми кофе в свою кружку", "co2": 0.1},
    {"id": 2, "title": "Короткий душ", "desc": "Сократи душ на 5 минут", "co2": 1.2},
    {"id": 3, "title": "День без мяса", "desc": "Попробуй вегетарианскую еду", "co2": 3.2},
    {"id": 4, "title": "Выключи свет", "desc": "Не забудь выключить свет", "co2": 0.3}
]

MAIN_MENU = ReplyKeyboardMarkup([['🎯 Задание', '📊 Статистика'], ['🏆 Достижения', '❓ Помощь']], resize_keyboard=True)
TASK_MENU = ReplyKeyboardMarkup([['✅ Выполнил', '↩️ Назад']], resize_keyboard=True)

# Удаляем старую базу и создаем новую
if os.path.exists('ecoguide.db'):
    os.remove('ecoguide.db')

def get_db():
    conn = sqlite3.connect('ecoguide.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                   (user_id INTEGER PRIMARY KEY, username TEXT, co2_saved REAL DEFAULT 0)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS completed 
                   (user_id INTEGER, challenge_id INTEGER)''')
    return conn

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user.id, user.username))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"Привет {user.first_name}! 🌱\nЯ помогу тебе делать добрые дела для планеты!",
        reply_markup=MAIN_MENU
    )

async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db()
    
    # Получаем выполненные задания
    cursor = conn.cursor()
    cursor.execute("SELECT challenge_id FROM completed WHERE user_id = ?", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    
    # Выбираем задание
    available = [t for t in CHALLENGES if t['id'] not in completed]
    task = random.choice(available) if available else random.choice(CHALLENGES)
    
    context.user_data['current_task'] = task
    conn.close()
    
    text = f"🎯 {task['title']}\n\n{task['desc']}\n\n💚 Сэкономит: {task['co2']} кг CO₂"
    await update.message.reply_text(text, reply_markup=TASK_MENU)

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    task = context.user_data.get('current_task')
    
    if not task:
        await update.message.reply_text("Сначала получи задание! 🎯", reply_markup=MAIN_MENU)
        return
    
    conn = get_db()
    
    # Добавляем CO2
    conn.execute("UPDATE users SET co2_saved = co2_saved + ? WHERE user_id = ?", (task['co2'], user.id))
    
    # Добавляем в выполненные
    conn.execute("INSERT INTO completed (user_id, challenge_id) VALUES (?, ?)", (user.id, task['id']))
    
    conn.commit()
    
    # Получаем обновленные данные
    cursor = conn.cursor()
    cursor.execute("SELECT co2_saved FROM users WHERE user_id = ?", (user.id,))
    co2_saved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM completed WHERE user_id = ?", (user.id,))
    completed_count = cursor.fetchone()[0]
    
    level = int(co2_saved / 5) + 1
    conn.close()
    
    text = f"""🎉 Молодец!

✅ {task['title']}
💚 +{task['co2']} кг CO₂

📊 Всего: {co2_saved:.1f} кг
📈 Уровень: {level}
✅ Заданий: {completed_count}"""
    
    await update.message.reply_text(text, reply_markup=MAIN_MENU)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    
    cursor = conn.cursor()
    cursor.execute("SELECT co2_saved FROM users WHERE user_id = ?", (user.id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("Начни с /start")
        conn.close()
        return
    
    co2_saved = result[0]
    cursor.execute("SELECT COUNT(*) FROM completed WHERE user_id = ?", (user.id,))
    completed_count = cursor.fetchone()[0]
    
    level = int(co2_saved / 5) + 1
    conn.close()
    
    text = f"""📊 Твоя статистика:

🏆 Уровень: {level}
💚 CO₂: {co2_saved:.1f} кг
✅ Заданий: {completed_count}"""
    
    await update.message.reply_text(text, reply_markup=MAIN_MENU)

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    
    cursor = conn.cursor()
    cursor.execute("SELECT co2_saved FROM users WHERE user_id = ?", (user.id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("Начни с /start")
        conn.close()
        return
    
    co2_saved = result[0]
    cursor.execute("SELECT COUNT(*) FROM completed WHERE user_id = ?", (user.id,))
    completed_count = cursor.fetchone()[0]
    conn.close()
    
    achievements = []
    
    # Достижения по количеству заданий
    if completed_count >= 1:
        achievements.append("🎖 Первое задание")
    if completed_count >= 3:
        achievements.append("🏅 Опытный эколог (3+ заданий)")
    if completed_count >= 5:
        achievements.append("⭐ Мастер экологии (5+ заданий)")
    
    # Достижения по сэкономленному CO2
    if co2_saved >= 5:
        achievements.append("🌍 Спасатель планеты (5+ кг CO₂)")
    if co2_saved >= 10:
        achievements.append("🚀 ЭкоГерой (10+ кг CO₂)")
    
    if achievements:
        text = "🏆 Твои достижения:\n\n" + "\n".join(f"• {ach}" for ach in achievements)
    else:
        text = "Пока нет достижений 😢\n\nВыполни первое задание чтобы получить достижение! 🎖"
    
    await update.message.reply_text(text, reply_markup=MAIN_MENU)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🤖 EcoGuide Bot

🎯 Задание - получить задание
📊 Статистика - твой прогресс  
🏆 Достижения - твои награды
✅ Выполнил - отметить выполнение
↩️ Назад - в главное меню

/start - начать
/stats - статистика
/help - помощь"""
    await update.message.reply_text(text, reply_markup=MAIN_MENU)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '🎯 Задание': 
        await get_task(update, context)
    elif text == '📊 Статистика': 
        await show_stats(update, context)
    elif text == '🏆 Достижения': 
        await show_achievements(update, context)
    elif text == '❓ Помощь': 
        await help_cmd(update, context)
    elif text == '✅ Выполнил': 
        await complete_task(update, context)
    elif text == '↩️ Назад': 
        await update.message.reply_text("Главное меню:", reply_markup=MAIN_MENU)
    else: 
        await update.message.reply_text("Используй кнопки меню 👆", reply_markup=MAIN_MENU)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен! 🌱")
    app.run_polling()

if __name__ == '__main__':
    main()