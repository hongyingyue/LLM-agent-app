// Configuration
const BACKEND_URL = 'http://localhost:8000';

// UUID generation function
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Session management
function getCurrentSessionId() {
    let sessionId = localStorage.getItem('sessionId');
    if (!sessionId) {
        sessionId = generateUUID();
        localStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
}

// Chat history array to store messages
let chatHistory = [];

// Function to add a message to the chat
function addMessage(content, isUser = false, fileInfo = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
    
    // Add file info if present
    if (fileInfo) {
        const fileMessage = document.createElement('div');
        fileMessage.className = 'file-message';
        fileMessage.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="file-name">${fileInfo.name}</span>
        `;
        messageDiv.appendChild(fileMessage);
    }
    
    // Add message content
    const contentDiv = document.createElement('div');
    contentDiv.textContent = content;
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to history
    chatHistory.push({
        content,
        isUser,
        fileInfo,
        timestamp: new Date().toISOString()
    });
}

function createMessageElement(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
    
    if (isUser) {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${content}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text"></div>
                <div class="thinking-steps"></div>
            </div>
        `;
    }
    
    return messageDiv;
}

function createThinkingStepElement(step) {
    const stepDiv = document.createElement('div');
    stepDiv.className = `thinking-step ${step.type === 'tool_call' ? 'tool-call' : ''}`;
    
    if (step.type === 'thinking') {
        stepDiv.innerHTML = `
            <div class="collapsible">Thinking Process</div>
            <div class="collapsible-content">
                <div class="thinking-content">${step.content}</div>
            </div>
        `;
    } else if (step.type === 'tool_call') {
        stepDiv.innerHTML = `
            <div class="collapsible">Tool Call: ${step.tool_name}</div>
            <div class="collapsible-content">
                <div class="tool-call-header">
                    <span class="tool-call-name">${step.tool_name}</span>
                </div>
                <div class="tool-call-args">${JSON.stringify(step.tool_args, null, 2)}</div>
                ${step.tool_result ? `
                    <div class="tool-result">${step.tool_result}</div>
                ` : ''}
            </div>
        `;
    }
    
    // Add click handler for collapsible
    const collapsible = stepDiv.querySelector('.collapsible');
    const content = stepDiv.querySelector('.collapsible-content');
    collapsible.addEventListener('click', () => {
        collapsible.classList.toggle('collapsed');
        content.classList.toggle('collapsed');
    });
    
    return stepDiv;
}

async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const content = userInput.value.trim();
    
    if (!content) return;
    
    const chatMessages = document.getElementById('chatMessages');
    const userMessage = createMessageElement(content, true);
    chatMessages.appendChild(userMessage);
    
    const assistantMessage = createMessageElement('', false);
    chatMessages.appendChild(assistantMessage);
    
    userInput.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        console.log('Sending message to backend:', {
            session_id: getCurrentSessionId(),
            content: content
        });

        const response = await fetch(`${BACKEND_URL}/api/messages/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
            },
            mode: 'cors',
            body: JSON.stringify({
                session_id: getCurrentSessionId(),
                content: content
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Backend error:', {
                status: response.status,
                statusText: response.statusText,
                body: errorText
            });
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const thinkingSteps = assistantMessage.querySelector('.thinking-steps');
        const messageText = assistantMessage.querySelector('.message-text');
        let finalResponse = '';
        
        while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            console.log('Received chunk:', chunk);
            
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        console.log('Parsed data:', data);
                        
                        if (data.type === 'thinking' || data.type === 'tool_call') {
                            const stepElement = createThinkingStepElement(data);
                            thinkingSteps.appendChild(stepElement);
                        } else {
                            finalResponse += data.content;
                            messageText.textContent = finalResponse;
                        }
                    } catch (e) {
                        console.error('Error parsing message:', e, 'Line:', line);
                    }
                }
            }
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    } catch (error) {
        console.error('Error in sendMessage:', error);
        const errorMessage = `Error: ${error.message}. Please check the console for more details.`;
        assistantMessage.querySelector('.message-text').textContent = errorMessage;
        
        // Add error details to thinking steps
        const errorStep = createThinkingStepElement({
            type: 'thinking',
            content: `Error details: ${error.stack || error.message}`
        });
        assistantMessage.querySelector('.thinking-steps').appendChild(errorStep);
    }
}

// Function to handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Function to handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // Add message with file info
        addMessage('I have uploaded a file:', true, {
            name: file.name,
            size: file.size,
            type: file.type
        });
        
        // Here you would typically handle the file upload to your server
        // For now, we'll just simulate a response
        simulateResponse(`I see you've uploaded ${file.name}. How can I help you with this file?`);
    }
}

