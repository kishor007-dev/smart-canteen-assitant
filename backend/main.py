# backend/main.py
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
import os, re, bcrypt
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import uvicorn
from collections import Counter

# --------------------------- DATABASE ---------------------------
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise Exception("MONGODB_URL not set in environment")
client = MongoClient(MONGODB_URL)
try:
    client.admin.command("ping")
    print("✅ MongoDB connection SUCCESS")
except Exception as e:
    print("❌ MongoDB connection FAILED:", e)
db = client["canteen_ai"]
users_col = db["users"]
orders_col = db["orders"]
menu_col = db["menu"]
chat_history_col = db["chat_history"]

# --------------------------- GROQ SETUP ---------------------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if not os.getenv("GROQ_API_KEY"):
    raise Exception("GROQ_API_KEY not set")

# --------------------------- FASTAPI ---------------------------
app = FastAPI(title="Smart Canteen AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running", "service": "Smart Canteen API", "version": "2.0"}

# --------------------------- MODELS ---------------------------
class LoginModel(BaseModel):
    username: str
    password: str
    role: str

class ChatModel(BaseModel):
    studentId: str
    message: str

class OrderModel(BaseModel):
    studentId: str
    item: str

class MenuUpdateModel(BaseModel):
    name: str
    price: int
    username: str

class MenuRemoveModel(BaseModel):
    name: str
    username: str

class SpecialModel(BaseModel):
    special: str
    username: str

class AvailabilityModel(BaseModel):
    name: str
    available: bool
    username: str

# --------------------------- HELPERS ---------------------------
DEFAULT_MENU = {
    "idly": 20,
    "dosa": 30,
    "poori": 35,
    "fried rice": 70,
    "noodles": 65,
    "paneer masala": 80
}

def get_menu():
    menu_doc = menu_col.find_one({})
    if not menu_doc:
        menu_col.insert_one({"menu": DEFAULT_MENU})
        return DEFAULT_MENU
    return menu_doc["menu"]

def next_token():
    last_order = orders_col.find_one({}, sort=[("token", -1)])
    if last_order and "token" in last_order:
        return last_order["token"] + 1
    return 1

# --------------------------- WEBSOCKET CONNECTIONS ---------------------------
staff_connections = []
active_connections = {}

async def broadcast_to_staff(order: dict):
    for conn in staff_connections[:]:
        try:
            await conn.send_json(order)
        except Exception:
            if conn in staff_connections:
                staff_connections.remove(conn)

# --------------------------- LOGIN / SIGNUP ---------------------------
@app.post("/signup")
def signup(user: LoginModel):
    existing = users_col.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users_col.insert_one({
        "username": user.username,
        "password": hashed,
        "role": user.role
    })
    return {"message": "Sign up successful!"}

