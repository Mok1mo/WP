import telebot
from telebot import types
import mysql.connector
from telebot.types import InputMediaPhoto, ReplyKeyboardRemove
import os
from dotenv import load_dotenv
import re

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

API_KEY = os.environ.get('API_KEY')
DB_PASS = os.environ.get('DB_PASS')
ADMN_PASS = os.environ.get('ADMN_PASS')

bot = telebot.TeleBot(API_KEY)

# Подключение к бд
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=DB_PASS,
    database="flowers",
)
cursor = db.cursor()


class User:
    def __init__(self, Id, first, username):
        self.Id = Id
        self.first = first
        self.username = username


class Flower:
    def __init__(self, Id, name, amount, price):
        self.Id = Id
        self.name = name
        self.amount = amount
        self.price = price

    def amountPlus(self):
        self.amount += 1
        return self.amount

    def amountMinus(self):
        self.amount -= 1
        return self.amount

    def display(self):
        print(
            f'Id = {self.Id}, name = {self.name}, amount = {self.amount}, price = {self.price}')


# Глобальная переменная списка цветов из выбраной категории
flowerDictData = {}

# Глобальная переменная списка цветов
flowerList = []


# Реакция на /start
@bot.message_handler(commands=['start'])
def start_message(message):
    cid = message.chat.id

    user = User(Id=cid, first=message.from_user.first_name, username=message.from_user.username)

    request = f'INSERT INTO customers(name, user_name, chat_id) SELECT * FROM(SELECT \'{user.first}\', \'{user.username}\', \'{user.Id}\') AS tmp WHERE NOT EXISTS(SELECT chat_id FROM customers WHERE chat_id=\'{user.Id}\') LIMIT 1'

    try:
        cursor.execute(request)
        db.commit()
    except:
        db.rollback()

    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in ['Меню📋', 'Корзина🛍️']])
    # keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    # keyboard.add(*[types.KeyboardButton(text=name)
    #                for name in ['Живые цветы', 'Искусственные']])
    bot.send_message(
        cid, f'Здравствуйте, {user.first}\nДобро пожаловать в наш цветочный магазин💐', reply_markup=keyboard)


def mainMenu(message):
    cid = message.chat.id

    cursor.execute('SELECT COUNT(*) FROM category')
    N = cursor.fetchone()
    N = int(str(N)[1:-2])

    cursor.execute('SELECT name FROM category')

    flowerList = []
    for i in range(N):
        flowerList.append(str(cursor.fetchone())[2:-3])

    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])
    keyboard.add('◀️Назад', 'Корзина🛍️')

    msg = bot.send_message(cid, 'Выберете категорию: ', reply_markup=keyboard)
    bot.register_next_step_handler(msg, selectCategory)


def selectCategory(message):
    cid = message.chat.id

    if message.text == '◀️Назад':
        start_message(message)

    elif message.text == 'Корзина🛍️':
        cart(message)

    elif message.text == '/start':
        bot.clear_step_handler_by_chat_id(cid)
        start_message(message)

    elif message.text == '/admin':
        bot.clear_step_handler_by_chat_id(cid)
        admin_message(message)

    elif message.text == '/help':
        bot.clear_step_handler_by_chat_id(cid)
        help_message(message)

    else:
        cursor.execute(
            f'SELECT id FROM category WHERE name=\'{message.text}\'')
        categoryId = cursor.fetchone()
        categoryId = int(str(categoryId)[1:-2])
        print('categoryId = ' + str(categoryId))

        cursor.execute(
            f'SELECT COUNT(*) FROM goods WHERE category=\'{categoryId}\'')
        N = cursor.fetchone()
        N = int(str(N)[1:-2])
        print('N = ' + str(N))

        if N != 0:
            cursor.execute(
                f'SELECT id FROM goods WHERE category=\'{categoryId}\'')
            flowerId = []
            for i in range(N):
                flowerId.append(str(cursor.fetchone())[1:-2])

            for i in flowerId:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(i))  # Если не работает то тут проверка
                               for name in ['☝️Добавить в корзину👈']])

                cursor.execute(f'SELECT name FROM goods WHERE id=\'{i}\'')
                name = cursor.fetchone()
                name = str(name)[2:-3]

                cursor.execute(f'SELECT price FROM goods WHERE id=\'{i}\'')
                price = cursor.fetchone()
                price = str(price)[1:-2]

                cursor.execute(f'SELECT amount FROM goods WHERE id=\'{i}\'')
                amount = cursor.fetchone()
                amount = str(amount)[1:-2]

                msg = bot.send_photo(
                    cid, open(f'images/{i}.jpg', 'rb'), caption=name +
                    '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                    'В наличие - ' + amount + ' шт' +
                    '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                    '1️⃣ шт - ' + price + ' грн💸', reply_markup=keyboard)

            bot.register_next_step_handler(msg, selectCategory)

        else:
            msg = bot.send_message(cid, 'Сейчас нет в наличии :(')
            bot.register_next_step_handler(msg, selectCategory)


# Корзина
def cart(message):
    cid = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in ['Оформить заказ📦', 'Меню📋']])
    bot.send_message(cid, 'Cart', reply_markup=keyboard)


