// Configuration
const API_BASE_URL = 'http://localhost:5000/api';
let currentUser = null;
let sessionId = generateSessionId();

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// DOM Elements - Auth
const authContainer = document.getElementById('authContainer');
const appContainer = document.getElementById('appContainer');
const loginCard = document.getElementById('loginCard');
const registerCard = document.getElementById('registerCard');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const loginError = document.getElementById('loginError');
const registerError = document.getElementById('registerError');
const showRegisterLink = document.getElementById('showRegister');
const showLoginLink = document.getElementById('showLogin');

// DOM Elements - Chat
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const suggestionsBar = document.getElementById('suggestionsBar');
const suggestionsContainer = document.getElementById('suggestionsContainer');
const newChatBtn = document.getElementById('newChatBtn');
const logoutBtn = document.getElementById('logoutBtn');
const backendStatus = document.getElementById('backend-status');

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    setupAuthListeners();
    setupChatListeners();
});

// ==================== AUTHENTICATION FUNCTIONS ====================

async function checkAuthentication() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/check`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.authenticated) {
            currentUser = data.user;
            showApp();
            loadUserProfile();
            applyRoleUI();
            checkBackendHealth();
        } else {
            showAuth();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showAuth();
    }
}

function setupAuthListeners() {
    // Toggle between login and register
    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginCard.style.display = 'none';
        registerCard.style.display = 'block';
        loginError.classList.remove('show');
    });

    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerCard.style.display = 'none';
        loginCard.style.display = 'block';
        registerError.classList.remove('show');
    });

    // Login form submission
    loginForm.addEventListener('submit', handleLogin);

    // Register form submission
    registerForm.addEventListener('submit', handleRegister);

    // Logout button
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

async function handleLogin(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        email: formData.get('email'),
        password: formData.get('password'),
        role: formData.get('role') || 'student'
    };


    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Signing in...</span>';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            currentUser = {
                ...result.user,
                role: result.user.role || data.role
            };

            showApp();
            loadUserProfile();
            applyRoleUI();
            checkBackendHealth();
        }

        else {
            showError(loginError, result.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError(loginError, 'Connection error. Please check if backend is running.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <span>Sign In</span>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M4 10H16M16 10L12 6M16 10L12 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `;
    }
}

async function handleRegister(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        email: formData.get('email'),
        password: formData.get('password'),
        enrollment_number: formData.get('enrollment_number'),
        phone: formData.get('phone'),
        department: formData.get('department'),
        semester: formData.get('semester')
    };

    // Validate
    if (!data.name || !data.email || !data.password || !data.enrollment_number || !data.department || !data.semester) {
        showError(registerError, 'Please fill in all required fields');
        return;
    }

    if (data.password.length < 6) {
        showError(registerError, 'Password must be at least 6 characters');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Creating account...</span>';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Show success message and switch to login
            showNotification('Account created successfully! Please log in.', 'success');
            registerCard.style.display = 'none';
            loginCard.style.display = 'block';
            registerForm.reset();
            registerError.classList.remove('show');

            // Pre-fill login email
            document.getElementById('loginEmail').value = data.email;
        } else {
            showError(registerError, result.error || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showError(registerError, 'Connection error. Please check if backend is running.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <span>Create Account</span>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M4 10H16M16 10L12 6M16 10L12 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `;
    }
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });

        currentUser = null;
        sessionId = generateSessionId();
        document.body.classList.remove('admin'); // ✅ add this
        showAuth();
        showNotification('Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
    }
}


function showAuth() {
    authContainer.style.display = 'flex';
    appContainer.style.display = 'none';
}

function showApp() {
    authContainer.style.display = 'none';
    appContainer.style.display = 'grid';
}

function showError(errorElement, message) {
    errorElement.textContent = message;
    errorElement.classList.add('show');
    setTimeout(() => {
        errorElement.classList.remove('show');
    }, 5000);
}

function loadUserProfile() {
    if (!currentUser) return;

    document.getElementById('student-name').textContent = currentUser.name;
    document.getElementById('student-dept').textContent = currentUser.department;
    document.getElementById('student-semester').textContent = currentUser.semester;

    const initials = currentUser.name.split(' ').map(n => n[0]).join('').substring(0, 2);
    document.getElementById('student-initials').textContent = initials;

    const nameEl = document.getElementById('userName');
    const roleEl = document.getElementById('userRole');

    if (nameEl) nameEl.textContent = currentUser.name;
    if (roleEl) roleEl.textContent = currentUser.role === 'admin' ? 'Admin / Faculty' : 'Student';

}

function applyRoleUI() {
    if (!currentUser) return;

    const isAdmin = currentUser.role === 'admin';

    // 🔹 Add or remove admin class on body
    if (isAdmin) {
        document.body.classList.add('admin');
    } else {
        document.body.classList.remove('admin');
    }

    // 🔹 Default view after login
    switchView(isAdmin ? 'insights' : 'chat');
}


function switchView(viewName) {
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });

    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    // Update sidebar active state
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        }
    });
}

// ==================== CHAT FUNCTIONS ====================

function setupChatListeners() {
    // Auto-resize textarea
    if (userInput) {
        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = userInput.scrollHeight + 'px';
        });
    }

    // Chat form submission
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = userInput.value.trim();
            if (message) {
                sendMessage(message);
                userInput.value = '';
                userInput.style.height = 'auto';
            }
        });
    }

    // New chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            sessionId = generateSessionId();
            clearChat();
        });
    }

    // Suggestion chips
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('chip') || e.target.closest('.chip')) {
            const chip = e.target.classList.contains('chip') ? e.target : e.target.closest('.chip');
            const message = chip.getAttribute('data-msg');
            if (message) {
                sendMessage(message);
            }
        }

        if (e.target.classList.contains('suggestion-btn')) {
            const message = e.target.textContent.trim();
            sendMessage(message);
        }
    });

    // Navigation buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-action');
            handleNavAction(action);

            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // New sidebar navigation (MindMate layout)
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            if (view) switchView(view);
        });
    });

}

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            updateBackendStatus(true);
        } else {
            updateBackendStatus(false);
        }
    } catch (error) {
        console.error('Backend health check failed:', error);
        updateBackendStatus(false);
    }
}

