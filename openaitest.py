import os
import argparse
import ffmpeg
from pydub import AudioSegment
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def key_points_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system","content": """
             Based on the following indonesian meeting minutes, I want to know is anything could be done to meet them again or close a deal.
             So, from these meeting minutes give me:
             1) The subjects that were disqcussed in the meeting(very briefly)
             2) The list of questions that have been asked during the meeting
             3) The decisions that were taken in this meeting
             4) Next actions to undertake related to this meeting subjects, questions,... (next meeting, something to do, information to send, etc...)
             Explain it in English only.
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    args = parser.parse_args()
    
    input_file = os.path.basename(args.input)
    base_name, extension = os.path.splitext(input_file)
    directory_path = os.path.dirname(args.input)

    mp4                     = os.path.join(directory_path, f'{base_name}.mp4')
    mp3                     = os.path.join(directory_path, f'{base_name}.mp3')
    key_points_file         = os.path.join(directory_path, f'{base_name}_key_points.txt')
    full_transcription_file = os.path.join(directory_path, f'{base_name}_full_transcription.txt')
    
    # Convert video to audio and apply filters
    ffmpeg.input(mp4).output(mp3, vn=None, af="silenceremove=start_periods=1:start_silence=0.5:start_threshold=-30dB,atempo=1.2").run(overwrite_output=True)
    
    # Split audio into chunks
    chunk_length_ms = 20 * 60 * 1000  # 20 minutes
    audio_chunks = split_audio(mp3, chunk_length_ms)
    
    transcriptions = []
    
    for i, chunk in enumerate(audio_chunks):
        chunk_file = os.path.join(directory_path, f"chunk_{i}.mp3")
        chunk.export(chunk_file, format="mp3")
        with open(chunk_file, 'rb') as audio_file:
            print(f"Transcribing chunk {i+1}/{len(audio_chunks)}...")
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcriptions.append(transcription.text)
        os.remove(chunk_file)
    
    # Merge transcriptions and process key points
    full_transcription = " ".join(transcriptions)
    print("Extracting Key points....")
    with open(full_transcription_file, 'w') as summary_file:
        summary_file.write(full_transcription)
        print(full_transcription)
    key_points = key_points_extraction(full_transcription)
    
    with open(key_points_file, 'w') as summary_file:
        summary_file.write(key_points)
        print(key_points)

    print("Audio processing and transcription completed.")