# Реакция на /admin
@ bot.message_handler(commands=['admin'])
def admin_message(message):
    cid = message.chat.id

    msg = bot.send_message(cid, 'Введите пароль: ')
    bot.register_next_step_handler(msg, confirmPassword)


def confirmPassword(message):
    cid = message.chat.id

    if message.text == ADMN_PASS:

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')

        msg = bot.send_message(
            cid, 'Рекомендую удалить ваше сообщение с паролем. Что будем делать?', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)

    elif message.text == '/start':
        bot.clear_step_handler_by_chat_id(cid)
        start_message(message)
    else:
        bot.send_message(cid, 'Пароль не верный :(')


# Функции админа
def adminArea(message):
    cid = message.chat.id
    global flowerList
    flowerList = []

    if message.text == 'Редактировать товар':

        cursor.execute('SELECT COUNT(*) FROM category')
        N = cursor.fetchone()
        N = int(str(N)[1:-2])

        cursor.execute('SELECT name FROM category ORDER BY name')
        for i in range(N):
            flowerList.append(str(cursor.fetchone())[2:-3])

        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])
        keyboard.add('Отменить❌')
        print('flowerList = ' + str(flowerList))

        msg = bot.send_message(cid, 'Выберете нужную категорию: ',
                               reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    elif message.text == 'Добавить категорию':

        keyboard = types.ReplyKeyboardMarkup(1, 1)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Отменить❌']])

        cursor.execute('SELECT COUNT(*) FROM category')
        N = cursor.fetchone()
        N = int(str(N)[1:-2])

        cursor.execute('SELECT name FROM category')
        flowerStr = ''
        for i in range(N):
            flowerStr += str(cursor.fetchone())[2:-3] + '\n'

        bot.send_message(cid, 'Существующие категории: ' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' + flowerStr)

        msg = bot.send_message(
            cid, 'Введите название новой категории: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminAddCategory)

    elif message.text == 'Добавить товар':

        cursor.execute('SELECT COUNT(*) FROM category')
        N = cursor.fetchone()
        N = int(str(N)[1:-2])

        cursor.execute('SELECT name FROM category ORDER BY name')
        flowerList = []
        for i in range(N):
            flowerList.append(str(cursor.fetchone())[2:-3])

        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])
        keyboard.add('Отменить❌')

        msg = bot.send_message(cid, 'Выберете нужную категорию:',
                               reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategory)

    elif message.text == 'Показать отчёт':
        msg = bot.send_message(cid, 'отчёт')
        bot.register_next_step_handler(msg, adminArea)

    elif message.text == 'Выйти из админ панели':
        bot.send_message(cid, 'Вы вышли из админ панели' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                         '◾️/start - проверить изменения', reply_markup=ReplyKeyboardRemove())

    elif message.text == '/start':
        bot.clear_step_handler_by_chat_id(cid)
        start_message(message)
    else:
        bot.send_message(cid, 'Такой команды нет')


# Редактирование товаров
def adminSelectCategoryForEdit(message):
    cid = message.chat.id

    if message.text != 'Отменить❌':

        global flowerDictData
        category = message.text

        try:
            cursor.execute(
                f'SELECT id FROM category WHERE name=\'{category}\'')
            categoryId = int(str(cursor.fetchone())[1:-2])
            print('categoryId = ' + str(categoryId))

            cursor.execute(
                f'SELECT COUNT(*) FROM goods WHERE category=\'{categoryId}\'')
            N = cursor.fetchone()
            N = int(str(N)[1:-2])
            print('N = ' + str(N))

        except:
            msg = bot.send_message(
                cid, 'Сейчас нет в наличии :(\nВыберете другую категорию: ')
            bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

        if N != 0:
            cursor.execute(
                f'SELECT id, name, price, amount FROM goods WHERE category=\'{categoryId}\' ORDER BY name')
            flowerDictData = {}
            for i in range(N):
                flowerDictData.update({i: cursor.fetchone()})

                flowerId = str(flowerDictData[i][0])
                name = str(flowerDictData[i][1])
                amount = str(flowerDictData[i][2])
                price = str(flowerDictData[i][3])

                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + flowerId)
                               for name in ['Редактировать цену', 'Редактировать количество', 'Удалить товар']])

                bot.send_message(cid, name +
                                 '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                                 'В наличие - ' + price + ' шт' +
                                 '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                                 '1️⃣ шт - ' + amount + ' грн💸', reply_markup=keyboard)

            flowerDictData = flowerDictData.copy()
            print('GLOBAL flowerDictData = ' + str(flowerDictData))

            msg = bot.send_message(cid, 'Можете выбрать другую категорию:')
            bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

        else:
            msg = bot.send_message(
                cid, 'Сейчас нет в наличии :(\nВыберете другую категорию: ')
            bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')

        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


# Редактирование цены
def adminEditPrice(message, flowerId):
    cid = message.chat.id
    print(message.text)

    keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])
    keyboard.add('Отменить❌')

    if message.text != 'Отменить❌':
        if message.text.isdigit():
            try:
                cursor.execute(
                    f'UPDATE goods SET price = \'{message.text}\' WHERE id = \'{flowerId}\'')
                db.commit()
            except:
                db.rollback()
        else:
            msg = bot.send_message(cid, 'Это не число, попробуйте ещё раз')
            bot.register_next_step_handler(msg, adminEditPrice, flowerId)

        bot.send_message(cid, f'Изменения внесены ({message.text})')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    else:
        bot.send_message(cid, 'Окей')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)


