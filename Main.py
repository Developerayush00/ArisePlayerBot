# main.py
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputStream, InputAudioStream
from yt_dlp import YoutubeDL
import os
from config import API_ID, API_HASH, BOT_TOKEN

# Bot Initialization
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

queue = {}
afks = {}

# YTDL Settings
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'noplaylist': True
}

# Helper: download song from YouTube
def download_youtube_audio(url):
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename

# /start command
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text("Hello! I'm your VC Music Bot. Use /play [song] to start.")

# /play command
@app.on_message(filters.command("play") & filters.group)
async def play(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("Please provide a song name or YouTube link.")

    query = " ".join(message.command[1:])
    await message.reply("Downloading...")

    audio_file = download_youtube_audio(query)

    chat_id = message.chat.id
    if chat_id not in queue:
        queue[chat_id] = []
    queue[chat_id].append(audio_file)

    await pytgcalls.join_group_call(
        chat_id,
        InputStream(
            InputAudioStream(audio_file),
        ),
        stream_type="local"
    )
    await message.reply(f"Now playing: {query}")

# /pause and /resume
@app.on_message(filters.command("pause") & filters.group)
async def pause(_, message: Message):
    await pytgcalls.pause_stream(message.chat.id)
    await message.reply("Paused.")

@app.on_message(filters.command("resume") & filters.group)
async def resume(_, message: Message):
    await pytgcalls.resume_stream(message.chat.id)
    await message.reply("Resumed.")

# /stop
@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message: Message):
    await pytgcalls.leave_group_call(message.chat.id)
    await message.reply("Stopped and left VC.")

# /tagall
@app.on_message(filters.command("tagall") & filters.group)
async def tagall(_, message: Message):
    members = []
    async for m in app.get_chat_members(message.chat.id):
        if not m.user.is_bot:
            members.append(m.user.mention)
    text = " ".join(members)
    if message.reply_to_message:
        await message.reply_to_message.reply(text)
    else:
        await message.reply(text)

# /afk command
@app.on_message(filters.command("afk") & filters.group)
async def afk(_, message: Message):
    user = message.from_user
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "AFK"
    afks[user.id] = reason
    await message.reply(f"{user.first_name} is now AFK: {reason}")

@app.on_message(filters.text & filters.group)
async def check_afk(_, message: Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user.id in afks:
            await message.reply(f"{user.first_name} is AFK: {afks[user.id]}")
    if message.from_user.id in afks:
        afks.pop(message.from_user.id)
        await message.reply(f"Welcome back, {message.from_user.first_name}!")

# Run
app.start()
pytgcalls.start()
print("Bot is online.")
asyncio.get_event_loop().run_forever()
