from flask import Flask, render_template, request, redirect ,url_for,session
import requests
from werkzeug.utils import secure_filename
import uuid
from io import BytesIO
import tempfile

import ast
import re
from apscheduler.schedulers.background import BackgroundScheduler
from htmlbody import *
import uuid
from firebase import firebase_admin
from firebase_admin import auth

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pandas as pd
from datetime import *
import smtplib
from firebase import firebase_ref
import boto3
from werkzeug.utils import secure_filename
import secrets
secrets.token_hex(16)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['token'] = ""
app.config['email'] = ""
# app.config['UPLOAD_FOLDER_prescriptions'] = os.path.join(
#     os.path.dirname(os.path.abspath(__file__)), 'frontend', 'uploads'
# )

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
# scheduler.__init__(app)
scheduler.start()

api_url = "http://127.0.0.1:5000"


medicine_data = pd.read_csv(r'scanPlus-main1\scanPlus-main\frontend\A_Z_medicines_dataset_of_India.csv')






@app.route("/", methods = ["GET"])
def home_page():
    return render_template("home.html")

@app.route("/about", methods = ["GET"])
def about():
    return render_template("about.html")

@app.route("/contact", methods = ["GET"])
def contact():
    return render_template("contact.html")

@app.route("/compare", methods = ["GET"])
def comapre():
    return render_template("compare.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    
    if request.method == "GET":
        if not app.config['token']:
            return redirect(url_for('scan'))  # Redirect to login if not authenticated

        url = "http://127.0.0.1:5000/dashboard"
        headers = {
            'Authorization': 'Bearer ' + app.config['token']
        }

        response = requests.request("GET", url, headers=headers)

        if response.status_code == 200:
            data = ast.literal_eval(response.text)
            name = data.get('name', 'Unknown')
            return render_template("dashboard.html", name=name)
        else:
            return "Invalid Token"
    else:
        # Handle POST request if needed
        pass




@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        dob = request.form['dob']
        gender = request.form['gender']
        location = request.form['location']

        # Store user data in Firebase
        new_user = {
            'name': name,
            'email': email,
            'password': password,  # Note: You should NOT store passwords in plaintext in a real app
            'dob': dob,
            'gender': gender,
            'location': location
        }
        firebase_ref.push(new_user)
        session['email'] = email
        # Redirect to dashboard after successful signup
        return render_template('login.html')

    else:
        # Handle GET request if needed
        return render_template('signup.html')
    
@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        try:
            # Get the user by email
            users = firebase_ref.order_by_child('email').equal_to(email).get()

            if users:
                # Since email should be unique, there should be only one user
                user_key = list(users.keys())[0]
                user_data = users[user_key]

                # Check if the provided password matches the stored password
                if user_data['password'] == password:
                    # Passwords match, redirect to dashboard
                    user_name = user_data['name']  # Get the user's name
                    return render_template("dashboard.html", user_name=user_name)
                else:
                    # Passwords don't match, redirect to login with status=invalid
                    return redirect("/login?status=invalid")
            else:
                # User not found, redirect to login with status=invalid
                return redirect("/login?status=invalid")

        except Exception as e:
            # Handle any other exceptions
            print(str(e))
            return redirect("/login?status=error")

    else:
        status = request.args.get('status')
        return render_template("login.html", status=status)


import boto3
import os
os.environ['AWS_ACCESS_KEY_ID'] = ''
os.environ['AWS_SECRET_ACCESS_KEY'] = ''
os.environ['AWS_DEFAULT_REGION'] = ''


textract = boto3.client('textract')


def detectText(local_file):
    with open(local_file, 'rb') as document:
        response = textract.detect_document_text(Document={'Bytes': document.read()})
    
    text = ""
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            text += " " + item["Text"]
    
    return text

@app.route("/scan.html", methods=["GET", "POST"])
def scan():
    if request.method == "POST":
        if 'picture' not in request.files:
            return redirect(request.url)
        
        # Get the uploaded file
        pic = request.files['picture']

        # Generate a temporary file path
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file_path = temp_file.name

        # Save the uploaded image to the temporary file
        pic.save(temp_file_path)

       
        detected_text = detectText(temp_file_path)
        
        # Close and delete the temporary file
        temp_file.close()
        os.unlink(temp_file_path)

        # Redirect to scan_result.html with detected text as parameter
        return redirect(url_for('scan_result', detected_text=detected_text))

    else:
        # Render the scan template for GET requests
        return render_template("scan.html")






# Define a new route for scan_result.html
@app.route("/scan_result.html")
def scan_result():
    # Get the detected text from the URL parameter
    detected_text = request.args.get('detected_text', '')
    
    # Render the scan_result.html template with the detected text
    return render_template("scan_result.html", detected_text=detected_text)



        
@app.route("/dashboard/upload", methods=["POST"])
def dashboard_upload():
    
    if request.method == "POST":
        
        # Get the uploaded image
        image = request.files['prescription']

        # Generate a unique filename for the uploaded image
        pic_filename = secure_filename(image.filename)
        pic_name = str(uuid.uuid1()) + "_" + pic_filename

        # Save the uploaded image to the specified directory
        upload_folder_prescriptions = app.config['UPLOAD_FOLDER_prescriptions']
        image.save(os.path.join(upload_folder_prescriptions, pic_name))

        # Prepare data for the API
        data = {
            'pic_name': pic_name,
            'email': app.config['email']  # Make sure this is set somewhere in your app
        }

        url = "http://127.0.0.1:5000/dashboard/upload_prescription"
        headers = {
            'Authorization': 'Bearer ' + app.config['token']
        }

        response = requests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            # Prescription upload successful
            return "Prescription uploaded successfully."
        else:
            # Handle any errors
            return "Error uploading prescription."

    else:
        # Render the scan template for GET requests
        return render_template("scan.html")
    
from difflib import SequenceMatcher
def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()
@app.route('/search', methods=['POST'])
def search():
    # Get the search query from the form
    medicine_name = request.form.get('medicine_name')

    # Calculate similarity scores for all medicine names in the DataFrame
    similarity_scores = medicine_data['name'].apply(lambda x: similarity_ratio(x, medicine_name))

    # Filter the DataFrame for medicine names with similarity scores above a threshold
    threshold = 0.7
    filtered_df = medicine_data[similarity_scores > threshold]

    if filtered_df.empty:
        search_results = []
    else:
        # Group the filtered DataFrame by manufacturer and calculate the minimum price
        comparison_df = filtered_df.groupby('manufacturer_name')['price(₹)'].min().reset_index()
        # Convert the comparison DataFrame to a list of dictionaries
        search_results = comparison_df.to_dict(orient='records')

    return render_template('compare.html', search_results=search_results)

if __name__=="__main__":
    app.run(debug=True, port=8000)