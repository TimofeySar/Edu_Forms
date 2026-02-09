#shek
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from survey_routes import survey_bp
from contextlib import closing
import os
import threading
import requests
import time
app = Flask(__name__)
app.secret_key = 'sekretniy_kod_shelest_ochen_xoroshy'

app.register_blueprint(survey_bp, url_prefix='/survey')

def ping_self():
    while True:
        try:
            requests.get("https://your-render-app.onrender.com")
        except Exception as e:
            print("Ping failed:", e)
        time.sleep(300)  # Пинг каждые 5 минут


def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.context_processor
def inject_theme():
    theme = session.get('theme', 'light')
    return {'theme': theme}


@app.route('/toggle_theme', methods=['POST'])
def toggle_theme():
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    return redirect(request.referrer or url_for('index'))


@app.route('/')
def index():
    user_id = session.get('user_id')
    surveys = []

    if user_id:
        try:
            with closing(get_db()) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, description FROM surveys WHERE user_id = ?', (user_id,))
                surveys = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            flash('Произошла ошибка при загрузке опросов.', 'danger')

    theme = session.get('theme', 'light')
    return render_template('index.html', theme=theme, surveys=surveys)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            user_id, username, hashed_password = user
            if check_password_hash(hashed_password, password):
                session['user_id'] = user_id
                session['username'] = username
                flash('Вы успешно вошли в систему!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный пароль.', 'danger')
        else:
            flash('Пользователь с таким email не найден.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                           (username, email, hashed_password))
            conn.commit()
            conn.close()
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Имя пользователя или email уже заняты.', 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('_flashes', None)
    session.pop('user_id', None)
    session.pop('user', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


def file_exists(filepath):
    return os.path.exists(os.path.join('static', 'graphs', filepath))


app.jinja_env.filters['file_exists'] = file_exists

if __name__ == '__main__':
    threading.Thread(target=ping_self, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
