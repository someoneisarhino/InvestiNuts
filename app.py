import os
import base64
import io
import google.generativeai as genai
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash # Added session and flash
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
        # Initialize user progress in session
        session['nuts'] = session.get('nuts', 0) # Keep existing nuts if already logged in? Or reset? Let's reset for simplicity on new login.
        session['nuts'] = 0
        session['lesson_3_1_q1_answered'] = False
        session['lesson_3_1_q2_answered'] = False
        session['lesson_2_1_q1_answered'] = False
        session['lesson_2_1_q2_answered'] = False
        session['lesson_2_1_q3_answered'] = False
        session['lesson_1_1_q1_answered'] = False
        session['lesson_1_1_q2_answered'] = False
        session['lesson_1_1_q1_answered'] = False
        session['lesson_1_1_q2_answered'] = False
        session['purchased_items'] = []
        session['equipped_item'] = None
        # Add keys for other questions/modules later as needed
        print(f"Login successful for: {email}. Initialized session progress.")
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
            # Initialize user progress in session
            session['nuts'] = 0
            session['lesson_3_1_q1_answered'] = False
            session['lesson_3_1_q2_answered'] = False
            session['lesson_2_1_q1_answered'] = False
            session['lesson_2_1_q2_answered'] = False
            session['lesson_2_1_q3_answered'] = False
            session['lesson_1_1_q1_answered'] = False
            session['lesson_1_1_q2_answered'] = False
            session['purchased_items'] = []
            session['equipped_item'] = None
            # Add keys for other questions/modules later as needed
            print(f"Signup successful for: {email}. Initialized session progress.")
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

@app.route('/reset_progress')
def reset_progress():
    """Resets user's Nuts and question progress in the session."""
    if 'email' in session:
        session['nuts'] = 0
        session['lesson_3_1_q1_answered'] = False
        session['lesson_3_1_q2_answered'] = False
        session['lesson_2_1_q1_answered'] = False
        session['lesson_2_1_q2_answered'] = False
        session['lesson_2_1_q3_answered'] = False
        session['lesson_1_1_q1_answered'] = False
        session['lesson_1_1_q2_answered'] = False
        session['purchased_items'] = []
        session['equipped_item'] = None
        # Reset other progress markers here if added later
        print(f"Reset progress for user: {session['email']}")
    # Redirect back to the page the user was on, or home as a fallback
    referrer = request.referrer or url_for('home')
    return redirect(referrer)

# --- End Route Protection & Logout ---


# --- Application Page Routes ---
@app.route('/home')
def home():
    """Renders the page with LEARN and CHAT buttons."""
    # require_login decorator handles authentication check
    # require_login decorator handles authentication check
    return render_template('home.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn')
def learn():
    """Renders the blank learning page."""
    # require_login decorator handles authentication check
    return render_template('learn.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/chat_page')
def chat_page():
    """Renders the chat interface page."""
    # require_login decorator handles authentication check
    return render_template('chat.html', user_email=session.get('email'), nuts=session.get('nuts', 0))
@app.route('/learn/module1')
def learn_module1():
    """Renders the page for Learning Module 1."""
    # require_login decorator handles authentication check implicitly via before_request
    return render_template('learn_module1.html', user_email=session.get('email'), nuts=session.get('nuts', 0))
@app.route('/learn/module2')
def learn_module2():
    """Renders the page for Learning Module 2."""
    # require_login decorator handles authentication check implicitly via before_request
    return render_template('learn_module2.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module3')
def learn_module3():
    """Renders the page for Learning Module 3."""
    # require_login decorator handles authentication check implicitly via before_request
    return render_template('learn_module3.html', user_email=session.get('email'), nuts=session.get('nuts', 0))
@app.route('/glossary')
def glossary():
    """Renders the glossary page."""
    return render_template('glossary.html', user_email=session.get('email'), nuts=session.get('nuts', 0))
