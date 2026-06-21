import os
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import requests
import qrcode
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
CHART_FOLDER = os.path.join('static', 'charts')
VOICE_FOLDER = 'voice_notes'
WEATHER_API_KEY = '9c69f234d9e39c94deff5943b6c26410'
QR_FOLDER = os.path.join('static', 'qr_codes')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create required folders
for folder in [UPLOAD_FOLDER, CHART_FOLDER, VOICE_FOLDER, QR_FOLDER]:
    os.makedirs(folder, exist_ok=True)

db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_name = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))


class EmergencyContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    trip_id = db.Column(
        db.Integer,
        db.ForeignKey('trip.id'),
        nullable=False
    )

    filename = db.Column(
        db.String(200),
        nullable=False
    )


class VoiceNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    trip_id = db.Column(
        db.Integer,
        db.ForeignKey('trip.id'),
        nullable=False
    )

    filename = db.Column(
        db.String(200),
        nullable=False
    )

# Helper Function
def save_to_db(obj):
    db.session.add(obj)
    db.session.commit()


# Routes
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        save_to_db(User(
            username=request.form['username'],
            email=request.form['email'],
            password=request.form['password']
        ))
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            email=request.form['email'],
            password=request.form['password']
        ).first()

        if user:
            return redirect(url_for('dashboard'))

        return "Invalid Email or Password"

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/create_trip', methods=['GET', 'POST'])
def create_trip():
    if request.method == 'POST':
        save_to_db(Trip(
            trip_name=request.form['trip_name'],
            destination=request.form['destination'],
            start_date=request.form['start_date'],
            end_date=request.form['end_date'],
            notes=request.form['notes']
        ))
        return redirect(url_for('dashboard'))

    return render_template('create_trip.html')


@app.route('/view_trips')
def view_trips():
    return render_template(
        'view_trips.html',
        trips=Trip.query.all()
    )


@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        save_to_db(Expense(
            category=request.form['category'],
            amount=float(request.form['amount']),
            description=request.form['description']
        ))
        return redirect(url_for('view_expenses'))

    return render_template('expenses.html')


@app.route('/view_expenses')
def view_expenses():
    expenses = Expense.query.all()
    total = sum(exp.amount for exp in expenses)

    return render_template(
        'view_expenses.html',
        expenses=expenses,
        total=total
    )


@app.route('/analytics')
def analytics():
    expenses = Expense.query.all()
    category_totals = {}
    total = sum(exp.amount for exp in expenses)

    for exp in expenses:
        category_totals[exp.category] = (
            category_totals.get(exp.category, 0) + exp.amount
        )

    if category_totals:
        plt.figure(figsize=(8, 5))
        plt.bar(category_totals.keys(), category_totals.values())
        plt.title('Expenses by Category')
        plt.xlabel('Category')
        plt.ylabel('Amount (₹)')
        plt.savefig(os.path.join(CHART_FOLDER, 'expense_chart.png'))
        plt.close()

    return render_template(
        'analytics.html',
        total=total,
        category_totals=category_totals
    )


@app.route('/location')
def location():
    return render_template('location.html')


@app.route('/emergency', methods=['GET', 'POST'])
def emergency():
    if request.method == 'POST':
        save_to_db(EmergencyContact(
            name=request.form['name'],
            relationship=request.form['relationship'],
            phone=request.form['phone']
        ))
        return redirect(url_for('view_emergency'))

    return render_template('emergency.html')


@app.route('/view_emergency')
def view_emergency():
    return render_template(
        'view_emergency.html',
        contacts=EmergencyContact.query.all()
    )

@app.route('/media_upload', methods=['GET', 'POST'])
def media_upload():

    trips = Trip.query.all()

    if request.method == 'POST':

        trip_id = request.form['trip_id']

        file = request.files['media']

        if file and file.filename:

            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

            new_media = Media(
                trip_id=trip_id,
                filename=filename
            )

            db.session.add(new_media)
            db.session.commit()

            return redirect(url_for('view_media'))

    return render_template(
        'media_upload.html',
        trips=trips
    )

