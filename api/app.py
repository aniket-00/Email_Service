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
# from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from jinja2 import Template
import json
import random
from datetime import datetime

# from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET_KEY = os.getenv('TWITTER_API_SECRET_KEY')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# try:
#     # Authenticate using client credentials
#     client  = tweepy.Client(
#         consumer_key=TWITTER_API_KEY,
#         consumer_secret=TWITTER_API_SECRET_KEY,
#         access_token=TWITTER_ACCESS_TOKEN,
#         access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
#         # bearer_token=TWITTER_BEARER_TOKEN
#     )
#     user = client.get_me(user_auth=True)

#     # Print the user's screen name
#     print(f"Authenticated as: {user.data}")

#     # auth = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
#     # Example: Make a request to the Twitter API v2
#     # response = client.create_tweet(text="Hello")
#     # print(response)
    
#     print("authorised")
# except Exception as e:
#     print(f"Error: {e}")

app = Flask(__name__)

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

@app.before_request
def before_request():
    if ENVIRONMENT == 'preview':
        app.config['SERVER_NAME'] = 'dev.mailego.com'
    if ENVIRONMENT == 'production':
        app.config['SERVER_NAME'] = 'mailego.com'
    else:
        host = request.host
        app.config['SERVER_NAME'] = host 

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

users = {'test': {'password': 'Abhishek@0099'}}

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
    message['Subject'] = 'Can you solve this!!'
    
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
def send_email(question=None):
    with app.app_context():  
        # check users status
        update_subscription_status_all_users()
        if not question:
            question = get_and_send_random_question()
        # Extract the 'users' list
        users_list = get_users()
        for user in users_list:
            user_id = user.get('user_id')
            email = user.get('email')
            subscription_status = user.get('subscription_status')
            # Do something with email and subscription_status
            payment_link = generate_payment_link(user_id)
            send_user_email(payment_link,question,user)
        return users_list

def update_subscription_status_all_users():
    # Get all users from the database
    all_users = db.Users.find()
    
    # Get the current date
    current_date = datetime.now()
    
    # Iterate through each user
    for user in all_users:
        # Retrieve subscription end date from the user document
        end_date = user.get('subscription_end_date')
        if end_date:
            # Check if the current date is greater than the subscription end date
            if current_date > end_date:
                # If so, update the user's subscription status to 'free'
                db.Users.update_one({'_id': user['_id']}, 
                                    {'$set': {'subscription_status': 'free'}})


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
        username = user.get('email')
        if user:
            return redirect(f"checkout?user_id={user_id}&username={username}")  # Redirect to the payment page
        else:
            return 'User not found', 404
    else:
        return 'Invalid request', 400

@app.route('/checkout', methods=['GET'])
def paypal_subscribe():
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    return render_template('checkout.html', user_id=user_id, username=username)

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
    if user_id:
        start_date = datetime.now()  # Subscription start date
        end_date = start_date + timedelta(days=30)
        # Retrieve user from the database using the user ID
        user = db.Users.find_one({'_id': ObjectId(user_id)})
        if user:
            # Update user's subscription status in the database
            db.Users.update_one({'_id': ObjectId(user_id)}, 
                                {'$set': {'subscription_status': 'paid',
                                          'subscription_start_date': start_date,
                                          'subscription_end_date': end_date}})
            return render_template('checkout_success.html')
    
    # Handle successful payment and update user's subscription status
    # For example, you can render a success template with a success message
    return "Unexpected issue, you paymnet is done, you can securly checkout"
    

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
    question = get_and_send_random_question()
    send_email(question)
    post_question_to_twitter(question)
    return f"email sent by cron!", 200

def format_question_for_twitter(question):
    title = question.get("title", "")
    description = question.get("description", "")
    
    example = question.get("examples", [{}])[0]
    example_input = example.get("input", "")
    example_output = example.get("output", "")
    
    constraints = ", ".join(question.get("constraints", []))

    tweet = (
        f"{title}\n\n"
        f"{description}\n\n"
        f"Constraints: {constraints}\n\n"
        f"Example:\n{example_input}\nOutput: {example_output}"
    )

    # Ensure the tweet does not exceed 280 characters
    if len(tweet) > 280:
        # Truncate the tweet to fit within the character limit
        tweet = tweet[:277]  # Ensure room for ellipsis
        last_space = tweet.rfind(' ')
        if last_space != -1:
            tweet = tweet[:last_space]
        tweet += "..."

    return tweet


def text_wrap(text, font, max_width):
    import cv2
    lines = []
    current_line = ""
    words = text.split()

    for word in words:
        # Check if adding the word exceeds the max width
        line_with_word = current_line + word + " " if current_line else word + " "
        text_size, _ = cv2.getTextSize(line_with_word, font, 0.8, 1)

        if text_size[0] > max_width:
            # If adding the word exceeds the max width, start a new line
            lines.append(current_line.strip())
            current_line = word + " "
        else:
            current_line = line_with_word

    if current_line:
        lines.append(current_line.strip())

    return lines

