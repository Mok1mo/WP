import telebot
from telebot import types
from telebot.types import LabeledPrice, ShippingOption
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
PROVIDER_TOKEN = os.environ.get('PROVIDER_TOKEN')

bot = telebot.TeleBot(API_KEY)
provider_token = PROVIDER_TOKEN

# Подключение к бд
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=DB_PASS,
    database="flowers",
)
cursor = db.cursor(buffered=True)


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

    def display(self):
        print(
            f'Id = {self.Id}, name = {self.name}, amount = {self.amount}, price = {self.price}')


# Глобальная переменная списка цветов из выбраной категории
flowerDictData = {}

# Глобальная переменная списка цветов
flowerList = []

# Корзина
# cart = {}

# Для показа всего к оплате из корзины
msgId = 0
allPrice = 0


# Реакция на /start
@bot.message_handler(commands=['start'])
def start_message(message):
    cid = message.chat.id

    user = User(Id=cid, first=message.from_user.first_name,
                username=message.from_user.username)

    request = f'INSERT INTO customers(name, user_name, chat_id) SELECT * FROM(SELECT \'{user.first}\', \'{user.username}\', \'{user.Id}\') AS tmp WHERE NOT EXISTS(SELECT chat_id FROM customers WHERE chat_id=\'{user.Id}\') LIMIT 1'

    try:
        cursor.execute(request)
        db.commit()
    except:
        db.rollback()

    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in ['Меню📋', 'Корзина🛍️']])
    bot.send_photo(
        cid, open('images/hello.jpg', 'rb'), caption=f'Здравствуйте, {user.first}\nДобро пожаловать в наш цветочный магазин💐', reply_markup=keyboard)


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
    keyboard.add('◀️Назад', 'Корзина🛍️')
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])

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
        categoryId = int(str(cursor.fetchone())[1:-2])
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
                name = str(cursor.fetchone())[2:-3]

                cursor.execute(f'SELECT price FROM goods WHERE id=\'{i}\'')
                price = str(cursor.fetchone())[1:-2]

                cursor.execute(f'SELECT amount FROM goods WHERE id=\'{i}\'')
                amount = str(cursor.fetchone())[1:-2]

                msg = bot.send_photo(
                    cid, open(f'images/{i}.jpg', 'rb'), caption=name +
                    '\nВ наличие - ' + amount + ' шт' +
                    '\n1️⃣ шт - ' + price + ' грн💸', reply_markup=keyboard)

            bot.register_next_step_handler(msg, selectCategory)

        else:
            msg = bot.send_message(cid, 'Сейчас нет в наличии :(')
            bot.register_next_step_handler(msg, selectCategory)


# Корзина
def cart(message):
    cid = message.chat.id
    global msgId
    allPrice = 0

    cursor.execute('SELECT COUNT(*) FROM basket')
    N = int(str(cursor.fetchone())[1:-2])
    print('N = ' + str(N))

    if N > 0:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Меню📋', 'Оформить заказ📦']])
        bot.send_message(
            cid, 'В корзине🛍️ сейчас такие товары:', reply_markup=keyboard)

        cart = {}
        cursor.execute(
            f'SELECT id_goods, amount, full_price FROM basket WHERE id_cust = \'{cid}\'')

        for i in range(N):
            cart.update({i: cursor.fetchone()})
            print(cart)

        for i in range(N):
            flowerId = int(cart[i][0])
            amount = int(cart[i][1])
            fullPrice = int(cart[i][2])

            cursor.execute(
                f'SELECT name, price FROM goods WHERE id=\'{flowerId}\'')
            a = str(cursor.fetchone())
            name = str(a.split(', ')[0])[2:-1]
            price = str(a.split(', ')[1])[:-1]

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(flowerId))
                           for name in ['-', f'{amount} шт.', '+', '❌', f'К оплате - {fullPrice} грн💸']])
            msg = bot.send_photo(
                cid, open(f'images/{flowerId}.jpg', 'rb'), caption=name +
                '\n1️⃣ шт - ' + price + ' грн💸', reply_markup=keyboard)

            allPrice += int(fullPrice)

        msgId = bot.send_message(
            cid, f'💸Всего к оплате - {allPrice}  грн💸').message_id

        bot.register_next_step_handler(msg, phoheNumber, cart)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Меню📋']])
        bot.send_message(
            cid, 'В корзине🛍️ сейчас нет товаров.', reply_markup=keyboard)


def phoheNumber(message, cart):
    cid = message.chat.id

    if message.text == 'Оформить заказ📦':
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        reg_button = types.KeyboardButton(
            text="Отправить номер телефона📲", request_contact=True,)
        keyboard.add('Отменить❌', reg_button)
        msg = bot.send_message(message.chat.id,
                               'Оставьте ваш контактный номер чтобы мы смогли связаться с вами: ',
                               reply_markup=keyboard)
        bot.register_next_step_handler(msg, delivery, cart)

    elif message.text == 'Меню📋':
        mainMenu(message)


