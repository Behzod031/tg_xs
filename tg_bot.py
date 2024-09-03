import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import datetime
import matplotlib.pyplot as plt  # Для создания графиков

# Этапы разговора
BRANCH, PROPERTY_CLASS, OBJECT, APARTMENT_COUNT, AMOUNT, CONFIRMATION, FINAL_CONFIRMATION = range(7)

# Клавиатуры для выбора вариантов
branch_keyboard = [['Vatan', 'Zo’rsan', 'Red House', 'Rohat', 'Yunusobod']]
property_class_keyboard = [['Квартира', 'Паркинг']]
object_keyboard = [['Vatan', 'Zo’rsan', 'Orzular', 'Parlament', 'Qo’yliq', 'Vodiiy', 'Muhabbat shahri', 'Ocean']]
confirmation_keyboard = [['Да', 'Нет']]
final_confirmation_keyboard = [['Подтверждаю', 'Не подтверждаю']]

# URL API Sheetsu и токен Telegram Bot
SHEETSU_API_URL = "https://sheetdb.io/api/v1/nsu9dn2lkthwl"
TELEGRAM_BOT_TOKEN = "7522846671:AAEOvWM_S2T-jsM04kMRgDpWPMRW3mfOwFw"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['data_list'] = []
    context.user_data['total_amount'] = 0
    reply_markup = ReplyKeyboardMarkup(branch_keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите филиал:', reply_markup=reply_markup)
    return BRANCH


async def select_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['branch'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(property_class_keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите класс недвижимости:', reply_markup=reply_markup)
    return PROPERTY_CLASS


async def select_property_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['property_class'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(object_keyboard, one_time_keyboard=True)
    await update.message.reply_text('По какому объекту:', reply_markup=reply_markup)
    return OBJECT


async def select_object(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['object'] = update.message.text
    await update.message.reply_text('Введите количество квартир:')
    return APARTMENT_COUNT


async def input_apartment_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['apartment_count'] = update.message.text
    await update.message.reply_text('Введите сумму (без букв и пробелов):')
    return AMOUNT


async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = update.message.text.strip()

    if not amount.isdigit():
        await update.message.reply_text('Пожалуйста, введите корректную сумму (только числа):')
        return AMOUNT

    context.user_data['amount'] = amount
    context.user_data['total_amount'] += int(amount)

    reply_markup = ReplyKeyboardMarkup(final_confirmation_keyboard, one_time_keyboard=True)
    await update.message.reply_text('Подтверждаю ли я процесс?', reply_markup=reply_markup)
    return FINAL_CONFIRMATION


async def final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'подтверждаю':
        data = {
            "Дата": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Филиал": context.user_data.get('branch', 'Не указано'),
            "Класс недвижимости": context.user_data.get('property_class', 'Не указано'),
            "Объект": context.user_data.get('object', 'Не указано'),
            "Количество квартир": context.user_data.get('apartment_count', 'Не указано'),
            "Сумма": context.user_data.get('amount', 'Не указано')
        }

        context.user_data['data_list'].append(data)

        await update.message.reply_text(
            f"Отладка: Данные сохранены: {data}\nОбщая сумма: {context.user_data['total_amount']}")

        reply_markup = ReplyKeyboardMarkup(confirmation_keyboard, one_time_keyboard=True)
        await update.message.reply_text('Добавите ещё?', reply_markup=reply_markup)
        return CONFIRMATION
    else:
        await update.message.reply_text('Процесс был отменен. Начинаем сначала.')
        return await start(update, context)


async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'да':
        reply_markup = ReplyKeyboardMarkup(branch_keyboard, one_time_keyboard=True)
        await update.message.reply_text('Выберите филиал:', reply_markup=reply_markup)
        return BRANCH
    else:
        for entry in context.user_data['data_list']:
            try:
                response = requests.post(SHEETSU_API_URL, json={"data": entry})
                response.raise_for_status()
            except requests.RequestException as e:
                await update.message.reply_text(f"Произошла ошибка при записи данных: {e}")
                return ConversationHandler.END

        await update.message.reply_text(
            f"Спасибо, ваши данные сохранены.\nОбщая сумма: {context.user_data['total_amount']}")
        return await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Процесс отменен.')
    return ConversationHandler.END


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен. Проверьте переменные окружения.")

    # Создайте объект приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Настройте обработчики для разговоров
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_branch)],
            PROPERTY_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_property_class)],
            OBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_object)],
            APARTMENT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_apartment_count)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount)],
            FINAL_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_confirmation)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
