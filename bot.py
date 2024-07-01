import logging
import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

GENDER, AGE, HOBBY, LOCATION, PHOTO, DESCRIPTION, MATCHING = range(7)

def start(update, context):
    user_id = update.message.from_user.id
    if user_already_registered(user_id):
        update.message.reply_text("Selamat datang kembali! Anda sudah terdaftar.")
    else:
        reply_keyboard = [[KeyboardButton('Pria'), KeyboardButton('Wanita')]]
        update.message.reply_text(
            'Halo! Silakan pilih jenis kelamin Anda.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return GENDER

def gender(update, context):
    user_id = update.message.from_user.id
    context.user_data['gender'] = update.message.text
    update.message.reply_text('Berapa usia Anda?')
    return AGE

def age(update, context):
    user_id = update.message.from_user.id
    context.user_data['age'] = update.message.text
    update.message.reply_text('Apa hobi Anda?')
    return HOBBY

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

def hobby(update, context):
    user_id = update.message.from_user.id
    context.user_data['hobby'] = update.message.text
    update.message.reply_text('Dimana lokasi Anda? Kirimkan lokasi Anda saat ini, silakan.')
    return LOCATION

def location(update, context):
    user_id = update.message.from_user.id
    location = update.message.location
    context.user_data['location'] = (location.latitude, location.longitude)
    update.message.reply_text('Terima kasih! Silakan unggah foto profil Anda sekarang.')
    return PHOTO

def photo(update, context):
    user_id = update.message.from_user.id
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('profile_photos/{}.jpg'.format(user_id))
    update.message.reply_text('Foto profil Anda telah diunggah. Silakan tambahkan deskripsi profil Anda sekarang.')
    return DESCRIPTION

def description(update, context):
    user_id = update.message.from_user.id
    context.user_data['description'] = update.message.text
    update.message.reply_text('Deskripsi profil Anda telah ditambahkan. Profil Anda telah disimpan.')
    update.message.reply_text('Mulai mencari pasangan?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def start_matching(update, context):
    user_id = update.message.from_user.id
    reply_keyboard = [[KeyboardButton('Suka'), KeyboardButton('Tidak Suka')]]
    update.message.reply_text(
        'Saya telah menemukan pasangan potensial untuk Anda. Apakah Anda tertarik?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return MATCHING

def choose_matching(update, context):
    user_id = update.message.from_user.id
    choice = update.message.text
    
    if choice == 'Suka':
        update.message.reply_text('Anda menyukai pasangan ini! Selamat!')
    else:
        update.message.reply_text('Anda tidak tertarik dengan pasangan ini. Coba yang lain ya!')
    
    update.message.reply_text('Apakah Anda ingin mencari pasangan lagi?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def cancel(update, context):
    user_id = update.message.from_user.id
    update.message.reply_text('Proses dibatalkan. Sampai jumpa!')
    return ConversationHandler.END

def user_already_registered(user_id):
    pass

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    updater = Updater(token='7245663010:AAEjpf2nLUcelttirNc1aanZi62Z2Ae4_PE', use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(Filters.text & ~Filters.command, gender)],
            AGE: [MessageHandler(Filters.text & ~Filters.command, age)],
            HOBBY: [MessageHandler(Filters.text & ~Filters.command, hobby)],
            LOCATION: [MessageHandler(Filters.location, location)],
            PHOTO: [MessageHandler(Filters.photo, photo)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, description)],
            MATCHING: [
                MessageHandler(Filters.text & ~Filters.command, start_matching),
                MessageHandler(Filters.text & ~Filters.command, choose_matching)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conversation_handler)
    
    updater.start_polling()
    updater.idle()
