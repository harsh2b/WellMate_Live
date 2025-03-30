let sessionId = null;
const apiUrl = '';
const botAvatar = '/static/cropped_image.webp';
const userAvatar = '/static/—Pngtree—user avatar placeholder white blue_6796231.png';

let currentConversation = { timestamp: Date.now(), messages: [] };
let pastConsultations = JSON.parse(localStorage.getItem('pastConsultations')) || [];

// Handle signup form submission
document.getElementById('signup')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const phone = document.getElementById('signup-phone').value;
    
    const response = await fetch(`${apiUrl}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone })
    });
    const data = await response.json();
    alert(data.message);
    if (data.status === 'success') {
        localStorage.setItem('phone', phone);
        showOTP(phone, false);
    }
});

// Handle login form submission
document.getElementById('login')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const phone = document.getElementById('login-phone').value;
    
    const response = await fetch(`${apiUrl}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: phone })
    });
    const data = await response.json();
    alert(data.message);
    if (data.status === 'success') {
        localStorage.setItem('phone', phone);
        showOTP(phone, true);
    }
});

// Display OTP verification form
function showOTP(phone, isLogin) {
    const otpForm = `
        <div class="container">
            <div class="auth-box">
                <img src="/static/cropped_image.webp" alt="Logo" class="logo">
                <h1>Verify OTP</h1>
                <form id="verify-otp">
                    <div class="input-group">
                        <label for="otp-phone">Phone Number</label>
                        <input type="tel" id="otp-phone" value="${phone}" readonly>
                    </div>
                    <div class="input-group">
                        <label for="otp-code">Enter OTP</label>
                        <input type="text" id="otp-code" required placeholder="6-digit OTP">
                    </div>
                    <button type="submit" class="btn">Verify OTP</button>
                </form>
                <p class="switch">Didn't receive OTP? <a href="#" onclick="resendOTP('${phone}', ${isLogin})">Resend</a></p>
            </div>
        </div>`;
    document.body.innerHTML = otpForm;
    
    document.getElementById('verify-otp').addEventListener('submit', async (e) => {
        e.preventDefault();
        const otp = document.getElementById('otp-code').value;
        const endpoint = isLogin ? '/verify-login-otp' : '/verify-otp';
        const response = await fetch(`${apiUrl}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier: phone, otp })
        });
        const data = await response.json();
        alert(data.message);
        if (data.status === 'success' && isLogin) {
            sessionId = data.session_id;
            localStorage.setItem('sessionId', sessionId);
            window.location.href = '/static/patient_form.html';
        } else if (data.status === 'success') {
            window.location.href = '/static/patient_form.html';
        }
    });
}

// Resend OTP
async function resendOTP(phone, isLogin) {
    const endpoint = isLogin ? '/login' : '/signup';
    const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [isLogin ? 'identifier' : 'phone']: phone })
    });
    const data = await response.json();
    alert(data.message);
}

// Handle patient form with autofill and validation
document.getElementById('patient-info')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const patientInfo = {
        name: document.getElementById('patient-name').value.trim(),
        age: parseInt(document.getElementById('patient-age').value) || 0,
        gender: document.getElementById('patient-gender').value,
        language: document.getElementById('patient-language').value,
        phone: localStorage.getItem('phone') || ''
    };

    if (!patientInfo.name || patientInfo.age <= 0) {
        alert('Please provide a valid name and age.');
        return;
    }

    localStorage.setItem('patientInfo', JSON.stringify(patientInfo));
    const sessionId = localStorage.getItem('sessionId');
    if (sessionId) {
        try {
            const response = await fetch(`${apiUrl}/update-patient`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, patient_info: patientInfo })
            });
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error('Failed to update patient info on server');
            }
        } catch (error) {
            console.error('Error updating patient info:', error);
            alert('Failed to save patient info on server. Proceeding with local data.');
        }
    } else {
        console.warn('No sessionId found. Proceeding with local data.');
    }
    window.location.href = '/static/chat.html';
});

// Autofill patient form if data exists
if (window.location.pathname === '/static/patient_form.html') {
    const patientInfo = JSON.parse(localStorage.getItem('patientInfo')) || {};
    document.getElementById('patient-name').value = patientInfo.name || '';
    document.getElementById('patient-age').value = patientInfo.age || '';
    document.getElementById('patient-gender').value = patientInfo.gender || 'Male';
    document.getElementById('patient-language').value = patientInfo.language || 'English';
}

// Load profile data
if (window.location.pathname === '/static/profile.html') {
    const patientInfo = JSON.parse(localStorage.getItem('patientInfo')) || {};
    document.getElementById('profile-phone').textContent = patientInfo.phone || 'N/A';
    document.getElementById('profile-name').textContent = patientInfo.name || 'N/A';
    document.getElementById('profile-age').textContent = patientInfo.age || 'N/A';
    document.getElementById('profile-gender').textContent = patientInfo.gender || 'N/A';
    document.getElementById('profile-language').textContent = patientInfo.language || 'N/A';
    updateSidebar();
}

// Load chat and profile functionality
if (window.location.pathname.includes('/static/chat.html') || window.location.pathname.includes('/static/profile.html')) {
    document.addEventListener('DOMContentLoaded', () => {
        sessionId = localStorage.getItem('sessionId');
        console.log('Session ID on page:', sessionId);

        // Toggle sidebar
        document.getElementById('menu-toggle').addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('active');
        });

        updateSidebar();

        if (window.location.pathname.includes('/static/chat.html')) {
            // Add welcome message when chat page loads
            setTimeout(() => {
                const chatMessages = document.getElementById('chat-messages');
                if (!chatMessages) {
                    console.error('Chat messages container not found');
                    return;
                }
                console.log('Number of chat messages:', document.querySelectorAll('.chat-message').length);
                if (document.querySelectorAll('.chat-message').length === 0) {
                    addMessage('assistant', "Hello! I'm Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
                }
            }, 500);
        }
    });
}

// Chat functionality
document.getElementById('send-button')?.addEventListener('click', sendChatMessage);
document.getElementById('user-input')?.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function sendChatMessage() {
    const userInput = document.getElementById('user-input').value.trim();
    if (!userInput || !sessionId) return;

    addMessage('user', userInput);
    document.getElementById('user-input').value = '';

    const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userInput })
    });
    const data = await response.json();
    const botResponse = data.response;
    addMessage('assistant', botResponse);

    currentConversation.messages.push({ role: 'user', content: userInput });
    currentConversation.messages.push({ role: 'assistant', content: botResponse });

    // Save and update synchronously
    console.log('Checking save condition:', userInput.toLowerCase(), window.performance.navigation.type);
    if (userInput.toLowerCase().includes('start new conversation') || window.performance.navigation.type === 1) {
        if (currentConversation.messages.length > 0) {
            pastConsultations.push({ ...currentConversation });
            console.log('Saved conversation:', currentConversation);
            currentConversation = { timestamp: Date.now(), messages: [] };
            localStorage.setItem('pastConsultations', JSON.stringify(pastConsultations));
            updateSidebar();
            document.getElementById('chat-messages').innerHTML = '';
            addMessage('assistant', "Hello! I'm Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
        }
    }
    updateSidebar(); // Always update sidebar to show current conversation
}

function convertMarkdownToHTML(text) {
    text = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    text = text.replace(/\*(.*?)\*/g, '<i>$1</i>');
    return text;
}

function addMessage(role, content) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message');
    const avatar = role === 'user' ? userAvatar : botAvatar;
    const formattedContent = convertMarkdownToHTML(content);
    messageDiv.innerHTML = `<img src="${avatar}" width="30" height="30"> <div>${formattedContent}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function loadConsultation(messages) {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '';
    messages.forEach(msg => addMessage(msg.role, msg.content));
    currentConversation = { timestamp: Date.now(), messages: [...messages] }; // Update current conversation
}

function updateSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    // Clear existing history
    const historyDiv = sidebar.querySelector('.chat-history');
    if (historyDiv) historyDiv.remove();

    // Create new history section
    const historySection = document.createElement('div');
    historySection.classList.add('chat-history');
    historySection.innerHTML = '<h3>Chat History</h3>';

    // Add current conversation (if it has messages)
    if (currentConversation.messages.length > 0) {
        const currentDiv = document.createElement('div');
        currentDiv.classList.add('history-item');
        const preview = currentConversation.messages[0].content.substring(0, 20) + '...';
        currentDiv.innerHTML = `
            <span class="history-title" onclick='loadConsultation(${JSON.stringify(currentConversation.messages)})'>Current Chat - ${new Date(currentConversation.timestamp).toLocaleDateString()} (${preview})</span>
            <button class="delete-btn" onclick="deleteCurrentConversation()">🗑️</button>
        `;
        historySection.appendChild(currentDiv);
    }

    // Add past consultations
    pastConsultations.forEach((consult, index) => {
        const consultDiv = document.createElement('div');
        consultDiv.classList.add('history-item');
        const preview = consult.messages.length > 0 ? consult.messages[0].content.substring(0, 20) + '...' : 'No messages';
        consultDiv.innerHTML = `
            <span class="history-title" onclick='loadConsultation(${JSON.stringify(consult.messages)})'>Consultation ${index + 1} - ${new Date(consult.timestamp).toLocaleDateString()} (${preview})</span>
            <button class="delete-btn" onclick="deleteConsultation(${index})">🗑️</button>
        `;
        historySection.appendChild(consultDiv);
    });

    sidebar.appendChild(historySection);
}

function deleteCurrentConversation() {
    const confirmDelete = confirm(`Are you sure you want to delete the current conversation? This action cannot be undone.`);
    if (!confirmDelete) return;

    currentConversation = { timestamp: Date.now(), messages: [] };
    updateSidebar();
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        if (document.querySelectorAll('.chat-message').length === 0) {
            addMessage('assistant', "Hello! I'm Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
        }
    }
    alert('Current conversation deleted successfully');
}

function deleteConsultation(index) {
    const confirmDelete = confirm(`Are you sure you want to delete Consultation ${index + 1}? This action cannot be undone.`);
    if (!confirmDelete) return;

    pastConsultations.splice(index, 1);
    localStorage.setItem('pastConsultations', JSON.stringify(pastConsultations));
    updateSidebar();
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        if (document.querySelectorAll('.chat-message').length === 0) {
            addMessage('assistant', "Hello! I'm Dr. Black, a physician with 30 years of experience. How may I help you today? 😊");
        }
    }
    alert('Consultation deleted successfully');
}

function logout() {
    localStorage.removeItem('sessionId');
    window.location.href = '/static/login.html';
}

// New chat handler
function newChat() {
    window.location.href = '/static/patient_form.html';
}