@app.post("/login")
def login(user: LoginModel):
    found = users_col.find_one({"username": user.username, "role": user.role})
    if not found or not bcrypt.checkpw(user.password.encode(), found["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "role": user.role, "username": user.username}

# --------------------------- MENU ---------------------------
@app.get("/menu")
def menu_api():
    menu_doc = menu_col.find_one({})
    menu = get_menu()
    availability = menu_doc.get("availability", {}) if menu_doc else {}
    return {
        "menu": [
            {
                "name": k.capitalize(),
                "price": v,
                "available": availability.get(k, True)
            }
            for k, v in menu.items()
        ]
    }

@app.post("/menu/update")
def update_menu_item(item: MenuUpdateModel):
    staff_user = users_col.find_one({"username": item.username.strip().lower(), "role": "staff"})
    if not staff_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    menu_doc = menu_col.find_one({})
    if not menu_doc:
        menu_col.insert_one({"menu": {item.name.lower(): item.price}})
    else:
        menu = menu_doc["menu"]
        menu[item.name.lower()] = item.price
        menu_col.update_one({}, {"$set": {"menu": menu}})
    return {"message": f"✅ Menu updated: {item.name.capitalize()} - ₹{item.price}"}

@app.post("/menu/remove")
def remove_menu_item(item: MenuRemoveModel):
    staff_user = users_col.find_one({"username": item.username, "role": "staff"})
    if not staff_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    menu_doc = menu_col.find_one({})
    if not menu_doc or item.name.lower() not in menu_doc["menu"]:
        raise HTTPException(status_code=400, detail=f"{item.name.capitalize()} not found in menu")
    menu = menu_doc["menu"]
    menu.pop(item.name.lower())
    menu_col.update_one({}, {"$set": {"menu": menu}})
    return {"message": f"✅ Removed {item.name.capitalize()} from menu"}

@app.post("/menu/special")
def set_daily_special(special: SpecialModel):
    staff_user = users_col.find_one({"username": special.username, "role": "staff"})
    if not staff_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    menu_doc = menu_col.find_one({})
    if not menu_doc or special.special.lower() not in menu_doc["menu"]:
        raise HTTPException(status_code=400, detail=f"{special.special.capitalize()} not in menu")
    menu_col.update_one({}, {"$set": {"daily_special": special.special.lower()}})
    return {"message": f"⭐ Daily special set to {special.special.capitalize()}"}

@app.post("/menu/availability")
async def toggle_availability(data: AvailabilityModel):
    staff_user = users_col.find_one({"username": data.username, "role": "staff"})
    if not staff_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    menu_col.update_one(
        {},
        {"$set": {f"availability.{data.name.lower()}": data.available}}
    )
    status = "available" if data.available else "unavailable"

    # Broadcast to all connected students
    message = f"⚠️ {data.name.capitalize()} is now {status}."
    for student_id, conn in list(active_connections.items()):
        try:
            await conn.send_text(message)
        except Exception:
            active_connections.pop(student_id, None)

    return {"message": f"✅ {data.name.capitalize()} marked as {status}"}
@app.get("/menu/special")
def get_daily_special():
    menu_doc = menu_col.find_one({})
    menu = get_menu()
    special = menu_doc.get("daily_special") if menu_doc else None
    if not special:
        recommended = list(menu.keys())[0]
        price = menu[recommended]
        return {"special": {"name": recommended.capitalize(), "price": price, "recommended": True}}
    price = menu.get(special, "N/A")
    return {"special": {"name": special.capitalize(), "price": price, "recommended": False}}

# --------------------------- ORDERS ---------------------------
@app.get("/orders/pending")
def get_pending_orders():
    orders = list(orders_col.find({"status": "pending"}).sort("token", 1))
    for o in orders:
        o["_id"] = str(o["_id"])
        if "createdAt" in o and not isinstance(o["createdAt"], str):
            o["createdAt"] = o["createdAt"].strftime("%Y-%m-%d %H:%M:%S")
    return orders

@app.post("/place-order")
async def place_order(data: OrderModel):
    menu = get_menu()
    item = data.item.strip().lower()
    if item not in menu:
        raise HTTPException(status_code=400, detail="Item not in menu")

    token = next_token()
    order = {
        "_id": str(ObjectId()),
        "token": token,
        "studentId": data.studentId.strip().lower(),
        "item": item,
        "status": "pending",
        "createdAt": datetime.now()
    }
    orders_col.insert_one(order)
    order["createdAt"] = order["createdAt"].strftime("%Y-%m-%d %H:%M:%S")
    await broadcast_to_staff(order)

    return {"message": f"✅ Order for {item.capitalize()} placed successfully!", "token": token}

@app.post("/orders/ready/{order_id}")
async def mark_order_ready(order_id: str):
    order = orders_col.find_one({"_id": order_id})
    if not order:
        try:
            order = orders_col.find_one({"_id": ObjectId(order_id)})
        except:
            pass
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    orders_col.update_one({"_id": order["_id"]}, {"$set": {"status": "ready"}})

    student_id = order["studentId"].strip().lower()
    if student_id in active_connections:
        try:
            await active_connections[student_id].send_text(
                f"🍽️ Your order for {order['item'].capitalize()} is ready! 🎫 Token #{order.get('token', '—')}"
            )
        except Exception:
            pass

    return {"message": f"Order {order_id} marked ready."}

@app.get("/orders/history/{studentId}")
def order_history(studentId: str):
    orders = list(orders_col.find({"studentId": studentId}).sort("createdAt", DESCENDING))
    for o in orders:
        o["_id"] = str(o["_id"])
        if "createdAt" in o and not isinstance(o["createdAt"], str):
            o["createdAt"] = o["createdAt"].strftime("%Y-%m-%d %H:%M")
    return {"orders": orders}

# --------------------------- ANALYTICS ---------------------------
@app.get("/analytics")
def get_analytics():
    today = datetime.now().strftime("%Y-%m-%d")
    all_orders = list(orders_col.find({}))

    today_orders = [
        o for o in all_orders
        if str(o.get("createdAt", "")).startswith(today)
    ]

    menu = get_menu()
    revenue = sum(menu.get(o["item"].lower(), 0) for o in today_orders)

    item_counts = Counter(o["item"] for o in all_orders)
    popular = [
        {"item": k.capitalize(), "count": v}
        for k, v in item_counts.most_common(5)
    ]

    pending = orders_col.count_documents({"status": "pending"})
    completed = orders_col.count_documents({"status": "ready"})

    return {
        "today_orders": len(today_orders),
        "today_revenue": revenue,
        "popular_items": popular,
        "pending": pending,
        "completed": completed
    }

# --------------------------- CHATBOT ---------------------------
student_memory = {}

@app.post("/chat")
async def chat(payload: ChatModel):
    student_id = payload.studentId
    user_msg = payload.message.strip().lower()

    menu = get_menu()
    menu_items = [k.lower() for k in menu.keys()]
    menu_lines = [f"{idx+1}. {item.capitalize()} - ₹{price}" for idx, (item, price) in enumerate(menu.items())]
    menu_text = "\n".join(menu_lines)
    menu_doc = menu_col.find_one({})
    daily_special = menu_doc.get("daily_special") if menu_doc else None

    if student_id not in student_memory:
        student_memory[student_id] = {
            "last_item": None,
            "last_action": None,
            "last_intent": "normal",
            "last_bot_message": "",
            "greeted": False
        }

    memory = student_memory[student_id]

    if memory["last_intent"] == "normal" and not memory.get("greeted"):
        memory["greeted"] = True
        return {"reply": "Welcome to our canteen! What can I get for you today? Would you like to see the menu or get a recommendation?"}

    reply = ""

    # ---------- Cancel last order ----------
    if re.search(r"\b(cancel|remove|forget|wrong item)\b", user_msg) and memory.get("last_item") and memory.get("last_action") == "order":
        last_item = memory["last_item"]
        result = orders_col.delete_one({"studentId": student_id, "item": last_item, "status": "pending"})
        if result.deleted_count > 0:
            reply = f"❌ Last order for {last_item.capitalize()} has been cancelled."
        else:
            reply = f"⚠️ No pending order found for {last_item.capitalize()} to cancel."
        memory["last_item"] = None
        memory["last_action"] = None
        return {"reply": reply}

    # ---------- Handle confirmation ----------
    if memory["last_intent"] == "waiting_confirmation":
        if user_msg in ["yes", "ok", "sure", "haa", "ha", "confirm"]:
            token = next_token()
            new_order = {
                "_id": str(ObjectId()),
                "token": token,
                "studentId": student_id,
                "item": memory["last_item"],
                "status": "pending",
                "createdAt": datetime.now()
            }
            orders_col.insert_one(new_order)
            new_order["createdAt"] = new_order["createdAt"].strftime("%Y-%m-%d %H:%M:%S")
            await broadcast_to_staff(new_order)
            memory["last_intent"] = "normal"
            memory["last_action"] = "order"
            reply = f"✅ Order placed for {memory['last_item'].capitalize()}! 🎫 Your token number is <strong>#{token}</strong>"
            chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
            return {"reply": reply, "token": token}

        elif user_msg in ["no", "cancel", "nope", "not now"]:
            memory["last_intent"] = "normal"
            return {"reply": "❌ Okay, cancelled! Let me know if you need anything else."}

    # ---------- Menu inquiry ----------
    if "menu" in user_msg:
        reply = f"📋 Here's our current menu:\n{menu_text}\n\nWould you like to order something?"
        chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
        return {"reply": reply}

    # ---------- Detect menu item mention ----------
    mentioned_item = None
    for item in menu_items:
        if item in user_msg:
            mentioned_item = item
            break

    if mentioned_item:
        memory["last_item"] = mentioned_item
        memory["last_action"] = "recommend"
        memory["last_intent"] = "waiting_confirmation"
        reply = f"👍 You selected {mentioned_item.capitalize()}. Should I place the order?"
        chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
        return {"reply": reply}

    # ---------- Recommend / Special ----------
    if any(word in user_msg for word in ["recommend", "special", "suggest", "best", "tasty", "combo"]):
        past_orders = list(orders_col.find({"studentId": student_id}))
        ordered_items = [o["item"] for o in past_orders]
        if daily_special:
            price = menu.get(daily_special, "N/A")
            reply = f"⭐ Today's special is {daily_special.capitalize()} at ₹{price}. Highly recommended!"
            if len(menu) > 2:
                other_items = [i for i in menu_items if i != daily_special]
                reply += f"\n💡 Combo suggestion: {daily_special.capitalize()} + {other_items[0].capitalize()} for a perfect meal!"
        else:
            system_prompt = f"You are a smart canteen assistant.\nMenu: {menu_text}\nStudent previously ordered: {ordered_items if ordered_items else 'None'}\nSuggest a tasty combo or single item."
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": payload.message}]
            try:
                response = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7, max_tokens=150)
                reply = response.choices[0].message.content.strip()
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"
        chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
        return {"reply": reply}

    # ---------- Direct order intent ----------
    possible_items = re.split(r'\band\b|,', user_msg)
    ordered_items = list(set(
        item for part in possible_items
        for item in menu_items if item in part.strip()
    ))

    if ordered_items:
        placed_tokens = []
        for ordered_item in ordered_items:
            token = next_token()
            new_order = {
                "_id": str(ObjectId()),
                "token": token,
                "studentId": student_id,
                "item": ordered_item,
                "status": "pending",
                "createdAt": datetime.now()
            }
            orders_col.insert_one(new_order)
            new_order["createdAt"] = new_order["createdAt"].strftime("%Y-%m-%d %H:%M:%S")
            await broadcast_to_staff(new_order)
            placed_tokens.append(token)
        memory["last_item"] = ordered_items[0]
        memory["last_action"] = "order"
        reply = f"✅ Orders placed for: {', '.join([i.capitalize() for i in ordered_items])}! 🎫 Token(s): {', '.join([f'#{t}' for t in placed_tokens])}"
        chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
        return {"reply": reply, "token": placed_tokens[0]}

    # ---------- Fallback LLM ----------
    system_prompt = f"You are a polite and friendly canteen assistant.\nCurrent menu:\n{menu_text}\nYou can suggest combos, menu items, or chat casually."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": payload.message}]
    try:
        response = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7, max_tokens=150)
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"⚠️ Error: {str(e)}"

    chat_history_col.insert_one({"studentId": student_id, "user": payload.message, "bot": reply, "createdAt": datetime.now()})
    return {"reply": reply}

