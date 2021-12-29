from os import getenv
import datetime
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, PicklePersistence
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

class DuttyAssignee(Base):
    __tablename__ = "duty_assignee"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)

class Duty(Base):
    __tablename__ = "duty"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("project.id"))
    assignee_id = Column(Integer, ForeignKey("duty_assignee.id"))
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
    state = getenv("STATE") or "state.pickle"
    persistence = PicklePersistence(filename=state)
    updater = Updater(token=token, persistence=persistence)
    dispatcher = updater.dispatcher

    ##

    db_url = getenv("DATABASE") or "sqlite:///duty.db"
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

    KEY_ASSIGN = 1

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
        context.user_data[KEY_ASSIGN] = {}
        calendar, step = make_calendar().build()
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Укажи дату начала дежурства",
            reply_markup=calendar
        )

    def done(update: Update, context: CallbackContext):
        if KEY_ASSIGN in context.user_data:
            duty = context.user_data[KEY_ASSIGN]
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=repr(duty)
            )

    def message(update: Update, context: CallbackContext):
        if KEY_ASSIGN in context.user_data:
            duty = context.user_data[KEY_ASSIGN]
            if "assignee" not in duty:
                duty["assignee"] = []
            assignees = update.message.text.strip().split(" ")
            duty["assignee"].extend(assignees)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join([
                    f"Назначил на дежурство {', '.join(assignees)}.",
                    f"Даты начала и конца дежурства: {duty['starts_at']} - {duty['ends_at']}",
                ])
            )

    def callback(update: Update, context: CallbackContext):
        query = update.callback_query

        if KEY_ASSIGN in context.user_data:
            duty = context.user_data[KEY_ASSIGN]

            if "starts_at" not in duty or "ends_at" not in duty:
                result, key, step = make_calendar().process(query.data)
                if not result and key:
                    context.bot.edit_message_text(
                        CalendarStep[step],
                        chat_id=update.effective_chat.id,
                        message_id=update.effective_message.message_id,
                        reply_markup=key
                    )
                    return

                if result:
                    if "starts_at" not in duty:
                        context.bot.edit_message_text(
                            f"Дата начала дежурства {result}",
                            chat_id=update.effective_chat.id,
                            message_id=update.effective_message.message_id,
                        )
                        duty["starts_at"] = result

                        calendar, step = make_calendar().build()
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Укажи дату конца дежурства",
                            reply_markup=calendar
                        )
                        return
                    if "ends_at" not in duty:
                        context.bot.edit_message_text(
                            f"Дата конца дежурства {result}",
                            chat_id=update.effective_chat.id,
                            message_id=update.effective_message.message_id,
                        )
                        duty["ends_at"] = result
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="\n".join([
                                "Укажи дежурных через @user.",
                                "Когда закончишь перечислять напиши /done",
                            ])
                        )
                        return
                    return
                return

    ##

    handlers = [
        (CommandHandler, "start", start,),
        (CommandHandler, "help", help,),
        (CommandHandler, "assign", assign,),
        (CommandHandler, "done", done,),
        (MessageHandler, Filters.text & (~Filters.command), message,),
        (CallbackQueryHandler, callback)
    ]

    for handler in handlers:
        dispatcher.add_handler(handler[0](*handler[1:]))

    updater.start_polling()

if __name__ == "__main__":
    main()
