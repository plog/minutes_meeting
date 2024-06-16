from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext
from pydub import AudioSegment
from dotenv import load_dotenv
from openai import OpenAI
from functools import wraps
import sqlite3
import ffmpeg
import uuid
import os
import logging
import time

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USERS = [int(user_id) for user_id in os.getenv('ALLOWED_USERS').split(' ')]
MEDIA_DIR=os.getenv('MEDIA_DIR')

def init_db():
    conn = sqlite3.connect('meeting_summaries.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            transcription TEXT,
            key_points TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('meeting_summaries.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def save_transcription(user_id, transcription, key_points):
    conn = sqlite3.connect('meeting_summaries.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transcriptions (user_id, transcription, key_points) VALUES (?, ?, ?)
    ''', (user_id, transcription, key_points))
    conn.commit()
    conn.close()

def get_user_transcriptions(user_id):
    conn = sqlite3.connect('meeting_summaries.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT transcription, key_points, created_at FROM transcriptions WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def key_points_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system","content": """
             Based on the following indonesian meeting transcription, I want to everything that can be done to meet them again or close a deal.
             From this meeting transcription give me:
             1) The subjects that were discussed in the meeting(very briefly)
             2) The list of questions that have been asked during the meeting
             3) The decisions that were taken in this meeting
             4) Next actions to undertake related to this meeting subjects, questions,... (next meeting, something to do, information to send, etc...)
             Explain it in English only and don't add any comment, just answer my request.
             """},
            {"role": "user","content": transcription}
        ]
    )
    return response.choices[0].message.content

def split_audio(input_file, chunk_length_ms):
    audio = AudioSegment.from_file(input_file)
    chunks = []
    for i in range(0, len(audio), chunk_length_ms):
        chunks.append(audio[i:i + chunk_length_ms])
    return chunks

def merge_audio(chunks, output_file):
    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += chunk
    combined.export(output_file, format="mp3")

def summarize_meeting(mp3,userid):
    chunk_length_ms = 20 * 60 * 1000  # 20 minutes
    audio_chunks = split_audio(mp3, chunk_length_ms)
    transcriptions = []
    
    for i, chunk in enumerate(audio_chunks):
        chunk_file = os.path.join(MEDIA_DIR, f"chunk_{i}.mp3")
        chunk.export(chunk_file, format="mp3")
        with open(chunk_file, 'rb') as audio_file:
            print(f"Transcribing chunk {i+1}/{len(audio_chunks)}...")
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcriptions.append(transcription.text)
        os.remove(chunk_file)
    
    # Merge transcriptions and process key points
    full_transcription = " ".join(transcriptions)
    key_points = key_points_extraction(full_transcription)
    save_transcription(userid, full_transcription, key_points)
    print("Audio processing and transcription completed.")
    return key_points, full_transcription

def get_allowed_users():
    global ALLOWED_USERS
    load_dotenv(override=True)
    ALLOWED_USERS = [int(user_id) for user_id in os.getenv('ALLOWED_USERS').split(' ')]
    print(ALLOWED_USERS)

def pre_process(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        get_allowed_users()
        return await func(update, context, *args, **kwargs)
    return wrapper

def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("List my previous meetings", callback_data='meetings'),
            InlineKeyboardButton("Help", callback_data='help'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

@pre_process
async def start(update: Update, context: CallbackContext) -> None:
    print(ALLOWED_USERS)
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        await update.message.reply_text('Send me a video (MP4) or an audio (MP3) file and I will process it.')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

async def download_video_with_retry(video, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            video_file = await video.get_file()
            video_path = f"{MEDIA_DIR}/{uuid.uuid4()}.mp4"
            await video_file.download_to_drive(video_path)
            return video_path
        except Exception as e:
            logger.error("Error downloading video (attempt %d/%d): %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise
    return None

@pre_process
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio_file = update.message.audio or update.message.voice
    user_id = update.message.from_user.id
    if audio_file:
        # Download the audio file
        audio_file_id = audio_file.file_id
        audio_file = await context.bot.get_file(audio_file_id)
        file_path = f"{MEDIA_DIR}/{uuid.uuid4()}.ogg"
        await audio_file.download_to_drive(file_path)
        mp3 = file_path.replace('.ogg', '.mp3')
        ffmpeg.input(file_path).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.2").run(overwrite_output=True)
        key_points, full_transcription = summarize_meeting(mp3,user_id)
        await update.message.reply_text(key_points)
        # Clean up the files
        os.remove(file_path)
        os.remove(mp3)

@pre_process
async def handle_video(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Please wait... The media will be processed asap, it can take a while...')
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text('You are not authorized to use this bot.')
        return

    try:
        video = update.message.video
        video_path = await download_video_with_retry(video)
        input_file = os.path.basename(video_path)
        base_name, extension = os.path.splitext(input_file)
        mp3 = f'{MEDIA_DIR}/{os.path.basename(base_name)}.mp3'
        if video_path:
            await update.message.reply_text('Video received. Processing...')
            ffmpeg.input(video_path).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.2").run(overwrite_output=True)
            key_points, full_transcription = summarize_meeting(mp3,user_id)
            await update.message.reply_text(key_points)
            os.remove(video_path)
            os.remove(mp3)
        else:
            await update.message.reply_text('Failed to download the video after multiple attempts.')

    except Exception as e:
        logger.error("Error handling video: %s", e)
        await update.message.reply_text(f'An error occurred while processing the video: {e}')

@pre_process
async def handle_text_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text('You are not authorized to use this bot.')
        return

    # Process the text message
    logger.info("Received a text message from user %d: %s", user_id, text)
    await update.message.reply_text(
        'Please send me a new Video (MP4), Audio (MP3) or choose an option below:', 
        reply_markup=get_main_menu()
    )

def main() -> None:
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.TEXT, handle_text_message))
    application.run_polling()

if __name__ == '__main__':
    main()