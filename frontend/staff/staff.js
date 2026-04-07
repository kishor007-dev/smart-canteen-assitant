// ------------------- CONFIG -------------------
import { API_URL, WS_URL } from "./config.js";

// ------------------- DOM ELEMENTS -------------------
const loginDiv = document.getElementById('loginDiv');
const signupDiv = document.getElementById('signupDiv');
const dashboardDiv = document.getElementById('dashboardDiv');

const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginError = document.getElementById('loginError');

const signupUsername = document.getElementById('signupUsername');
const signupPassword = document.getElementById('signupPassword');
const signupRole = document.getElementById('signupRole');
const signupError = document.getElementById('signupError');

const staffName = document.getElementById('staffName');
const pendingOrdersList = document.getElementById('pendingOrdersList');

const menuList = document.getElementById('menuList');
const menuItemName = document.getElementById('menuItemName');
const menuItemPrice = document.getElementById('menuItemPrice');
const specialSelect = document.getElementById('specialSelect');
const specialMsg = document.getElementById('specialMsg');

let currentUser = localStorage.getItem("user") || null;
let staffSocket;

// ------------------- INITIALIZATION -------------------
window.addEventListener("load", () => {
    document.getElementById("addmenu").addEventListener("click", addOrUpdateMenuItem);
    document.getElementById("removeitem").addEventListener("click", removeMenuItem);
    document.getElementById("special").addEventListener("click", setDailySpecial);
    document.getElementById("logout-btn").addEventListener("click", logout);
    document.getElementById("login").addEventListener("click", login);
    document.getElementById("signupid").addEventListener("click", showSignup);
    document.getElementById("signup").addEventListener("click", signup);

    if (currentUser) initDashboard();
});

// ------------------- LOGIN / SIGNUP UI -------------------
function showSignup() {
    loginDiv.style.display = "none";
    signupDiv.style.display = "block";
}
function showLogin() {
    signupDiv.style.display = "none";
    loginDiv.style.display = "block";
}

// ------------------- AUTH -------------------
async function signup() {
    const username = signupUsername.value.trim();
    const password = signupPassword.value.trim();
    const role = signupRole.value;
    if (!username || !password) { signupError.textContent = "Enter username & password"; return; }

    const res = await fetch(`${API_URL}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role })
    });
    const data = await res.json();
    if (!res.ok) { signupError.textContent = data.detail || "Sign Up failed"; return; }
    alert("✅ Registration successful! Login now.");
    showLogin();
}

async function login() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    if (!username || !password) { loginError.textContent = "Enter username & password"; return; }

    const res = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role: "staff" })
    });
    const data = await res.json();
    if (!res.ok) { loginError.textContent = data.detail || "Login failed"; return; }

    currentUser = username;
    localStorage.setItem("user", username);
    initDashboard();
}

function logout() {
    localStorage.removeItem("user");
    currentUser = null;
    if (staffSocket) staffSocket.close();
    dashboardDiv.style.display = "none";
    loginDiv.style.display = "block";
    usernameInput.value = "";
    passwordInput.value = "";
}

// ------------------- DASHBOARD INIT -------------------
function initDashboard() {
    loginDiv.style.display = "none";
    signupDiv.style.display = "none";
    dashboardDiv.style.display = "block";
    staffName.textContent = currentUser;

    loadPendingOrders();
    loadMenu();
    loadAnalytics();
    connectStaffWS();

    setInterval(loadPendingOrders, 4000);
    setInterval(loadAnalytics, 30000);
}

// ------------------- PENDING ORDERS -------------------
async function loadPendingOrders() {
    try {
        const res = await fetch(`${API_URL}/orders/pending`);
        if (!res.ok) throw new Error("Failed to fetch pending orders");
        const orders = await res.json();
        pendingOrdersList.innerHTML = "";

        if (orders.length === 0) {
            pendingOrdersList.innerHTML = "<li style='color:#888;padding:10px;'>No pending orders ✅</li>";
            return;
        }

        orders.forEach(order => {
            const li = document.createElement('li');
            li.style.cssText = "padding:10px 8px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;gap:8px;";
            li.innerHTML = `
                <span>
                    🎫 <strong>Token #${order.token || "—"}</strong> &nbsp;|&nbsp;
                    🍽️ ${order.item.charAt(0).toUpperCase() + order.item.slice(1)} &nbsp;|&nbsp;
                    👤 ${order.studentId} &nbsp;|&nbsp;
                    🕒 ${order.createdAt || ""}
                </span>
            `;
            const readyBtn = document.createElement('button');
            readyBtn.textContent = "✅ Mark Ready";
            readyBtn.style.cssText = "padding:5px 12px;background:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;white-space:nowrap;";
            readyBtn.onclick = async () => {
                readyBtn.disabled = true;
                readyBtn.textContent = "Marking...";
                await fetch(`${API_URL}/orders/ready/${order._id}`, { method: "POST" });
                loadPendingOrders();
                loadAnalytics();
            };
            li.appendChild(readyBtn);
            pendingOrdersList.appendChild(li);
        });
    } catch (err) { console.error(err); }
}

// ------------------- MENU -------------------
async function loadMenu() {
    try {
        const res = await fetch(`${API_URL}/menu`);
        const data = await res.json();
        menuList.innerHTML = "";
        specialSelect.innerHTML = "";

        data.menu.forEach(item => {
            const li = document.createElement('li');
            li.style.cssText = "padding:7px 4px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #eee;";

            const label = document.createElement('span');
            label.innerHTML = `${item.available ? "✅" : "❌"} <strong>${item.name}</strong>: ₹${item.price}
                ${!item.available ? '<em style="color:red;font-size:12px;"> (Out of Stock)</em>' : ""}`;
            li.appendChild(label);

            const toggleBtn = document.createElement('button');
            toggleBtn.textContent = item.available ? "Mark Unavailable" : "Mark Available";
            toggleBtn.style.cssText = `padding:3px 9px;font-size:12px;cursor:pointer;border:none;border-radius:4px;
                background:${item.available ? "#dc3545" : "#28a745"};color:white;`;
            toggleBtn.onclick = async () => {
                await fetch(`${API_URL}/menu/availability`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: item.name, available: !item.available, username: currentUser })
                });
                loadMenu();
            };
            li.appendChild(toggleBtn);
            menuList.appendChild(li);

            if (item.available) {
                const option = document.createElement('option');
                option.value = item.name;
                option.textContent = item.name;
                specialSelect.appendChild(option);
            }
        });
    } catch (err) { console.error(err); }
}

// ------------------- ADD / REMOVE MENU -------------------
async function addOrUpdateMenuItem() {
    const name = menuItemName.value.trim();
    const price = parseInt(menuItemPrice.value.trim());
    if (!name || isNaN(price)) return alert("Enter valid name & price");

    const res = await fetch(`${API_URL}/menu/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, price, username: currentUser })
    });
    const data = await res.json();
    alert(data.message || "Menu updated");
    menuItemName.value = "";
    menuItemPrice.value = "";
    loadMenu();
}