def delivery(message, cart):
    cid = message.chat.id

    if message.text == 'Отменить❌':
        start_message(message)

    else:
        nomer = message.contact
        try:
            cursor.execute(
                f'UPDATE customers SET phone = \'{nomer}\' WHERE chat_id = \'{cid}\'')
            db.commit()
        except:
            db.rollback()

        #Описать в доке про кнопку
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        reg_button = types.KeyboardButton(text="Отправить локацию",request_location=True)
        keyboard.add('Отменить❌', reg_button)
        msg = bot.send_message(message.chat.id,
                               'Укажите место доставки: ',
                               reply_markup=keyboard)
                               
        bot.register_next_step_handler(msg, buyCart, cart)


def buyCart(message, cart):
    cid = message.chat.id
    mid = message.message_id

    global allPrice
    allPrice = 0

    d = {}
    desc = ''

    if message.text == 'Отменить❌':
        start_message(message)

    else:
        #вынести в документацию
        location = f'{message.location.latitude},{message.location.longitude}'
        print(location)
        #

        for i in range(len(cart)):
            flowerId = int(cart[i][0])

            cursor.execute(
                f'SELECT name FROM goods WHERE id=\'{flowerId}\'')
            name = str(cursor.fetchone())[2:-3]

            cursor.execute(
                f'SELECT amount FROM basket WHERE id_goods=\'{flowerId}\'')
            amount = str(cursor.fetchone())[1:-2]

            d.update({f'{name}': f'{amount}'})

        print(d)

        for i in d:
            desc += f'{i} - {d.get(i)} шт\n'

        print(desc)

        cursor.execute(f'SELECT full_price FROM basket')
        for i in range(len(cart)):
            fullPrice = int(str(cursor.fetchone())[1:-2])
            allPrice += fullPrice

        prices = [LabeledPrice(label=f'{desc}', amount=f'{allPrice}00')]

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=text)
                       for text in ['Меню📋']])
        bot.send_message(cid, 'Ваш заказ сформирован:', reply_markup=keyboard)

        bot.send_invoice(message.chat.id, title='📦Заказ № ...',
                         description='Все цветы вырощены в наших теплицах и обладают выраженим ароматом🌸👃😋',
                         provider_token=provider_token,
                         currency='uah',
                         is_flexible=False,  # True If you need to set up Shipping Fee
                         prices=prices,
                         start_parameter='Flowers',
                         invoice_payload='Flower Store')


# Кто-то попытался украсть CVV вашей карты...
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Кто-то попытался украсть CVV вашей карты, но мы успешно защитили ваши учетные данные,"
                                                " попробуйте повторить оплату еще раз через несколько минут, нам нужен небольшой отдых.")