# Редактирование количества
def adminEditAmount(message, flowerId):
    cid = message.chat.id
    print(message.text)

    keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])
    keyboard.add('Отменить❌')

    if message.text != 'Отменить❌':
        if message.text.isdigit():
            try:
                cursor.execute(
                    f'UPDATE goods SET amount = \'{message.text}\' WHERE id = \'{flowerId}\'')
                db.commit()
            except:
                db.rollback()
        else:
            msg = bot.send_message(cid, 'Это не число, попробуйте ещё раз')
            bot.register_next_step_handler(msg, adminEditPrice, flowerId)

        bot.send_message(cid, f'Изменения внесены ({message.text})')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    else:
        bot.send_message(cid, 'Окей')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)


# Добавление категории
def adminAddCategory(message):
    cid = message.chat.id

    if message.text != 'Отменить❌':
        category = message.text
        request = f'INSERT INTO category(name) SELECT * FROM(SELECT \'{category}\') AS tmp WHERE NOT EXISTS(SELECT name FROM category WHERE name = \'{category}\') LIMIT 1'

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')

        msg = bot.send_message(
            cid, 'Категория добавлена', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')
        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


# Добавление товара
def adminSelectCategory(message):
    cid = message.chat.id

    if message.text != 'Отменить❌':
        category = message.text

        cursor.execute(f'SELECT id FROM category WHERE name=\'{category}\'')
        categoryId = int(str(cursor.fetchone())[1:-2])
        print(categoryId)

        keyboard = types.ReplyKeyboardMarkup(1, 1)
        keyboard.add('Отменить❌')

        msg = bot.send_message(
            cid, 'Введите название нового товара: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminAddPosition, categoryId)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')
        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


def adminAddPosition(message, categoryId):
    cid = message.chat.id

    if message.text != 'Отменить❌':
        # categoryId = categoryId
        newFlower = message.text

        try:
            cursor.execute(
                f'INSERT INTO goods (category, name) VALUES (\'{categoryId}\', \'{newFlower}\')')
            db.commit()
        except:
            db.rollback()

        msg = bot.send_message(cid, 'Введите количество товара: ')
        bot.register_next_step_handler(msg, adminAddAmount, newFlower)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')
        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


def adminAddAmount(message, newFlower):
    cid = message.chat.id

    if message.text != 'Отменить❌':
        newFlower = newFlower
        amount = message.text

        request = f'UPDATE goods SET amount = \'{amount}\'WHERE name = \'{newFlower}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

        msg = bot.send_message(cid, 'Введите цену цветка: ')
        bot.register_next_step_handler(msg, adminAddPosPrice, newFlower)
    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')
        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


def adminAddPosPrice(message, newFlower):
    cid = message.chat.id

    if message.text != 'Отменить❌':
        newFlower = newFlower
        newFlowerPrice = message.text

        request = f'UPDATE goods SET price = \'{newFlowerPrice}\'WHERE name = \'{newFlower}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

        msg = bot.send_message(cid, 'Прикрепите фото: ')
        bot.register_next_step_handler(msg, adminAddPhoto, newFlower)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
        keyboard.add('Выйти из админ панели')
        msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminArea)


