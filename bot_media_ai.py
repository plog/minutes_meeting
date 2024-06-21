from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

from bot_database import *

import os
import ffmpeg
import time
import uuid
import logging
import lorem

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("meeting_minutes")

openaicli = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
MEDIA_DIR       = os.getenv('MEDIA_DIR', './media')
DEBUG           = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

def get_allowed_users():
    load_dotenv(override=True)
    return [int(user_id) for user_id in os.getenv('ALLOWED_USERS').split(' ')]

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

def delete_old_media(directory, age_in_minutes=1):
    cutoff_time = time.time() - (age_in_minutes * 60)
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            # If the file is older than the cutoff time, delete it
            if file_mtime < cutoff_time:
                os.remove(filepath)
                print(f"Deleted {filepath}")

def key_points_extraction(transcription):
    response = openaicli.chat.completions.create(
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

def summarize_meeting(mp3,userid):
    chunk_length_ms = 10 * 60 * 1000  # 20 minutes
    audio_chunks = split_audio(mp3, chunk_length_ms)
    transcriptions = []

    for i, chunk in enumerate(audio_chunks):
        chunk_file = os.path.join(MEDIA_DIR, f"chunk_{i}.mp3")
        chunk.export(chunk_file, format="mp3")
        with open(chunk_file, 'rb') as audio_file:
            print(f"Transcribing chunk {i+1}/{len(audio_chunks)}...")
            transcription = openaicli.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcriptions.append(transcription.text)
        os.remove(chunk_file)
        
    # Merge transcriptions and process key points
    full_transcription = " ".join(transcriptions)
    key_points = key_points_extraction(full_transcription)

    save_transcription(userid, full_transcription, key_points)
    print("Audio processing and transcription completed.")
    return key_points, full_transcription

def get_file_info(media):
    file_name = f"{MEDIA_DIR}/{uuid.uuid4()}"
    file_extension = None
    for attribute in media.attributes:
        if isinstance(attribute, DocumentAttributeAudio):
            mime_type = media.mime_type
            if mime_type.startswith('audio/'):
                file_extension = f".{mime_type.split('/')[1].lower()}"
        elif isinstance(attribute, DocumentAttributeVideo):
            mime_type = media.mime_type
            if mime_type.startswith('video/'):
                file_extension = f".{mime_type.split('/')[1].lower()}"

    if file_extension:
        return f"{file_name}{file_extension}"
    else:
        return None

async def download_file(media, media_type, telegramcli):
    delete_old_media(MEDIA_DIR)
    logger.info(f"Received {media_type} file size: {media.size} bytes")
    if media.size > 2 * 1024 * 1024 * 1024:
        return None, f"The {media_type} file is too big. Please send a smaller file."

    # Get file name and extension
    file_name = get_file_info(media)
    if not file_name:
        return None, "Invalid file format."
    await telegramcli.download_media(media, file_name)
    logger.info(f"{media_type.capitalize()} file saved to: {file_name}")
    return file_name, None

async def process_media(event, media, media_type, telegramcli):
    user_id = event.sender_id
    if user_id not in get_allowed_users():
        await event.respond("You are not allowed to use this bot.")
        return
    
    await event.respond('Please wait, it can take a moment...')
    add_user(user_id)
    
    media_path, error = await download_file(media, media_type, telegramcli)
    if error:
        await event.respond(error)
        return

    input_file = os.path.basename(media_path)
    mp3 = f"{MEDIA_DIR}/{uuid.uuid4()}.mp3"
    
    if media_path:
        await event.respond(f'{media_type.capitalize()} received. Processing...')
        ffmpeg.input(media_path).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.3").run(overwrite_output=True)
        if DEBUG:
            key_points = "\n".join([lorem.paragraph() for _ in range(5)])
            full_transcription = "\n".join([lorem.paragraph() for _ in range(20)])
        else:
            key_points, full_transcription = summarize_meeting(mp3, user_id)
        save_transcription(user_id, full_transcription, key_points)
        await event.respond(key_points)
        os.remove(media_path)
        os.remove(mp3)
    else:
        await event.respond(f'Failed to download the {media_type} after multiple attempts.')