# --- Shop Routes ---
SHOP_ITEMS = {
    "rainbowhat": {"name": "Rainbow Hat", "price": 15, "image": "rainbowhat.png", "full_image": "nuttyrainbowhat.jpg"},
    "bowtie": {"name": "Bowtie", "price": 10, "image": "bowtie.png", "full_image": "nuttybowtie.jpg"}, # Assuming nuttybowtie.jpg exists
    "brownhat": {"name": "Brown Hat", "price": 10, "image": "brownhat.png", "full_image": "nuttybrownhat.jpg"}, # Assuming nuttybrownhat.jpg exists
    "camobowtie": {"name": "Camo Bowtie", "price": 10, "image": "camobowtie.png", "full_image": "nuttycamobowtie.jpg"},
    "greenpolkadot": {"name": "Green Polkadot Tie", "price": 10, "image": "greenpolkadottie.png", "full_image": "nuttygreenpolkadot.jpg"}, # Assuming nuttygreenpolkadot.jpg exists
    "pinkhat": {"name": "Pink Hat", "price": 10, "image": "pinkhat.png", "full_image": "nuttypinkhat.jpg"}, # Assuming nuttypinkhat.jpg exists
    "purpletie": {"name": "Purple Tie", "price": 10, "image": "purpletie.png", "full_image": "nuttypurpletie.jpg"}, # Assuming nuttypurpletie.jpg exists
    "redorangetie": {"name": "Red/Orange Tie", "price": 10, "image": "redorangetie.png", "full_image": "nuttyredorangetie.jpg"}, # Assuming nuttyredorangetie.jpg exists
    "sprout": {"name": "Sprout", "price": 5, "image": "sprout.png", "full_image": "nuttysprout.jpg"},
    "whitebluetie": {"name": "White/Blue Tie", "price": 10, "image": "whitebluetie.png", "full_image": "nuttywhitebluetie.jpg"}, # Assuming nuttywhitebluetie.jpg exists
    "yellowflower": {"name": "Yellow Flower", "price": 5, "image": "yellowflower.png", "full_image": "nuttyyellowflower.jpg"}, # Assuming nuttyyellowflower.jpg exists
}

@app.route('/shop')
def shop():
    """Renders the main shop page."""
    # Pass item details (like image filenames) to the template
    # Also pass purchase status for greying out/disabling links
    purchased_items = session.get('purchased_items', [])
    items_for_template = {id: {'image': data['image'], 'purchased': id in purchased_items} for id, data in SHOP_ITEMS.items()}
    return render_template('shop.html', user_email=session.get('email'), nuts=session.get('nuts', 0), items=items_for_template)

@app.route('/shop/item/<item_id>')
def shop_item(item_id):
    """Renders the purchase confirmation page for a specific item."""
    item = SHOP_ITEMS.get(item_id)
    if not item:
        flash("Item not found!", "error")
        return redirect(url_for('shop'))

    purchased = item_id in session.get('purchased_items', [])
    return render_template('shop_item.html', user_email=session.get('email'), nuts=session.get('nuts', 0), item_id=item_id, item=item, purchased=purchased)

@app.route('/shop/purchase/<item_id>', methods=['POST'])
def purchase_item(item_id):
    """Handles the purchase logic for an item."""
    if 'email' not in session:
        return redirect(url_for('index'))

    item = SHOP_ITEMS.get(item_id)
    if not item:
        flash("Item not found!", "error")
        return redirect(url_for('shop'))

    purchased_items = session.get('purchased_items', [])
    if item_id in purchased_items:
        flash("You already own this item!", "info")
        return redirect(url_for('shop'))

    current_nuts = session.get('nuts', 0)
    item_price = item['price']

    if current_nuts >= item_price:
        # Deduct nuts
        session['nuts'] = current_nuts - item_price
        # Add item to purchased list
        purchased_items.append(item_id)
        session['purchased_items'] = purchased_items
        # Set this as the equipped item
        # session['equipped_item'] = item_id # Removed: Nutty image should not change
        session.modified = True
        flash(f"Successfully purchased {item['name']}!", "success")
        print(f"User {session['email']} purchased {item_id}. Nuts remaining: {session['nuts']}")
        return redirect(url_for('shop'))
    else:
        flash("Not enough Nuts to purchase this item!", "error")
        print(f"User {session['email']} failed purchase of {item_id}. Has {current_nuts}, needs {item_price}.")
        return redirect(url_for('shop_item', item_id=item_id))

# --- End Shop Routes ---



