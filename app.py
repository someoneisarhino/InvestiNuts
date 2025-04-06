import os
import base64
import io
import google.generativeai as genai
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session # Added session
from dotenv import load_dotenv
from PIL import Image # Import Pillow
# import re

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management if we add it later, good practice

# --- Login File Handling ---
LOGIN_FILE = os.path.join('static', 'logins.env')

def read_logins():
    """Reads logins from the logins.env file."""
    logins = {}
    try:
        if os.path.exists(LOGIN_FILE):
            with open(LOGIN_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        # Split only on the first '=', allowing '=' in passwords
                        email, password = line.split('=', 1)
                        logins[email.strip()] = password.strip()
    except Exception as e:
        print(f"Error reading login file: {e}")
    return logins

def write_login(email, password):
    """Appends a new login to the logins.env file."""
    try:
        # Ensure the static directory exists
        os.makedirs(os.path.dirname(LOGIN_FILE), exist_ok=True)
        with open(LOGIN_FILE, 'a') as f:
            f.write(f"{email}={password}\n")
        return True
    except Exception as e:
        print(f"Error writing to login file: {e}")
        return False

def check_login(email, password):
    """Checks if email and password match stored credentials."""
    logins = read_logins()
    return logins.get(email) == password

def email_exists(email):
    """Checks if an email already exists in the login file."""
    logins = read_logins()
    return email in logins
# --- End Login File Handling ---

# Configure the Google Gemini API
try:
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
    # Use a model that supports vision, like gemini-pro-vision or a newer equivalent
    # 'gemini-2.0-flash' might not support multimodal input directly in this way.
    # Let's assume 'gemini-1.5-flash' or similar is needed for image input.
    # Check Google AI documentation for the correct model supporting image+text.
    # For now, we'll proceed assuming a compatible model exists.
    # If 'gemini-2.0-flash' *does* support multimodal, keep it. Otherwise, adjust.
    model_name = 'gemini-1.5-flash-latest' # Example: Use a known multimodal model
    print(f"Using Gemini model: {model_name}")
    model = genai.GenerativeModel(model_name)
except Exception as e:
    print(f"Error configuring Google Gemini: {e}")
    model = None # Set model to None if configuration fails

@app.route('/')
def index():
    """Renders the main chat page."""
    # This now renders the main menu / login page
    return render_template('index.html')

# --- Authentication Routes ---
@app.route('/login', methods=['POST'])
def login():
    """Handles user login."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    if check_login(email, password):
        session['email'] = email # Store email in session
        print(f"Login successful for: {email}")
        return jsonify({"success": True})
    else:
        print(f"Login failed for: {email}")
        session.pop('email', None) # Ensure session is clear on failed login
        # Check if the email exists at all to give a slightly more specific (but less secure) message
        # if email_exists(email):
        #     return jsonify({"success": False, "message": "Incorrect password."}), 401
        # else:
        #     return jsonify({"success": False, "message": "Account not found! Please sign up."}), 401
        # Sticking to the requested message:
        return jsonify({"success": False, "message": "Account not found! Please sign up."}), 401


@app.route('/signup', methods=['POST'])
def signup():
    """Handles user signup."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    # Basic validation (can be expanded)
    if '@' not in email or '.' not in email.split('@')[-1]:
         return jsonify({"success": False, "message": "Invalid email format."}), 400
    # Add password complexity rules if desired

    if email_exists(email):
        print(f"Signup attempt failed: Email {email} already exists.")
        return jsonify({"success": False, "message": "Email already exists. Please log in."}), 409 # 409 Conflict
    else:
        if write_login(email, password):
            session['email'] = email # Store email in session after successful signup
            print(f"Signup successful for: {email}")
            return jsonify({"success": True})
        else:
            print(f"Signup failed for {email}: Could not write to file.")
            return jsonify({"success": False, "message": "Signup failed. Please try again later."}), 500
# --- End Authentication Routes ---

# --- Route Protection & Logout ---
@app.before_request
def require_login():
    """Redirects to login page if user is not logged in and accessing protected routes."""
    allowed_routes = ['login', 'signup', 'index', 'static'] # Routes accessible without login
    if 'email' not in session and request.endpoint not in allowed_routes:
        print(f"User not logged in, redirecting from {request.endpoint}")
        return redirect(url_for('index')) # Redirect to the main login/signup page

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    print(f"Logging out user: {session.get('email')}")
    session.pop('email', None)
    return redirect(url_for('index'))
# --- End Route Protection & Logout ---


# --- Application Page Routes ---
@app.route('/home')
def home():
    """Renders the page with LEARN and CHAT buttons."""
    # require_login decorator handles authentication check
    # require_login decorator handles authentication check
    return render_template('home.html', user_email=session.get('email'))

@app.route('/learn')
def learn():
    """Renders the blank learning page."""
    # require_login decorator handles authentication check
    return render_template('learn.html', user_email=session.get('email'))

@app.route('/chat_page')
def chat_page():
    """Renders the chat interface page."""
    # require_login decorator handles authentication check
    return render_template('chat.html', user_email=session.get('email'))
@app.route('/learn/module1')
def learn_module1():
    """Renders the page for Learning Module 1."""
    # require_login decorator handles authentication check implicitly via before_request
    return render_template('learn_module1.html', user_email=session.get('email'))
@app.route('/learn/module2')
def learn_module2():
    """Renders the page for Learning Module 2."""
    # require_login decorator handles authentication check implicitly via before_request
    return render_template('learn_module2.html', user_email=session.get('email'))


# --- End Application Page Routes ---


@app.route('/chat', methods=['POST'])
def chat(): # Renamed back to chat
    """Handles chat requests, potentially including images."""
    if not model:
        return jsonify({"error": "Gemini model not configured properly."}), 500

    try:
        data = request.get_json()
        user_message = data.get('message', '') # Get message, default to empty string
        image_data_base64 = data.get('image_data') # Get base64 image data
        csv_data = data.get('csv_data', []) # Get CSV data [{name: string, content: string}]

        # Check if at least one input type is provided
        if not user_message and not image_data_base64 and not csv_data:
            return jsonify({"error": "No message, image, or CSV file provided."}), 400

        # Prepare content parts for the API
        content_parts = []
        if image_data_base64:
            try:
                # Decode the base64 string
                image_bytes = base64.b64decode(image_data_base64)
                # Use Pillow to open the image and get format/data
                img = Image.open(io.BytesIO(image_bytes))
                # Gemini API typically needs mime type and raw bytes
                # Determine mime type (common types)
                mime_type = Image.MIME.get(img.format)
                if not mime_type:
                     # Fallback or raise error if format unknown/unsupported
                     print(f"Warning: Unknown image format {img.format}. Falling back to PNG.")
                     mime_type = "image/png" # Default or guess

                # Add image part for the API
                content_parts.append({
                    "mime_type": mime_type,
                    "data": image_bytes
                })
            except Exception as img_err:
                print(f"Error processing image: {img_err}")
                return jsonify({"error": f"Failed to process image: {str(img_err)}"}), 400

        # --- Prepare context including CSV data ---
        context_message = ""
        if csv_data:
            context_message += "Use the following CSV data as context:\n\n"
            for csv_file in csv_data:
                # Removed escape_latex calls
                csv_name = csv_file.get('name', 'Unnamed')
                csv_content = csv_file.get('content', '')
                context_message += f"--- START CSV: {csv_name} ---\n"
                context_message += csv_content
                context_message += f"\n--- END CSV: {csv_name} ---\n\n"
            context_message += "Now, answer the following question:\n"

        # Combine context (if any) with the user's actual message
        full_user_message = context_message + user_message
        # --- End Prepare context ---


        # Add text part if present (now includes CSV context)
        if full_user_message:
             content_parts.append(full_user_message) # Send combined message

        # Generate content using the Gemini model with combined parts
        print(f"Sending to Gemini: {len(content_parts)} parts (Text: {'Yes' if full_user_message else 'No'}, Image: {'Yes' if image_data_base64 else 'No'}, CSVs: {len(csv_data)})")
        response = model.generate_content(content_parts)

        # Ensure response.text exists and is not empty
        bot_message = response.text if hasattr(response, 'text') and response.text else "Sorry, I couldn't generate a response."

        # Return both user message and bot reply for frontend processing
        # Return the ORIGINAL user message and the RAW bot reply (no escaping)
        # Return just the reply, the frontend already has the user message
        return jsonify({"reply": bot_message})

    except Exception as e:
        print(f"Error during chat generation: {e}")
        # Check for specific API errors if possible
        if "API key not valid" in str(e):
             return jsonify({"error": "Invalid Google Gemini API Key."}), 500
        # Add more specific error handling if needed
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Use debug=True for development, turn off for production
    app.run(debug=True)