# Реакция на успешный платеж
@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
#TODO:
    # try:
    #     cursor.execute(
    #         f'INSERT INTO orders (id_cust, name) VALUES (\'{categoryId}\', \'{newFlower}\')')
    #     db.commit()
    # except:
    #     db.rollback()

    bot.send_message(message.chat.id,
                     '📦Заказ № ... оплачен☺️👍\n' +
                     '\nОн будет у вас в ближайщее время⌚️. В случае ошибки используйте /help\n' +
                     '\n😋Хорошего времени суток😋')


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
        keyboard.add('Назад◀️')
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])
        print('flowerList = ' + str(flowerList))

        msg = bot.send_message(cid, 'Выберете нужную категорию: ',
                               reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    elif message.text == 'Добавить категорию':

        cursor.execute('SELECT COUNT(*) FROM category')
        N = cursor.fetchone()
        N = int(str(N)[1:-2])

        cursor.execute('SELECT name FROM category')
        flowerStr = ''
        for i in range(N):
            flowerStr += str(cursor.fetchone())[2:-3] + '\n'

        bot.send_message(cid, 'Существующие категории: ' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' + flowerStr)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add('◀️Назад')
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
        print('flowerList = ' + str(flowerList))

        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add('◀️Назад')
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])

        msg = bot.send_message(cid, 'Выберете нужную категорию:',
                               reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategory)

    elif message.text == 'Показать отчёт':
        msg = bot.send_message(cid, 'отчёт')
        bot.register_next_step_handler(msg, adminArea)

    elif message.text == 'Выйти из админ панели':
        bot.send_message(cid, 'Вы вышли из админ панели' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n', reply_markup=ReplyKeyboardRemove())
        start_message(message)

    elif message.text == '/start':
        bot.clear_step_handler_by_chat_id(cid)
        start_message(message)

    else:
        bot.send_message(cid, 'Такой команды нет')


# Редактирование товаров
def adminSelectCategoryForEdit(message):
    cid = message.chat.id

    if message.text != '◀️Назад':

        global flowerDictData
        category = message.text

        try:
            cursor.execute(
                f'SELECT id FROM category WHERE name=\'{category}\'')
            categoryId = int(str(cursor.fetchone())[1:-2])
            print('categoryId = ' + str(categoryId))

            cursor.execute(
                f'SELECT COUNT(*) FROM goods WHERE category=\'{categoryId}\'')
            N = int(str(cursor.fetchone())[1:-2])
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

                flowerDictData = flowerDictData.copy()
                print('GLOBAL flowerDictData = ' + str(flowerDictData))

                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + flowerId)
                               for name in ['Редактировать цену', 'Редактировать количество', 'Удалить товар']])
                msg = bot.send_photo(
                    cid, open(f'images/{flowerId}.jpg', 'rb'), caption=name +
                    'В наличие - ' + amount + ' шт' +
                    '1️⃣ шт - ' + price + ' грн💸', reply_markup=keyboard)

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
    keyboard.add('◀️Назад')
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])

    if message.text != '◀️Назад':
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
    keyboard.add('◀️Назад')
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in flowerList])

    if message.text != '◀️Назад':
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

    if message.text != '◀️Назад':
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

    if message.text != '◀️Назад':
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
    newFlower = message.text

    if message.text != 'Отменить❌':

        try:
            cursor.execute(
                f'INSERT INTO goods (category, name) VALUES (\'{categoryId}\', \'{newFlower}\')')
            db.commit()
        except:
            db.rollback()

        msg = bot.send_message(cid, 'Введите количество товара: ')
        bot.register_next_step_handler(msg, adminAddAmount, newFlower)

    else:
        request = f'DELETE FROM goods WHERE name = \'{newFlower}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

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
        request = f'DELETE FROM goods WHERE name = \'{newFlower}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

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
        request = f'DELETE FROM goods WHERE name = \'{newFlower}\''

        try:
            cursor.execute(request)
            db.commit()
        except:
            db.rollback()

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
            flowerID = int(str(cursor.fetchone())[1:-2])
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
            request = f'DELETE FROM goods WHERE name = \'{newFlower}\''

            try:
                cursor.execute(request)
                db.commit()
            except:
                db.rollback()

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
        keyboard.add('◀️Назад')
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])

        msg = bot.send_message(cid, 'Позиция удалена')
        msg = bot.send_message(
            cid, 'Можете выбрать другую категорию:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, adminSelectCategoryForEdit)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
        keyboard.add('◀️Назад')
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in flowerList])

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
        cart(message)

    elif message.text == 'Оформить заказ📦':
        phoheNumber(message, cart)

    else:
        bot.send_message(cid, 'Такой команды нет')


