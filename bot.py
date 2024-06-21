import os
import logging
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv

from bot_database import *
from bot_media_ai import *

import ffmpeg
import uuid
import os
import logging
import lorem

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("meeting_minutes")

DEBUG           = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
API_ID          = os.getenv('API_ID')
API_HASH        = os.getenv('API_HASH')
BOT_TOKEN       = os.getenv('BOT_TOKEN')

telegramcli = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
buttons = [
    [Button.inline("List previous meetings", b"list"),Button.inline("Test", b"test")],
]

# Event handler for new messages
@telegramcli.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("Send me a video (MP4) or an audio (MP3) file and I will process it.",buttons=buttons)

# Handle button clicks
@telegramcli.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    # Check if the user is allowed to use the bot
    if user_id not in get_allowed_users():
        await event.answer("You are not allowed to use this bot.")
        return

    data = event.data.decode('utf-8')
    if data == "list":
        buttons = get_user_transcriptions(user_id)
        await telegramcli.send_message(user_id,"Here are your meetings:\n",link_preview=False,buttons=buttons)      
    else:
        await event.respond("Invalid option selected.")

# Event handler for receiving video files
@telegramcli.on(events.NewMessage(func=lambda e: e.video))
async def handle_video(event):
    await process_media(event, event.video, 'video', telegramcli)

# Event handler for receiving audio files
@telegramcli.on(events.NewMessage(func=lambda e: e.audio))
async def handle_audio(event):
    await process_media(event, event.audio, 'audio', telegramcli)

@telegramcli.on(events.CallbackQuery(pattern=r'view_(\d+)'))
async def view_item(event):
    meeting_id = int(event.pattern_match.group(1))
    await event.respond(view_meeting(event.sender_id, meeting_id),buttons=buttons)

def main() -> None:
    init_db()
    print(DEBUG)
    telegramcli.run_until_disconnected()

if __name__ == '__main__':
    main()