@app.route('/learn/module3/lesson1/page1')
def lesson_3_1_page1():
    """Renders the first page of Lesson 3.1."""
    return render_template('lesson_3_1_page1.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module3/lesson1/page2')
def lesson_3_1_page2():
    """Renders the second page of Lesson 3.1."""
    return render_template('lesson_3_1_page2.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module3/lesson1/practice')
def lesson_3_1_practice():
    """Renders the practice page for Lesson 3.1."""
    # Pass question answered status to the template
    q1_answered = session.get('lesson_3_1_q1_answered', False)
    return render_template('lesson_3_1_practice.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q1_answered=q1_answered)

@app.route('/learn/module3/lesson1/practice/q2')
def lesson_3_1_practice_q2():
    """Renders the second practice question page for Lesson 3.1."""
    q2_answered = session.get('lesson_3_1_q2_answered', False)
    return render_template('lesson_3_1_practice_q2.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q2_answered=q2_answered)

@app.route('/learn/module2/lesson1/page1')
def lesson_2_1_page1():
    """Renders the first page of Lesson 2.1."""
    return render_template('lesson_2_1_page1.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module2/lesson1/page2')
def lesson_2_1_page2():
    """Renders the second page of Lesson 2.1."""
    return render_template('lesson_2_1_page2.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module2/lesson1/practice')
def lesson_2_1_practice():
    """Renders the practice page for Lesson 2.1."""
    q1_answered = session.get('lesson_2_1_q1_answered', False)
    return render_template('lesson_2_1_practice.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q1_answered=q1_answered)

@app.route('/learn/module2/lesson1/practice/q2')
def lesson_2_1_practice_q2():
    """Renders the second practice question page for Lesson 2.1."""
    q2_answered = session.get('lesson_2_1_q2_answered', False)
    return render_template('lesson_2_1_practice_q2.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q2_answered=q2_answered)

@app.route('/learn/module2/lesson1/practice/q3')
def lesson_2_1_practice_q3():
    """Renders the third practice question page for Lesson 2.1."""
    q3_answered = session.get('lesson_2_1_q3_answered', False)
    return render_template('lesson_2_1_practice_q3.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q3_answered=q3_answered)

@app.route('/learn/module1/lesson1/page1')
def lesson_1_1_page1():
    """Renders the first page of Lesson 1.1."""
    return render_template('lesson_1_1_page1.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module1/lesson1/page2')
def lesson_1_1_page2():
    """Renders the second page of Lesson 1.1."""
    return render_template('lesson_1_1_page2.html', user_email=session.get('email'), nuts=session.get('nuts', 0))

@app.route('/learn/module1/lesson1/practice')
def lesson_1_1_practice():
    """Renders the practice page for Lesson 1.1."""
    # Add logic later to track answered status if needed
    return render_template('lesson_1_1_practice.html', user_email=session.get('email'), nuts=session.get('nuts', 0))
@app.route('/learn/module1/lesson1/practice/q2')
def lesson_1_1_practice_q2():
    """Renders the second practice question page for Lesson 1.1."""
    q2_answered = session.get('lesson_1_1_q2_answered', False)
    return render_template('lesson_1_1_practice_q2.html', user_email=session.get('email'), nuts=session.get('nuts', 0), q2_answered=q2_answered)



# --- End Application Page Routes ---

# --- Answer Submission Routes ---
@app.route('/submit_answer/lesson3_1_q1', methods=['POST'])
def submit_lesson_3_1_q1():
    """Handles submission for Lesson 3.1, Question 1."""
    if 'email' not in session:
        return redirect(url_for('index')) # Redirect if not logged in

    if not session.get('lesson_3_1_q1_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'b'
    
        session['lesson_3_1_q1_answered'] = True
        session['lesson_3_1_q1_correct'] = (answer == correct_answer)

        if session['lesson_3_1_q1_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q1 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q1 incorrectly.")

        session.modified = True  # Make sure session updates
    else:
        print(f"User {session['email']} tried to re-answer Q1.")

    # Redirect to the next question page
    return redirect(url_for('lesson_3_1_practice_q2'))

@app.route('/submit_answer/lesson3_1_q2', methods=['POST'])
def submit_lesson_3_1_q2():
    """Handles submission for Lesson 3.1, Question 2."""
    if 'email' not in session:
        return redirect(url_for('index')) # Redirect if not logged in

    if not session.get('lesson_3_1_q2_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'c'
    
        session['lesson_3_1_q2_answered'] = True
        session['lesson_3_1_q2_correct'] = (answer == correct_answer)

        if session['lesson_3_1_q2_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q2 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q2 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q2.")

    # Redirect back to Module 3 overview after the last question
    # Or redirect to a "Lesson Complete" page in the future
    return redirect(url_for('learn_module3'))
@app.route('/submit_answer/lesson2_1_q1', methods=['POST'])
def submit_lesson_2_1_q1():
    """Handles submission for Lesson 2.1, Question 1."""
    if 'email' not in session:
        return redirect(url_for('index'))     
        
    if not session.get('lesson_2_1_q1_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'a'
    
        session['lesson_2_1_q1_answered'] = True
        session['lesson_2_1_q1_correct'] = (answer == correct_answer)

        if session['lesson_2_1_q1_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q1 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q1 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q1.")

    return redirect(url_for('lesson_2_1_practice_q2')) # Redirect to Q2

@app.route('/submit_answer/lesson2_1_q2', methods=['POST'])
def submit_lesson_2_1_q2():
    """Handles submission for Lesson 2.1, Question 2."""
    if 'email' not in session:
        return redirect(url_for('index'))

    if not session.get('lesson_2_1_q2_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'c'
    
        session['lesson_2_1_q2_answered'] = True
        session['lesson_2_1_q2_correct'] = (answer == correct_answer)

        if session['lesson_2_1_q2_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q2 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q2 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q1.")

    return redirect(url_for('lesson_2_1_practice_q3')) # Redirect to Q3

@app.route('/submit_answer/lesson2_1_q3', methods=['POST'])
def submit_lesson_2_1_q3():
    """Handles submission for Lesson 2.1, Question 3."""
    if 'email' not in session:
        return redirect(url_for('index'))

    if not session.get('lesson_2_1_q3_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'd'
    
        session['lesson_2_1_q3_answered'] = True
        session['lesson_2_1_q3_correct'] = (answer == correct_answer)

        if session['lesson_2_1_q3_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q3 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q3 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q1.")

    return redirect(url_for('learn_module2')) # Redirect back to Module 2 overview
@app.route('/submit_answer/lesson1_1_q1', methods=['POST'])
def submit_lesson_1_1_q1():
    """Handles submission for Lesson 1.1, Question 1."""
    if 'email' not in session:
        return redirect(url_for('index'))

    if not session.get('lesson_1_1_q1_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'd'
    
        session['lesson_1_1_q1_answered'] = True
        session['lesson_1_1_q1_correct'] = (answer == correct_answer)

        if session['lesson_1_1_q1_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q1 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q1 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q1.")

    return redirect(url_for('lesson_1_1_practice_q2')) # Redirect to Q2

@app.route('/submit_answer/lesson1_1_q2', methods=['POST'])
def submit_lesson_1_1_q2():
    """Handles submission for Lesson 1.1, Question 2."""
    if 'email' not in session:
        return redirect(url_for('index'))

    if not session.get('lesson_1_1_q2_answered', False):
        answer = request.form.get('answer')
        correct_answer = 'b'
    
        session['lesson_1_1_q2_answered'] = True
        session['lesson_1_1_q2_correct'] = (answer == correct_answer)

        if session['lesson_1_1_q2_correct']:
            session['nuts'] = session.get('nuts', 0) + 10
            print(f"User {session['email']} answered Q2 correctly. Nuts: {session['nuts']}")
        else:
            print(f"User {session['email']} answered Q2 incorrectly.")

        session.modified = True
    else:
        print(f"User {session['email']} tried to re-answer Q2.")

    # Since this is the last question for this lesson, redirect back to Module 1 overview
    return redirect(url_for('learn_module1'))



# --- End Answer Submission Routes ---


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
        # Prepend instruction for brevity
        instruction = "Please answer the following question succinctly, in 2-3 sentences.\n\n"
        full_user_message = instruction + context_message + user_message
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