def adminAddPhoto(message, newFlower):
    cid = message.chat.id

    try:
        if message.text != 'Отменить❌':
            newFlower = newFlower

            cursor.execute(f'SELECT id FROM goods WHERE name=\'{newFlower}\'')
            flowerID = cursor.fetchone()
            flowerID = int(str(flowerID)[1:-2])
            print(flowerID)

            fileInfo = bot.get_file(message.document.file_id)
            print(fileInfo)
            downloadedFile = bot.download_file(fileInfo.file_path)

            src = 'images/' + str(flowerID) + '.jpg'
            with open(src, 'wb') as new_file:
                new_file.write(downloadedFile)

            keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
            keyboard.add(*[types.KeyboardButton(text=admbutton)
                           for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
            keyboard.add('Выйти из админ панели')

            msg = bot.send_message(
                cid, 'Позиция добавлена', reply_markup=keyboard)
            bot.register_next_step_handler(msg, adminArea)

        else:
            keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
            keyboard.add(*[types.KeyboardButton(text=admbutton)
                           for admbutton in ['Редактировать товар', 'Добавить товар', 'Добавить категорию', 'Показать отчёт']])
            keyboard.add('Выйти из админ панели')

            msg = bot.send_message(cid, 'Окей', reply_markup=keyboard)
            bot.register_next_step_handler(msg, adminArea)

    except Exception as e:
        print(e)
        msg = bot.reply_to(
            message, 'Не сжимайте изображение\nПопробуйте ещё раз')
        bot.register_next_step_handler(msg, adminAddPhoto, newFlower)


# Удаление товара
def adminConfirmDel(message, flowerId):
    cid = message.chat.id

    if message.text == 'Да':

        os.remove(f'images/{flowerId}.jpg')

        request = f'DELETE FROM goods WHERE id = \'{flowerId}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])
        keyboard.add('Отменить❌')

        msg = bot.send_message(cid, 'Позиция удалена')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])
        keyboard.add('Отменить❌')

        bot.send_message(cid, 'Окей', reply_markup=keyboard)
        msg = bot.send_message(cid, 'Можете выбрать другую категорию:')
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)


# Реакция на /help
@ bot.message_handler(commands=['help'])
def help_message(message):
    cid = message.chat.id
    bot.send_message(cid, 'Если нашли поломку, пишите ему - @parubanok')


# Реакция на текст
@ bot.message_handler(content_types=['text'])
def send_text(message):
    cid = message.chat.id

    if message.text == 'Меню📋':
        mainMenu(message)

    elif message.text == 'Корзина🛍️':
        bot.send_message(cid, 'Корзина🛍️')

    else:
        bot.send_message(cid, 'Такой команды нет')


