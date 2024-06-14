#!/bin/bash

# Directory containing the MP4 files
input_dir="./assets"

# Check if the input directory exists
if [ ! -d "$input_dir" ]; then
  echo "Directory $input_dir does not exist."
  exit 1
fi

# Process each MP4 file in the directory
for input_file in "$input_dir"/*.mp4; do
  [ -e "$input_file" ] || continue  # Skip if no MP4 files found

  base_name=$(basename "$input_file" .mp4)
  chunk_prefix="${base_name}_chunk_"
  chunk_duration=180  # 3 minutes in seconds

  # Extract audio from the video file and save it as a temporary wav file
  ffmpeg -i "$input_file" -ar 16000 -ac 1 -q:a 0 -map a "$input_dir/${base_name}.wav"

  # Split the audio file into chunks
  ffmpeg -i "$input_dir/${base_name}.wav" -f segment -segment_time "$chunk_duration" -c copy "$input_dir/$chunk_prefix%03d.wav"

  # Remove the temporary wav file
  rm "$input_dir/${base_name}.wav"

  # Initialize the output file
  output_file="$input_dir/${base_name}.txt"
  > "$output_file"

  # Process each chunk with the python script
  for chunk in "$input_dir/$chunk_prefix"*.wav; do
    python wrapper.py --filename "$chunk" --output "$output_file"
  done

  echo "Processing complete for $input_file. Output saved to $output_file."
done

echo "All videos processed."