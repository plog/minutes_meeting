# Meeting Minutes Bot

This repository contains a Telegram bot designed to process video (MP4) and audio (MP3) files to create meeting summaries and transcriptions. The bot leverages the [Telethon](https://docs.telethon.dev/) library for Telegram API interactions, [ffmpeg](https://ffmpeg.org/) for media processing, and OpenAI’s Whisper and GPT-4o for generating transcriptions and summaries.
## Features

- Accepts video (MP4) and audio (MP3) files.
- Processes media files to remove silence and speed up the audio.
- Generates and saves meeting summaries and full transcriptions.
- Provides a list of previous meetings for each user.
- Restricts usage to a list of allowed users.

## Setup

### Prerequisites

- Python 3.7+
- Telegram API credentials (`API_ID`, `API_HASH`, `BOT_TOKEN`)
- Required Python packages (listed in `requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/meeting_minutes_bot.git
   cd meeting_minutes_bot
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Telegram API credentials:
   ```
    BOT_TOKEN='67....'
    ALLOWED_USERS='386000000 987000000'
    MEDIA_DIR='media'
    OPENAI_API_KEY=sk-....
    API_HASH=b7....
    API_ID=1....
    DEBUG=False
   ```

4. Ensure `ffmpeg` is installed on your system.

### Usage

Run the bot:

use ```pymon``` in dev to reload when you change a file
```bash
pymon bot.py
```
or
```bash
python bot.py
```
## Telegram

### How to Find your Telegram User ID

Type “userinfobot” in your contacts search bar and “/start.”

### Create a Bot 

Go to https://telegram.me/BotFather

### APP ID etc..

Go here: https://my.telegram.org/apps

## Code Explanation

### Imports and Configuration

- **Environment Variables**: Loaded using `dotenv` to manage sensitive information.
- **Logging**: Configured to log bot activities for debugging and monitoring.
- **Telethon**: Used for interacting with the Telegram API.

### Bot Initialization

- **TelegramClient**: Initialized with the provided API credentials and bot token.
- **Buttons**: Defined for user interaction within the bot.

### Event Handlers

- **/start Command**: Sends a welcome message and buttons to users.
- **Button Clicks**: Handles button interactions, checking user permissions and responding accordingly.
- **New Messages**: Processes incoming video and audio files, checking user permissions, downloading the files, processing them with `ffmpeg`, and generating transcriptions and summaries.

### Helper Functions

- **get_allowed_users**: Retrieves the list of users allowed to use the bot.
- **download_file**: Downloads media files sent by users.
- **summarize_meeting**: Summarizes the content of the media files.
- **save_transcription**: Saves the transcriptions and key points of the meetings.
- **view_meeting**: Displays a specific meeting transcription.

### Main Function

- **Database Initialization**: Sets up the database.
- **Bot Run**: Starts the bot and keeps it running until manually stopped.

### Error Handling

- Errors during media processing are logged and communicated to the user to ensure smooth bot operation and debugging.
