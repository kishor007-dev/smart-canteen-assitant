// ------------------- CONFIG -------------------
import { API_URL, WS_URL } from "./config.js";

// ------------------- ELEMENTS -------------------
const authDiv = document.getElementById("authDiv");
const chatDiv = document.getElementById("chatDiv");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const authError = document.getElementById("authError");
const studentNameSpan = document.getElementById("studentName");
const chatBox = document.getElementById("chatBox");
const chatInput = document.getElementById("chatInput");
const notifications = document.getElementById("notifications");
const orderHistorySection = document.getElementById("orderHistorySection");
const orderHistoryList = document.getElementById("orderHistoryList");
const recentOrdersBtn = document.getElementById("recentOrdersBtn");

let currentUser = null;
let ws = null;

// ------------------- AUTO LOGIN ON REFRESH -------------------
window.onload = () => {
    document.getElementById("login").addEventListener("click", login);
    document.getElementById("signup").addEventListener("click", signup);
    document.getElementById("logout").addEventListener("click", logout);

    recentOrdersBtn.addEventListener("click", () => {
        orderHistorySection.classList.toggle("show");
    });

    const savedUser = localStorage.getItem("studentUser");
    if (savedUser) {
        currentUser = savedUser;
        authDiv.style.display = "none";
        chatDiv.style.display = "block";
        studentNameSpan.textContent = currentUser;
        connectWebSocket();
        addBotMessage(`👋 Welcome back ${currentUser}! How can I help you today?`);
        loadOrderHistory();
    }
};

// ------------------- REQUEST NOTIFICATION PERMISSION -------------------
if ("Notification" in window && Notification.permission !== "granted") {
    Notification.requestPermission();
}

// ------------------- LOGIN -------------------
async function login() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    if (!username || !password) {
        authError.textContent = "Please enter username and password";
        return;
    }

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, role: "student" })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        currentUser = username;
        localStorage.setItem("studentUser", username);
        studentNameSpan.textContent = currentUser;
        authDiv.style.display = "none";
        chatDiv.style.display = "block";
        connectWebSocket();
        addBotMessage(`👋 Hello ${currentUser}! You can ask me about the menu, place orders, or just chat.`);
        loadOrderHistory();
    } catch (err) {
        authError.style.color = "red";
        authError.textContent = err.message;
    }
}

// ------------------- SIGNUP -------------------
async function signup() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    if (!username || !password) {
        authError.textContent = "Please enter username and password";
        return;
    }

    try {
        const res = await fetch(`${API_URL}/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, role: "student" })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.message || "Signup failed");

        authError.style.color = "green";
        authError.textContent = "Signup successful! Please login.";
    } catch (err) {
        authError.style.color = "red";
        authError.textContent = err.message;
    }
}

// ------------------- LOGOUT -------------------
function logout() {
    localStorage.removeItem("studentUser");
    currentUser = null;
    if (ws) { ws.close(); ws = null; }
    authDiv.style.display = "block";
    chatDiv.style.display = "none";
    chatBox.innerHTML = "";
    authError.textContent = "";
}

// ------------------- ORDER HISTORY -------------------
async function loadOrderHistory() {
    if (!currentUser) return;

    try {
        const res = await fetch(`${API_URL}/orders/history/${currentUser}`);
        if (!res.ok) throw new Error("Failed to load order history");

        const data = await res.json();
        const orders = data.orders || [];

        orderHistorySection.style.display = "block";
        orderHistoryList.innerHTML = "";

        if (orders.length === 0) {
            orderHistoryList.innerHTML = "<p>No orders yet.</p>";
            return;
        }

        orders.forEach(o => {
            const div = document.createElement("div");
            div.className = "orderItem";
            div.style.cssText = "padding:6px 4px;border-bottom:1px solid #ddd;";
            const dateStr = o.createdAt ? new Date(o.createdAt).toLocaleString() : "";
            const tokenBadge = o.token ? `🎫 <strong>#${o.token}</strong> &nbsp;|&nbsp; ` : "";
            const statusColor = o.status === "ready" ? "green" : "orange";
            div.innerHTML = `
                ${tokenBadge}
                <strong>${o.item.charAt(0).toUpperCase() + o.item.slice(1)}</strong>
                <div style="font-size:12px;color:#555;">
                    ${dateStr} — <span style="color:${statusColor};font-weight:bold;">${o.status}</span>
                </div>
            `;
            orderHistoryList.appendChild(div);
        });
    } catch (err) {
        console.error(err);
        orderHistoryList.innerHTML = "<p>Error loading history</p>";
    }
}

// ------------------- CHAT -------------------
async function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg || !currentUser) return;

    addUserMessage(msg);
    chatInput.value = "";

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ studentId: currentUser, message: msg })
        });
        const data = await res.json();
        addBotMessage(data.reply);

        if (data.token) {
            addBotMessage(`🎫 Your token number is <strong>#${data.token}</strong>. Show this at the counter when collecting your order.`);
            loadOrderHistory();
        }
    } catch (err) {
        addBotMessage("⚠️ Error connecting to server");
    }
}

// ------------------- CHAT UI -------------------
function addUserMessage(msg) {
    const div = document.createElement("div");
    div.className = "chat user";
    div.textContent = msg;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addBotMessage(msg) {
    const div = document.createElement("div");
    div.className = "chat bot";
    div.innerHTML = msg.replace(/\n/g, "<br>");
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ------------------- WEBSOCKET -------------------
function connectWebSocket() {
    if (!currentUser) return;
    if (ws) ws.close();

    ws = new WebSocket(`${WS_URL}/ws/${currentUser}`);

    ws.onmessage = (event) => {
        const message = event.data;
        addBotMessage(message);

        if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Canteen AI 🍽️", { body: message });
        }

        const note = document.createElement("div");
        note.className = "notification";
        note.textContent = message;
        notifications.appendChild(note);
        setTimeout(() => note.remove(), 5000);

        loadOrderHistory();
    };

    ws.onclose = () => {
        console.log("WebSocket closed, reconnecting...");
        setTimeout(connectWebSocket, 3000);
    };
}

// ------------------- VOICE INPUT -------------------
const micbtn = document.getElementById("mic-btn");
let recognition;

if ("webkitSpeechRecognition" in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";

    recognition.onstart = () => micbtn.classList.add("listening");
    recognition.onend = () => micbtn.classList.remove("listening");
    recognition.onresult = (e) => { chatInput.value = e.results[0][0].transcript; };

    micbtn.addEventListener("click", () => recognition.start());
}

// ------------------- SEND BUTTON / ENTER -------------------
document.getElementById("send-btn").addEventListener("click", sendMessage);
chatInput.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });
