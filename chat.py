from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import datetime
import os
import time
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "data.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    group_id INTEGER,
    group_name TEXT,
    name TEXT,
    daily_count INTEGER,
    total_count INTEGER,
    last_date TEXT,
    last_active TEXT
)
""")
conn.commit()

# ================= LIFETIME RANK =================
def get_lifetime_rank(total):
    if total >= 5000000: return "👑 Legend"
    elif total >= 1500000: return "🧠 Master"
    elif total >= 1000000: return "⚡ Pro"
    elif total >= 500000: return "🔥 Epic"

    elif total >= 170000: return "💎 Diamond V"
    elif total >= 130000: return "💎 Diamond IV"
    elif total >= 100000: return "💎 Diamond III"
    elif total >= 80000: return "💎 Diamond II"
    elif total >= 60000: return "💎 Diamond I"

    elif total >= 50000: return "💠 Platinum III"
    elif total >= 35000: return "💠 Platinum II"
    elif total >= 25000: return "💠 Platinum I"

    elif total >= 20000: return "🥇 Gold III"
    elif total >= 15000: return "🥇 Gold II"
    elif total >= 10000: return "🥇 Gold I"

    elif total >= 9000: return "🥈 Silver III"
    elif total >= 6000: return "🥈 Silver II"
    elif total >= 3000: return "🥈 Silver I"

    elif total >= 2000: return "🥉 Bronze III"
    elif total >= 1000: return "🥉 Bronze II"
    else: return "🥉 Bronze I"

# ================= DAILY RANK =================
def get_daily_rank(count):
    if count >= 500:
        return "🔥 Daily Legend"
    elif count >= 250:
        return "💎 Daily Pro"
    elif count >= 100:
        return "🥇 Daily Active"
    elif count >= 30:
        return "🥈 Daily Starter"
    else:
        return "🥉 Beginner"

# ================= DECAY =================
def apply_decay(total, days):
    if days >= 5:
        total -= 2000
    elif days >= 3:
        total -= 1000
    return max(total, 0)

# ================= START UI =================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        InlineKeyboardButton("➕ Add me in group", url="https://t.me/erzachris_bot?startgroup=true")
    )

    keyboard.add(
        InlineKeyboardButton("📊 Your Stats", callback_data="stats"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="top")
    )

    keyboard.add(
        InlineKeyboardButton("📢 Updates", url="https://t.me/erzaupdates")
    )

    text = (
        "🤖 Welcome!\n\n"
        "🔥 Compete daily and climb lifetime ranks\n"
        "🏆 Become the top chatter in your group\n\n"
        "💡 Use commands below to explore"
    )

    await message.answer(text, reply_markup=keyboard)

# ================= CALLBACK =================
@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_btn(callback: types.CallbackQuery):
    await callback.message.answer("Use /stats in group 📊")

@dp.callback_query_handler(lambda c: c.data == "top")
async def top_btn(callback: types.CallbackQuery):
    await callback.message.answer("Use /top in group 🏆")

# ================= PING =================
@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    await message.reply("🏓 Bot is alive!")

# ================= ADMIN CHECK =================
async def is_admin(message: types.Message):
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.is_chat_admin()

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

@dp.message_handler(commands=['promote'])
async def promote_user(message: types.Message):
    if not await is_admin(message): return await message.reply("❌ Not admin")
    if not message.reply_to_message: return await message.reply("Reply to user")

    await bot.promote_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        can_delete_messages=True,
        can_restrict_members=True
    )

    await message.reply("👑 Promoted")

@dp.message_handler(commands=['demote'])
async def demote_user(message: types.Message):
    if not await is_admin(message): return await message.reply("❌ Not admin")
    if not message.reply_to_message: return await message.reply("Reply to user")

    await bot.promote_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        can_delete_messages=False,
        can_restrict_members=False,
        can_promote_members=False
    )

    await message.reply("⬇️ Demoted")

# ================= STATS =================
@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):

    cursor.execute("""
    SELECT daily_count, total_count, last_active 
    FROM users WHERE user_id=? AND group_id=?
    """, (message.from_user.id, message.chat.id))

    data = cursor.fetchone()

    if data:
        daily, total, last_active = data

        if last_active:
            last_date = datetime.datetime.strptime(last_active, "%Y-%m-%d").date()
            diff = (datetime.date.today() - last_date).days
            total = apply_decay(total, diff)
    else:
        daily, total = 0, 0

    await message.reply(
        f"📊 {message.from_user.full_name}\n\n"
        f"🏆 Daily Rank: {get_daily_rank(daily)}\n"
        f"💎 Lifetime Rank: {get_lifetime_rank(total)}\n\n"
        f"💬 Today: {daily}\n"
        f"📈 Total: {total}"
    )

# ================= GROUP TOP =================
@dp.message_handler(commands=['top'])
async def top_group(message: types.Message):

    cursor.execute("""
    SELECT name, daily_count FROM users 
    WHERE group_id=? 
    ORDER BY daily_count DESC LIMIT 10
    """, (message.chat.id,))

    data = cursor.fetchall()

    text = "🏆 Top Users Today:\n\n"
    for i, user in enumerate(data, 1):
        text += f"{i}. {user[0]} — {user[1]} msgs\n"

    await message.reply(text)

# ================= GLOBAL =================
@dp.message_handler(commands=['global'])
async def global_users(message: types.Message):

    cursor.execute("""
    SELECT name, SUM(total_count) FROM users 
    GROUP BY user_id 
    ORDER BY SUM(total_count) DESC LIMIT 10
    """)

    data = cursor.fetchall()

    text = "🌍 Top Users (Global):\n\n"
    for i, user in enumerate(data, 1):
        text += f"{i}. {user[0]} — {user[1]}\n"

    await message.reply(text)

# ================= GROUPS =================
@dp.message_handler(commands=['groups'])
async def top_groups(message: types.Message):

    cursor.execute("""
    SELECT group_name, SUM(total_count) FROM users 
    GROUP BY group_id 
    ORDER BY SUM(total_count) DESC LIMIT 10
    """)

    data = cursor.fetchall()

    text = "🏆 Top Groups:\n\n"
    for i, g in enumerate(data, 1):
        text += f"{i}. {g[0]} — {g[1]} msgs\n"

    await message.reply(text)

# ================= MY GROUPS =================
@dp.message_handler(commands=['mygroups'])
async def my_groups(message: types.Message):

    cursor.execute("""
    SELECT group_name, total_count FROM users 
    WHERE user_id=? 
    ORDER BY total_count DESC LIMIT 5
    """, (message.from_user.id,))

    data = cursor.fetchall()

    text = "📊 Your Top Groups:\n\n"
    for i, g in enumerate(data, 1):
        text += f"{i}. {g[0]} — {g[1]} msgs\n"

    await message.reply(text)

# ================= MESSAGE HANDLER =================
@dp.message_handler(lambda message: message.text and not message.text.startswith('/'))
async def count_msg(message: types.Message):

    if message.chat.type == "private":
        return

    user_id = message.from_user.id
    group_id = message.chat.id
    group_name = message.chat.title
    name = message.from_user.full_name
    today = str(datetime.date.today())

    cursor.execute("""
    SELECT daily_count, total_count, last_date, last_active 
    FROM users WHERE user_id=? AND group_id=?
    """, (user_id, group_id))

    db = cursor.fetchone()

    if db:
        daily, total, last_date, last_active = db

        if last_date != today:
            daily = 0

        if last_active:
            last_date_obj = datetime.datetime.strptime(last_active, "%Y-%m-%d").date()
            diff = (datetime.date.today() - last_date_obj).days
            total = apply_decay(total, diff)

        daily += 1
        total += 1

        cursor.execute("""
        UPDATE users SET daily_count=?, total_count=?, last_date=?, last_active=?, name=?, group_name=?
        WHERE user_id=? AND group_id=?
        """, (daily, total, today, today, name, group_name, user_id, group_id))

    else:
        cursor.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, group_id, group_name, name, 1, 1, today, today))

    conn.commit()

# =================Welcome New Chat Members=================
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def welcome_new_members(message: types.Message):

    for user in message.new_chat_members:

        if user.id == (await bot.me).id:
            continue

        name = user.full_name
        username = f"@{user.username}" if user.username else "No username"

        text = (
            f"🎉 Welcome to <b>{message.chat.title}</b>\n\n"
            f"👋 <b>Welcome {name}!</b>\n\n"
            f"👤 Username: {username}\n"
            f"💬 Start chatting to earn ranks\n"
            f"🏆 Compete in leaderboard\n\n"
            f"📊 Use /stats to track your progress\n"
            f"🚀 Stay active & climb the ranks!"
        )

        try:
            photos = await bot.get_user_profile_photos(user.id, limit=1)

            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                await bot.send_photo(
                    message.chat.id,
                    file_id,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await message.reply(text, parse_mode="HTML")

        except Exception as e:
            print("WELCOME ERROR:", e)
            await message.reply(text, parse_mode="HTML")

# ================= LEFT CHAT MEMBERS =================

@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def left_member(message: types.Message):

    user = message.left_chat_member

    # Skip bot itself
    if user.id == (await bot.me).id:
        return

    user_id = user.id
    group_id = message.chat.id
    name = user.full_name

    # Get user stats
    cursor.execute("""
    SELECT total_count FROM users 
    WHERE user_id=? AND group_id=?
    """, (user_id, group_id))

    data = cursor.fetchone()

    if data:
        total = data[0]
        rank = get_lifetime_rank(total)
    else:
        total = 0
        rank = "🥉 Bronze I"

    text = (
        f"🚪 <b>{name} has left the arena!</b>\n\n"
        f"💎 Rank: {rank}\n"
        f"📈 Total Messages: {total}\n\n"
        f"⚔️ One less competitor...\n"
        f"🏆 The battle continues!"
    )

    await message.reply(text, parse_mode="HTML")
# ================= START =================
if __name__ == "__main__":
    print("✅ Bot running...")
    executor.start_polling(dp, skip_updates=True)