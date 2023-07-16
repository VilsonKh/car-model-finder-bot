import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, error
from telegram.ext import CommandHandler, Application, ContextTypes, ConversationHandler, MessageHandler, filters
import json
import os

TELEGRAM_API_KEY = os.environ['TELEGRAM_API_KEY']
# MY_DEVELOPER_ID = os.environ['DEVELOPER_CHAT_ID']
API_KEY = os.environ['API_KEY']

MANUFACTURER, MODEL, YEAR, CHOICE = range(4)

API_URL = 'https://api.api-ninjas.com/v1/cars?'

class InvalidDataException(Exception):
    "Вызывается, когда api возвращает некорректные данные"
    pass


async def error_handler(update, context):
    message_text = 'Произошла ошибка ' + str(context.error) + "\n Сообщение: " + str(update.message.text)
    await update.message.reply_text(
        "Произошла ошибка.\n"
    )
    # await context.bot.send_message(chat_id=MY_DEVELOPER_ID, text=message_text)


async def custom_error_handler(update, context, e, message):
    message_text = 'Произошла ошибка ' + str(e) + "\n Сообщение: " + str(message)
    await update.message.reply_text(
        "Произошла ошибка.\n"
    )
    # await context.bot.send_message(chat_id=MY_DEVELOPER_ID, text=message_text)


# служит для тестирования ошибок
# async def bad_guy(update, context):
#     raise error.TelegramError('Unauthorized')


async def manufacturer(update, context) -> int:
    await update.message.reply_text(
        "Введите название модели:\n"
    )
    message_from_user = update.message.text
    context.user_data["manufacturer"] = message_from_user
    return MODEL


async def model(update, context) -> int:
    await update.message.reply_text(
        "Введите год выпуска модели:\n"
    )
    message_from_user = update.message.text
    context.user_data["model"] = message_from_user

    return YEAR


async def year(update, context) -> int:
    message_from_user = update.message.text
    context.user_data["year"] = message_from_user

    make_name = context.user_data["manufacturer"]
    model_name = context.user_data["model"]
    year_name = context.user_data["year"]
    result = ''

    try:
        result = await get_data_from_api(API_KEY, API_URL, make_name, model_name, year_name, 50)

    except InvalidDataException:
        await update.message.reply_text(
            "Произошла ошибка, данные не найдены. Наберите /start, чтобы начать новый поиск"
        )
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(
            "Произошла ошибка, попробуйте повторить операцию позже."
        )
        await custom_error_handler(update, context, e, message_from_user)
        return ConversationHandler.END

    reply_keys = ''

    try:
        result_parsed = json.loads(result)
        key = 'model'
        result_models = [entry[key] for entry in result_parsed]
        result_models = list(dict.fromkeys(result_models))
        n = 3
        reply_keys = [result_models[i:i + n] for i in range(0, len(result_models), n)]
    except Exception as e:
        await update.message.reply_text(
            "Произошла ошибка, попробуйте повторить операцию позже."
        )
        await custom_error_handler(update, context, e, message_from_user)
        return ConversationHandler.END

    await update.message.reply_text(
        # ' '.join(str(a) for a in result_models)
        "Выберите конкретную модель из списка:\n",
        reply_markup=ReplyKeyboardMarkup(

            reply_keys, one_time_keyboard=True, input_field_placeholder="Модель"

        )
    )
    return CHOICE


async def get_data_from_api(api_key, api_url, make_name, model_name, year_name, limit) -> str:
    result_url = api_url + 'make={}&model={}&year={}&limit={}'.format(make_name, model_name, year_name, limit)
    response = requests.get(result_url, headers={'X-Api-Key': api_key})
    result = ''
    if response.status_code == requests.codes.ok:
        result = response.text
        if len(response.text) < 4:
            raise InvalidDataException('Invalid data')
    else:
        raise Exception("Error when processing request")
    return result


async def parse_json(json_text):
    parsed_json = json.loads(json_text)
    string_text = str(json.dumps(parsed_json, sort_keys=True,
                      indent=0, separators=(',', ': ')))
    string_text = string_text.replace('[', '').replace(']', '').replace('"', ' ').replace(',', '')\
                             .replace('{', '').replace('}', '')
    return string_text


async def choice(update, context) -> int:
    message_from_user = update.message.text
    context.user_data["choice"] = message_from_user
    make_name = context.user_data["manufacturer"]
    model_name = context.user_data["choice"]
    year_name = context.user_data["year"]
    result = ''

    try:
        result = await get_data_from_api(API_KEY, API_URL, make_name, model_name, year_name, 10)

    except InvalidDataException:
        await update.message.reply_text(
            "Произошла ошибка, данные не найдены."
        )
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(
            "Произошла ошибка, попробуйте повторить операцию позже."
        )
        await custom_error_handler(update, context, e, message_from_user)
        return ConversationHandler.END

    result = await parse_json(result)

    await update.message.reply_text(
        "Ваш результат:\n" +
        str(result), reply_markup = ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def start(update, context) -> int:
    await update.message.reply_text(
        "Введите название компании-производителя автомобиля\n" +
        "Отправь /cancel, если захочешь остановить операцию\n", reply_markup = ReplyKeyboardRemove())


    # message_from_user = update.message.text
    # context.user_data["manufacturer"] = message_from_user
    return MANUFACTURER


async def galya_otmena(update, context) -> int:
    await update.message.reply_text(
        "Операция отменена. Чтобы начать заново, наберите /start"
    )
    return ConversationHandler.END


def main() -> None:
    # token вынести в константу и в env
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MANUFACTURER: [MessageHandler(filters.TEXT & ~filters.COMMAND, manufacturer)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice)]
        },
        fallbacks=[CommandHandler("cancel", galya_otmena)],
    )
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    # application.add_handler(CommandHandler("errors", bad_guy))
    application.run_polling()


if __name__ == "__main__":
    main()