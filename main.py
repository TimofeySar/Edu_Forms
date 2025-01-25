#shek


import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from survey_routes import survey_bp

app = Flask(__name__)
app.secret_key = 'sekretniy_kod_shelest_lochen_xoroshy'

app.register_blueprint(survey_bp, url_prefix='/survey')
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # пользоватили
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')

    # опросики
    cursor.execute('''CREATE TABLE IF NOT EXISTS surveys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        user_id INTEGER NOT NULL
                    )''')

    # вопросики
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        survey_id INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        type TEXT NOT NULL,  -- 'text', 'quiz', 'text_with_validation'
                        metadata TEXT,  -- Дополнительные данные в формате JSON
                        FOREIGN KEY (survey_id) REFERENCES surveys(id)
                    )''')
    # ответики пользователей молимся что бы не сработало
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_answers   (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            survey_id INTEGER NOT NULL,  -- ID опроса
                            user_id INTEGER NOT NULL,  -- ID пользователя (если есть авторизация)
                            question_id INTEGER NOT NULL,  -- ID вопроса
                            answer TEXT NOT NULL,  -- Ответ пользователя
                            is_correct BOOLEAN NOT NULL,  -- Правильный ли ответ
                            FOREIGN KEY (survey_id) REFERENCES surveys(id),
                            FOREIGN KEY (question_id) REFERENCES questions(id)
                       )''')
    # ответики для викторины

    conn.commit()
    conn.close()


init_db()


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
    user = session.get('user')
    return render_template('index.html', user=user)


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


# опрос
# @app.route('/create_survey', methods=['GET', 'POST'])
# def create_survey():
#     if not session.get('user_id'):
#         flash("Для создания опроса необходимо войти в систему.", "warning")
#         return redirect(url_for('login'))
#
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()
#
#     if request.method == 'POST':
#         survey_name = request.form.get('survey_name')
#         question_text = request.form.get('question_text')
#         question_type = request.form.get('question_type')
#         quiz_options = request.form.getlist('quiz_options[]')
#
#         if not survey_name:
#             flash("Название опроса не может быть пустым.", "danger")
#             return redirect(url_for('create_survey'))
#
#         if question_text and question_type:
#             # Добавляем новый опрос, если его еще нет
#             cursor.execute("SELECT id FROM surveys WHERE name = ? AND user_id = ?", (survey_name, session['user_id']))
#             survey = cursor.fetchone()
#             if not survey:
#                 cursor.execute("INSERT INTO surveys (name, user_id) VALUES (?, ?)", (survey_name, session['user_id']))
#                 survey_id = cursor.lastrowid
#             else:
#                 survey_id = survey[0]
#
#             # Добавляем вопрос в базу данных
#             cursor.execute("INSERT INTO questions (survey_id, text, type) VALUES (?, ?, ?)",
#                            (survey_id, question_text, question_type))
#             question_id = cursor.lastrowid
#
#             # Если это викторина, добавляем варианты ответа
#             if question_type == 'quiz' and quiz_options:
#                 for option in quiz_options:
#                     cursor.execute("INSERT INTO quiz_options (question_id, text, correct) VALUES (?, ?, ?)",
#                                    (question_id, option, False))  # Пока нет флага "correct"
#
#             conn.commit()
#
#     cursor.execute("""
#         SELECT q.id, q.text, q.type, qo.text AS option_text, qo.correct
#         FROM questions q
#         LEFT JOIN quiz_options qo ON q.id = qo.question_id
#         WHERE q.survey_id = (SELECT id FROM surveys WHERE user_id = ? ORDER BY id DESC LIMIT 1)
#     """, (session['user_id'],))
#     questions_data = cursor.fetchall()
#
#     # Группируем вопросы и их варианты ответов
#     questions = {}
#     for row in questions_data:
#         question_id = row[0]
#         if question_id not in questions:
#             questions[question_id] = {
#                 'id': question_id,
#                 'text': row[1],
#                 'type': row[2],
#                 'options': []
#             }
#         if row[3]:  # Если есть вариант ответа
#             questions[question_id]['options'].append({
#                 'text': row[3],
#                 'correct': row[4]
#             })
#
#     conn.close()
#
#     return render_template('create_survey.html', questions=questions.values())
#
# @app.route('/remove_question/<int:question_id>', methods=['POST'])
# def remove_question(question_id):
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
#     cursor.execute("DELETE FROM quiz_options WHERE question_id = ?", (question_id,))
#     conn.commit()
#     conn.close()
#     flash('Вопрос успешно удалён.', 'success')
#     return redirect(url_for('create_survey'))

if __name__ == '__main__':
    app.run(debug=True)
