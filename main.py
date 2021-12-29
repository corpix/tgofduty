from os import getenv
import datetime
import logging

from telegram import Update
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP as CalendarStep

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, create_engine as open_db
from sqlalchemy.orm import sessionmaker as open_db_session
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

##

Base = declarative_base()

class Project(Base):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    telegram_id = Column(Integer)

class Sentry(Base):
    __tablename__ = "sentry"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)

class Duty(Base):
    __tablename__ = "duty"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("project.id"))
    sentry_id = Column(Integer, ForeignKey("sentry.id"))
    starts_at = Column(DateTime)
    ends_at = Column(DateTime)

##

logging.basicConfig(
    format="%(levelname)s - %(name)s - %(message)s",
    level=logging.INFO
)

##

def main():
    token = getenv("TOKEN")
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    ##

    db_url = getenv("DATABASE") or "sqlite:///state.db"
    db = open_db(db_url)
    db_conn = db.connect()
    db_session = open_db_session(bind=db)

    Base.metadata.create_all(db)

    ##

    def make_calendar():
        today = datetime.date.today()
        return DetailedTelegramCalendar(
            current_date=today,
            min_date=today,
            locale="ru"
        )

    ##

    def help(update: Update, context: CallbackContext):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\n".join([
                "/help - показать список команд",
                "/assign - назначить человека на дежурство",
            ])
        )

    def start(update: Update, context: CallbackContext):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Бот для планирования дежурств."
        )
        help(update, context)

    def assign(update: Update, context: CallbackContext):
        calendar, step = make_calendar().build()
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Укажи дату начала дежурства",
            reply_markup=calendar
        )

    def callback(update: Update, context: CallbackContext):
        query = update.callback_query

        result, key, step = make_calendar().process(query.data)
        if not result and key:
            context.bot.edit_message_text(
                CalendarStep[step],
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
                reply_markup=key
            )
        elif result:
            context.bot.edit_message_text(
                f"Дата начала дежурства {result}",
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
            )
            calendar, step = make_calendar().build()
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Укажи дату конца дежурства",
                reply_markup=calendar
            )

    ##

    handlers = [
        (CommandHandler, "start", start,),
        (CommandHandler, "help", help,),
        (CommandHandler, "assign", assign,),
        (CallbackQueryHandler, callback)
        #(MessageHandler, Filters.text & (~Filters.command), echo,),
    ]

    for handler in handlers:
        dispatcher.add_handler(handler[0](*handler[1:]))

    updater.start_polling()

if __name__ == "__main__":
    main()
