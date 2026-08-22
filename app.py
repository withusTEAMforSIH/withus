import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Doctor, Plan, Appointment, Payment
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        age = request.form.get('age')
        gender = request.form.get('gender', 'other')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.')
            return redirect(url_for('signup'))

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            age=age,
            gender=gender
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        return redirect(url_for('plans'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('plans'))

        flash('Invalid email or password.')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        doctor = Doctor.query.filter_by(email=email).first()
        if doctor and check_password_hash(doctor.password_hash, password):
            session['doctor_id'] = doctor.id
            return redirect(url_for('doctor_dashboard'))

        flash('Invalid email or password.')
        return redirect(url_for('doctor_login'))

    return render_template('doctor_login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/plans')
def plans():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    standard_plans = Plan.query.filter_by(tier='standard').all()
    premium_plans = Plan.query.filter_by(tier='premium').all()

    return render_template('plans.html', standard_plans=standard_plans, premium_plans=premium_plans)


@app.route('/doctors/<int:plan_id>')
def doctor_list(plan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    plan = Plan.query.get_or_404(plan_id)

    if plan.tier == 'premium':
        doctors = Doctor.query.filter_by(tier='premium').order_by(Doctor.booking_count.desc()).limit(5).all()
    else:
        doctors = Doctor.query.filter_by(tier='standard').order_by(Doctor.rating.desc()).limit(5).all()

    return render_template('doctors.html', doctors=doctors, plan=plan)


@app.route('/book/<int:doctor_id>/<int:plan_id>', methods=['GET', 'POST'])
def book(doctor_id, plan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doctor_id)
    plan = Plan.query.get_or_404(plan_id)

    if request.method == 'POST':
        scheduled_time_str = request.form.get('scheduled_time')
        try:
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Please pick a valid date and time.')
            return redirect(url_for('book', doctor_id=doctor_id, plan_id=plan_id))

        new_appointment = Appointment(
            user_id=session['user_id'],
            doctor_id=doctor.id,
            plan_id=plan.id,
            scheduled_time=scheduled_time,
            status='booked'
        )
        db.session.add(new_appointment)
        db.session.commit()

        new_payment = Payment(
            appointment_id=new_appointment.id,
            amount=plan.price,
            payment_status='pending'
        )
        db.session.add(new_payment)

        doctor.booking_count += 1
        db.session.commit()

        return redirect(url_for('confirmation', appointment_id=new_appointment.id))

    return render_template('book.html', doctor=doctor, plan=plan)


@app.route('/confirmation/<int:appointment_id>')
def confirmation(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('confirmation.html', appointment=appointment)


@app.route('/my-appointments')
def my_appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    appointments = Appointment.query.filter_by(user_id=session['user_id']).order_by(Appointment.created_at.desc()).all()
    return render_template('my_appointments.html', appointments=appointments)



@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))

    doctor = Doctor.query.get_or_404(session['doctor_id'])

    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id
    ).order_by(
        Appointment.scheduled_time.asc()
    ).all()

    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        appointments=appointments
    )



@app.route('/recompute-tiers')
def recompute_tiers():
    Doctor.query.update({Doctor.tier: 'standard'})
    db.session.commit()

    top_doctors = Doctor.query.order_by(Doctor.booking_count.desc()).limit(5).all()
    for doc in top_doctors:
        doc.tier = 'premium'
    db.session.commit()

    return redirect(url_for('plans'))


if __name__ == '__main__':
    app.run(debug=True)