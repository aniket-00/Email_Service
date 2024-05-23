from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
# import stripe
import os
# import paypalrestsdk
# from flask_pymongo import PyMongo
import urllib.parse
from flask_pymongo import ObjectId
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
# from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import re
from jinja2 import Template
import json
import random
from datetime import datetime
# from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()


app = Flask(__name__)
vercel_url = os.environ.get('VERCEL_URL')
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/' 
password = "Tester@12345"
username = "test"
encoded_password = urllib.parse.quote_plus(password)
api_key = os.environ.get("MONGO_API_KEY")
cluster_name = 'cluster0'
# app.config['MONGO_URI'] = f"mongodb+srv://test:{encoded_password}@cluster0.pzqagzo.mongodb.net/"
uri = f"mongodb+srv://{username}:{encoded_password}@{cluster_name}.pzqagzo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


# Create a new client and connect to the server
client = MongoClient(uri)
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client.Email_Service  # Replace 'test_database' with your actual database name


# db = SQLAlchemy(app)
app.static_folder = 'static'
app.template_folder = 'templates'

@app.route('/')
def home():
    return render_template('home.html', login_url='login')
# app.secret_key = os.environ.get('SECRET_KEY') or 'your_secret_key'

# paypalrestsdk.configure({
#     "mode": "sandbox",  # Change to "live" for production
#     "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
#     "client_secret": os.environ.get('PAYPAL_CLIENT_SECRET')
# })

# Mock user database for demonstration
class User(UserMixin):
    def __init__(self, id):
        self.id = id

users = {'user1': {'password': 'password1'}, 'test': {'password': 'test'}}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Initialize Stripe
# stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def all_questions_sent():
    return db.questions.count_documents({'sent': False}) == 0

# Function to reset the 'sent' field for all questions to False
def reset_sent_field():
    db.questions.update_many({}, {'$set': {'sent': False}})

def get_and_send_random_question():
    # Check if all questions have been sent
    if all_questions_sent():
        # Reset the 'sent' field for all questions to False
        reset_sent_field()
    
    # Query the database to fetch all available questions
    all_questions = db.questions.find({'sent': False})
    
    # Shuffle the list of questions to ensure randomness
    all_questions = list(all_questions)
    random.shuffle(all_questions)
    
    # Iterate through the shuffled list of questions
    for question in all_questions:
        # Check if the question has not been sent before
        if not question.get('sent', False):         
            # Mark the question as sent in the database
            db.questions.update_one({'_id': question['_id']}, {'$set': {'sent': True}})
            
            return question

def send_user_email(payment_link,question, user):
    sender_email = 'mailego.mail.ai@gmail.com'
    receiver_email = user.get('email')
    password = os.environ.get("PASSWORD")

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = 'Daily Morning Dose'
    
    # Prepare question content
    is_paid_user = user.get('subscription_status')=='paid'

    with open('api/templates/email.html', 'r') as file:
        template = Template(file.read())
    
    html_content = template.render(
        question=question,
        is_paid_user=is_paid_user,
        payment_link=payment_link
    )
    
    # Attach the HTML content to the email
    message.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        print('Email sent successfully!', 'success')
    except Exception as e:
        print('An error occurred while sending the email: {}'.format(str(e)), 'error')

    return "Unexpected issue"

# @app.route('/generate_payment_link/<user_id>', methods=['GET'])
def generate_payment_link(user_id):
    # Construct the payment URL with the user's ID as a parameter
    payment_url = url_for('payment_redirect', user_id=user_id, _external=True)
    return payment_url


@app.route('/send_email', methods=['GET', 'POST'])
def send_email():
    with app.app_context():
        users_list = get_users()  # Extract the 'users' list
        # Now you can work with the 'users_list' data
        question = get_and_send_random_question()
        for user in users_list:
            user_id = user.get('user_id')
            email = user.get('email')
            subscription_status = user.get('subscription_status')
            # Do something with email and subscription_status
            payment_link = generate_payment_link(user_id)
            send_user_email(payment_link,question,user)
        return users_list



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html') 

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'You have been logged out'