function updateBackendStatus(isHealthy) {
    const statusDot = document.querySelector('.status-dot');

    if (isHealthy) {
        backendStatus.textContent = 'Connected';
        if (statusDot) statusDot.style.background = 'var(--color-success)';
    } else {
        backendStatus.textContent = 'Disconnected';
        if (statusDot) statusDot.style.background = 'var(--color-error)';
        showNotification('Backend server is not responding. Please start the server.', 'error');
    }
}

async function sendMessage(message) {
    if (!currentUser) {
        showNotification('Please log in first', 'error');
        return;
    }

    // Hide welcome screen
    const welcomeScreen = document.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // Add user message to chat
    addMessageToChat(message, 'user');

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (response.status === 401) {
            showNotification('Session expired. Please log in again.', 'error');
            showAuth();
            return;
        }

        if (data.success) {
            addMessageToChat(data.response, 'bot');

            if (data.suggestions && data.suggestions.length > 0) {
                showSuggestions(data.suggestions);
            } else {
                hideSuggestions();
            }
        } else {
            throw new Error(data.error || 'Failed to get response');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator(typingId);
        addMessageToChat('Sorry, I encountered an error. Please make sure the backend server is running.', 'bot');
        showNotification('Failed to send message. Check your connection.', 'error');
    }
}

function addMessageToChat(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = text;

    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    contentDiv.appendChild(textDiv);
    contentDiv.appendChild(timeDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    const typingId = 'typing-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
    messageDiv.id = typingId;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    contentDiv.appendChild(typingDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return typingId;
}

function removeTypingIndicator(typingId) {
    const typingElement = document.getElementById(typingId);
    if (typingElement) {
        typingElement.remove();
    }
}

function showSuggestions(suggestions) {
    suggestionsContainer.innerHTML = '';

    suggestions.forEach(suggestion => {
        const btn = document.createElement('button');
        btn.className = 'suggestion-btn';
        btn.textContent = suggestion;
        suggestionsContainer.appendChild(btn);
    });

    suggestionsBar.style.display = 'block';
}

function hideSuggestions() {
    suggestionsBar.style.display = 'none';
}

function clearChat() {
    chatMessages.innerHTML = `
        <div class="welcome-screen">
            <div class="welcome-icon">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                    <circle cx="32" cy="32" r="30" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                    <path d="M32 16V32L40 40" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                    <circle cx="32" cy="32" r="20" stroke="currentColor" stroke-width="2"/>
                </svg>
            </div>
            <h3>Welcome to Your AI Academic Assistant!</h3>
            <p>I can help you with performance tracking, study planning, and academic guidance.</p>
            
            <div class="suggestion-chips">
                <button class="chip" data-msg="Show my academic performance">
                    📊 My Performance
                </button>
                <button class="chip" data-msg="Create a personalized study plan for me">
                    📚 Study Plan
                </button>
                <button class="chip" data-msg="What are my weak subjects?">
                    📈 Weak Subjects
                </button>
                <button class="chip" data-msg="Predict my semester performance">
                    🔮 Prediction
                </button>
            </div>
        </div>
    `;
    hideSuggestions();
}

async function handleNavAction(action) {
    if (action === 'chat') {
        return;
    } else if (action === 'performance') {
        sendMessage('Show my academic performance in detail');
    } else if (action === 'history') {
        await loadChatHistory();
    }
}

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/history`, {
            credentials: 'include'
        });

        if (response.status === 401) {
            showNotification('Session expired. Please log in again.', 'error');
            showAuth();
            return;
        }

        const data = await response.json();

        if (data.success && data.history.length > 0) {
            const welcomeScreen = document.querySelector('.welcome-screen');
            if (welcomeScreen) {
                welcomeScreen.style.display = 'none';
            }

            const existingMessages = chatMessages.querySelectorAll('.message');
            existingMessages.forEach(msg => msg.remove());

            addMessageToChat('📜 Here\'s your recent chat history:', 'bot');

            const recentHistory = data.history.slice(0, 5);
            recentHistory.forEach(chat => {
                const historyText = `Q: ${chat.user_message}\nA: ${chat.bot_response.substring(0, 100)}...`;
                addMessageToChat(historyText, 'bot');
            });
        } else {
            addMessageToChat('No chat history found yet. Start chatting to build your history!', 'bot');
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
        showNotification('Failed to load chat history', 'error');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'error' ? 'var(--color-error)' : type === 'success' ? 'var(--color-success)' : 'var(--color-primary)'};
        color: white;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: slideIn 0.3s ease;
        font-family: var(--font-body);
        font-size: 0.9375rem;
        font-weight: 500;
        max-width: 300px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (userInput) userInput.focus();
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        if (newChatBtn) newChatBtn.click();
    }
});


// Right left panels toggle
function toggleLeft() {
    document.getElementById("leftPanel").classList.toggle("hide-left");
}

function toggleRight() {
    document.getElementById("rightPanel").classList.toggle("hide-right");
}

function toggleLeft() {
    document.getElementById("leftPanel").classList.toggle("hide-left");
}

function toggleRight() {
    document.getElementById("rightPanel").classList.toggle("hide-right");
}