# Реакция на инлайновые кнокпи меню
@ bot.callback_query_handler(func=lambda call: True)
def send_answer(call):
    print('\n' + call.data)

    cid = call.message.chat.id
    mid = call.message.message_id

    flowerId = call.data.split(':')[1]
    cursor.execute(
        f'SELECT name, price FROM goods WHERE id=\'{flowerId}\'')
    flower = cursor.fetchone()
    f = Flower(flowerId, name=flower[0],
               amount=1, price=flower[1])
    f.display()

    if re.match(r'☝️Добавить в корзину👈', call.data):
        bot.answer_callback_query(
            callback_query_id=call.id, text="Добавленно в корзину", show_alert=False)
        
        try:
            cursor.execute(
                f'INSERT INTO basket (id_cust, id_goods, amount, price) VALUES (\'{}\', \'{newFlower}\', \'{newFlower}\', \'{newFlower}\')')
            db.commit()
        except:
            db.rollback()

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(f.Id))
                       for name in ['-', f'{f.amount} шт.', '+', '❌', 'Корзина🛍️']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

    elif re.match(r'❌', call.data):

        bot.answer_callback_query(
            callback_query_id=call.id, text="Удаленно из корзины", show_alert=False)

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(f.Id))
                       for name in ['☝️Добавить в корзину👈']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

    elif re.match(r'\+', call.data):

        f.amountPlus()

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(f.Id))
                       for name in ['-', f'{f.amount} шт.', '+', '❌', 'Корзина🛍️']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

        print('amount = ' + str(f.amount))

    elif re.match(r'-', call.data):

        if f.amount > 1:
            f.amountMinus()

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(f.Id))
                           for name in ['-', f'{f.amount} шт.', '+', '❌', 'Корзина🛍️']])
            bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

            print('amount = ' + str(f.amount))

    elif re.match(r'Редактировать цену', call.data):
        bot.clear_step_handler_by_chat_id(cid)

        flowerId = call.data.split(':')[1]
        print('flowerId = ' + str(flowerId))

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add('Отменить❌')

        msg = bot.send_message(
            cid, 'Введите новую цену: ',  reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminEditPrice, flowerId)

    elif re.match(r'Редактировать количество', call.data):
        bot.clear_step_handler_by_chat_id(cid)

        flowerId = call.data.split(':')[1]
        print('flowerId = ' + str(flowerId))

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add('Отменить❌')

        msg = bot.send_message(
            cid, 'Введите новое количество: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminEditAmount, flowerId)

    elif re.match(r'Удалить товар', call.data):
        bot.clear_step_handler_by_chat_id(cid)

        flowerId = call.data.split(':')[1]
        print('flowerId = ' + str(flowerId))

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Да', 'Нет']])
        msg = bot.send_message(
            cid, 'Вы уверены, что хотите удали этот товар?', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminConfirmDel, flowerId)

#################################################################################
    if call.data == 'Выполнено':

        bot.send_message(cid, 'Ваш букет готов☺️👍' +
                         '\nЗаберите его, пожалуйста, в ближайщее время⌚️' +
                         '\n😋Хорошего времени суток😋')


def buyFlower(message, price, name):
    cid = message.chat.id

    name = name
    count = message.text
    print(count)

    if count != '0':
        if count.isdigit():

            fPrice = price*int(count)

            keyboard = types.ReplyKeyboardMarkup(1, 1)
            keyboard.add(*[types.KeyboardButton(text=name)
                           for name in ['Подтвердить', 'Отменить заказ']])

            msg = bot.send_message(cid, 'Количество : ' + str(count) + ' шт'
                                   '\nК оплате : ' + str(fPrice) + ' грн💸' +
                                   '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                                   'Подтвердите заказ: ', reply_markup=keyboard)
            bot.register_next_step_handler(
                msg, confirmOrder, count, name, fPrice)

        elif count == '/start':
            bot.clear_step_handler_by_chat_id(cid)
            start_message(message)
        else:
            msg = bot.send_message(cid, 'Это не число, попробуйте снова😕')
            bot.register_next_step_handler(msg, buyFlower, price)
    else:
        msg = bot.send_message(cid, 'Это ноль, попробуйте снова😕')
        bot.register_next_step_handler(msg, buyFlower, price)


def confirmOrder(message, count, name, fPrice):
    cid = message.chat.id

    name = name
    count = count
    fPrice = fPrice
    answ = message.text
    print(answ)

    if answ == 'Подтвердить':
        bot.send_message(cid, '😉Ваш букет будет готов в течение пары минут⏳' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                         '◾️/start - совершить ещё покупку', reply_markup=ReplyKeyboardRemove())

        # СМС админу про заказ
        # keyboard = types.InlineKeyboardMarkup()
        # keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
        #                for name in ['Выполнено']])
        bot.send_message('461861635', 'Заказали букет - ' + name +
                         '\nКоличество - ' + count + ' шт' +
                         '\n➖➖➖➖➖➖➖➖➖➖' +
                         '\nК оплате - ' + str(fPrice) + ' грн💸')

    elif answ == 'Отменить заказ':
        bot.send_message(cid, '📦Ваш заказ успешно отменен!🚮' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
                         '◾️/start - вернуться на главную', reply_markup=ReplyKeyboardRemove())
    else:
        msg = bot.send_message(cid, 'Такого ответа нет, используйте панель😕')
        bot.register_next_step_handler(msg, confirmOrder)


bot.infinity_polling(True)
