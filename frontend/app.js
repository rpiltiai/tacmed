
// Configuration from global scope (injected in index.html)
const CONFIG = window.APP_CONFIG;

// Clients
let userPool;
let currentUser;

// DOM Elements
const screens = {
    auth: document.getElementById('auth-screen'),
    dashboard: document.getElementById('dashboard-screen')
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initCognito();
    setupEventListeners();
    checkSession();
    loadLeaderboard();
});

function initCognito() {
    const poolData = {
        UserPoolId: CONFIG.UserPoolId,
        ClientId: CONFIG.ClientId
    };
    userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);
}

function setupEventListeners() {
    // Auth Toggles
    document.getElementById('show-register').onclick = () => {
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    };

    document.getElementById('show-login').onclick = () => {
        document.getElementById('register-form').classList.add('hidden');
        document.getElementById('login-form').classList.remove('hidden');
    };

    // Forms
    document.getElementById('login-form').onsubmit = handleLogin;
    document.getElementById('register-form').onsubmit = handleRegister;
    document.getElementById('logout-btn').onclick = handleLogout;

    // Features
    const recordBtn = document.getElementById('record-btn');
    if (recordBtn) {
        recordBtn.addEventListener('mousedown', startRecording);
        recordBtn.addEventListener('mouseup', stopRecording);
        recordBtn.addEventListener('touchstart', startRecording);
        recordBtn.addEventListener('touchend', stopRecording);
    }

    document.getElementById('start-quiz').onclick = startQuiz;

    // Chat
    document.getElementById('send-btn').onclick = sendTextQuery;
    document.getElementById('chat-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendTextQuery();
    };

    // Chat
    document.getElementById('send-btn').onclick = sendTextQuery;
    document.getElementById('chat-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendTextQuery();
    };
}

// Auth Handlers
function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;

    if (password !== confirm) {
        alert("Passwords do not match");
        return;
    }

    const attributeList = [];
    const dataEmail = { Name: 'email', Value: email };
    attributeList.push(new AmazonCognitoIdentity.CognitoUserAttribute(dataEmail));

    userPool.signUp(email, password, attributeList, null, (err, result) => {
        if (err) {
            alert(err.message || JSON.stringify(err));
            return;
        }
        alert('Registration successful! Please check your email for verification link (not implemented in this simplified flow) or ask admin to confirm.');
        // In real flow, enter code. For now, assume auto-verify or admin confirm.
        // Actually, "setup.ps1" uses 'email' verification.
    });
}

function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    const authData = { Username: email, Password: password };
    const authDetails = new AmazonCognitoIdentity.AuthenticationDetails(authData);

    const userData = { Username: email, Pool: userPool };
    const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

    cognitoUser.authenticateUser(authDetails, {
        onSuccess: (result) => {
            currentUser = cognitoUser;
            showDashboard();
            loadLeaderboard();
        },
        onFailure: (err) => {
            alert(err.message || JSON.stringify(err));
        }
    });
}

function handleLogout() {
    if (currentUser) {
        currentUser.signOut();
    }
    screens.dashboard.classList.add('hidden');
    screens.auth.classList.remove('hidden');
}

function checkSession() {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser != null) {
        cognitoUser.getSession((err, session) => {
            if (session.isValid()) {
                currentUser = cognitoUser;
                showDashboard();
                loadLeaderboard();
            }
        });
    }
}

function showDashboard() {
    screens.auth.classList.add('hidden');
    screens.dashboard.classList.remove('hidden');
}

// Features
// Audio Logic
let mediaRecorder;
let audioChunks = [];

async function startRecording() {
    document.getElementById('recording-status').innerText = "Listening...";
    document.getElementById('record-btn').style.transform = "scale(1.1)";

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.start();
    } catch (err) {
        console.error("Mic error:", err);
        alert("Microphone access denied");
    }
}

function stopRecording() {
    document.getElementById('recording-status').innerText = "Processing...";
    document.getElementById('record-btn').style.transform = "scale(1)";

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' }); // Transcribe supports webm
            // Convert to base64
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = reader.result.split(',')[1];
                await sendAudioQuery(base64Audio);
            };
        };
    }
}

