import telebot
from telebot import types
import mysql.connector
from telebot.types import ReplyKeyboardRemove

bot = telebot.TeleBot('1505203267:AAGNOvojdLur7H7-Lowxtjg5aSoWtLfg92E')

# Подключение к бд
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="789456",
    database="flowers",
)
cursor = db.cursor()


class User:
    def __init__(self, Id, first, last, username, message):
        self.Id = Id
        self.first = first
        self.last = last
        self.username = username

    def getId(self):
        return self.Id


# Сбор инфы
        # body = '{message}\n' \
        #    '--\n' \
        #    '{first}, {last}\n' \
        #    '{username}, {id}'.format(message=message.text, first=message.from_user.first_name,
        #                              last=message.from_user.last_name, username=message.from_user.username,
        #                              id=message.chat.id)

# Реакция на /start


@bot.message_handler(commands=['start'])
def start_message(message):
    cid = message.chat.id

    user = User(cid, message.from_user.first_name,
                message.from_user.last_name, message.from_user.username, message)
    print(user.Id)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                   for name in ['Роза🌹', 'Хризантема🌸', 'Тюльпан🌷']])
    bot.send_message(
        cid, 'Здравствуйте, выберите из каких цветов будет состоять ваш букет💐', reply_markup=keyboard)


# Реакция на текст
@bot.message_handler(content_types=['text'])
def send_text(message):

    cid = message.chat.id

    bot.send_message(
        cid, 'К сожалению, я не понимаю человеческий. Используйте панель команд :)', reply_markup=ReplyKeyboardRemove())

    user = User(cid, message.from_user.first_name,
                message.from_user.last_name, message.from_user.username, message)
    print(user.Id)


@bot.callback_query_handler(func=lambda call: True)
def send_answer(call):
    print(call.data)

    cid = call.message.chat.id
    mid = call.message.message_id

    def get_price(request):

        cursor.execute(request)

        result = cursor.fetchone()
        return int(str(result)[1:-2])

    def func(name):
        price = get_price(
            'SELECT oneprice FROM flower WHERE name IN (\'' + name[:-1] + '\')')
        bot.send_message(cid, 'Выбраный товар: ' + call.data +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n1 ' + name + ' - ' + str(price) + ' грн💸' +
                         '\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n◾️/start - вернуться на главную')

        # keyboard = types.ReplyKeyboardMarkup(1, 1, row_width=1, selective=0)
        # keyboard.add(*[types.KeyboardButton(text=str(i+1))
        #                for i in range(100)])
        msg = bot.send_message(cid, 'Введите нужное количество:')
        bot.register_next_step_handler(msg, buyFlower, price, name)

    if call.data == 'Выполнено':
        # if userId == '461861635':
        bot.send_message(cid, 'Ваш букет готов☺️👍' +
                         '\nЗаберите его, пожалуйста, в ближайщее время⌚️' +
                         '\n😋Хорошего времени суток😋')

    elif call.data == 'Роза🌹':
        bot.delete_message(cid, mid)
        bot.send_photo(cid, photo=open("images/rose.jpg", 'rb'))
        func(call.data)

    elif call.data == 'Хризантема🌸':
        bot.delete_message(cid, mid)
        bot.send_photo(cid, photo=open("images/chrys.jpg", 'rb'))
        func(call.data)

    elif call.data == 'Тюльпан🌷':
        bot.delete_message(cid, mid)
        bot.send_photo(cid, photo=open('images/tulip.jpg', 'rb'))
        func(call.data)

    else:
        bot.send_message(cid, 'Такой команды не существует :(')


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
