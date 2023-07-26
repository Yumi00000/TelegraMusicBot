import os
import subprocess
from ShazamAPI import Shazam
import spotipy
import telebot
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
from telebot import types
import requests
from lyricsgenius import Genius


load_dotenv()
lg_token = os.getenv('LG_TOKEN')
telegram_token = os.getenv('TELEGRAM_TOKEN')
spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
bot = telebot.TeleBot(telegram_token)
genius = Genius(lg_token)
spotify_credentials = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)
current_index = 0
query = ''
tracks = []
button_next = types.InlineKeyboardButton('Next', callback_data='next')
button_previous = types.InlineKeyboardButton('Previous', callback_data='previous')
button_lyrics = types.InlineKeyboardButton('Lyrics', callback_data='lyrics')
keyboard = types.InlineKeyboardMarkup()
keyboard.row(button_previous, button_next)
keyboard.add(button_lyrics)
keyboard_lyrics = types.InlineKeyboardMarkup()
back_button = types.InlineKeyboardButton('Back', callback_data='back')
keyboard_lyrics.row(back_button)


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
                     "Hi! I'm Hitori! Your personal music finder. "
                     "Give me a song name, and I'll find it for you.")


@bot.message_handler(func=lambda message: True, content_types=['text', 'voice'])
def handle_message(message):
    global current_index, query, tracks
    query = message.text
    current_index = 0
    try:
        query_v = bot.get_file(message.voice.file_id)
        path = query_v.file_path
        qname = os.path.basename(path)
        getting_file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(telegram_token, query_v.file_path))
        with open(qname, 'wb') as f:
            f.write(getting_file.content)
            directory = os.path.join(os.getcwd(), qname)
        subprocess.run(["ffmpeg", "-i", qname, "-ar", "44100", "-ac", "2", "-b:a", "192k", "{}.mp3".format(directory)])
        os.remove(qname)
        for song in os.listdir():
            if song.endswith('.mp3'):
                shazam = Shazam(open(song, 'rb').read())
                recognize_generator = shazam.recognizeSong()
                os.remove(song)
                find_sh = next(recognize_generator)
                try:
                    query = find_sh[1].get('track').get('title')
                except AttributeError:
                    pass
        if query is None:
            bot.send_message(message.chat.id, "No tracks found.")
            return
    except TypeError:
        pass
    tracks = search_track(query)
    if not tracks:
        bot.send_message(message.chat.id, "No tracks found.")
        return
    track_info = get_track_info(tracks[current_index])
    bot.send_message(message.chat.id, track_info, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global current_index, query, tracks
    try:
        if call.data == 'next' or call.data == 'previous':
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
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=track_info, reply_markup=keyboard)
        elif call.data == 'lyrics':
            try:
                info = search_track(query)[current_index]
                name = info['name']
                artist = info[current_index]['artists'][0]['name']
                find_song = genius.search_song(f"{name} {artist}")
                if find_song is None:
                    bot.answer_callback_query(call.id, 'Lyrics not found')
                else:
                    lyrics = find_song.lyrics
                    if len(lyrics) <= 4090:
                        bot.send_message(call.message.chat.id, lyrics, reply_markup=keyboard_lyrics)
                    else:
                        bot.answer_callback_query(call.id, 'Lyrics too long')
            except KeyError:
                current_index += 1
        if call.data == 'back'and call.message:
            bot.delete_message(call.message.chat.id, call.message.message_id)
    except spotipy.exceptions.SpotifyException:
        bot.delete_message(call.message.chat.id, call.message.message_id)


bot.polling()
