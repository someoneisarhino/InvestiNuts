document.addEventListener('DOMContentLoaded', () => {
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const imageInput = document.getElementById('imageInput');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const errorMessageDiv = document.getElementById('error-message');
    const csvInput = document.getElementById('csvInput');
    const clearCsvButton = document.getElementById('clearCsvButton'); // Added
    const csvPreviewContainer = document.getElementById('csv-preview-container'); // Added
    let imageBase64 = null; // Variable to store the base64 encoded image
    let imageName = null; // Variable to store the image name
    let selectedCsvFiles = []; // Variable to store selected CSV files
    // Handle image selection
    imageInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const maxSize = 4 * 1024 * 1024; // 4MB limit
            if (file.size > maxSize) {
                displayError('Image size exceeds 4MB limit.');
                imageInput.value = '';
                imagePreviewContainer.textContent = '';
                imageBase64 = null;
                imageName = null;
                return;
            }

            const reader = new FileReader();
            reader.onloadend = () => {
                imageBase64 = reader.result.split(',')[1];
                imageName = file.name;
                imagePreviewContainer.textContent = `Selected: ${imageName}`;
                displayError('');
            };
            reader.onerror = () => {
                displayError('Failed to read image file.');
                imageBase64 = null;
                imageName = null;
                imagePreviewContainer.textContent = '';
            };
            reader.readAsDataURL(file);
        } else {
            imageBase64 = null;
            imageName = null;
            imagePreviewContainer.textContent = '';
        }
    });

    // Function to update CSV preview and button visibility
    function updateCsvPreview() {
        if (selectedCsvFiles.length > 0) {
            const fileNames = selectedCsvFiles.map(file => file.name).join(', ');
            csvPreviewContainer.textContent = `Selected CSVs: ${fileNames}`;
            clearCsvButton.style.display = 'inline-block'; // Show button
            displayError('');
        } else {
            csvPreviewContainer.textContent = '';
            clearCsvButton.style.display = 'none'; // Hide button
        }
        // Basic validation
        let valid = true;
        selectedCsvFiles.forEach(file => {
            if (!file.name.toLowerCase().endsWith('.csv')) {
                displayError(`Invalid file type: ${file.name}. Only CSV files allowed.`);
                valid = false;
            }
            // Add size validation if needed here
        });

        if (!valid) {
            csvInput.value = ''; // Clear input
            selectedCsvFiles = []; // Clear stored files
            updateCsvPreview(); // Update UI (hide button, clear text)
        }
    }

    // Handle CSV file selection
    csvInput.addEventListener('change', (event) => {
        selectedCsvFiles = Array.from(event.target.files); // Store File objects
        updateCsvPreview(); // Update display and button visibility
    });

    // Handle Clear CSVs button click
    clearCsvButton.addEventListener('click', () => {
        csvInput.value = ''; // Clear the file input element
        selectedCsvFiles = []; // Clear the stored files array
        updateCsvPreview(); // Update the preview and hide the button
    });

    function addMessage(sender, text, imageName = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        if (sender === 'user') {
            messageDiv.classList.add('user-message');
            if (imageName) {
                const imageIndicator = document.createElement('span');
                imageIndicator.textContent = ` (Image: ${imageName})`;
                imageIndicator.style.fontSize = '0.8em';
                imageIndicator.style.color = '#6b7280';
                messageDiv.textContent = text;
                messageDiv.appendChild(imageIndicator);
            } else {
                 messageDiv.textContent = text;
            }
        } else { // Bot message
            messageDiv.classList.add('bot-message');
            messageDiv.textContent = text; // Set text content for bot
        }

        // KaTeX rendering removed

        chatbox.appendChild(messageDiv);
        chatbox.scrollTop = chatbox.scrollHeight; // Scroll to bottom
    }

    function displayError(message) {
        errorMessageDiv.textContent = message;
        if (message) {
            setTimeout(() => {
                errorMessageDiv.textContent = '';
            }, 5000);
        }
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        // Allow sending message if text OR image OR CSV is present
        if (!messageText && !imageBase64 && selectedCsvFiles.length === 0) {
            displayError('Please type a message, select an image, or upload CSV files.');
            return;
        }

        // Display user message, indicating if CSVs were included
        let userDisplayMessage = messageText || '(Image/CSV analysis request)';
        if (selectedCsvFiles.length > 0) {
             const csvFileNames = selectedCsvFiles.map(f => f.name).join(', ');
             userDisplayMessage += ` (using CSVs: ${csvFileNames})`;
        }
        addMessage('user', userDisplayMessage, imageName);


        // --- Read CSV files ---
        const csvContents = [];
        const fileReadPromises = selectedCsvFiles.map(file => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve({ name: file.name, content: e.target.result });
                reader.onerror = (e) => reject(`Error reading ${file.name}: ${e.target.error}`);
                reader.readAsText(file); // Read as text
            });
        });

        let csvData = [];
        try {
            // Wait for all files to be read
            csvData = await Promise.all(fileReadPromises);
            displayError(''); // Clear any previous reading errors
        } catch (error) {
            console.error("Error reading CSV files:", error);
            displayError(`Error reading CSV files: ${error}`);
            // Decide if you want to proceed without CSVs or stop
            // For now, we'll stop if there's a reading error
             addMessage('bot', `Error processing CSV files. Could not send message.`);
             return;
        }
        // --- End Read CSV files ---


        const payload = {
            message: messageText,
            image_data: imageBase64,
            csv_data: csvData // Add CSV data {name: string, content: string}[]
        };

        userInput.value = '';
        imageInput.value = '';
        imagePreviewContainer.textContent = '';
        csvPreviewContainer.textContent = ''; // Clear CSV preview
        const sentImageName = imageName;
        imageBase64 = null;
        imageName = null;
        // csvInput.value = ''; // Clearing is now handled by the clear button or new selection
        selectedCsvFiles = []; // Clear the stored files
        errorMessageDiv.textContent = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { error: response.statusText };
                }
                console.error('Error from server:', errorData);
                displayError(`Error: ${errorData.error || 'Failed to get response'}`);
                addMessage('bot', `Sorry, an error occurred: ${errorData.error || response.statusText}`);
                return;
            }

            const data = await response.json();
            // The addMessage function will now handle KaTeX rendering for the bot reply
            addMessage('bot', data.reply);

        } catch (error) {
            console.error('Network or fetch error:', error);
            displayError('Network error. Could not reach the server.');
            addMessage('bot', 'Sorry, I could not connect to the server.');
        }
    }

    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    // Initial KaTeX render block removed
});