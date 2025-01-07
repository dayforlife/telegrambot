from aiogram import F, types, Router
from aiogram.filters import CommandStart
from aiogram.types import InputMediaPhoto

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_to_cart,
    orm_add_user,
    orm_delete_from_cart,
    orm_get_user_carts,
)

from filters.chat_types import ChatTypeFilter
from handlers.menu_processing import get_menu_content
from kbds.inline import MenuCallBack



user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    media, reply_markup = await get_menu_content(session, level=0, menu_name="main")

    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


async def add_to_cart(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    user = callback.from_user
    await orm_add_user(
        session,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=None,
    )
    await orm_add_to_cart(session, user_id=user.id, product_id=callback_data.product_id)
    await callback.answer("Товар добавлен в корзину.")

async def process_order(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id

    # Получаем товары из корзины
    carts = await orm_get_user_carts(session, user_id)

    if not carts:
        await callback.answer("Ваша корзина пуста. Добавьте товары перед оформлением заказа.")
        return

    # Отправляем картинку и сообщение
    media = InputMediaPhoto(media="https://malyish.ru/upload/medialibrary/cd5/cd507b04cf99ea1a529dcd563a44944a.png", caption="Спасибо за заказ!")
    await callback.message.answer_media_group(media=[media])

    # Очищаем корзину
    for cart_item in carts:
        await orm_delete_from_cart(session, user_id, cart_item.product_id)

    await callback.answer("Ваш заказ оформлен. Спасибо!")


@user_private_router.callback_query(MenuCallBack.filter())
async def user_menu(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    if callback_data.menu_name == 'order':
        await process_order(callback, session)
        return

    if callback_data.menu_name == "add_to_cart":
        await add_to_cart(callback, callback_data, session)
        return

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id,
    )

    await callback.message.edit_media(media=media, reply_markup=reply_markup)
    await callback.answer()