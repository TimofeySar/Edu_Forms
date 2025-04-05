from datetime import datetime, timezone
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import json
from contextlib import closing

survey_bp = Blueprint('survey', __name__)


def get_db():
    """Возвращает соединение с базой данных."""

    return sqlite3.connect('database.db')


def shorten_url(long_url):
    """Создает короткую ссылку через TinyURL."""
    api_url = f"https://tinyurl.com/api-create.php?url={long_url}"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Ошибка при сокращении ссылки: {e}")
        return long_url


@survey_bp.route('/survey_created/<int:survey_id>')
def survey_created(survey_id):
    long_link = url_for('survey.take_survey', survey_id=survey_id, _external=True)
    short_link = shorten_url(long_link)
    return render_template('survey_created.html', survey_link=short_link, survey_id=survey_id)


@survey_bp.route('/create_survey', methods=['GET', 'POST'])
def create_survey():
    if request.method == 'POST':
        print("POST-запрос получен!")  # Для отладки

        survey_title = request.form.get('survey_title')
        survey_description = request.form.get('survey_description', '')
        show_correct_answers = 1 if request.form.get('show_correct_answers') == 'on' else 0  # Чекбокс
        user_id = session.get('user_id')

        if not user_id:
            flash('Пожалуйста, войдите в систему для создания опроса.', 'danger')
            return redirect(url_for('login'))

        if not survey_title:
            flash('Название опроса не может быть пустым.', 'danger')
            return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)

        questions = []
        i = 0
        while f'question_{i}' in request.form:
            question_text = request.form.get(f'question_{i}')
            answer_type = request.form.get(f'answer_type_{i}')

            if not question_text or not answer_type:
                flash('Все вопросы должны быть заполнены.', 'danger')
                return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)

            metadata = {}
            if answer_type == 'text':
                pass
            elif answer_type == 'quiz':
                options = [
                    request.form.get(f'quiz_answer_{i}_1'),
                    request.form.get(f'quiz_answer_{i}_2'),
                    request.form.get(f'quiz_answer_{i}_3'),
                    request.form.get(f'quiz_answer_{i}_4')
                ]
                metadata = {
                    'options': [opt for opt in options if opt],
                    'correct_answer': int(request.form.get(f'correct_answer_{i}', -1))
                }
                if not metadata['options']:
                    flash('Необходимо указать хотя бы один вариант ответа для викторины.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)
                if len(metadata['options']) < 2:
                    flash('Викторина должна содержать хотя бы два варианта ответа.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)
                if metadata['correct_answer'] == -1 or metadata['correct_answer'] > len(metadata['options']):
                    flash('Необходимо выбрать правильный ответ для викторины.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)
            elif answer_type == 'quiz_no_correct':
                options = [
                    request.form.get(f'quiz_answer_{i}_1'),
                    request.form.get(f'quiz_answer_{i}_2'),
                    request.form.get(f'quiz_answer_{i}_3'),
                    request.form.get(f'quiz_answer_{i}_4')
                ]
                metadata = {
                    'options': [opt for opt in options if opt]
                }
                if not metadata['options']:
                    flash('Необходимо указать хотя бы один вариант ответа для викторины.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)
                if len(metadata['options']) < 2:
                    flash('Викторина должна содержать хотя бы два варианта ответа.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)
            elif answer_type == 'text_with_validation':
                correct_answers = [
                    request.form.get(f'text_validation_answer_{i}_1'),
                    request.form.get(f'text_validation_answer_{i}_2')
                ]
                metadata = {
                    'correct_answers': [ans for ans in correct_answers if ans]
                }
                if not metadata['correct_answers']:
                    flash('Необходимо указать хотя бы один правильный ответ для текстового вопроса с проверкой.', 'danger')
                    return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)

            questions.append({
                'question_text': question_text,
                'answer_type': answer_type,
                'metadata': metadata
            })
            i += 1

        if not questions:
            flash('Опрос должен содержать хотя бы один вопрос.', 'danger')
            return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)

        try:
            with closing(get_db()) as conn:
                cursor = conn.cursor()

                cursor.execute('INSERT INTO surveys (name, description, user_id, show_correct_answers) VALUES (?, ?, ?, ?)',
                              (survey_title, survey_description, user_id, show_correct_answers))
                survey_id = cursor.lastrowid

                for question in questions:
                    cursor.execute('''
                        INSERT INTO questions (survey_id, text, type, metadata)
                        VALUES (?, ?, ?, ?)
                    ''', (survey_id, question['question_text'], question['answer_type'], json.dumps(question['metadata'])))

                conn.commit()
                flash('Опрос успешно создан!', 'success')
                return redirect(url_for('survey.survey_created', survey_id=survey_id))

        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            flash('Произошла ошибка при создании опроса.', 'danger')
            return render_template('create_survey.html', survey_title=survey_title, survey_description=survey_description, show_correct_answers=show_correct_answers)

    return render_template('create_survey.html', survey_title='', survey_description='', show_correct_answers=0)



@survey_bp.route('/take/<int:survey_id>', methods=['GET', 'POST'])
def take_survey(survey_id):
    with closing(get_db()) as conn:
        cursor = conn.cursor()

        # Получаем информацию об опросе
        cursor.execute('SELECT name, description FROM surveys WHERE id = ?', (survey_id,))
        survey = cursor.fetchone()
        if not survey:
            flash('Опрос не найден.', 'danger')
            return redirect(url_for('index'))

        survey_name, survey_description = survey

        # Получаем вопросы
        cursor.execute('SELECT id, text, type, metadata FROM questions WHERE survey_id = ?', (survey_id,))
        questions_data = cursor.fetchall()

        questions = []
        for q_id, q_text, q_type, q_metadata in questions_data:
            questions.append({
                'id': q_id,
                'text': q_text,
                'type': q_type,
                'metadata': json.loads(q_metadata) if q_metadata else {}
            })

        if request.method == 'POST':
            # Получаем IP-адрес и User-Agent
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')

            # Вычисляем время прохождения
            start_time_str = request.form.get('start_time')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.now(timezone.utc)
                time_taken = int((end_time - start_time).total_seconds())
            else:
                time_taken = 0

            # Сохранение ответов пользователя
            for question in questions:
                question_id = question['id']
                answer = request.form.get(f'answer_{question_id}')

                if answer:
                    is_correct = None  # По умолчанию None, если вопрос не тестовый
                    if question['type'] == 'quiz':
                        correct_answer_idx = question['metadata']['correct_answer'] - 1
                        is_correct = int(answer) == correct_answer_idx
                    elif question['type'] == 'text_with_validation':
                        correct_answers = [ans.lower() for ans in question['metadata']['correct_answers'] if ans]
                        is_correct = answer.lower() in correct_answers
                    # Для quiz_no_correct и text is_correct остается None

                    cursor.execute('''
                        INSERT INTO user_answers (survey_id, user_id, question_id, answer, is_correct, question_type, ip_address, user_agent, time_taken)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (survey_id, session.get('user_id', 0), question_id, answer, is_correct, question['type'], ip_address, user_agent, time_taken))

            conn.commit()
            return redirect(url_for('survey.survey_results', survey_id=survey_id))

        # Передаем survey_id в шаблон
        return render_template('take_survey.html', survey_name=survey_name, survey_description=survey_description,
                              questions=questions, survey_id=survey_id)


@survey_bp.route('/results/<int:survey_id>', methods=['GET'])
def survey_results(survey_id):
    with closing(get_db()) as conn:
        cursor = conn.cursor()

        # Получаем информацию об опросе
        cursor.execute('SELECT name FROM surveys WHERE id = ?', (survey_id,))
        survey = cursor.fetchone()
        if not survey:
            flash('Опрос не найден.', 'danger')
            return redirect(url_for('index'))
        survey_name = survey[0]

        # Получаем вопросы
        cursor.execute('SELECT id, text, type, metadata FROM questions WHERE survey_id = ?', (survey_id,))
        questions_data = cursor.fetchall()

        questions = []
        for q_id, q_text, q_type, q_metadata in questions_data:
            questions.append({
                'id': q_id,
                'text': q_text,
                'type': q_type,
                'metadata': json.loads(q_metadata) if q_metadata else {}
            })

        # Получаем ответы пользователя
        user_id = session.get('user_id', 0)
        cursor.execute('SELECT question_id, answer, is_correct FROM user_answers WHERE survey_id = ? AND user_id = ?',
                       (survey_id, user_id))
        user_answers = cursor.fetchall()

        # Формируем результаты
        results = []
        has_test_questions = False
        all_correct = True

        for question in questions:
            # Ищем ответ пользователя на этот вопрос
            user_answer = next((ans for ans in user_answers if ans[0] == question['id']), None)
            if not user_answer:
                continue  # Если ответа нет, пропускаем

            question_id, answer, is_correct = user_answer
            result = {
                'text': question['text'],
                'type': question['type'],
                'answer': answer,
                'is_correct': is_correct,
                'answer_text': answer,  # По умолчанию это сам ответ
                'correct_answer': None
            }

            # Если это тестовый вопрос, добавляем информацию о правильном ответе
            if question['type'] == 'quiz':
                has_test_questions = True
                correct_idx = question['metadata']['correct_answer'] - 1
                result['answer_text'] = question['metadata']['options'][int(answer)]  # Текст выбранного ответа
                result['correct_answer'] = question['metadata']['options'][correct_idx]  # Текст правильного ответа
                if not is_correct:
                    all_correct = False
            elif question['type'] == 'text_with_validation':
                has_test_questions = True
                result['correct_answer'] = question['metadata']['correct_answers']  # Список правильных ответов
                if not is_correct:
                    all_correct = False
            elif question['type'] == 'quiz_no_correct':
                result['answer_text'] = question['metadata']['options'][int(answer)]  # Текст выбранного ответа

            results.append(result)

    # Передаем данные в шаблон
    return render_template('survey_results.html', survey_name=survey_name, results=results,
                           has_test_questions=has_test_questions, all_correct=all_correct)


# survey_routes.py (добавляем новый маршрут)
@survey_bp.route('/<int:survey_id>', methods=['GET'])
def view_survey(survey_id):
    with closing(get_db()) as conn:
        cursor = conn.cursor()

        # Получаем информацию об опросе
        cursor.execute('SELECT name, description, user_id FROM surveys WHERE id = ?', (survey_id,))
        survey = cursor.fetchone()
        if not survey:
            flash('Опрос не найден.', 'danger')
            return redirect(url_for('index'))

        survey_name, survey_description, survey_user_id = survey

        # Проверяем, принадлежит ли опрос текущему пользователю
        user_id = session.get('user_id')
        if not user_id or user_id != survey_user_id:
            flash('У вас нет доступа к этому опросу.', 'danger')
            return redirect(url_for('index'))

        # Получаем вопросы
        cursor.execute('SELECT id, text, type, metadata FROM questions WHERE survey_id = ?', (survey_id,))
        questions_data = cursor.fetchall()

        questions = []
        for q_id, q_text, q_type, q_metadata in questions_data:
            questions.append({
                'id': q_id,
                'text': q_text,
                'type': q_type,
                'metadata': json.loads(q_metadata) if q_metadata else {}
            })

        # Генерируем ссылку на опрос
        long_link = url_for('survey.take_survey', survey_id=survey_id, _external=True)
        short_link = shorten_url(long_link)

        return render_template('view_survey.html', survey_name=survey_name, survey_description=survey_description,
                              questions=questions, survey_id=survey_id, survey_link=short_link)