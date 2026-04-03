// ------------------- ELEMENTS -------------------
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

let currentUser = null;
// ------------------- AUTO LOGIN ON REFRESH -------------------
window.onload = () => {
    const savedUser = localStorage.getItem("user");
    if (savedUser) {
        currentUser = savedUser;

        loginDiv.style.display = "none";
        signupDiv.style.display = "none";
        dashboardDiv.style.display = "block";

        staffName.textContent = savedUser;

        loadPendingOrders();
        loadMenu();
    }
};


// ------------------- SHOW LOGIN/SIGNUP -------------------
function showSignup() {
    loginDiv.style.display = "none";
    signupDiv.style.display = "block";
}
function showLogin() {
    signupDiv.style.display = "none";
    loginDiv.style.display = "block";
}

// ------------------- STAFF SIGNUP -------------------
async function signup() {
    const username = signupUsername.value.trim();
    const password = signupPassword.value.trim();
    const role = signupRole.value;

    if (!username || !password) {
        signupError.textContent = "Enter username and password";
        return;
    }

    const res = await fetch('http://localhost:8000/signup', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role })
    });
    const data = await res.json();

    if (res.status !== 200) {
        signupError.textContent = data.detail || "Sign Up failed";
        return;
    }

    alert("Registration successful! You can login now.");
    showLogin();
}

// ------------------- STAFF LOGIN -------------------
async function login() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        loginError.textContent = "Enter username and password";
        return;
    }

    const res = await fetch('http://localhost:8000/login', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role: "staff" })
    });

    const data = await res.json();

    if (res.status !== 200) {
        loginError.textContent = data.detail || "Login failed";
        return;
    }

currentUser = username;
localStorage.setItem("user", username);  // <<< Save login session

loginDiv.style.display = "none";
dashboardDiv.style.display = "block";
staffName.textContent = username;

loadPendingOrders();
loadMenu(); 

}

// ------------------- LOGOUT -------------------
function logout() {
    localStorage.removeItem("user"); // <<< clear session
    currentUser = null;

    dashboardDiv.style.display = "none";
    loginDiv.style.display = "block";
    usernameInput.value = "";
    passwordInput.value = "";
}


// ------------------- LOAD PENDING ORDERS -------------------
async function loadPendingOrders() {
    const res = await fetch('http://localhost:8000/orders/pending');
    const orders = await res.json();
    pendingOrdersList.innerHTML = "";

    orders.forEach(order => {
        const li = document.createElement('li');
        li.textContent = `Order: ${order.item} | Student: ${order.studentId} `;
        const readyBtn = document.createElement('button');
        readyBtn.textContent = "Mark Ready";
        readyBtn.onclick = async () => {
            await fetch(`http://localhost:8000/orders/ready/${order._id}`, { method: "POST" });
            loadPendingOrders(); // refresh
        };
        li.appendChild(readyBtn);
        pendingOrdersList.appendChild(li);
    });
}

// ------------------- LOAD MENU -------------------
async function loadMenu() {
    const res = await fetch('http://localhost:8000/menu');
    const data = await res.json();
    menuList.innerHTML = "";
    specialSelect.innerHTML = "";

    data.menu.forEach(item => {
        // List menu items
        const li = document.createElement('li');
        li.textContent = `${item.name}: ₹${item.price}`;
        menuList.appendChild(li);

        // Add to special select
        const option = document.createElement('option');
        option.value = item.name;
        option.textContent = item.name;
        specialSelect.appendChild(option);
    });
}
// ------------------- ADD OR UPDATE MENU ITEM -------------------
async function addOrUpdateMenuItem() {
    const name = menuItemName.value.trim();
    const price = parseInt(menuItemPrice.value.trim());
    if (!name || isNaN(price)) {
        alert("Enter valid name and price");
        return;
    }

    const res = await fetch('http://localhost:8000/menu/update', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, price, username: currentUser }) // include username
    });
    const data = await res.json();
    alert(data.message);
    menuItemName.value = "";
    menuItemPrice.value = "";
    loadMenu();
}

// ------------------- REMOVE MENU ITEM -------------------
async function removeMenuItem() {
    const name = menuItemName.value.trim();
    if (!name) {
        alert("Enter item name to remove");
        return;
    }

    const res = await fetch('http://localhost:8000/menu/remove', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, username: currentUser }) // include username
    });
    const data = await res.json();
    alert(data.message);
    menuItemName.value = "";
    menuItemPrice.value = "";
    loadMenu();
}

// ------------------- SET DAILY SPECIAL -------------------
async function setDailySpecial() {
    const specialItem = specialSelect.value;
    if (!specialItem) return;

    const res = await fetch('http://localhost:8000/menu/special', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ special: specialItem, username: currentUser }) // include username
    });
    const data = await res.json();
    specialMsg.textContent = data.message;
}