# --------------------------- SEED ---------------------------
@app.get("/seed")
def seed_users():
    users_col.delete_many({})
    hashed_student = bcrypt.hashpw(b"123", bcrypt.gensalt()).decode()
    hashed_staff = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
    users_col.insert_many([
        {"username": "student1", "password": hashed_student, "role": "student"},
        {"username": "staff1", "password": hashed_staff, "role": "staff"},
    ])
    return {"message": "Sample users added with hashed passwords"}

@app.get("/seed-orders")
def seed_orders():
    orders_col.delete_many({})
    orders_col.insert_many([
        {"token": 1, "studentId": "student1", "item": "idly", "status": "pending", "createdAt": datetime.now()},
        {"token": 2, "studentId": "student2", "item": "dosa", "status": "pending", "createdAt": datetime.now()}
    ])
    return {"message": "Sample orders added"}

# --------------------------- WEBSOCKETS ---------------------------
@app.websocket("/ws/staff")
async def staff_ws(websocket: WebSocket):
    await websocket.accept()
    staff_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in staff_connections:
            staff_connections.remove(websocket)

@app.websocket("/ws/{student_id}")
async def websocket_endpoint(websocket: WebSocket, student_id: str):
    await websocket.accept()
    active_connections[student_id.strip().lower()] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.pop(student_id, None)

# --------------------------- RUN ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
