from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import main_menu

router = Router()

# Назад в главное меню
@router.callback_query(lambda c: c.data == "menu_back")
async def back_to_main(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Главное меню 👇",
        reply_markup=main_menu()
    )
    await cb.answer()


# Отмена любого действия (создание цели и т.д.)
@router.callback_query(lambda c: c.data == "menu_cancel")
async def cancel_action(cb: types.CallbackQuery, state: FSMContext):
    # сбрасываем все состояния
    await state.clear()

    await cb.message.edit_text(
        "❌ Действие отменено.\n\nГлавное меню 👇",
        reply_markup=main_menu()
    )
    await cb.answer()
