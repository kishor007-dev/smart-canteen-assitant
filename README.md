# 🍴 Smart Canteen AI Assistant

**AI-powered Smart Canteen Assistant for students and staff with real-time chat, menu management, and order tracking.**

---

## 🌐 Live Demo

| Panel | Link |
|-------|------|
| 👨‍🎓 Student Side | https://canteenstudent.netlify.app |
| 👨‍🍳 Staff Side | https://canteenstaff.netlify.app |
| ⚙️ Backend API | https://smart-canteen-assitant-3.onrender.com |

---

## 🚀 Overview

Smart Canteen AI is a full-stack web application that streamlines food ordering in college canteens.

It allows:
- Students to interact with an AI assistant for food recommendations and ordering 
- Staff to manage menu items and track orders in real time  

The system combines **AI, real-time communication, and cloud deployment** to deliver a modern canteen experience.

---

## 🔥 Key Features

### 👨‍🎓 Student Panel
- Login / Signup
- Chat with AI assistant
- View menu & daily specials
- Place / cancel orders
- Token number assigned on order placement
- View order history

### 👨‍🍳 Staff Panel
- Manage menu items (add / remove)
- Toggle item availability in real time
- Set daily specials
- Track and update order status
- Analytics dashboard (orders, revenue, popular items)

### 🤖 AI Capabilities
- AI-powered food recommendations
- Conversational interface (Groq + LLaMA 3.1 8B)
- Combo suggestions based on daily specials and order history
- Fallback LLM responses for general queries

### ⚡ Real-Time Features
- WebSocket-based order notifications to staff
- Live order-ready alerts to students

### 🔐 Security
- Secure password hashing using bcrypt

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | MongoDB Atlas |
| AI Model | Groq API (LLaMA 3.1 8B) |
| Frontend | HTML, CSS, JavaScript |
| Real-time | WebSockets |
| Authentication | bcrypt password hashing |
| Deployment | Netlify (Frontend), Render (Backend) |

---

## 🆕 Recent Updates

- ✅ Token-based order tracking system
- ✅ Real-time item availability toggle
- ✅ Staff analytics dashboard (revenue & trends)
- ✅ Secure password hashing (bcrypt)
- ✅ Migration to MongoDB Atlas (cloud database)
- ✅ Full deployment (Netlify + Render)
- ✅ Environment-based configuration (.env)

---

## 📂 Project Structure

```
Smart-Canteen-Assistant/
│
├── backend/
│   └── main.py
│
├── frontend/
│   ├── student/
│   └── staff/
│
├── .gitignore
├── requirements.txt
├── runtime.txt
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/kishor007-dev/smart-canteen-assistant
cd smart-canteen-assistant
```

### 2️⃣ Backend Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3️⃣ Environment Variables

Create a `.env` file:

```env
MONGODB_URL=your_mongodb_atlas_connection_string
GROQ_API_KEY=your_groq_api_key
```

### 4️⃣ Run Backend Server

```bash
uvicorn backend.main:app --reload
```

### 5️⃣ Run Frontend

Open in browser:

- `frontend/student/student.html`
- `frontend/staff/staff.html`

Or use the deployed links above.

---

## 🔗 Repository

https://github.com/kishor007-dev/smart-canteen-assistant

---

## 📌 Future Improvements

- [ ] JWT-based session management
- [ ] Hybrid Search (Vector + Keyword)
- [ ] RAG-based AI recommendations
- [ ] Payment gateway integration
- [ ] Mobile-responsive UI improvements
- [ ] Docker deployment

---

## 🧠 Learnings

- Built scalable backend using FastAPI with async patterns
- Integrated LLM into a real-world food ordering workflow
- Implemented WebSockets for real-time updates
- Migrated database to MongoDB Atlas
- Deployed full-stack application using Netlify and Render
- Implemented secure password storage using bcrypt

---

## 📜 License

This project is for educational purposes.
