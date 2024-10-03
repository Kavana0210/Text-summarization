import streamlit as st
import pandas as pd
import hashlib
import firebase_admin
from firebase_admin import credentials, firestore
import webbrowser
from transformers import BartForConditionalGeneration, BartTokenizer
import torch
import time
import json
from datetime import datetime, timedelta
import os
from PIL import Image
import pytesseract
from streamlit_option_menu import option_menu

# Initialize Firebase (ensure it's only initialized once)
if not firebase_admin._apps:
    cred = credentials.Certificate("/Users/kavan/Downloads/Text Summarization/login-e116e-firebase-adminsdk-urv3x-d5b15d0c98.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Convert password to hash format
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Check if hashed passwords match
def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# DB Functions for create table
def create_usertable():
    # Firestore is schema-less, no need to explicitly create tables
    pass

# Insert the data into table
def add_userdata(username, email, password):
    users_ref = db.collection('userstable')
    users_ref.add({
        'username': username,
        'email': email,
        'password': password
    })

# Password and email fetch
def login_user(email):
    users_ref = db.collection('userstable')
    query = users_ref.where('email', '==', email).stream()
    for doc in query:
        return doc.to_dict()
    return None

# Update password
def update_password(email, new_password):
    users_ref = db.collection('userstable')
    query = users_ref.where('email', '==', email).stream()
    for doc in query:
        users_ref.document(doc.id).update({'password': make_hashes(new_password)})

def view_all_users():
    users_ref = db.collection('userstable')
    users = users_ref.stream()
    return [user.to_dict() for user in users]

# Summarization Tool Page
def summarization_tool():
    st.markdown('<div><h2>Summarization Tool</h2></div>', unsafe_allow_html=True)
    
    model_path = '/Users/kavan/Downloads/Text Summarization/fine_tuned_bart'
    model = BartForConditionalGeneration.from_pretrained(model_path)
    tokenizer = BartTokenizer.from_pretrained('/Users/kavan/Downloads/Text Summarization/tokenizer')
    
    def load_history():
        history_file = f'{st.session_state.username}_history.json'
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        else:
            return []
    
    def save_history(history):
        history_file = f'{st.session_state.username}_history.json'
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def categorize_history(history):
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        today_entries = []
        yesterday_entries = []
        previous_entries = []

        for entry in history:
            entry_date = datetime.fromisoformat(entry['timestamp']).date()
            if entry_date == today:
                today_entries.append(entry)
            elif entry_date == yesterday:
                yesterday_entries.append(entry)
            else:
                previous_entries.append(entry)

        return today_entries, yesterday_entries, previous_entries
    
    history = load_history()
    today_entries, yesterday_entries, previous_entries = categorize_history(history)
    
    menu = ["Home", "Enter Text", "Upload Document"]
    choice = st.sidebar.selectbox("Menu", menu)

    options = ['Small', 'Medium', 'Large', 'Extra Large']
    
    size = st.sidebar.select_slider(
        'Select the size:',
        options=options,
        value='Medium'
    )
    
    if size == "Medium":
        min_len = 250
        max_len = 400
    elif size == "Large":
        min_len = 400
        max_len = 550
    elif size == "Extra Large":
        min_len = 550
        max_len = 700
    else:
        min_len = 100
        max_len = 250
    
    if choice == "Home":
        st.subheader("Home")
        st.write('<p style="color:#36454F; font-size:18px;">Transforming Long Reads into Clear Insights – Your Ultimate Text Summarization Tool.</p>', unsafe_allow_html=True)
        st.write('<p style="color:white; font-size:15px;">Welcome to our Text Summarization Tool, your go-to solution for transforming lengthy articles, reports, and documents into concise, easy-to-read summaries. Our advanced algorithms ensure that you capture the essence of any text, saving you valuable time and effort. Whether you\'re a student, researcher, or professional, our tool helps you stay informed and focused on what matters most. Try it out today and experience the power of efficient reading!</p>', unsafe_allow_html=True)
        prompt = st.chat_input("Say something")
        if prompt:
            st.write(f"User has sent the following prompt: {prompt}")
    elif choice == "Enter Text":
        st.subheader("Enter Text")
        text = st.text_area("Enter text here...")
        if st.button("Summarize"):
            if text:
                inputs = tokenizer(text, max_length=1024, truncation=True, return_tensors='pt')
                summary_ids = model.generate(inputs['input_ids'], max_length=max_len, min_length=min_len, num_beams=4, early_stopping=True)
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                st.subheader("Summary")
                
                def stream():
                    for word in summary.split(" "):
                        yield word + " "
                        time.sleep(0.05)
                
                st.write_stream(stream)
                
                history_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'text': text,
                    'summary': summary
                }
                    
                history.append(history_entry)
                save_history(history)
            else:
                st.write("Please enter some text to summarize.") 

    elif choice == "Upload Document":
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            if st.button("Summarize"):
                image = Image.open(uploaded_file)
                st.image(image, caption='Uploaded Image.', use_column_width=True)
                st.write("")
                st.write("Extracting text...")

                text = pytesseract.image_to_string(image)
                st.text_area("Extracted Text", text, height=200)
                
                inputs = tokenizer(text, max_length=1024, truncation=True, return_tensors='pt')
                summary_ids = model.generate(inputs['input_ids'], max_length=max_len, min_length=min_len, num_beams=3, early_stopping=True)
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                st.subheader("Summary")
                
                def stream():
                    for word in summary.split(" "):
                        yield word + " "
                        time.sleep(0.05)
                
                st.write_stream(stream)   
                
                history_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'text': text,
                    'summary': summary
                }
                    
                history.append(history_entry)
                save_history(history)
                         
    st.sidebar.title('History')
    
    if today_entries:
        st.sidebar.write('### Today')
        for entry in today_entries:
            if st.sidebar.button(entry['timestamp']):
                st.sidebar.write(f"**Summary:** {entry['summary']}")
    
    if yesterday_entries:
        st.sidebar.write('### Yesterday')
        for entry in yesterday_entries:
            if st.sidebar.button(entry['timestamp']):
                st.sidebar.write(f"**Summary:** {entry['summary']}")
    
    if previous_entries:
        st.sidebar.write('### Previous Days')
        for entry in previous_entries:
            if st.sidebar.button(entry['timestamp']):
                st.sidebar.write(f"**Summary:** {entry['summary']}")

