import argparse
from src.inference import Wav2Vec2Inference
import warnings
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("--model_name", type=str, default="arifagustyawan/wav2vec2-large-xlsr-common_voice_13_0-id")
    parser.add_argument("--model_name", type=str, default="indonesian-nlp/wav2vec2-large-xlsr-indonesian")
    parser.add_argument("--filename", type=str, default="assets/halo.wav")
    parser.add_argument("--output", type=str, default="assets/halo.txt")
    args = parser.parse_args()

    asr = Wav2Vec2Inference(args.model_name)
    transcription, confidence = asr.file_to_text(args.filename, args.output)
    print(f'Writing to {args.output}')
    with open(args.output, 'a') as file:
        file.write(transcription)         
    # print("\033[94mTranscription:\033[0m", transcription)
    print("\033[94mConfidence:\033[0m", confidence)
