from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/event_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    event = db.relationship('Event', backref=db.backref('registrations', lazy='dynamic'))
    student = db.relationship('User')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('home_page'))
@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        student_name = request.form['student_name']
        roll_number = request.form['roll_number']
        branch = request.form['branch']
        year = request.form['year']
        section = request.form['section']

        new_registration = Registration(
            student_name=student_name,
            roll_number=roll_number,
            branch=branch,
            year=year,
            section=section,
            event_id=event.id,
            student_id=current_user.id
        )
        db.session.add(new_registration)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register_event.html', event=event)

@app.route('/registrations/<int:event_id>')
@login_required
def view_registrations(event_id):
    if current_user.role != 'organizer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        flash('You can only view registrations for your events.', 'danger')
        return redirect(url_for('dashboard'))

    registrations = event.registrations.all()
    return render_template('view_registrations.html', event=event, registrations=registrations)

@app.route('/home')
def home_page():
    return render_template('home.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please login.', 'danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role == 'organizer':
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            date = request.form['date']
            location = request.form['location']
            image = request.files.get('image')
            image_filename = None
            if image and image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
            new_event = Event(title=title, description=description, date=date,
                              location=location, organizer_id=current_user.id,
                              image_filename=image_filename)
            db.session.add(new_event)
            db.session.commit()
            flash('Event uploaded successfully!', 'success')
        events = Event.query.filter_by(organizer_id=current_user.id).all()
        return render_template('organizer_dashboard.html', user=current_user, events=events)
    else:
        events = Event.query.all()
        return render_template('student_dashboard.html', user=current_user, events=events)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
