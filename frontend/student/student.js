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

let currentUser = null;
let ws = null;
// ------------------- AUTO LOGIN ON REFRESH -------------------
window.onload = () => {
    const savedUser = localStorage.getItem("studentUser");
    if (savedUser) {
        currentUser = savedUser;

        authDiv.style.display = "none";
        chatDiv.style.display = "block";
        
        studentNameSpan.textContent = currentUser;
        connectWebSocket();
        addBotMessage(`👋 Welcome back ${currentUser}! How can I help you today?`);
        loadOrderHistory();   // <--- add this

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
        const res = await fetch("http://localhost:8000/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, role: "student" })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        currentUser = username;
localStorage.setItem("studentUser", username);   // <<< store username

studentNameSpan.textContent = currentUser;
authDiv.style.display = "none";
chatDiv.style.display = "block";

connectWebSocket();
addBotMessage(`👋 Hello ${currentUser}! You can ask me about the menu, place orders, or just chat.`);
loadOrderHistory();  // <--- add this


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
        const res = await fetch("http://localhost:8000/signup", {
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
    localStorage.removeItem("studentUser");   // <<< clear session storage
    currentUser = null;

    if (ws) {
        ws.close();
        ws = null;
    }

    authDiv.style.display = "block";
    chatDiv.style.display = "none";
    chatBox.innerHTML = "";
    authError.textContent = "";
}

// ------------------- ORDER HISTORY -------------------
const orderHistorySection = document.getElementById("orderHistorySection");
const orderHistoryList = document.getElementById("orderHistoryList");
const recentOrdersBtn = document.getElementById("recentOrdersBtn");

recentOrdersBtn.addEventListener("click", () => {
    orderHistorySection.classList.toggle("show");
});



async function loadOrderHistory() {
    if (!currentUser) return;

    try {
        const res = await fetch(`http://localhost:8000/orders/history/${currentUser}`);
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
            div.innerHTML = `
                <strong>${o.item}</strong>
                <div style="font-size:12px;color:#555;">${dateStr} — ${o.status}</div>
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
        const res = await fetch("http://localhost:8000/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ studentId: currentUser, message: msg })
        });
        const data = await res.json();
        addBotMessage(data.reply);
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

    if (ws) ws.close(); // Close old connection

    ws = new WebSocket(`ws://localhost:8000/ws/${currentUser}`);

    ws.onmessage = (event) => {
        const message = event.data;

        // Show in chat
        addBotMessage(message);

        // Show desktop notification
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Canteen AI", { body: message });
        }

        // Also add in notifications div
        const note = document.createElement("div");
        note.className = "notification";
        note.textContent = message;
        notifications.appendChild(note);
        setTimeout(() => note.remove(), 5000);
    };

    ws.onclose = () => console.log("WebSocket closed");
}
//voice input
// const micbtn=document.getElementById("mic-btn");
// let recognition;
// if("webkitSpeechRecognition" in window) {
//     recognition = new webkitSpeechRecognition();
//     recognition.lang="en-IN";
//     recognition.onresult=e=>chatInput.value=e.results[0][0].transcript;
//     micbtn.addEventListener("click",()=>recognition.start());
// }
const micbtn = document.getElementById("mic-btn");
let recognition;

if ("webkitSpeechRecognition" in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";

    recognition.onstart = () => {
        micbtn.classList.add("listening");
    };

    recognition.onend = () => {
        micbtn.classList.remove("listening");
    };

    recognition.onresult = (e) => {
        chatInput.value = e.results[0][0].transcript;
    };

    micbtn.addEventListener("click", () => recognition.start());
}
//enter button
const sendbtn=document.getElementById("send-btn");
sendbtn.addEventListener("click",sendMessage);
chatInput.addEventListener("keypress",e=> { if(e.key==="Enter") sendMessage();});