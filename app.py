import os , anthropic
from flask import Flask, render_template, request, redirect, url_for, session, flash , jsonify
from flask_socketio import SocketIO, join_room, emit
from models import db, User, Admin, Doctor, Plan, Appointment, Payment, Review ,ChatMessage
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
DB_PORT = os.environ.get('DB_PORT')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# ============================================
# Helper functions
# ============================================

def recompute_doctor_tiers():
    """Reset all doctors to standard, then promote the top 5 by booking_count to premium."""
    Doctor.query.update({Doctor.tier: 'standard'})
    top_doctors = Doctor.query.order_by(Doctor.booking_count.desc()).limit(5).all()
    for doc in top_doctors:
        doc.tier = 'premium'
    db.session.commit()


def recompute_doctor_rating(doctor):
    """Recalculate a doctor's average rating from their reviews."""
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(doctor_id=doctor.id).scalar()
    doctor.rating = round(avg, 1) if avg else 0.0
    db.session.commit()



    


# ============================================
# Public pages
# ============================================

@app.route('/')
def index():
    return render_template('index.html')




# ============================================
# Homepage AI chatbot (public, pre-screening only)
# ============================================

anthropic_client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

CHATBOT_SYSTEM_PROMPT = """You are the WithUS homepage assistant.

WithUS is a private, judgment-free platform where people can chat, call,
or video with a real doctor. You are NOT a doctor and this is NOT a
diagnostic tool.

Rules you must always follow:
- Never diagnose a condition or claim something is or isn't serious.
- Never recommend medications, dosages, or treatments.
- Keep responses short (2-4 sentences), warm, and non-judgmental.
- For anything specific to the person's body or symptoms, gently guide
  them to book a real doctor on WithUS rather than trying to answer it
  yourself.
- You can answer general questions about how WithUS works (plans,
  privacy, chat/voice/video, pricing starting at ₹99).
- If the person seems to be in a medical emergency, tell them clearly
  to contact local emergency services immediately.
"""

# Very basic in-memory rate limiting per session.
# For production with multiple server workers, replace with Redis.
from collections import defaultdict
import time

_chat_rate_limit = defaultdict(list)
RATE_LIMIT_MAX_MESSAGES = 15
RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes


@app.route('/api/chatbot', methods=['POST'])
def chatbot():

    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    if len(user_message) > 500:
        return jsonify({'error': 'Message too long'}), 400

    # Rate limit by session (Flask session cookie, works for anonymous visitors too)
    if 'chat_session_id' not in session:
        session['chat_session_id'] = os.urandom(8).hex()

    session_id = session['chat_session_id']
    now = time.time()

    _chat_rate_limit[session_id] = [
        t for t in _chat_rate_limit[session_id]
        if now - t < RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(_chat_rate_limit[session_id]) >= RATE_LIMIT_MAX_MESSAGES:
        return jsonify({
            'error': 'rate_limited',
            'reply': "You've sent a lot of messages — please try again in a few minutes, or sign up to talk to a real doctor."
        }), 429

    _chat_rate_limit[session_id].append(now)

    # Build message history for the API (cap length to keep cost/context sane)
    api_messages = []
    for turn in history[-6:]:
        role = turn.get('role')
        content = turn.get('content', '')
        if role in ('user', 'assistant') and content:
            api_messages.append({'role': role, 'content': content})

    api_messages.append({'role': 'user', 'content': user_message})

    try:
        response = anthropic_client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            system=CHATBOT_SYSTEM_PROMPT,
            messages=api_messages
        )

        reply_text = ''.join(
            block.text for block in response.content if block.type == 'text'
        )

    except Exception as e:
        app.logger.error(f'Chatbot API error: {e}')
        return jsonify({
            'error': 'api_error',
            'reply': "Sorry, I'm having trouble responding right now. Please try again shortly."
        }), 500

    return jsonify({'reply': reply_text})    


# ============================================
# User auth
# ============================================

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

        if not doctor:
            flash('Invalid email or password.')
            return redirect(url_for('doctor_login'))

        if not doctor.is_active:
            flash('You are no longer part of this organisation.')
            return redirect(url_for('doctor_login'))

        if not check_password_hash(doctor.password_hash, password):
            flash('Invalid email or password.')
            return redirect(url_for('doctor_login'))

        session['doctor_id'] = doctor.id
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor_login.html')



@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        admin = Admin.query.filter_by(email=email).first()

        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session['admin_id'] = admin.id
            return redirect(url_for('admin_dashboard'))

        flash('Invalid admin email or password.')
        return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))