@app.route('/view_media')
def view_media():

    media_files = Media.query.all()

    return render_template(
        'view_media.html',
        media_files=media_files
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    if request.method == 'POST':
        Budget.query.delete()

        save_to_db(
            Budget(
                amount=float(request.form['budget'])
            )
        )

        return redirect(url_for('budget_alert'))

    return render_template('budget.html')


@app.route('/budget_alert')
def budget_alert():
    budget = Budget.query.first()

    total_expenses = (
        db.session.query(
            db.func.sum(Expense.amount)
        ).scalar() or 0
    )

    if budget:
        budget_amount = budget.amount

        percentage = round(
            (total_expenses / budget_amount) * 100,
            2
        ) if budget_amount else 0

        if percentage >= 100:
            message = "🚨 Alert! You have exceeded your budget."
        elif percentage >= 80:
            message = "⚠ Warning! You have used more than 80% of your budget."
        else:
            message = "✅ You are within your budget."

    else:
        budget_amount = 0
        percentage = 0
        message = "No budget set yet."

    return render_template(
        'budget_alert.html',
        budget=budget_amount,
        expenses=total_expenses,
        percentage=percentage,
        message=message
    )


# Voice Notes Routes
@app.route('/voice_notes')
def voice_notes():

    trips = Trip.query.all()

    return render_template(
        'voice_notes.html',
        trips=trips
    )


@app.route('/save_voice_note', methods=['POST'])
def save_voice_note():

    trip_id = request.form['trip_id']

    audio = request.files.get('audio')

    if audio:

        filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"

        audio.save(
            os.path.join(
                VOICE_FOLDER,
                filename
            )
        )

        new_note = VoiceNote(
            trip_id=trip_id,
            filename=filename
        )

        db.session.add(new_note)
        db.session.commit()

        return "Voice note saved successfully!"

    return "No audio received."


@app.route('/view_voice_notes')
def view_voice_notes():

    notes = VoiceNote.query.all()

    return render_template(
        'view_voice_notes.html',
        notes=notes
    )


@app.route('/voice_notes/<filename>')
def get_voice_note(filename):
    return send_from_directory(
        VOICE_FOLDER,
        filename
    )


# Weather Forecast Route
@app.route('/weather', methods=['GET', 'POST'])
def weather():

    weather_data = None
    error = None

    if request.method == 'POST':

        city = request.form['city']

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}"
            f"&appid={WEATHER_API_KEY}"
            f"&units=metric"
        )

        response = requests.get(url)

        data = response.json()

        if data.get('cod') == 200:

            weather_data = {
                'city': data['name'],
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description'].title(),
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed']
            }

        else:
            error = "City not found. Please enter a valid city name."

    return render_template(
        'weather.html',
        weather=weather_data,
        error=error
    )
@app.route('/travel_summary')
def travel_summary():

    trips = Trip.query.all()
    expenses = Expense.query.all()

    total_expense = sum(exp.amount for exp in expenses)

    media_count = len(os.listdir(UPLOAD_FOLDER))

    voice_count = len(os.listdir(VOICE_FOLDER))

    summary = []

    summary.append("AI TRAVEL SUMMARY")
    summary.append("-----------------------------")

    summary.append(f"Total Trips Created: {len(trips)}")

    for trip in trips:
        summary.append(
            f"Trip: {trip.trip_name} | Destination: {trip.destination}"
        )

    summary.append("")
    summary.append(f"Total Expenses: ₹{total_expense}")

    summary.append(f"Uploaded Media Files: {media_count}")

    summary.append(f"Voice Notes Recorded: {voice_count}")

    if total_expense > 10000:
        summary.append(
            "Expense Analysis: High spending detected."
        )
    elif total_expense > 5000:
        summary.append(
            "Expense Analysis: Moderate spending."
        )
    else:
        summary.append(
            "Expense Analysis: Budget-friendly trip."
        )

    return render_template(
        'travel_summary.html',
        summary=summary
    )
# QR Trip Sharing

@app.route('/qr_share')
def qr_share():

    trips = Trip.query.all()

    return render_template(
        'qr_share.html',
        trips=trips
    )


@app.route('/generate_qr/<int:trip_id>')
def generate_qr(trip_id):

    trip = Trip.query.get_or_404(trip_id)

    qr_data = request.host_url + f"trip/{trip.id}"

    filename = f"trip_{trip.id}.png"

    filepath = os.path.join(
        QR_FOLDER,
        filename
    )

    img = qrcode.make(qr_data)

    img.save(filepath)

    return render_template(
        'view_qr.html',
        qr_image=filename,
        trip=trip
    )


@app.route('/trip/<int:trip_id>')
def trip_details(trip_id):

    trip = Trip.query.get_or_404(trip_id)

    media_files = Media.query.filter_by(
        trip_id=trip_id
    ).all()

    voice_notes = VoiceNote.query.filter_by(
        trip_id=trip_id
    ).all()

    return render_template(
        'trip_details.html',
        trip=trip,
        media_files=media_files,
        voice_notes=voice_notes
    )


print(app.url_map)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)