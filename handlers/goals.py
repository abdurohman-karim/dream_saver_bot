from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from states.goals import GoalStates
from rpc import rpc
from keyboards.keyboards import cancel_button, main_menu

router = Router()


@router.callback_query(lambda c: c.data == "menu_newgoal")
async def new_goal_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(GoalStates.waiting_for_title)

    sent = await cb.message.edit_text(
        "🎯 <b>Введите название цели:</b>",
        reply_markup=cancel_button()
    )

    # сохраняем ID сообщения бота
    await state.update_data(bot_message_id=sent.message_id)
    await cb.answer()


@router.message(GoalStates.waiting_for_title)
async def set_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await state.set_state(GoalStates.waiting_for_amount)

    sent = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="💰 <b>Введите сумму цели (UZS):</b>",
        reply_markup=cancel_button()
    )

    await state.update_data(bot_message_id=sent.message_id)


@router.message(GoalStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Введите сумму числом ⚠️")

    await state.update_data(amount_total=message.text)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await state.set_state(GoalStates.waiting_for_deadline)

    sent = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="📅 <b>Введите дедлайн (YYYY-MM-DD):</b>",
        reply_markup=cancel_button()
    )

    await state.update_data(bot_message_id=sent.message_id)


@router.message(GoalStates.waiting_for_deadline)
async def set_deadline(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    goal = {
        "tg_user_id": message.from_user.id,
        "title": data["title"],
        "amount_total": data["amount_total"],
        "deadline": message.text
    }

    result = await rpc("goal.create", goal)
    print("RPC RESPONSE goal.create:", result)

    await state.clear()

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="🎉 Цель успешно создана!",
        reply_markup=main_menu()
    )