# ============================================
# Chat
# ============================================

@app.route('/chat/<int:appointment_id>')
def chat(appointment_id):

    if 'user_id' not in session and 'doctor_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    # Patient access
    if 'user_id' in session:

        if appointment.user_id != session['user_id']:
            flash('You are not authorized to access this chat.')
            return redirect(url_for('my_appointments'))

        current_user_type = 'user'
        current_user_id = session['user_id']

    # Doctor access
    else:

        if appointment.doctor_id != session['doctor_id']:
            flash('You are not authorized to access this chat.')
            return redirect(url_for('doctor_dashboard'))

        current_user_type = 'doctor'
        current_user_id = session['doctor_id']

    messages = ChatMessage.query.filter_by(
        appointment_id=appointment.id
    ).order_by(
        ChatMessage.created_at.asc()
    ).all()

    return render_template(
        'chat.html',
        appointment=appointment,
        messages=messages,
        current_user_type=current_user_type,
        current_user_id=current_user_id
    )


# ============================================
# Plans & doctors
# ============================================

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

    mode_column = {
        'chat': Doctor.offers_chat,
        'voice': Doctor.offers_voice,
        'video': Doctor.offers_video
    }[plan.mode]

    query = Doctor.query.filter(
    Doctor.tier == plan.tier,
    Doctor.is_active == True,
    mode_column == True
     )

    if plan.tier == 'premium':
        doctors = query.order_by(Doctor.booking_count.desc()).limit(5).all()
    else:
        doctors = query.order_by(Doctor.rating.desc()).limit(5).all()

    return render_template('doctors.html', doctors=doctors, plan=plan)


# ============================================
# Booking & payment
# ============================================

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

        recompute_doctor_tiers()

        return redirect(url_for('payment', payment_id=new_payment.id))

    return render_template('book.html', doctor=doctor, plan=plan)


@app.route('/payment/<int:payment_id>', methods=['GET', 'POST'])
def payment(payment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    payment_obj = Payment.query.get_or_404(payment_id)
    appointment = payment_obj.appointment

    if appointment.user_id != session['user_id']:
        flash('You are not authorized to view this payment.')
        return redirect(url_for('my_appointments'))

    if payment_obj.payment_status == 'success':
        return redirect(url_for('confirmation', appointment_id=appointment.id))

    if request.method == 'POST':
        method = request.form.get('payment_method', 'upi')
        payment_obj.payment_method = method
        payment_obj.payment_status = 'success'
        payment_obj.paid_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('confirmation', appointment_id=appointment.id))

    return render_template('payment.html', payment=payment_obj, appointment=appointment)


