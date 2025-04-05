#shek
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from survey_routes import survey_bp
from contextlib import closing

app = Flask(__name__)
app.secret_key = 'sekretniy_kod_shelest_lochen_xoroshy'

app.register_blueprint(survey_bp, url_prefix='/survey')


def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Пользователи
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')

    # Опросы
    cursor.execute('''CREATE TABLE IF NOT EXISTS surveys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id INTEGER NOT NULL,
                        show_correct_answers BOOLEAN DEFAULT 0
                    )''')

    # Проверяем, есть ли поле show_correct_answers в таблице surveys
    cursor.execute("PRAGMA table_info(surveys)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'show_correct_answers' not in columns:
        cursor.execute('ALTER TABLE surveys ADD COLUMN show_correct_answers BOOLEAN DEFAULT 0')

    # Вопросы
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        survey_id INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        type TEXT NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (survey_id) REFERENCES surveys(id)
                    )''')

    # Ответы пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_answers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        survey_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        question_id INTEGER NOT NULL,
                        answer TEXT NOT NULL,
                        is_correct BOOLEAN,
                        question_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT,
                        time_taken INTEGER,
                        FOREIGN KEY (survey_id) REFERENCES surveys(id),
                        FOREIGN KEY (question_id) REFERENCES questions(id)
                    )''')

    # Проверяем, есть ли новые поля в таблице user_answers
    cursor.execute("PRAGMA table_info(user_answers)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'ip_address' not in columns:
        cursor.execute('ALTER TABLE user_answers ADD COLUMN ip_address TEXT')
    if 'user_agent' not in columns:
        cursor.execute('ALTER TABLE user_answers ADD COLUMN user_agent TEXT')
    if 'time_taken' not in columns:
        cursor.execute('ALTER TABLE user_answers ADD COLUMN time_taken INTEGER')
    if 'created_at' not in columns:
        cursor.execute('ALTER TABLE user_answers ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    if 'question_type' not in columns:
        cursor.execute('ALTER TABLE user_answers ADD COLUMN question_type TEXT')

    conn.commit()
    conn.close()


init_db()


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

    if user_id:  # Если пользователь авторизован
        try:
            with closing(get_db()) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, description FROM surveys WHERE user_id = ?', (user_id,))
                surveys = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            flash('Произошла ошибка при загрузке опросов.', 'danger')

    theme = session.get('theme', 'light')  # Предполагаем, что у тебя есть поддержка тем
    return render_template('index.html', theme=theme, surveys=surveys)


# Авторизация
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
        print(hashed_password)

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


if __name__ == '__main__':
    app.run(debug=True)
