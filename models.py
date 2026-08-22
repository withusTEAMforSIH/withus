from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.Enum('male', 'female', 'other'), default='other')
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    appointments = db.relationship('Appointment', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)




class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)



class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    specialty = db.Column(db.String(150))
    photo_url = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Numeric(2, 1), default=0.0)
    booking_count = db.Column(db.Integer, default=0)
    tier = db.Column(db.Enum('standard', 'premium'), default='standard')
    fee_per_session = db.Column(db.Numeric(6, 2), default=99.00)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    offers_chat = db.Column(db.Boolean, default=True)
    offers_voice = db.Column(db.Boolean, default=True)
    offers_video = db.Column(db.Boolean, default=True)

    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    reviews = db.relationship('Review', backref='doctor', lazy=True)


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.Enum('chat', 'voice', 'video'), nullable=False)
    tier = db.Column(db.Enum('standard', 'premium'), default='standard')
    price = db.Column(db.Numeric(6, 2), nullable=False)
    duration_minutes = db.Column(db.Integer, default=20)
    description = db.Column(db.String(255))

    appointments = db.relationship('Appointment', backref='plan', lazy=True)


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id', ondelete='CASCADE'), nullable=False)
    scheduled_time = db.Column(db.DateTime)
    status = db.Column(db.Enum('booked', 'ongoing', 'completed', 'cancelled'), default='booked')
    notes = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    payment = db.relationship('Payment', backref='appointment', uselist=False, lazy=True)
    review = db.relationship('Review', backref='appointment', uselist=False, lazy=True)


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(6, 2), nullable=False)
    payment_method = db.Column(db.Enum('upi', 'card', 'netbanking', 'wallet'), default='upi')
    payment_status = db.Column(db.Enum('pending', 'success', 'failed', 'refunded'), default='pending')
    paid_at = db.Column(db.TIMESTAMP, nullable=True)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)