# Реакция на инлайновые кнокпи меню
@ bot.callback_query_handler(func=lambda call: True)
def send_answer(call):
    print('\n' + call.data)

    cid = call.message.chat.id
    mid = call.message.message_id
    global allPrice
    allPrice = 0

    if re.match(r'☝️Добавить в корзину👈', call.data):
        bot.answer_callback_query(
            callback_query_id=call.id, text="Добавленно в корзину", show_alert=False)

        flowerId = call.data.split(':')[1]

        cursor.execute(
            f'SELECT price FROM goods WHERE id=\'{flowerId}\'')
        price = int(str(cursor.fetchone())[1:-2])

        try:
            cursor.execute(
                f'INSERT INTO basket (id_cust, id_goods, amount, full_price) VALUES (\'{cid}\', \'{flowerId}\', \'1\', \'{price}\')')
            db.commit()
        except:
            db.rollback()
            print("err")

        cursor.execute(
            f'SELECT amount FROM basket WHERE id_goods=\'{flowerId}\'')
        amount = int(str(cursor.fetchone())[1:-2])

        fullPrice = amount * price

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(flowerId))
                       for name in ['-', f'{amount} шт.', '+', '❌', f'К оплате - {fullPrice} грн💸']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

        # Редактирование общей оплаты
        try:
            cursor.execute(
                f'SELECT COUNT(*) FROM basket')
            N = int(str(cursor.fetchone())[1:-2])
            print('N = ' + str(N))

            cursor.execute(
                f'SELECT full_price FROM basket')

            for i in range(N):
                fullPrice = int(str(cursor.fetchone())[1:-2])
                allPrice += fullPrice

            bot.edit_message_text(
                f'💸Всего к оплате - {allPrice}  грн💸', cid, msgId)
        except Exception as e:
            print(e)

    elif re.match(r'❌', call.data):
        bot.answer_callback_query(
            callback_query_id=call.id, text="Удаленно из корзины", show_alert=False)

        flowerId = call.data.split(':')[1]

        try:
            cursor.execute(
                f'DELETE FROM basket WHERE id_goods= \'{flowerId}\' AND id_cust = \'{cid}\'')
            db.commit()
        except:
            db.rollback()

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(flowerId))
                       for name in ['☝️Добавить в корзину👈']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

        # Редактирование общей оплаты
        try:
            cursor.execute(
                f'SELECT COUNT(*) FROM basket')
            N = int(str(cursor.fetchone())[1:-2])
            print('N = ' + str(N))

            cursor.execute(
                f'SELECT full_price FROM basket')

            for i in range(N):
                fullPrice = int(str(cursor.fetchone())[1:-2])
                allPrice += fullPrice

            bot.edit_message_text(
                f'💸Всего к оплате - {allPrice}  грн💸', cid, msgId)
        except Exception as e:
            print(e)

    elif re.match(r'\+', call.data):
        flowerId = call.data.split(':')[1]

        cursor.execute(
            f'SELECT amount FROM basket WHERE id_goods=\'{flowerId}\'')
        amount = int(str(cursor.fetchone())[1:-2]) + 1

        cursor.execute(
            f'SELECT price FROM goods WHERE id=\'{flowerId}\'')
        price = int(str(cursor.fetchone())[1:-2])

        fullPrice = amount * price

        try:
            cursor.execute(
                f'UPDATE basket SET amount = \'{amount}\', full_price = \'{fullPrice}\' WHERE id_goods = \'{flowerId}\' AND id_cust = \'{cid}\'')
            db.commit()
        except:
            db.rollback()

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(flowerId))
                       for name in ['-', f'{amount} шт.', '+', '❌', f'К оплате - {fullPrice} грн💸']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)
        print('amount = ' + str(amount))

        # Редактирование общей оплаты
        cursor.execute(
            f'SELECT COUNT(*) FROM basket')
        N = int(str(cursor.fetchone())[1:-2])
        print('N = ' + str(N))

        if N != 0:
            cursor.execute(
                f'SELECT full_price FROM basket')

            for i in range(N):
                fullPrice = int(str(cursor.fetchone())[1:-2])
                allPrice += fullPrice

            bot.edit_message_text(
                f'💸Всего к оплате - {allPrice}  грн💸', cid, msgId)

    elif re.match(r'-', call.data):
        flowerId = call.data.split(':')[1]

        cursor.execute(
            f'SELECT amount FROM basket WHERE id_goods=\'{flowerId}\'')
        amount = int(str(cursor.fetchone())[1:-2])

        cursor.execute(
            f'SELECT price FROM goods WHERE id=\'{flowerId}\'')
        price = int(str(cursor.fetchone())[1:-2])

        if amount > 1:
            amount -= 1

            fullPrice = amount * price

            try:
                cursor.execute(
                    f'UPDATE basket SET amount = \'{amount}\', full_price = \'{fullPrice}\' WHERE id_goods = \'{flowerId}\' AND id_cust = \'{cid}\'')
                db.commit()
            except:
                db.rollback()

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(flowerId))
                           for name in ['-', f'{amount} шт.', '+', '❌', f'К оплате - {fullPrice} грн💸']])
            bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)
            print('amount = ' + str(amount))

            # Редактирование общей оплаты
            try:
                cursor.execute(
                    f'SELECT COUNT(*) FROM basket')
                N = int(str(cursor.fetchone())[1:-2])
                print('N = ' + str(N))

                cursor.execute(
                    f'SELECT full_price FROM basket')

                for i in range(N):
                    fullPrice = int(str(cursor.fetchone())[1:-2])
                    allPrice += fullPrice

                bot.edit_message_text(
                    f'💸Всего к оплате - {allPrice}  грн💸', cid, msgId)
            except Exception as e:
                print(e)

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
    # '😉Ваш букет будет готов в течение пары минут⏳' +
    #                      '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
    #                      '◾️/start - совершить ещё покупку', reply_markup=ReplyKeyboardRemove())
    #     bot.send_message('461861635', 'Заказали букет - ' + name +
    #                      '\nКоличество - ' + count + ' шт' +
    #                      '\n➖➖➖➖➖➖➖➖➖➖' +
    #                      '\nК оплате - ' + str(fPrice) + ' грн💸')

    # elif answ == 'Отменить заказ':
    #     bot.send_message(cid, '📦Ваш заказ успешно отменен!🚮' +
    #                      '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n' +
    #                      '◾️/start - вернуться на главную', reply_markup=ReplyKeyboardRemove())
    # else:
# msg = bot.send_message(cid, 'Такого ответа нет, используйте панель😕')


bot.skip_pending = True
bot.infinity_polling(True)
