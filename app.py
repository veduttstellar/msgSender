from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
import requests
import datetime
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler


app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

schedules = []

scheduler = BackgroundScheduler()
scheduler.start()

CHATWORK_API_TOKEN = 'd4d2eb1a6ed22050b0a30708b2a88850'
CHATWORK_API_URL = 'https://api.chatwork.com/v2'
ROOM_ID = '338546706'

# Schedule model
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    send_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Schedule {self.room_id} - {self.message} at {self.send_time}>"
    
def send_message(room_id, message):
    """Send a message to a Chatwork group."""
    headers = {
        'X-ChatWorkToken': CHATWORK_API_TOKEN
    }
    data = {'body': message}
    response = requests.post(
        f"{CHATWORK_API_URL}/rooms/{room_id}/messages",
        headers=headers,
        data=data
    )
    return response.status_code == 200

def schedule_message(room_id, message, send_time):
    """Schedule a message to be sent at a specific time."""
    job_id = f"{room_id}_{send_time}"
    scheduler.add_job(
        func=send_message,
        args=[room_id, message],
        trigger='date',
        run_date=send_time,
        id=job_id,
        replace_existing=True
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/schedule', methods=['POST'])
def schedule():
    data = request.json
    new_schedules = data['schedules']
    
    for schedule in new_schedules:
        message = schedule['message']
        send_time_str = schedule['send_time']
        
        # Convert string to datetime object
        send_time = datetime.datetime.strptime(send_time_str, "%Y-%m-%d %H:%M:%S")
        
        # Create a new Schedule object
        new_schedule = Schedule(room_id=ROOM_ID, message=message, send_time=send_time)
        
        # Add to the database
        db.session.add(new_schedule)
        db.session.commit()
        
        # Schedule the message
        schedule_message(ROOM_ID, message, send_time)
    
    return jsonify({"status": "Messages scheduled"})

@app.route('/get_schedules', methods=['GET'])
def get_schedules():
    schedules = Schedule.query.all()
    return jsonify([{
        'id': schedule.id,
        'room_id': schedule.room_id,
        'message': schedule.message,
        'send_time': schedule.send_time.strftime("%Y-%m-%d %H:%M:%S")
    } for schedule in schedules])

@app.route('/delete_schedule/<int:id>', methods=['DELETE'])
def delete_schedule(id):
    schedule_to_delete = Schedule.query.get(id)
    if schedule_to_delete:
        db.session.delete(schedule_to_delete)
        db.session.commit()
        return jsonify({"status": "Schedule deleted"})
    else:
        return jsonify({"status": "Schedule not found"}), 404

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == "__main__":
    with app.app_context():
         db.create_all()
    if not app.debug:
        handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
    serve(app, host='0.0.0.0', port=8080)
    # serve(app, host='0.0.0.0', port=8080)
    # app.run(debug=True)
    #db.create_all()