async function removeMenuItem() {
    const name = menuItemName.value.trim();
    if (!name) return alert("Enter item name to remove");

    const res = await fetch(`${API_URL}/menu/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, username: currentUser })
    });
    const data = await res.json();
    alert(data.message || "Item removed");
    menuItemName.value = "";
    menuItemPrice.value = "";
    loadMenu();
}

// ------------------- DAILY SPECIAL -------------------
async function setDailySpecial() {
    const specialItem = specialSelect.value;
    if (!specialItem) return;

    const res = await fetch(`${API_URL}/menu/special`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ special: specialItem, username: currentUser })
    });
    const data = await res.json();
    specialMsg.textContent = data.message || "Daily special set!";
}

// ------------------- ANALYTICS -------------------
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_URL}/analytics`);
        const data = await res.json();
        const div = document.getElementById("analyticsDiv");
        if (!div) return;

        div.innerHTML = `
            <h3 style="margin:0 0 10px 0;">📊 Dashboard</h3>
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;">
                <div style="background:#e8f5e9;padding:10px 18px;border-radius:8px;text-align:center;min-width:90px;">
                    <div style="font-size:22px;font-weight:bold;color:purple">${data.today_orders}</div>
                    <div style="font-size:12px;color:#555;">Orders Today</div>
                </div>
                <div style="background:#e3f2fd;padding:10px 18px;border-radius:8px;text-align:center;min-width:90px;">
                    <div style="font-size:22px;font-weight:bold;color:green">₹${data.today_revenue}</div>
                    <div style="font-size:12px;color:#555;">Revenue Today</div>
                </div>
                <div style="background:#fff8e1;padding:10px 18px;border-radius:8px;text-align:center;min-width:90px;">
                    <div style="font-size:22px;font-weight:bold;color:red">${data.pending}</div>
                    <div style="font-size:12px;color:#555;">Pending</div>
                </div>
                <div style="background:#fce4ec;padding:10px 18px;border-radius:8px;text-align:center;min-width:90px;">
                    <div style="font-size:22px;font-weight:bold;color:pink">${data.completed}</div>
                    <div style="font-size:12px;color:#555;">Completed</div>
                </div>
            </div>
            <strong>🔥 Top Items (All Time):</strong>
            <ul style="margin:6px 0 0 0;padding:0;list-style:none;">
    ${data.popular_items.map(i => `
        <li style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #eee;">
            <span>${i.item}</span>
            <strong style="min-width:40px;text-align:right;">${i.count} orders</strong>
        </li>`).join("")}
</ul>
        `;
    } catch (err) { console.error("Analytics error:", err); }
}

// ------------------- STAFF WEBSOCKET -------------------
function connectStaffWS() {
    staffSocket = new WebSocket(`${WS_URL}/ws/staff`);

    staffSocket.onopen = () => console.log("✅ WS Connected");
    staffSocket.onmessage = (event) => {
        console.log("📩 New order received via WS");
        loadPendingOrders();
        loadAnalytics();
    };
    staffSocket.onerror = (err) => console.log("❌ WS error:", err);
    staffSocket.onclose = () => {
        console.log("⚠️ WS closed. Reconnecting...");
        setTimeout(connectStaffWS, 2000);
    };
}
