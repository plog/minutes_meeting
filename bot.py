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
    try:
        user_id = event.sender_id
        # Check if the user is allowed to use the bot
        if user_id not in get_allowed_users():
            await event.respond("You are not allowed to use this bot.")
            return
        else:
            await event.respond('Please wait, it can take a moment...')

        add_user(user_id)
        video = event.video
        video_path, error = await download_file(video, 'video', telegramcli)
        if error:
            await event.respond(error)
            return

        input_file    = os.path.basename(video_path)
        base_name, _  = os.path.splitext(input_file)
        mp3 = f'{MEDIA_DIR}/{base_name}.mp3'
        if video_path:
            await event.respond('Video received. Processing...')
            ffmpeg.input(video_path).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.3").run(overwrite_output=True)
            # Summarize meeting and save transcription
            print(DEBUG)
            if DEBUG:
                print("----------------- DEBUG -------------------------")
                key_points = "\n".join([lorem.paragraph() for _ in range(3)])
                full_transcription = "\n".join([lorem.paragraph() for _ in range(20)])
            else:
                key_points, full_transcription = summarize_meeting(mp3, user_id)

            save_transcription(user_id, full_transcription, key_points)
            await event.respond(key_points)

            os.remove(video_path)
            # os.remove(mp3)
        else:
            await event.respond('Failed to download the video after multiple attempts.')

    except Exception as e:
        logger.error("Error handling video: %s", e, exc_info=True)
        await event.respond(f'An error occurred while processing the video: {e}')

# Event handler for receiving audio files
@telegramcli.on(events.NewMessage(func=lambda e: e.audio))
async def handle_audio(event):
    try:
        user_id = event.sender_id
        # Check if the user is allowed to use the bot
        if user_id not in get_allowed_users():
            await event.respond("You are not allowed to use this bot.")
            return
        else:
            await event.respond('Please wait, it can take a moment...')

        add_user(user_id)
        audio = event.audio

        audio_path, error = await download_file(audio, 'audio', telegramcli)
        if error:
            await event.respond(error)
            return

        if audio_path:
            await event.respond(f'Audio received. Processing...')
            mp3 = f"{MEDIA_DIR}/{uuid.uuid4()}.mp3"
            ffmpeg.input(audio_path).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.3").run(overwrite_output=True)
            if DEBUG:
                key_points = "\n".join([lorem.paragraph() for _ in range(5)])
                full_transcription = "\n".join([lorem.paragraph() for _ in range(20)])
            else:
                # Summarize meeting and save transcription
                key_points, full_transcription = summarize_meeting(audio_path, user_id)
                
            save_transcription(user_id, full_transcription, key_points)
            await event.respond(key_points)
            await event.respond("Audio Done!")

            os.remove(audio_path)
            # os.remove(mp3)
        else:
            await event.respond('Failed to download the audio after multiple attempts.')

    except Exception as e:
        logger.error("Error handling audio: %s", e, exc_info=True)
        await event.respond(f'An error occurred while processing the audio: {e}')

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