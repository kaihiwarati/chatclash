from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import datetime
import os
import time
from dotenv import load_dotenv
import random

OWNER_ID = 7480261167 # put your Telegram ID here

def is_owner(user_id):
    return user_id == OWNER_ID

# ================= ENV =================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN not found in .env")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "data_v2.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    group_id INTEGER,
    group_name TEXT,
    name TEXT,
    daily_count INTEGER DEFAULT 0,
    weekly_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    last_active_date TEXT,
    UNIQUE(user_id, group_id)
)
""")
conn.commit()

# ================= START UI =================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        InlineKeyboardButton("➕ Add me in group", url="https://t.me/erzachris_bot?startgroup=true")
    )

    keyboard.add(
        InlineKeyboardButton("📊 Your Stats", callback_data="stats"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="lb_overall")
    )

    keyboard.add(
        InlineKeyboardButton("📢 Updates", url="https://t.me/erzaupdates")
    )

    text = (
        "🤖 Welcome!\n\n"
        "🔥 Compete daily and climb leaderboard\n"
        "🏆 Become the top chatter in your group\n\n"
        "💡 Use commands below to explore"
    )

    await message.answer(text, reply_markup=keyboard)

# ================= CALLBACK =================
@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_btn(callback: types.CallbackQuery):
    await callback.message.answer("Use /stats in group 📊")

@dp.callback_query_handler(lambda c: c.data == "lb_overall")
async def open_leaderboard(callback: types.CallbackQuery):

    text = await get_leaderboard_text(
        callback.message.chat.id,
        "total_count",
        "Overall Leaderboard"
    )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=leaderboard_buttons("overall")
    )

    await callback.answer()

# ================= PING =================
@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    await message.reply("🏓 Bot is alive!")

# ================= ADMIN CHECK =================
async def is_admin(message: types.Message):
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ["administrator", "creator"]

# ================= ADMIN =================
@dp.message_handler(commands=['ban'])
async def ban_user(message: types.Message):
    if not await is_admin(message): return await message.reply("❌ Not admin")
    if not message.reply_to_message: return await message.reply("Reply to user")

    await bot.kick_chat_member(message.chat.id, message.reply_to_message.from_user.id)
    await message.reply("🚫 User banned")

@dp.message_handler(commands=['mute'])
async def mute_user(message: types.Message):
    if not await is_admin(message): return await message.reply("❌ Not admin")
    if not message.reply_to_message: return await message.reply("Reply to user")

    try:
        duration = int(message.get_args())
    except:
        return await message.reply("Usage: /mute 60")

    await bot.restrict_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        types.ChatPermissions(can_send_messages=False),
        until_date=int(time.time()) + duration
    )

    await message.reply(f"🔇 Muted for {duration} sec")

@dp.message_handler(commands=['unmute'])
async def unmute_user(message: types.Message):
    if not await is_admin(message): return await message.reply("❌ Not admin")
    if not message.reply_to_message: return await message.reply("Reply to user")

    await bot.restrict_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        types.ChatPermissions(can_send_messages=True)
    )

    await message.reply("🔊 Unmuted")

# ================= STATS =================
@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):

    cursor.execute("""
    SELECT daily_count, total_count 
    FROM users WHERE user_id=? AND group_id=?
    """, (message.from_user.id, message.chat.id))

    data = cursor.fetchone()

    if data:
        daily, total = data
    else:
        daily, total = 0, 0

    await message.reply(
        f"👤 {message.from_user.full_name}\n\n"
        f"📅 Today: {daily}\n"
        f"📊 Total: {total}"
    )

# ================= MESSAGE TRACK =================
@dp.message_handler(lambda message: message.text and not message.text.startswith('/'))
async def track_message(message: types.Message):

    if message.chat.type == "private":
        return

    user_id = message.from_user.id
    group_id = message.chat.id
    group_name = message.chat.title
    name = message.from_user.full_name

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    week = datetime.datetime.now().strftime("%Y-%W")

    cursor.execute("""
    INSERT OR IGNORE INTO users 
    (user_id, group_id, group_name, name, daily_count, weekly_count, total_count, last_active_date)
    VALUES (?, ?, ?, ?, 0, 0, 0, ?)
    """, (user_id, group_id, group_name, name, today))

    # Reset daily
    cursor.execute("""
    UPDATE users SET daily_count=0 
    WHERE group_id=? AND last_active_date != ?
    """, (group_id, today))

    # Update counts
    cursor.execute("""
    UPDATE users SET
        daily_count = daily_count + 1,
        weekly_count = weekly_count + 1,
        total_count = total_count + 1,
        last_active_date = ?
    WHERE user_id=? AND group_id=?
    """, (today, user_id, group_id))

    conn.commit()

# ================= LEADERBOARD =================
def leaderboard_buttons(active="overall"):
    return InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton(f"🔵 Overall {'✅' if active=='overall' else ''}", callback_data="lb_overall"),
        InlineKeyboardButton(f"🟢 Today {'✅' if active=='today' else ''}", callback_data="lb_today"),
        InlineKeyboardButton(f"🟡 Week {'✅' if active=='week' else ''}", callback_data="lb_week"),
    )

async def get_leaderboard_text(group_id, column, title):

    cursor.execute(f"""
    SELECT user_id, {column} FROM users
    WHERE group_id=?
    ORDER BY {column} DESC LIMIT 10
    """, (group_id,))

    users = cursor.fetchall()

    text = f"📊 <b>{title}</b>\n\n"
    total = 0

    for i, (uid, count) in enumerate(users, 1):
        try:
            member = await bot.get_chat_member(group_id, uid)
            name = member.user.full_name
        except:
            name = "Unknown"

        text += f"{i}. 👤 {name} • {count}\n"
        total += count

    text += f"\n📨 Total messages: {total}"
    return text

@dp.message_handler(lambda message: message.text and message.text.lower().startswith('/leaderboard'))
async def leaderboard(message: types.Message):
    print("LEADERBOARD TRIGGERED")

    await message.reply("Working")

    text = await get_leaderboard_text(
        message.chat.id,
        "total_count",
        "Overall Leaderboard"
    )

    await message.reply(
        text,
        parse_mode="HTML",
        reply_markup=leaderboard_buttons("overall")
    )

@dp.callback_query_handler(lambda c: c.data.startswith("lb_"))
async def leaderboard_callback(callback: types.CallbackQuery):

    data = callback.data
    group_id = callback.message.chat.id

    if data == "lb_today":
        column = "daily_count"
        title = "Today Leaderboard"
        active = "today"

    elif data == "lb_week":
        column = "weekly_count"
        title = "Weekly Leaderboard"
        active = "week"

    else:
        column = "total_count"
        title = "Overall Leaderboard"
        active = "overall"

    text = await get_leaderboard_text(group_id, column, title)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=leaderboard_buttons(active)
    )

    await callback.answer()

# ================= COUPLE =================
@dp.message_handler(commands=['couple'])
async def couple(message: types.Message):

    group_id = message.chat.id

    cursor.execute("""
    SELECT user_id FROM users 
    WHERE group_id=? AND total_count > 0
    """, (group_id,))
    
    users = [u[0] for u in cursor.fetchall()]

    if len(users) < 2:
        return await message.reply("❌ Not enough users.")

    user1_id, user2_id = random.sample(users, 2)

    user1 = await bot.get_chat_member(group_id, user1_id)
    user2 = await bot.get_chat_member(group_id, user2_id)

    caption = (
        f"💘 <b>Couple of the Day</b>\n\n"
        f"💖 {user1.user.full_name} ❤️ {user2.user.full_name}\n\n"
        f"🔥 Stay together for today!"
    )

    with open("couple.png", "rb") as photo:
        await bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="HTML")

# ================ ID ===============
@dp.message_handler(commands=['id'])
async def get_id(message: types.Message):

    user = message.from_user
    chat = message.chat

    text = (
        f"👤 <b>Your Info</b>\n\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"📛 Name: {user.full_name}\n"
        f"🔗 Username: @{user.username if user.username else 'None'}\n\n"
        f"💬 <b>Chat Info</b>\n"
        f"🆔 Chat ID: <code>{chat.id}</code>\n"
        f"📌 Type: {chat.type}"
    )

    # If replying to someone, show their ID too
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        text += (
            f"\n\n👥 <b>Replied User</b>\n"
            f"🆔 ID: <code>{target.id}</code>\n"
            f"📛 Name: {target.full_name}\n"
            f"🔗 Username: @{target.username if target.username else 'None'}"
        )

    await message.reply(text, parse_mode="HTML")

# ==================Freeze =============
@dp.message_handler(commands=['lockdown'])
async def lockdown(message: types.Message):

    if not is_owner(message.from_user.id):
        return

    await bot.set_chat_permissions(
        message.chat.id,
        types.ChatPermissions(can_send_messages=False)
    )

    await message.reply("🔒 Chat locked")

# ================Freeze unlock============
@dp.message_handler(commands=['unlock'])
async def unlock(message: types.Message):

    if not is_owner(message.from_user.id):
        return

    await bot.set_chat_permissions(
        message.chat.id,
        types.ChatPermissions(can_send_messages=True)
    )

    await message.reply("🔓 Chat unlocked")
# ================= START =================
if __name__ == "__main__":
    print("✅ Bot running...")
    executor.start_polling(dp, skip_updates=True)
