from openai import OpenAI
import os
import argparse
import ffmpeg
from dotenv import load_dotenv
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
             1) The subjects that were disqcussed (very briefly)
             2) The list of questions that have been asked
             3) The decisions that were made 
             4) Next actions to undertake (next meeting, something to do, information to send, etc...)

             Explain it in English only.
             """},
            {"role": "user","content": transcription}
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str,required=True)
    args = parser.parse_args()


    mp4 = args.input
    mp3 = args.input.replace('mp4','mp3')
    ffmpeg.input(mp4).output(mp3, vn=None).run(overwrite_output=True)    
    with open(mp3, 'rb') as audio_file:
        print("Transcribing video....")
        transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        print("Extracting Key points....", transcription)
        key_points = key_points_extraction(transcription.text)
        with open(args.output, 'w') as summary_file:
            summary_file.write(key_points)         
            print(key_points)