def get_users():
    collection = db.Users
    users = collection.find()
    user_list = []
    for user in users:
        user_id =str(user['_id'])
        email = user.get('email')
        subscription_status = user.get('subscription_status')
        if email is not None and subscription_status is not None:
            user_list.append({'user_id': user_id,'email': email, 'subscription_status': subscription_status})
    return user_list

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    collection = db.Users
    user = collection.find_one({'_id': ObjectId(user_id)})  # Assuming you're using ObjectId for user IDs

    if user:
        user_id =str(user['_id'])
        email = user.get('email')
        subscription_status = user.get('subscription_status')
        if email is not None and subscription_status is not None:
            user_info = {'user_id': user_id,'email': email, 'subscription_status': subscription_status}
            return jsonify(user_info), 200
        else:
            return jsonify({'message': 'User information incomplete'}), 400
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/users/<user_id>/update_subscription', methods=['POST'])
def update_subscription(user_id):
    # Parse the request data
    data = request.json
    new_subscription_status = data.get('subscription_status')

    if new_subscription_status is None:
        return jsonify({'message': 'Subscription status not provided'}), 400

    # Update the user's subscription status
    collection = db.Users
    result = collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'subscription_status': new_subscription_status}}
    )

    if result.modified_count == 1:
        return jsonify({'message': 'Subscription status updated successfully'}), 200
    else:
        return jsonify({'message': 'Failed to update subscription status'}), 500

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        data = request.get_json()  # Get JSON data from the request body
        email = data.get('email') 
        
        # Check if the email is already subscribed
        users_collection = db.Users
        existing_user = users_collection.find_one({'email': email})
        
        
        if existing_user:
            flash('You are already subscribed to our email service.', 'info')
            return {"status": "already_subscribed"}
        else:
            # Create a new user record with the email address and subscription status
            new_user = {"email":email, "subscription_status":'free'}
            users_collection.insert_one(new_user)
            flash('Subscription to email service successful!', 'success')
            return {"status": "success"}
    
    return render_template('subscribe.html')

@app.route('/payment_redirect', methods=['GET'])
def payment_redirect():
    user_id = request.args.get('user_id')  # Extract user ID from query parameters
    if user_id:
        # Retrieve user from the database using the user ID
        user = db.Users.find_one({'_id': ObjectId(user_id)})
        if user:
            return redirect(f"checkout?user_id={user_id}")  # Redirect to the payment page
        else:
            return 'User not found', 404
    else:
        return 'Invalid request', 400

@app.route('/checkout', methods=['GET'])
def paypal_subscribe():
    user_id = request.args.get('user_id')
    return render_template('checkout.html', user_id=user_id)

def save_subscription(subscription, end_date, email):
    # Access the MongoDB collection
    collection = db.subscriptions

    # Prepare the subscription data to be saved
    subscription_data = {
        'email': email,
        'subscription_id': subscription.id,
        'start_date': datetime.now(),
        'end_date': end_date,
        'status': 'active'  # Assuming the subscription is active upon creation
    }

    # Insert the subscription data into the collection
    collection.insert_one(subscription_data)

def parse_question_and_answer_file(file_path):
    with open(file_path, 'r') as file:
        content = json.load(file)
    
    return content

def add_question_to_db(question_data):
    questions_collection = db['questions']
    questions_collection.insert_one(question_data)
    client.close()

@app.route('/questions/<question_id>', methods=['GET'])
def get_question(question_id):
    # Replace with your method of getting the current user
    questions_collection = db['questions']
    question = questions_collection.find_one({'_id': ObjectId(question_id)})
    if question:
        response = {
            "title": question["title"],
            "description": question["description"],
            "examples": question["examples"],
            "constraints": question["constraints"]
        }
        # if user['subscription_status'] == 'paid':
        #     response["answers"] = question["answers"]
        return jsonify(response)
    else:
        return jsonify({'error': 'Question not found'}), 404


# @app.route('/paypal_webhook', methods=['POST'])
# def paypal_webhook():
#     # Parse the JSON payload from the webhook request
#     payload = request.get_json()

#     # Extract the email address from the webhook payload
#     email = payload['subscriber']['email_address']

#     # Process the subscription based on the email
#     process_subscription(email)

#     return 'Webhook received', 200

def process_subscription(email):
    # Placeholder function to process the subscription
    # You can implement your subscription logic here
    paypal_subscribe()
    print(f"Processing subscription for email: {email}")


@app.route('/paypal_success')
def paypal_success():
    # Retrieve subscription ID and user ID from query parameters
    subscription_id = request.args.get('subscriptionID')
    user_id = request.args.get('user_id')
    print(user_id)
    if user_id:
        # Retrieve user from the database using the user ID
        user = db.Users.find_one({'_id': ObjectId(user_id)})
        if user:
            # Update user's subscription status in the database
            db.Users.update_one({'_id': ObjectId(user_id)}, {'$set': {'subscription_status': 'paid'}})
            return render_template('checkout_success.html')
    
    # Handle successful payment and update user's subscription status
    # For example, you can render a success template with a success message
    return "Unexpected issue, you paymnet is done, you can securly checkoutt"
    

@app.route('/paypal_failed')
def paypal_failed():
    # Handle Failed payment
    flash('Payment Failed, try again later', 'success')
    return render_template('checkout_failed.html')

@app.route('/paypal_cancel')
def paypal_cancel():
    flash('Payment canceled.', 'error')
    return render_template('checkout_cancel.html')

@app.route('/api/cron')
def run_cron():
    send_email()
    return f"email sent by cron!", 200

# file_path = 'api/questions/6.json'
# question_data = parse_question_and_answer_file(file_path)
# add_question_to_db(question_data)

if __name__ == '__main__':

    app.run(debug=True)
