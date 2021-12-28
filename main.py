from os import getenv
import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

##

logging.basicConfig(
    format="%(levelname)s - %(name)s - %(message)s",
    level=logging.INFO
)

##

def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Здесь есть кошка"
    )

##

handlers = {
    "start": start
}

def main():
    token = getenv("TOKEN")
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    for command, handler in handlers.items():
        dispatcher.add_handler(CommandHandler(command, handler))

    updater.start_polling()

if __name__ == "__main__":
    main()
