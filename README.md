# 🍴 Smart Canteen AI Assistant

**AI-powered Smart Canteen Assistant for students and staff with real-time chat, menu management, and order tracking.**

---

## 🚀 Overview

Smart Canteen AI is a full-stack web application that allows students to interact with an AI-powered assistant for food recommendations, ordering, and menu browsing.

It also provides a staff panel to manage menu items and track orders in real time.

---

## 🔥 Key Features

### 👨‍🎓 Student Panel

* Login / Signup
* Chat with AI assistant
* View menu & daily specials
* Place / cancel orders
* View order history

### 👨‍🍳 Staff Panel

* Manage menu items
* Set daily specials
* Track and update order status

### 🤖 AI Capabilities

* AI-powered food recommendations
* Conversational interface (Groq + LLaMA 3.1 70B)

### ⚡ Real-Time Features

* WebSocket-based notifications
* Live order updates

---

## 🛠️ Tech Stack

* **Backend:** FastAPI
* **Database:** MongoDB Atlas (Cloud)
* **AI Model:** Groq (LLaMA 3.1 70B)
* **Frontend:** HTML, CSS, JavaScript
* **Real-time:** WebSockets

---

## 🆕 Recent Updates

* Migrated database from local MongoDB to MongoDB Atlas
* Improved backend configuration using environment variables
* Cleaned and structured backend code

---

## 📂 Project Structure

Smart-Canteen-Assitant/
│
├─ backend/
│   ├─ main.py
│   └─ requirements.txt
│
├─ student/
├─ staff/
├─ assets/
└─ README.md

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/kishor007-dev/smart-canteen-assitant
cd smart-canteen-assitant
```

---

### 2️⃣ Backend Setup

```bash
python -m venv venv

# Activate environment

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
```

---

### 3️⃣ Environment Variables

Create a `.env` file in the root directory:

```
MONGODB_URL=your_mongodb_atlas_connection_string
GROQ_API_KEY=your_api_key
```

---

### 4️⃣ Run Backend Server

```bash
uvicorn backend.main:app --reload
```

---

### 5️⃣ Run Frontend

Open in browser using Live Server (VS Code):

* student/student.html
* staff/staff.html

---

## 🔗 Repository Link

https://github.com/kishor007-dev/smart-canteen-assitant

---

## 📌 Future Improvements

* Hybrid Search (Vector + Keyword)
* Advanced AI recommendations (RAG)
* Payment gateway integration
* Admin analytics dashboard
* Docker deployment

---

## 🧠 Learnings

* Built scalable backend using FastAPI
* Integrated AI (LLM) into real-world application
* Migrated database to cloud (MongoDB Atlas)
* Implemented real-time communication using WebSockets

---

## 📜 License

This project is for educational purposes.