// Function to simulate API response (replace with actual API call)
function simulateResponse(userMessage) {
    // Show loading state
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant-message';
    loadingDiv.textContent = '...';
    document.getElementById('chatMessages').appendChild(loadingDiv);
    
    // Simulate API delay
    setTimeout(() => {
        // Remove loading message
        loadingDiv.remove();
        
        // Add response (replace with actual API response)
        const response = `This is a simulated response to: "${userMessage}"`;
        addMessage(response, false);
    }, 1000);
}

// Function to reset textarea height to default
function resetTextareaHeight(textarea) {
    textarea.style.height = '24px'; // Match min-height from CSS
}

// Auto-resize textarea
const textarea = document.getElementById('userInput');

// Handle input for auto-resize
textarea.addEventListener('input', function() {
    this.style.height = '24px'; // Reset to min-height
    const newHeight = Math.min(this.scrollHeight, 200); // Max height of 200px
    this.style.height = newHeight + 'px';
});

// Reset height when clicked
textarea.addEventListener('click', function() {
    if (this.value === '') {
        resetTextareaHeight(this);
    }
});

// Reset height when focused
textarea.addEventListener('focus', function() {
    if (this.value === '') {
        resetTextareaHeight(this);
    }
});

// Reset height when blurred
textarea.addEventListener('blur', function() {
    if (this.value === '') {
        resetTextareaHeight(this);
    }
});

// Initialize upload button
document.getElementById('uploadButton').addEventListener('click', function() {
    document.getElementById('fileInput').click();
});

// Initialize with a welcome message
window.onload = function() {
    addMessage('Hello! How can I help you today?', false);
    // Set initial height
    resetTextareaHeight(textarea);
};

// Authentication Modal Handling
const userIconButton = document.getElementById('userIconButton');
const authModal = document.getElementById('authModal');
const closeButton = document.querySelector('.close-button');
const modalTitle = document.getElementById('modalTitle');
const authForm = document.getElementById('authForm');
const switchToRegister = document.getElementById('switchToRegister');
let isRegisterMode = false;

// Show modal when clicking the user icon
userIconButton.addEventListener('click', () => {
    authModal.style.display = 'block';
});

// Close modal when clicking the close button or outside the modal
closeButton.addEventListener('click', () => {
    authModal.style.display = 'none';
});

window.addEventListener('click', (event) => {
    if (event.target === authModal) {
        authModal.style.display = 'none';
    }
});

// Switch between sign in and register modes
switchToRegister.addEventListener('click', (e) => {
    e.preventDefault();
    isRegisterMode = !isRegisterMode;
    modalTitle.textContent = isRegisterMode ? 'Register' : 'Sign In';
    authForm.querySelector('button[type="submit"]').textContent = isRegisterMode ? 'Register' : 'Sign In';
    switchToRegister.textContent = isRegisterMode ? 'Sign In' : 'Register';
});

// Handle form submission
authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        // Here you would typically make an API call to your backend
        // For now, we'll just simulate a successful login
        console.log(`${isRegisterMode ? 'Registering' : 'Signing in'} with:`, { email, password });
        
        // Update UI to show logged-in state
        userIconButton.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12Z" fill="currentColor"/>
                <path d="M20 21C20 18.8783 19.1571 16.8434 17.6569 15.3431C16.1566 13.8429 14.1217 13 12 13C9.87827 13 7.84344 13.8429 6.34315 15.3431C4.84285 16.8434 4 18.8783 4 21" fill="currentColor"/>
            </svg>
        `;
        userIconButton.style.color = '#007AFF';
        
        // Close the modal
        authModal.style.display = 'none';
        
        // Clear the form
        authForm.reset();
    } catch (error) {
        console.error('Authentication error:', error);
        // Here you would typically show an error message to the user
    }
}); 