import asyncio
import os
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.enums import ChatMemberStatus, ParseMode
from datetime import datetime, timedelta

import database as db
from config import BOT_TOKEN, DEFAULT_SETTINGS, WARN_LIMIT, BAN_WORD, MUTE_WORD

PROXY_URL = os.getenv("PROXY_URL", "")

if PROXY_URL:
    connector = ProxyConnector.from_url(PROXY_URL)
    session = AiohttpSession(connector=connector)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=session)
else:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

user_message_counts = {}


async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["creator", "administrator"]


async def log_action(chat_id, text):
    log_chat = await db.get_log_chat(chat_id)
    if log_chat:
        try:
            await bot.send_message(log_chat, text)
        except Exception:
            pass


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-модератор.\n\n"
        "Главная фича:\n"
        "Ответь на сообщение человека и напиши слово бана или мута:\n"
        f"  • Бан: <b>{BAN_WORD}</b> (сменить: /setbanword)\n"
        f"  • Мут: <b>{MUTE_WORD}</b> (сменить: /setmuteword)\n\n"
        "Команды:\n"
        "/ban - забанить\n"
        "/mute - замутить\n"
        "/unban - разбанить\n"
        "/unmute - размутить\n"
        "/warn - выдать варн\n"
        "/resetwarns - сбросить варны\n"
        "/warnings - кол-во варнов\n"
        "/words - узнать слова команд\n"
        "/setwelcome - настроить приветствие\n"
        "/setlog - канал для логов\n"
        "/antiflood - вкл/выкл антифлуд\n"
        "/settings - настройки чата"
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого хочешь забанить.")
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        return await message.answer("Нельзя банить себя.")
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await log_action(message.chat.id,
            f"В <b>{message.chat.title}</b>\n"
            f"Забанен: {target.full_name} (ID: {target.id})\n"
            f"Админ: {message.from_user.full_name}"
        )
        await message.answer(f"Пользователь {target.full_name} забанен.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого хочешь разбанить.")
    target = message.reply_to_message.from_user
    try:
        await bot.unban_chat_member(message.chat.id, target.id)
        await log_action(message.chat.id,
            f"В <b>{message.chat.title}</b>\n"
            f"Разбанен: {target.full_name} (ID: {target.id})\n"
            f"Админ: {message.from_user.full_name}"
        )
        await message.answer(f"Пользователь {target.full_name} разбанен.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого хочешь замутить.")
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        return await message.answer("Нельзя мутить себя.")
    try:
        until = datetime.now() + timedelta(hours=1)
        permissions = message.chat.permissions.model_copy()
        permissions.can_send_messages = False
        await bot.restrict_chat_member(message.chat.id, target.id, permissions, until_date=until)
        await log_action(message.chat.id,
            f"В <b>{message.chat.title}</b>\n"
            f"Замучен: {target.full_name} (ID: {target.id})\n"
            f"Длительность: 1 час\n"
            f"Админ: {message.from_user.full_name}"
        )
        await message.answer(f"Пользователь {target.full_name} замучен на 1 час.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого хочешь размутить.")
    target = message.reply_to_message.from_user
    try:
        permissions = message.chat.permissions
        await bot.restrict_chat_member(message.chat.id, target.id, permissions)
        await log_action(message.chat.id,
            f"В <b>{message.chat.title}</b>\n"
            f"Размучен: {target.full_name} (ID: {target.id})\n"
            f"Админ: {message.from_user.full_name}"
        )
        await message.answer(f"Пользователь {target.full_name} размучен.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(Command("warn"))
async def cmd_warn(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого хочешь предупредить.")
    target = message.reply_to_message.from_user
    count = await db.add_warn(message.chat.id, target.id)
    limit = int(await db.get_setting(message.chat.id, "warn_limit", WARN_LIMIT))
    await log_action(message.chat.id,
        f"В <b>{message.chat.title}</b>\n"
        f"Варн: {target.full_name} (ID: {target.id})\n"
        f"Варнов: {count}/{limit}\n"
        f"Админ: {message.from_user.full_name}"
    )
    if count >= limit:
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
            await db.reset_warns(message.chat.id, target.id)
            await message.answer(f"{target.full_name} забанен за превышение лимита варнов ({count}/{limit}).")
        except Exception as e:
            await message.answer(f"Ошибка бана: {e}")
    else:
        await message.answer(f"Варн для {target.full_name}: {count}/{limit}")


@router.message(Command("resetwarns"))
async def cmd_reset_warns(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кому сбросить варны.")
    target = message.reply_to_message.from_user
    await db.reset_warns(message.chat.id, target.id)
    await message.answer(f"Варны {target.full_name} сброшены.")


@router.message(Command("warnings"))
async def cmd_warnings(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение того, кого проверить.")
    target = message.reply_to_message.from_user
    count = await db.get_warns(message.chat.id, target.id)
    limit = int(await db.get_setting(message.chat.id, "warn_limit", WARN_LIMIT))
    await message.answer(f"Варнов у {target.full_name}: {count}/{limit}")


@router.message(Command("setbanword"))
async def cmd_set_ban_word(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Использование: /setbanword слово")
    word = args[1].strip().lower()
    await db.set_setting(message.chat.id, "ban_word", word)
    await message.answer(f"Слово для бана установлено: <b>{word}</b>")


@router.message(Command("setmuteword"))
async def cmd_set_mute_word(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Использование: /setmuteword слово")
    word = args[1].strip().lower()
    await db.set_setting(message.chat.id, "mute_word", word)
    await message.answer(f"Слово для мута установлено: <b>{word}</b>")


@router.message(Command("words"))
async def cmd_words(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    ban_word = await db.get_setting(message.chat.id, "ban_word", BAN_WORD)
    mute_word = await db.get_setting(message.chat.id, "mute_word", MUTE_WORD)
    await message.answer(
        f"Слова команд:\n"
        f"• Бан: <b>{ban_word}</b> (ответь на сообщение и напиши слово)\n"
        f"• Мут: <b>{mute_word}</b> (ответь на сообщение и напиши слово)\n\n"
        f"Изменить: /setbanword или /setmuteword"
    )


@router.message(Command("setwelcome"))
async def cmd_set_welcome(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "Использование: /setwelcome текст\n"
            "Переменные: {user} - имя, {count} - номер участника"
        )
    await db.set_setting(message.chat.id, "welcome_message", args[1])
    await message.answer("Приветствие обновлено!")


@router.message(Command("setlog"))
async def cmd_set_log(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Использование: /setlog ID_канала")
    try:
        log_id = int(args[1])
        await db.set_log_chat(message.chat.id, log_id)
        await message.answer(f"Канал логов установлен: {log_id}")
    except ValueError:
        await message.answer("Неверный ID канала.")


@router.message(Command("antiflood"))
async def cmd_antiflood(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    current = await db.get_setting(message.chat.id, "antiflood_enabled", "True")
    new_val = "False" if current == "True" else "True"
    await db.set_setting(message.chat.id, "antiflood_enabled", new_val)
    status = "включен" if new_val == "True" else "выключен"
    await message.answer(f"Антифлуд {status}.")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.answer("Нет прав.")
    welcome = await db.get_setting(message.chat.id, "welcome_enabled", "True")
    antiflood = await db.get_setting(message.chat.id, "antiflood_enabled", "True")
    ban_word = await db.get_setting(message.chat.id, "ban_word", BAN_WORD)
    mute_word = await db.get_setting(message.chat.id, "mute_word", MUTE_WORD)
    text = (
        f"Настройки <b>{message.chat.title}</b>:\n\n"
        f"Приветствие: {'вкл' if welcome == 'True' else 'выкл'}\n"
        f"Антифлуд: {'вкл' if antiflood == 'True' else 'выкл'}\n"
        f"Слово бана: <b>{ban_word}</b>\n"
        f"Слово мута: <b>{mute_word}</b>"
    )
    await message.answer(text)


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    welcome = await db.get_setting(event.chat.id, "welcome_enabled", "True")
    if welcome != "True":
        return
    template = await db.get_setting(
        event.chat.id,
        "welcome_message",
        DEFAULT_SETTINGS["welcome_message"]
    )
    member_count = await bot.get_chat_member_count(event.chat.id)
    text = template.replace("{user}", event.new_chat_member.user.full_name).replace(
        "{count}", str(member_count)
    )
    await event.answer(text)


@router.message()
async def on_message(message: Message):
    if message.from_user is None or message.text is None:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip().lower()

    ban_word = await db.get_setting(chat_id, "ban_word", BAN_WORD)
    mute_word = await db.get_setting(chat_id, "mute_word", MUTE_WORD)

    if message.reply_to_message and text == ban_word:
        if not await is_admin(chat_id, user_id):
            return
        target = message.reply_to_message.from_user
        if target.id == user_id:
            return await message.answer("Нельзя банить себя.")
        try:
            await bot.ban_chat_member(chat_id, target.id)
            await log_action(chat_id,
                f"В <b>{message.chat.title}</b>\n"
                f"Бан по слову: {target.full_name} (ID: {target.id})\n"
                f"Админ: {message.from_user.full_name}"
            )
            await message.answer(f"Пользователь {target.full_name} забанен.")
            await message.delete()
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
        return

    if message.reply_to_message and text == mute_word:
        if not await is_admin(chat_id, user_id):
            return
        target = message.reply_to_message.from_user
        if target.id == user_id:
            return await message.answer("Нельзя мутить себя.")
        try:
            until = datetime.now() + timedelta(hours=1)
            permissions = message.chat.permissions.model_copy()
            permissions.can_send_messages = False
            await bot.restrict_chat_member(chat_id, target.id, permissions, until_date=until)
            await log_action(chat_id,
                f"В <b>{message.chat.title}</b>\n"
                f"Мут по слову: {target.full_name} (ID: {target.id})\n"
                f"Длительность: 1 час\n"
                f"Админ: {message.from_user.full_name}"
            )
            await message.answer(f"Пользователь {target.full_name} замучен на 1 час.")
            await message.delete()
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
        return

    if await is_admin(chat_id, user_id):
        return

    antiflood = await db.get_setting(chat_id, "antiflood_enabled", "True")
    if antiflood == "True":
        key = (chat_id, user_id)
        now = asyncio.get_event_loop().time()
        if key not in user_message_counts:
            user_message_counts[key] = []
        user_message_counts[key].append(now)
        user_message_counts[key] = [
            t for t in user_message_counts[key] if now - t < 10
        ]
        if len(user_message_counts[key]) > 5:
            try:
                until = datetime.now() + timedelta(minutes=5)
                permissions = message.chat.permissions.model_copy()
                permissions.can_send_messages = False
                await bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until)
                await log_action(chat_id,
                    f"В <b>{message.chat.title}</b>\n"
                    f"Антифлуд: {message.from_user.full_name} (ID: {user_id})\n"
                    f"Замучен на 5 минут"
                )
                user_message_counts[key] = []
            except Exception:
                pass


async def main():
    await db.init_db()
    dp.include_router(router)
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