def generate_image_from_json(question, output_file):
    import cv2
    import numpy as np
    # Define the image width
    width = 1200
    
    # Define font properties
    font_face = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.8
    font_color = (36, 86, 150)  # Soft blue
    thickness = 1

    # Initialize line y-coordinate and image height
    line_y = 50
    height = line_y

    # Create a blank image
    img = np.zeros((height, width, 3), np.uint8)
    img.fill(255)  # Set white background

    # Draw the title
    title = question['title']
    title_lines = text_wrap(title, font_face, width - 100)
    for line in title_lines:
        line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
        line_y += line_size[1] + 20
    
    # Adjust image height based on title height
    height = line_y

    # Draw the description
    description = question['description']
    description_lines = text_wrap(description, font_face, width - 100)
    for line in description_lines:
        line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
        line_y += line_size[1] + 20

    # Adjust image height based on description height
    height = max(height, line_y)

    # Draw examples
    examples = question['examples']
    line_y += 50
    for example in examples:
        input_text = f"Input: {example['input']}"
        output_text = f"Output: {example['output']}"
        explanation_text = f"Explanation: {example['explanation']}"
        
        input_lines = text_wrap(input_text, font_face, width - 100)
        for line in input_lines:
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        output_lines = text_wrap(output_text, font_face, width - 100)
        for line in output_lines:
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        explanation_lines = text_wrap(explanation_text, font_face, width - 100)
        for line in explanation_lines:
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        line_y += 20  # Add some spacing between examples

    # Adjust image height based on example text
    height = max(height, line_y)

    # Draw constraints header
    cv2.putText(img, "Constraints:", (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
    line_y += 20  # Add spacing after constraints header

    # Draw constraints
    constraints = question['constraints']
    for constraint in constraints:
        constraint_lines = text_wrap(constraint, font_face, width - 100)  # Adjusted width for constraints
        for line in constraint_lines:
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20

    # Adjust image height based on constraint text
    height = max(height, line_y + 50)  # Add some padding at the bottom

    # Create a new image with the adjusted height
    img = np.zeros((height, width, 3), np.uint8)
    img.fill(255)  # Set white background

    # Redraw text on the new image
    line_y = 50  # Reset line y-coordinate
    for line in title_lines:
        cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
        line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
        line_y += line_size[1] + 20
    
    line_y += 50  # Add spacing after title
    for line in description_lines:
        cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
        line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
        line_y += line_size[1] + 20

    line_y += 50  # Add spacing after description
    for example in examples:
        input_text = f"Input: {example['input']}"
        output_text = f"Output: {example['output']}"
        explanation_text = f"Explanation: {example['explanation']}"
        
        input_lines = text_wrap(input_text, font_face, width - 100)
        for line in input_lines:
            cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        output_lines = text_wrap(output_text, font_face, width - 100)
        for line in output_lines:
            cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        explanation_lines = text_wrap(explanation_text, font_face, width - 100)
        for line in explanation_lines:
            cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20
        
        line_y += 20  # Add spacing between examples

    # Draw constraints header
    cv2.putText(img, "Constraints:", (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
    line_y += 50  # Add spacing after constraints header

    # Draw constraints
    for constraint in constraints:
        constraint_lines = text_wrap(constraint, font_face, width - 100)  # Adjusted width for constraints
        for line in constraint_lines:
            cv2.putText(img, line, (50, line_y), font_face, font_scale, font_color, thickness, cv2.LINE_AA)
            line_size, _ = cv2.getTextSize(line, font_face, font_scale, thickness)
            line_y += line_size[1] + 20

    # Save the image
    cv2.imwrite(output_file, img)
    return output_file

@app.route("/post_tweet", methods=['POST'])
def post_question_to_twitter(question=None):
    # Assuming you have a function to get the question details
    if not question:
        question = get_and_send_random_question()

    # Format the question data as needed
    image_path = generate_image_from_json(question, 'question_image.png')
    
    import tweepy

    auth = tweepy.OAuth1UserHandler(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET_KEY,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    api = tweepy.API(auth)
    clientV2  = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET_KEY,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        # bearer_token=TWITTER_BEARER_TOKEN
    )
    # Make a request to a Twitter API v2 endpoint
    tweet_text = f"Can you solve this Challenge??\n\n {question['title']}\n\n" \
             "Ready to elevate your career to new heights? Click the link below to join our daily challenge! " \
             "https://www.mailego.com/subscribe\n\n" \
             "#coding #DSA #100DaysOfCode #programming #algorithm #codingChallenge"

    try:
        media = api.media_upload(image_path)
        response = clientV2.create_tweet(text=tweet_text,media_ids=[media.media_id_string])
        return "tweet Posted", 200
    except Exception as e:
        return f'Error accessing Twitter API v2: {e}', 500

@app.route("/webhook/callback", methods=['POST'])
def webhook():
    print(request.data)
    return "Hello World"



@app.route("/post_question")
def upload_question():
    folder_path = 'api/questions/'
    files = os.listdir(folder_path)
    
    for file_name in files:
        # Step 2: Iterating Over Files
        file_path = os.path.join(folder_path, file_name)
        print(file_path)
        
        if os.path.isfile(file_path):
            # Step 3: Processing Each File
            question_data = parse_question_and_answer_file(file_path)
            
            # Step 4: Adding Data to Database
            add_question_to_db(question_data)
    return "Upload success"

if __name__ == '__main__':
    app.run(debug=True)
