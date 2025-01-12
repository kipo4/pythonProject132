from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Настройка базы данных H2
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'  # Заменить на H2 при необходимости
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модель для пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "employee" или "manager"

# Модель для задачи
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.DateTime, nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default="pending")

# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role == "manager":
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter((Task.assigned_to == user.id) | (Task.assigned_to == None)).all()

    return render_template('index.html', user=user, tasks=tasks)


# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))

        return "Неверные данные для входа"

    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Создание задачи (только для менеджера)
@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != "manager":
        return render_template('403.html'), 403

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')

        new_task = Task(title=title, description=description, deadline=deadline)
        db.session.add(new_task)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('create_task.html')

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    print(f"Attempting to delete task with id: {task_id}")
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != "manager":
        return "Доступ запрещен. Только начальник может удалять задачи.", 403

    task = Task.query.get(task_id)
    if task:
        db.session.delete(task)
        db.session.commit()
        print(f"Task {task_id} deleted successfully.")
    else:
        print(f"Task {task_id} not found.")

    return redirect(url_for('index'))


# Взять задачу (для сотрудников)
@app.route('/take_task/<int:task_id>')
def take_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task = Task.query.get(task_id)
    task.assigned_to = session['user_id']
    db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# HTML Templates:

# index.html
"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #121212;
            color: white;
        }
        .task-card {
            background-color: #2c2c2c;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .task-card.assigned {
            border-left: 5px solid green;
        }
        .task-card.unassigned {
            border-left: 5px solid gray;
        }
    </style>
</head>
<body>
    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center">
            <h1>Добро пожаловать, {{ user.username }}</h1>
            <a href="/logout" class="btn btn-danger">Выйти</a>
        </div>

        {% if user.role == 'manager' %}
        <div class="mt-3">
            <a href="/create_task" class="btn btn-primary">Создать задачу</a>
        </div>
        {% endif %}

        <div class="mt-4">
            <h3>Все задачи</h3>
            {% for task in tasks %}
            <div class="task-card {% if task.assigned_to %}assigned{% else %}unassigned{% endif %}">
                <h5>{{ task.title }}</h5>
                <p>Описание: {{ task.description }}</p>
                <p>Дедлайн: {{ task.deadline.strftime('%Y-%m-%d %H:%M') }}</p>
                {% if task.assigned_to %}
                    <p>Сотрудник: {{ task.assigned_to }}</p>
                {% else %}
                    <p>Задача не назначена</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""
