# handlers/navigation.py
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from ui.menus import get_main_menu

router = Router()


@router.callback_query(lambda c: c.data == "menu_back")
async def back_to_main(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Быстрые действия и ключевые разделы — ниже.",
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()


@router.callback_query(lambda c: c.data == "menu_cancel")
async def cancel_action(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await cb.message.edit_text(
        "❌ <b>Действие отменено</b>\n\n"
        "Ты снова в главном меню.",
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()
