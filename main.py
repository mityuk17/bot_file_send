import logging

import aiogram
from aiogram import Bot , Dispatcher , types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State , StatesGroup
import asyncio
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import json

from aiogram.types import ContentType
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token='token')
dp = Dispatcher(bot , storage=storage)

class States(StatesGroup):
    get_nickname = State()
    get_value = State()
    wait = State()

def get_config_data(key):
    with open('config.json', 'r', encoding='utf8') as config:
        data = json.load(config)
    return data.get(key)
def change_config(key, value):
    with open('config.json', 'r', encoding='utf8') as config:
        data = json.load(config)
    data[key] = value
    with open('config.json', 'w', encoding='utf8') as config:
        json.dump(data, config)

@dp.message_handler(commands=[ 'start' ])
async def start(message: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text = get_config_data('button'), callback_data='go_process'))
    await message.answer(get_config_data('start_message'), reply_markup = kb)
@dp.callback_query_handler(lambda query: query.data == 'go_process')
async def go_analys(callback_query: types.CallbackQuery):
    await callback_query.message.answer(get_config_data("after_button_message"))
    await States.get_nickname.set()
@dp.message_handler(state=States.get_nickname)
async def get_nickname(message: types.Message, state: FSMContext):
    nickname = message.text
    await States.wait.set()
    await message.answer(get_config_data("process_message"))
    await asyncio.sleep(10)
    await message.answer(f'{nickname}, {get_config_data("final_message")}')
    await state.finish()
    await bot.send_document(chat_id= message.chat.id, document=types.InputFile(get_config_data("file_path")))
    with open('ids.txt', 'a+') as file:
        file.write(f'{message.chat.id}\n')


@dp.message_handler(commands=[ 'admin' ])
async def admin(message: types.Message):
    if not(message.chat.id == get_config_data("admin_id")):
        return await message.answer('Вы не админ')
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text='Изменить приветсвенное сообщение', callback_data='configchange-start_message'))
    kb.add(types.InlineKeyboardButton(text='Изменить текст кнопки' , callback_data='configchange-button'))
    kb.add(types.InlineKeyboardButton(text='Изменить сообщение после нажатия кнопки' , callback_data='configchange-after_button_message'))
    kb.add(types.InlineKeyboardButton(text='Изменить сообщение перед таймаутом' , callback_data='configchange-process_message'))
    kb.add(types.InlineKeyboardButton(text='Изменить сообщение перед отправкой файла' , callback_data='configchange-final_message'))
    kb.add(types.InlineKeyboardButton(text='Изменить файл' , callback_data='configchange-file_path'))
    await message.answer('Выберите параметр, который хотите изменить:',reply_markup = kb)
@dp.callback_query_handler(lambda query: query.data == 'admin_menu')
async def give_admin_menu(callback_query: types.CallbackQuery):
    await admin(callback_query.message)
@dp.callback_query_handler(lambda query: query.data.startswith('configchange-'))
async def configchange(callback_query: types.CallbackQuery, state: FSMContext):
    target = callback_query.data.split('-')[-1]
    async with state.proxy() as data:
        data['target'] = target
    if target != 'file_path':
        await callback_query.message.answer('Пришлите новый текст:')
        await States.get_value.set()
    elif target == 'file_path':
        await callback_query.message.answer('Пришлите новый файл:')
        await States.get_value.set()
@dp.message_handler(state=States.get_value, content_types= ContentType.TEXT)
async def get_text(message:types.Message, state: FSMContext):
    admin_kb = types.InlineKeyboardMarkup()
    admin_kb.add(types.InlineKeyboardButton(text='Назад', callback_data='admin_menu'))
    async with state.proxy() as data:
        target = data['target']
    value = message.text
    change_config(target, value)
    await message.answer('Значение параметра успешно изменено', reply_markup= admin_kb)
    await state.finish()
@dp.message_handler(state=States.get_value, content_types= ContentType.DOCUMENT)
async def get_text(message:types.Message, state: FSMContext):
    admin_kb = types.InlineKeyboardMarkup()
    admin_kb.add(types.InlineKeyboardButton(text='Назад' , callback_data='admin_menu'))
    async with state.proxy() as data:
        target = data['target']
    file_name = message.document.file_name
    try:
        await message.document.download(file_name)
    except aiogram.utils.exceptions.FileIsTooBig:
        await message.answer('Файл слишком большой', reply_markup= admin_kb)
        await state.finish()
        return None
    change_config(target, file_name)
    await message.answer('Файл успешно заменён', reply_markup= admin_kb)
    await state.finish()



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)