async function sendAudioQuery(audioData) {
    addMessage("Sending audio...", "user");

    try {
        const response = await fetch(`${CONFIG.ApiEndpoint}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio: audioData, question: "Audio Query" }) // Send audio
        });

        const data = await response.json();
        addMessage(data.answer || "No response", "system");
        document.getElementById('recording-status').innerText = "Hold to Speak";
    } catch (err) {
        addMessage("Error connecting to HQ.", "system");
        console.error(err);
    }
}

function addMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerText = text;
    document.getElementById('chat-history').appendChild(div);
    document.getElementById('chat-history').scrollTop = document.getElementById('chat-history').scrollHeight;
}

// Leaderboard
async function loadLeaderboard() {
    try {
        const res = await fetch(`${CONFIG.ApiEndpoint}/leaderboard`);
        const data = await res.json();
        const list = document.getElementById('leaderboard-list');
        list.innerHTML = "";

        if (data.leaderboard && data.leaderboard.length > 0) {
            data.leaderboard.forEach(user => {
                const li = document.createElement('li');
                li.innerText = `${user.UserId}: ${user.TotalScore}`;
                list.appendChild(li);
            });
        } else {
            list.innerHTML = "<li>No data yet</li>";
        }
    } catch (e) {
        console.error(e);
    }
}

async function startQuiz() {
    const quizArea = document.getElementById('quiz-area');
    quizArea.classList.remove('hidden');
    quizArea.innerHTML = '<div class="loading">Generating tactical scenario...</div>';
    document.getElementById('start-quiz').classList.add('hidden');

    try {
        const res = await fetch(`${CONFIG.ApiEndpoint}/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        renderQuizQuestion(data);
    } catch (e) {
        quizArea.innerHTML = '<div class="error">Failed to load scenario. HQ offline.</div>';
        document.getElementById('start-quiz').classList.remove('hidden');
        console.error(e);
    }
}

function renderQuizQuestion(data) {
    const quizArea = document.getElementById('quiz-area');

    // Check if fallback or real
    if (!data.question) {
        quizArea.innerHTML = '<div class="error">Invalid data from HQ.</div>';
        return;
    }

    let html = `
        <div class="quiz-question">
            <p>${data.question}</p>
            <div class="options">
    `;

    data.options.forEach((opt, idx) => {
        html += `<button class="btn-option" onclick="checkAnswer(${idx}, ${data.correct_index}, '${data.explanation.replace(/'/g, "\\'")}')">${opt}</button>`;
    });

    html += `</div><div id="quiz-feedback"></div></div>`;
    quizArea.innerHTML = html;
}

async function updateScore() {
    if (!currentUser) return 'GUEST';
    try {
        const username = currentUser.getUsername();
        const res = await fetch(`${CONFIG.ApiEndpoint}/score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: username })
        });
        const data = await res.json();
        console.log("Score updated:", data);
        loadLeaderboard();
        return data.newScore;
    } catch (e) {
        console.error("Score update failed:", e);
        return null;
    }
}

window.checkAnswer = async function (selected, correct, explanation) {
    const feedback = document.getElementById('quiz-feedback');
    const buttons = document.querySelectorAll('.btn-option');

    buttons.forEach((btn, idx) => {
        btn.disabled = true;
        if (idx === correct) btn.classList.add('correct');
        if (idx === selected && selected !== correct) btn.classList.add('wrong');
    });

    if (selected === correct) {
        feedback.innerHTML = `<div class="feedback success">Correct! ${explanation} <br><strong>+100 XP</strong></div>`;
        const newScore = await updateScore();
        if (newScore === 'GUEST') {
            feedback.innerHTML += `<div class="score-update" style="margin-top: 5px; color: #fbbf24; font-size: 0.9em;">(Login to save score)</div>`;
        } else if (newScore !== null) {
            feedback.innerHTML += `<div class="score-update" style="margin-top: 5px; font-weight: bold; color: #4ade80;">Total Score: ${newScore}</div>`;
        } else {
            feedback.innerHTML += `<div class="score-update" style="margin-top: 5px; color: #f87171; font-size: 0.9em;">(Error saving score)</div>`;
        }
    } else {
        feedback.innerHTML = `<div class="feedback failure">Incorrect. ${explanation}</div>`;
    }

    // Reset button
    setTimeout(() => {
        const resetBtn = document.createElement('button');
        resetBtn.className = 'btn-secondary';
        resetBtn.innerText = 'Next Scenario';
        resetBtn.onclick = startQuiz;
        feedback.appendChild(resetBtn);
    }, 1500);
}

async function sendTextQuery() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    addMessage(text, "user");

    try {
        const response = await fetch(`${CONFIG.ApiEndpoint}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });

        const data = await response.json();
        addMessage(data.answer || "No response", "system");
    } catch (err) {
        addMessage("Error connecting to HQ.", "system");
        console.error(err);
    }
}