# Change Password Page
def change_password():
    st.markdown("""
        <style>
            .main {
                background: #71797E;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.1);
                color: white;
            }
            .title h1 {
                color: #36454F;
                text-align: center;
            }
            .box {
                background: #A9A9A9;
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
                
            }
            .stButton{
                justify-content: center;
                align-items: center;
            }
            .stButton button {
                background: #B2BEB5;
                color: white;
                border: none;
                padding: 20px;
                border-radius: 5px;
                width: 700px;
                height: 20px;
                justify-content: center;
                align-items: center;
                margin: 5px;
                cursor: pointer;
            }
            .stButton button:hover {
                background: #B2BEB5;
            }

        </style>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="title"><h1>Welcome!</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="box"><h2>Change Password</h2></div>', unsafe_allow_html=True)
    email = st.text_input("Enter email address", key='change_email')
    old_password = st.text_input("Enter old password", type='password', key='change_old_password')
    new_password = st.text_input("Enter new password", type='password', key='change_new_password')

    if st.button("Change Password", key='change_password_button'):
        user_data = login_user(email)
        if user_data and check_hashes(old_password, user_data['password']):
            update_password(email, new_password)
            st.success("Password changed successfully!")
        else:
            st.error("Invalid email or old password")

# About Page
def about():
    st.markdown('<div class="box"><h2>About</h2></div>', unsafe_allow_html=True)
    st.write('<p style="color:white; font-size:15px;">Welcome to our text summarization application! We are dedicated to providing efficient and accurate text summarization solutions. Our tool is designed to help you extract key insights from lengthy documents, saving you time and effort. Whether you need to summarize articles, reports, or any other textual content, our application can assist you in generating concise summaries.</p>', unsafe_allow_html=True)

# Main Function
def main():
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Home", "Summarization Tool", "About", "Logout"])

    if choice == "Home":
        st.markdown('<div class="box"><h2>Home</h2></div>', unsafe_allow_html=True)
        st.write('<p style="color:white; font-size:15px;">Welcome to the Text Summarization Application!</p>', unsafe_allow_html=True)

    elif choice == "Summarization Tool":
        summarization_tool()

    elif choice == "About":
        about()

    elif choice == "Logout":
        st.session_state.logged_in = False
        st.experimental_rerun()

# Login Page
def login():
    st.markdown("""
        <style>
            .main {
                background: #71797E;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.1);
                color: white;
            }
            .title h1 {
                color: #36454F;
                text-align: center;
            }
            .box {
                background: #A9A9A9;
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
                
            }
            .stButton{
                justify-content: center;
                align-items: center;
            }
            .stButton button {
                background: #B2BEB5;
                color: white;
                border: none;
                padding: 20px;
                border-radius: 5px;
                width: 700px;
                height: 20px;
                justify-content: center;
                align-items: center;
                margin: 5px;
                cursor: pointer;
            }
            .stButton button:hover {
                background: #B2BEB5;
            }

        </style>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="title"><h1>Welcome!</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="box"><h2>Login</h2></div>', unsafe_allow_html=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type='password')

    if st.button("Login"):
        user_data = login_user(email)
        if user_data and check_hashes(password, user_data['password']):
            st.session_state.logged_in = True
            st.session_state.username = user_data['username']
            st.experimental_rerun()
        else:
            st.error("Invalid email or password")

# Signup Page
def signup():
    st.markdown("""
        <style>
            .main {
                background: #71797E;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.1);
                color: white;
            }
            .title h1 {
                color: #36454F;
                text-align: center;
            }
            .box {
                background: #A9A9A9;
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
                
            }
            .stButton{
                justify-content: center;
                align-items: center;
            }
            .stButton button {
                background: #B2BEB5;
                color: white;
                border: none;
                padding: 20px;
                border-radius: 5px;
                width: 700px;
                height: 20px;
                justify-content: center;
                align-items: center;
                margin: 5px;
                cursor: pointer;
            }
            .stButton button:hover {
                background: #B2BEB5;
            }

        </style>
            """, unsafe_allow_html=True)
    st.markdown('<div class="title"><h1>Welcome!</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="box"><h2>Create Account</h2></div>', unsafe_allow_html=True)
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type='password')

    if st.button("Signup"):
        if not login_user(email):
            add_userdata(username, email, make_hashes(password))
            st.success("Account created successfully! Please login.")
        else:
            st.error("Email already exists. Please use a different email.")

# Main App
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main()
else:
    with st.sidebar:
        page = option_menu("Navigation", 
                           ["Login", "Signup", "Change Password"],
                           icons=['person', 'person-plus','key'], 
                           menu_icon="menu-app",
                           )
        
    
    #page = st.sidebar.selectbox("Select a page", ["Login", "Signup","change password"])
    if page == "Login":
        login()
    elif page == "Signup":
        signup()
    elif page == "Change Password":
        change_password()
