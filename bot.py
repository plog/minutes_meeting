from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os

# Your bot token
BOT_TOKEN = '6710442586:AAFBE-bV0GQ2hwVp3GvtENPu1Svpiud3w2E'
# List of allowed user IDs
ALLOWED_USERS = [386108080, 987654321]  # Replace with actual user IDs

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        await update.message.reply_text('Send me a video and I will process it.')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

async def handle_video(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text('You are not authorized to use this bot.')
        return

    video = update.message.video
    video_file = await video.get_file()
    video_path = 'received_video.mp4'
    await video_file.download_to_drive(video_path)
    await update.message.reply_text('Video received. Processing...')

    # Process the video (example: renaming the file for simplicity)
    processed_video_path = 'processed_video.mp4'
    os.rename(video_path, processed_video_path)

    # Send the processed video back
    with open(processed_video_path, 'rb') as video_file:
        await context.bot.send_video(chat_id=update.message.chat_id, video=video_file)
    os.remove(processed_video_path)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    application.run_polling()

if __name__ == '__main__':
    main()