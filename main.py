import asyncio
import random
from os import getenv

from aiogram.exceptions import TelegramBadRequest
from aiogram.utils import keyboard
from dotenv import load_dotenv
from aiogram import F, types, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()
token = getenv('TELEGRAM_BOT_TOKEN')
if not token:
    raise ValueError('ERROR: Telegram token not found')

dp = Dispatcher()


class RouletteStates(StatesGroup):
    choosing_bet = State()
    choosing_number_or_color = State()
    spinning = State()


def get_bet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="10", callback_data="bet_10"),
        types.InlineKeyboardButton(text="50", callback_data="bet_50"),
        types.InlineKeyboardButton(text="100", callback_data="bet_100")
    )
    builder.row(
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_numbers_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(0, 37, 6):
        row = [types.InlineKeyboardButton(text=str(j), callback_data=f"number_{j}")
               for j in range(i, min(i + 6, 37))]
        builder.row(*row)
    return builder


@dp.message(Command("start"))
async def start_handler(message: Message):
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🎰 Крутить рулетку",
        callback_data="play_roulette"
    ))

    # Отправляем фото с приветствием
    try:
        await message.answer_photo(
            photo='AgACAgIAAxkBAANqaBnoIPBHWuZTZBziKsMzJOWbSdkAAl33MRucKdBII-fYvq4E-_0BAAMCAAN5AAM2BA',
            caption=(
                "🎉 <b>Добро пожаловать в BluexRoulette!</b> 🎉\n\n"
                "Здесь начинается ваше захватывающее путешествие в мир азартных игр!\n"
                "🍀 <i>Почувствуйте атмосферу казино, сделайте ставку и позвольте удаче улыбнуться вам!</i>\n\n"
                "🔥 <b>Готовы испытать свою удачу?</b> Вперёд к большим выигрышам!"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Фолбэк на случай проблем с фото
        await message.answer(
            text=(
                "🎰 <b>BluexRoulette приветствует вас!</b> 🎰\n\n"
                "Готовы к адреналину и крупным выигрышам?\n"
                "Каждый спин может изменить вашу жизнь!\n\n"
                "<i>Сделайте ставку и докажите свою удачу!</i> 🔥"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

@dp.message(lambda msg: msg.photo)  # Ловим любое фото
async def handle_photo(message: types.Message):
    file_id = message.photo[-1].file_id  # Берём ID в максимальном качестве
    await message.answer(
        f"🖼 <b>Фото принято!</b>\n"
        f"🔑 <code>{file_id}</code> — твой file_id\n"
        f"Используй его для сохранения или пересылки!",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "play_roulette")
async def start_roulette(callback: CallbackQuery, state: FSMContext):
    try:
        # Пытаемся отредактировать текст сообщения
        await callback.message.edit_text(
            "🎰 Рулетка\nВыберите ставку:",
            reply_markup=get_bet_keyboard()
        )
    except TelegramBadRequest:
        # Если сообщение было фото - удаляем его и отправляем новое текстовое
        await callback.message.delete()
        await callback.message.answer(
            "🎰 Рулетка\nВыберите ставку:",
            reply_markup=get_bet_keyboard()
        )

    await state.set_state(RouletteStates.choosing_bet)
    await callback.answer()


@dp.callback_query(RouletteStates.choosing_bet, F.data.startswith("bet_"))
async def process_bet(callback: CallbackQuery, state: FSMContext):
    bet_amount = int(callback.data.split("_")[1])
    await state.update_data(bet_amount=bet_amount)

    builder = get_numbers_keyboard()
    builder.row(
        types.InlineKeyboardButton(text="🔴 Красное", callback_data="color_red"),
        types.InlineKeyboardButton(text="⚫ Чёрное", callback_data="color_black")
    )
    builder.row(
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel")
    )

    await callback.message.edit_text(
        f"Ставка: {bet_amount}\nВыберите число или цвет:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RouletteStates.choosing_number_or_color)
    await callback.answer()


@dp.callback_query(RouletteStates.choosing_number_or_color, F.data.startswith(("number_", "color_")))
async def process_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet_amount = data["bet_amount"]

    if callback.data.startswith("number_"):
        selected = int(callback.data.split("_")[1])
        bet_type = "number"
    else:
        selected = callback.data.split("_")[1]  # "red" или "black"
        bet_type = "color"

    await state.update_data(selected=selected, bet_type=bet_type)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🎯 Крутить рулетку!", callback_data="spin")),
    builder.row(types.InlineKeyboardButton(text='Отмена', callback_data='cancel'))


    await callback.message.edit_text(
        f"Ставка: {bet_amount}\nВаш выбор: {selected}\n\nГотовы крутить?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RouletteStates.spinning)
    await callback.answer()


@dp.callback_query(RouletteStates.spinning, F.data == "spin")
async def spin_roulette(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet_amount = data["bet_amount"]
    selected = data["selected"]
    bet_type = data["bet_type"]

    # Анимация вращения
    message = await callback.message.edit_text("🔄 Рулетка крутится...")
    for _ in range(3):
        await asyncio.sleep(1)
        temp_num = random.randint(0, 36)
        await message.edit_text(f"🎰 Выпадает: {temp_num}...")

    # Финальный результат
    result = random.randint(0, 36)
    is_red = result in {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    color = "red" if is_red else "black" if result != 0 else "zero"

    # Расчет выигрыша
    if bet_type == "number":
        win = bet_amount * 36 if result == selected else 0
    else:  # color bet
        win = bet_amount * 2 if (selected == color) else 0

    # Формирование результата
    result_text = (
        f"🎰 Результат: {result} ({color})\n"
        f"Ваша ставка: {selected}\n"
        f"Сумма ставки: {bet_amount}\n\n"
        f"{'🎉 Поздравляем! Вы выиграли ' + str(win) if win > 0 else '😢 К сожалению, вы проиграли'}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎰 Играть снова", callback_data="play_roulette")
    )

    await message.edit_text(
        result_text,
        reply_markup=builder.as_markup()
    )
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено")
    await callback.answer()


async def main():
    bot = Bot(token=token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())