@app.route('/confirmation/<int:appointment_id>')
def confirmation(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.user_id != session['user_id']:
        flash('You are not authorized to view this appointment.')
        return redirect(url_for('my_appointments'))

    return render_template('confirmation.html', appointment=appointment)


@app.route('/my-appointments')
def my_appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    appointments = Appointment.query.filter_by(
        user_id=session['user_id']
    ).order_by(Appointment.created_at.desc()).all()

    return render_template('my_appointments.html', appointments=appointments)


# ============================================
# Reviews
# ============================================

@app.route('/review/<int:appointment_id>', methods=['GET', 'POST'])
def review(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.user_id != session['user_id']:
        flash('You are not authorized to review this appointment.')
        return redirect(url_for('my_appointments'))

    if appointment.status != 'completed':
        flash('You can leave a review once this appointment is marked completed.')
        return redirect(url_for('my_appointments'))

    if appointment.review:
        flash('You have already reviewed this appointment.')
        return redirect(url_for('my_appointments'))

    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '')

        new_review = Review(
            appointment_id=appointment.id,
            user_id=appointment.user_id,
            doctor_id=appointment.doctor_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
        db.session.commit()

        recompute_doctor_rating(appointment.doctor)

        flash('Thanks for your review!')
        return redirect(url_for('my_appointments'))

    return render_template('review.html', appointment=appointment)


# ============================================
# Doctor dashboard
# ============================================

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


@app.route('/doctor/appointment/<int:appointment_id>/status', methods=['POST'])
def update_appointment_status(appointment_id):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != session['doctor_id']:
        flash('You are not authorized to update this appointment.')
        return redirect(url_for('doctor_dashboard'))

    new_status = request.form.get('status')
    if new_status in ('ongoing', 'completed', 'cancelled'):
        appointment.status = new_status
        db.session.commit()
        flash(f'Appointment marked as {new_status}.')

    return redirect(url_for('doctor_dashboard'))


# ============================================
# Admin utility (manual trigger, kept for convenience)
# ============================================

@app.route('/recompute-tiers')
def recompute_tiers():
    recompute_doctor_tiers()
    return redirect(url_for('plans'))



@app.route('/admin/dashboard')
def admin_dashboard():

    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    admin = Admin.query.get_or_404(session['admin_id'])

    doctors = Doctor.query.order_by(
        Doctor.created_at.desc()
    ).all()

    total_doctors = Doctor.query.count()

    verified_doctors = Doctor.query.filter_by(
        verified=True
    ).count()

    active_doctors = Doctor.query.filter_by(
        is_active=True
    ).count()

    return render_template(
        'admin_dashboard.html',
        admin=admin,
        doctors=doctors,
        total_doctors=total_doctors,
        verified_doctors=verified_doctors,
        active_doctors=active_doctors
    )



@app.route('/admin/doctors/add', methods=['GET', 'POST'])
def add_doctor():

    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        specialty = request.form.get('specialty', '').strip()
        fee_per_session = request.form.get('fee_per_session', '99.00').strip()

        offers_chat = request.form.get('offers_chat') == '1'
        offers_voice = request.form.get('offers_voice') == '1'
        offers_video = request.form.get('offers_video') == '1'
        is_active = request.form.get('is_active') == '1'

        # Basic validation
        if not name or not email or not password or not specialty:
            flash('Name, email, password and specialty are required.')
            return redirect(url_for('add_doctor'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.')
            return redirect(url_for('add_doctor'))

        existing_doctor = Doctor.query.filter_by(email=email).first()
        if existing_doctor:
            flash('A doctor with this email already exists.')
            return redirect(url_for('add_doctor'))

        try:
            fee_value = float(fee_per_session)
        except ValueError:
            fee_value = 99.00

        new_doctor = Doctor(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            specialty=specialty,
            fee_per_session=fee_value,
            is_active=is_active,
            offers_chat=offers_chat,
            offers_voice=offers_voice,
            offers_video=offers_video
        )

        db.session.add(new_doctor)
        db.session.commit()

        flash(f'Dr. {new_doctor.name} was created. They can now log in with the email and password you set.')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_doctor.html')

@app.route('/admin/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
def edit_doctor(doctor_id):

    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        specialty = request.form.get('specialty', '').strip()
        

        is_active = request.form.get('is_active') == '1'

        offers_chat = request.form.get('offers_chat') == '1'
        offers_voice = request.form.get('offers_voice') == '1'
        offers_video = request.form.get('offers_video') == '1'

        # Basic validation
        if not name or not email or not specialty:
            flash('Name, email and specialty are required.')
            return redirect(url_for('edit_doctor', doctor_id=doctor.id))

        # Check whether another doctor already uses this email
        existing_doctor = Doctor.query.filter(
            Doctor.email == email,
            Doctor.id != doctor.id
        ).first()

        if existing_doctor:
            flash('Another doctor is already using this email.')
            return redirect(url_for('edit_doctor', doctor_id=doctor.id))

        doctor.name = name
        doctor.email = email
        doctor.specialty = specialty

         
         

        doctor.is_active = is_active

        doctor.offers_chat = offers_chat
        doctor.offers_voice = offers_voice
        doctor.offers_video = offers_video

        db.session.commit()

        flash(f'{doctor.name} updated successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template(
        'edit_doctor.html',
        doctor=doctor
    )




# ============================================
# Voice/Video Call
# ============================================

@app.route('/call/<int:appointment_id>')
def call(appointment_id):

    if 'user_id' not in session and 'doctor_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.status not in ('booked', 'ongoing'):
        flash('This call is not available for this appointment.')
        if 'user_id' in session:
            return redirect(url_for('my_appointments'))
        return redirect(url_for('doctor_dashboard'))

    # Patient access
    if 'user_id' in session:

        if appointment.user_id != session['user_id']:
            flash('You are not authorized to access this call.')
            return redirect(url_for('my_appointments'))

        current_user_type = 'user'
        current_user_id = session['user_id']

    # Doctor access
    else:

        if appointment.doctor_id != session['doctor_id']:
            flash('You are not authorized to access this call.')
            return redirect(url_for('doctor_dashboard'))

        current_user_type = 'doctor'
        current_user_id = session['doctor_id']

    mode = request.args.get('mode', 'video')
    if mode not in ('video', 'voice'):
        mode = 'video'

    return render_template(
        'call.html',
        appointment=appointment,
        current_user_type=current_user_type,
        current_user_id=current_user_id,
        mode=mode
    )




@socketio.on('join_chat')
def handle_join_chat(data):

    appointment_id = data.get('appointment_id')

    if not appointment_id:
        return

    appointment = Appointment.query.get(appointment_id)

    if not appointment:
        return

    # Check whether patient or doctor belongs to appointment

    if 'user_id' in session:

        if appointment.user_id != session['user_id']:
            return

    elif 'doctor_id' in session:

        if appointment.doctor_id != session['doctor_id']:
            return

    else:
        return

    room = f'appointment_{appointment_id}'

    join_room(room)

    emit(
        'joined_chat',
        {
            'message': 'Connected to chat.'
        }
    )




@socketio.on('send_message')
def handle_send_message(data):

    appointment_id = data.get('appointment_id')
    message_text = data.get('message', '').strip()

    if not appointment_id or not message_text:
        return

    appointment = Appointment.query.get(appointment_id)

    if not appointment:
        return

    # Determine sender

    if 'user_id' in session:

        if appointment.user_id != session['user_id']:
            return

        sender_type = 'user'
        sender_id = session['user_id']

    elif 'doctor_id' in session:

        if appointment.doctor_id != session['doctor_id']:
            return

        sender_type = 'doctor'
        sender_id = session['doctor_id']

    else:
        return

    new_message = ChatMessage(
        appointment_id=appointment.id,
        sender_type=sender_type,
        sender_id=sender_id,
        message=message_text
    )

    db.session.add(new_message)
    db.session.commit()

    room = f'appointment_{appointment_id}'

    emit(
        'new_message',
        {
            'id': new_message.id,
            'message': new_message.message,
            'sender_type': new_message.sender_type,
            'sender_id': new_message.sender_id,
            'created_at': new_message.created_at.strftime('%H:%M')
        },
        to=room
    )

# ============================================
# Error handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500



# ============================================
# Call signaling
# ============================================

def _authorize_call(appointment_id):
    """Returns (appointment, sender_type, sender_id) or (None, None, None) if unauthorized."""

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return None, None, None

    if appointment.status not in ('booked', 'ongoing'):
        return None, None, None

    if 'user_id' in session:
        if appointment.user_id != session['user_id']:
            return None, None, None
        return appointment, 'user', session['user_id']

    elif 'doctor_id' in session:
        if appointment.doctor_id != session['doctor_id']:
            return None, None, None
        return appointment, 'doctor', session['doctor_id']

    return None, None, None


@socketio.on('call_join')
def handle_call_join(data):

    appointment_id = data.get('appointment_id')
    if not appointment_id:
        return

    appointment, sender_type, sender_id = _authorize_call(appointment_id)
    if not appointment:
        return

    room = f'call_{appointment_id}'
    join_room(room)

    # Tell whoever is already in the room that a new peer joined
    emit(
        'call_peer_joined',
        {'sender_type': sender_type},
        to=room,
        include_self=False
    )


@socketio.on('call_offer')
def handle_call_offer(data):

    appointment_id = data.get('appointment_id')
    appointment, sender_type, sender_id = _authorize_call(appointment_id)
    if not appointment:
        return

    room = f'call_{appointment_id}'
    emit(
        'call_offer',
        {'sdp': data.get('sdp'), 'sender_type': sender_type},
        to=room,
        include_self=False
    )


@socketio.on('call_answer')
def handle_call_answer(data):

    appointment_id = data.get('appointment_id')
    appointment, sender_type, sender_id = _authorize_call(appointment_id)
    if not appointment:
        return

    room = f'call_{appointment_id}'
    emit(
        'call_answer',
        {'sdp': data.get('sdp'), 'sender_type': sender_type},
        to=room,
        include_self=False
    )


@socketio.on('call_ice_candidate')
def handle_call_ice_candidate(data):

    appointment_id = data.get('appointment_id')
    appointment, sender_type, sender_id = _authorize_call(appointment_id)
    if not appointment:
        return

    room = f'call_{appointment_id}'
    emit(
        'call_ice_candidate',
        {'candidate': data.get('candidate'), 'sender_type': sender_type},
        to=room,
        include_self=False
    )


@socketio.on('call_end')
def handle_call_end(data):

    appointment_id = data.get('appointment_id')
    appointment, sender_type, sender_id = _authorize_call(appointment_id)
    if not appointment:
        return

    room = f'call_{appointment_id}'
    emit(
        'call_ended',
        {'sender_type': sender_type},
        to=room,
        include_self=False
    )



 


if __name__ == '__main__':
   socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), allow_unsafe_werkzeug=True)
