from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import json
from contextlib import closing


survey_bp = Blueprint('survey', __name__)

def get_db():
    """Возвращает соединение с базой данных."""

    return sqlite3.connect('database.db')

@survey_bp.route('/create_survey', methods=['GET', 'POST'])
def create_survey():
    if request.method == 'POST':
        print("POST-запрос получен!")  # Для отладки

        survey_title = request.form.get('survey_title')
        survey_description = request.form.get('survey_description', '')
        user_id = session.get('user_id')

        if not user_id:
            flash('Пожалуйста, войдите в систему для создания опроса.', 'danger')
            return redirect(url_for('login'))

        if not survey_title:
            flash('Название опроса не может быть пустым.', 'danger')
            return redirect(url_for('survey.create_survey'))

        questions = []
        i = 0
        while f'question_{i}' in request.form:
            question_text = request.form.get(f'question_{i}')
            answer_type = request.form.get(f'answer_type_{i}')

            if not question_text or not answer_type:
                flash('Все вопросы должны быть заполнены.', 'danger')
                return redirect(url_for('survey.create_survey'))

            metadata = {}
            if answer_type == 'text':
                pass
            elif answer_type == 'quiz':
                metadata = {
                    'options': [
                        request.form.get(f'quiz_answer_{i}_1'),
                        request.form.get(f'quiz_answer_{i}_2'),
                        request.form.get(f'quiz_answer_{i}_3'),
                        request.form.get(f'quiz_answer_{i}_4')
                    ],
                    'correct_answer': int(request.form.get(f'correct_answer_{i}'))
                }
            elif answer_type == 'text_with_validation':
                metadata = {
                    'correct_answers': [
                        request.form.get(f'text_validation_answer_{i}_1'),
                        request.form.get(f'text_validation_answer_{i}_2')
                    ]
                }

            questions.append({
                'question_text': question_text,
                'answer_type': answer_type,
                'metadata': metadata
            })
            i += 1

        if not questions:
            flash('Опрос должен содержать хотя бы один вопрос.', 'danger')
            return redirect(url_for('survey.create_survey'))

        try:
            with closing(get_db()) as conn:
                cursor = conn.cursor()

                cursor.execute('INSERT INTO surveys (name, description, user_id) VALUES (?, ?, ?)',
                              (survey_title, survey_description, user_id))
                survey_id = cursor.lastrowid

                for question in questions:
                    cursor.execute('''
                        INSERT INTO questions (survey_id, text, type, metadata)
                        VALUES (?, ?, ?, ?)
                    ''', (survey_id, question['question_text'], question['answer_type'], json.dumps(question['metadata'])))

                conn.commit()
                flash('Опрос успешно создан!', 'success')
                return redirect(url_for('index'))  # Перенаправляем на главную страницу

        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            flash('Произошла ошибка при создании опроса.', 'danger')
            return redirect(url_for('survey.create_survey'))

    return render_template('create_survey.html')