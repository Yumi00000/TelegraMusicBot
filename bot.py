import os

import lyricsgenius
import spotipy
import telebot
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
from telebot import types

load_dotenv()
lg_token = os.getenv('LG_TOKEN')
telegram_token = os.getenv('TELEGRAM_TOKEN')
spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
genius = lyricsgenius.Genius(lg_token)
bot = telebot.TeleBot(telegram_token)
spotify_credentials = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)

current_index = 0
query = ''
button_next = types.InlineKeyboardButton('Next', callback_data='next')
button_previous = types.InlineKeyboardButton('Previous', callback_data='previous')
keyboard = types.InlineKeyboardMarkup()
keyboard.row(button_previous, button_next)


def get_track_info(track):
    track_name = track['name']
    artist_name = track['artists'][0]['name']
    song_page = track['external_urls']['spotify']
    response = f"Track: {track_name}\nArtist: {artist_name}\n{song_page}"
    return response


def search_track(query):
    search_results = spotify.search(query, type='track')
    if len(search_results['tracks']['items']) == 0:
        return None
    return search_results['tracks']['items']


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Hi! I'm Hitori! Your personal music finder. Give me a song name, and I'll find it for you.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global current_index, query
    query = message.text
    if query:
        current_index = 0
        if query == "":
            bot.send_message(message.chat.id, "Give me a song name")
            return
        tracks = search_track(query)
        if not tracks:
            bot.send_message(message.chat.id, "No tracks found.")
            return
        track_info = get_track_info(tracks[current_index])
        bot.send_message(message.chat.id, track_info, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global current_index, query
    tracks = search_track(query)
    if call.data == 'next':
        current_index += 1
        if current_index >= len(tracks):
            current_index = len(tracks) - 1
            bot.answer_callback_query(call.id, text='No more tracks available.')
            return
    elif call.data == 'previous':
        current_index -= 1
        if current_index < 0:
            current_index = 0
            bot.answer_callback_query(call.id, text='No previous tracks available.')
            return

    track_info = get_track_info(tracks[current_index])
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=track_info,
                          reply_markup=keyboard)


bot.polling()