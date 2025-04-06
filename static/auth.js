document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('login-btn');
    const signupBtn = document.getElementById('signup-btn');
    const enterBtn = document.getElementById('enter-btn');
    const backBtn = document.getElementById('back-btn'); // Get the back button

    const initialButtons = document.getElementById('initial-buttons');
    const authForm = document.getElementById('auth-form');
    const formTitle = document.getElementById('form-title');
    const messageArea = document.getElementById('message-area'); // Area for messages

    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    let currentAction = null; // To track if we are logging in or signing up

    function showAuthForm(action) {
        currentAction = action;
        initialButtons.classList.add('hidden');
        authForm.classList.remove('hidden');
        formTitle.textContent = action === 'login' ? 'Log In' : 'Sign Up';
        messageArea.textContent = ''; // Clear previous messages
        emailInput.value = ''; // Clear fields
        passwordInput.value = '';
    }

    function showInitialButtons() {
        initialButtons.classList.remove('hidden');
        authForm.classList.add('hidden');
        currentAction = null;
        messageArea.textContent = ''; // Clear messages when going back
    }

    loginBtn.addEventListener('click', () => showAuthForm('login'));
    signupBtn.addEventListener('click', () => showAuthForm('signup'));
    backBtn.addEventListener('click', showInitialButtons); // Back button functionality

    enterBtn.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        messageArea.textContent = ''; // Clear previous messages

        if (!email || !password) {
            messageArea.textContent = 'Email and password cannot be empty.';
            return;
        }

        // Basic email format check (optional but good practice)
        if (!/\S+@\S+\.\S+/.test(email)) {
             messageArea.textContent = 'Please enter a valid email address.';
             return;
        }

        const url = currentAction === 'login' ? '/login' : '/signup';
        const payload = { email, password };

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Redirect on success
                window.location.href = '/home'; // Redirect to the new home page
            } else {
                // Display error message from backend or a default one
                messageArea.textContent = result.message || 'An error occurred.';
                if (currentAction === 'login' && response.status === 401) {
                    // Specific handling for "Account not found" on login
                    // The message from the backend should already be set
                } else if (currentAction === 'signup' && response.status === 409) {
                     // Specific handling for "Email already exists" on signup
                     // The message from the backend should already be set
                }
            }
        } catch (error) {
            console.error('Error during authentication:', error);
            messageArea.textContent = 'Failed to connect to the server.';
        }
    });

    // Optional: Allow pressing Enter in password field to submit
    passwordInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission if wrapped in <form>
            enterBtn.click(); // Trigger the ENTER button click
        }
    });
     emailInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            passwordInput.focus(); // Move focus to password field
        }
    });
});