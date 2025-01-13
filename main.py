import app as app
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "employee" or "manager"

# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.DateTime, nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Home page
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        return "User not found. Please log in again.", 404

    tasks = Task.query.all() if user.role == "manager" else Task.query.filter(
        (Task.assigned_to == user.id) | (Task.assigned_to == None)).all()

    now = datetime.now()
    assigned_users = {u.id: u.username for u in User.query.all()}

    return render_template('index.html', user=user, tasks=tasks, now=now, assigned_users=assigned_users)

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        # Логирование данных формы
        app.logger.info(f"Form Data: {request.form}")

        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        # Проверка и обработка данных
        if not username or not password or not role:
            error_message = "All fields are required."
        elif len(password) < 6:
            error_message = "Password must be at least 6 characters long."
        elif User.query.filter_by(username=username).first():
            error_message = "Username already exists."
        else:
            # Создание пользователя
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))

    return render_template('register.html', error_message=error_message)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            error_message = "Both fields are required."
        else:
            user = User.query.filter_by(username=username, password=password).first()
            if user:
                session['user_id'] = user.id
                return redirect(url_for('index'))
            error_message = "Invalid login credentials."

    return render_template('login.html', error_message=error_message)

# User logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Create task (for managers only)
@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != "manager":
        return render_template('403.html'), 403

    error_message = None
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline = request.form.get('deadline')

        if not title or not deadline:
            error_message = "Title and deadline are required."
        else:
            try:
                deadline = datetime.strptime(deadline, '%Y-%m-%dT%H:%M')
                new_task = Task(title=title, description=description, deadline=deadline)
                db.session.add(new_task)
                db.session.commit()
                return redirect(url_for('index'))
            except ValueError:
                error_message = "Invalid date/time format."

    return render_template('create_task.html', error_message=error_message)

# Delete task (for managers only)
@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != "manager":
        return "Access denied. Only managers can delete tasks.", 403

    task = Task.query.get(task_id)
    if task:
        db.session.delete(task)
        db.session.commit()

    return redirect(url_for('index'))

# Take task (for employees only)
@app.route('/take_task/<int:task_id>')
def take_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task = Task.query.get(task_id)
    if task:
        task.assigned_to = session['user_id']
        db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
