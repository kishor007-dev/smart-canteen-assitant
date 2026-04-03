# backend/main.py
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
import os
import re
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import uvicorn


# --------------------------- DATABASE ---------------------------
load_dotenv()
MONGODB_URL=os.getenv("MONGODB_URL")
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

# --------------------------- groq SETUP ---------------------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # Ensure this env variable is set
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
    return {
        "status": "running",
        "service": "Smart Canteen API",
        "version": "1.0"
    }

# --------------------------- MODELS ---------------------------
class LoginModel(BaseModel):
    username: str
    password: str
    role: str  # student / staff

class ChatModel(BaseModel):
    studentId: str
    message: str

class OrderModel(BaseModel):
    studentId: str
    item: str

# --------------------------- MODELS ---------------------------
class MenuUpdateModel(BaseModel):
    name: str
    price: int
    username: str  # for authentication

class MenuRemoveModel(BaseModel):
    name: str
    username: str

class SpecialModel(BaseModel):
    special: str
    username: str


# --------------------------- HELPER FUNCTIONS ---------------------------
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

def staff_required(username: str):
    user = users_col.find_one({"username": username, "role": "staff"})
    if not user:
        raise HTTPException(status_code=403, detail="Only staff can perform this action")
    return True

# --------------------------- LOGIN / SIGNUP ---------------------------
@app.post("/login")
def login(user: LoginModel):
    found = users_col.find_one({"username": user.username, "password": user.password, "role": user.role})
    if not found:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "role": user.role, "username": user.username}

@app.post("/signup")
def signup(user: LoginModel):
    existing = users_col.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    users_col.insert_one({
        "username": user.username,
        "password": user.password,
        "role": user.role
    })
    return {"message": "Sign up successful!"}

# --------------------------- MENU ---------------------------
@app.get("/menu")
def menu_api():
    menu = get_menu()
    return {"menu": [{"name": k.capitalize(), "price": v} for k, v in menu.items()]}

# --------------------------- PLACE ORDER ---------------------------
@app.post("/place-order")
def place_order(data: OrderModel):
    menu = get_menu()
    item = data.item.strip().lower()
    if item not in menu:
        raise HTTPException(status_code=400, detail="Item not in menu")
    order = {"studentId": data.studentId, "item": item, "status": "pending", "createdAt": datetime.now()}
    orders_col.insert_one(order)
    return {"message": f"✅ Order for {item.capitalize()} placed successfully!"}

# --------------------------- PENDING ORDERS ---------------------------
@app.get("/orders/pending")
def get_pending_orders():
    orders = list(orders_col.find({"status": "pending"}))
    for o in orders:
        o["_id"] = str(o["_id"])
    return orders
    
# --------------------------- ORDER HISTORY ---------------------------
from pymongo import DESCENDING

@app.get("/orders/history/{studentId}")
def order_history(studentId: str):
    orders = list(
        orders_col.find({"studentId": studentId}).sort("createdAt", DESCENDING)
    )

    for o in orders:
        o["_id"] = str(o["_id"])
        if "createdAt" in o:
            o["createdAt"] = o["createdAt"].strftime("%Y-%m-%d %H:%M")

    return {"orders": orders}



# --------------------------- MENU UPDATE ---------------------------
@app.post("/menu/update")
def update_menu_item(item: MenuUpdateModel):
    staff_user = users_col.find_one({"username": item.username, "role": "staff"})
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

# --------------------------- MENU REMOVE ---------------------------
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

# --------------------------- SET DAILY SPECIAL ---------------------------
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


# --------------------------- GET DAILY SPECIAL / RECOMMENDATION ---------------------------
@app.get("/menu/special")
def get_daily_special():
    menu_doc = menu_col.find_one({})
    menu = get_menu()
    special = menu_doc.get("daily_special") if menu_doc else None
    if not special:
        # Fallback: pick the first item as recommended special
        recommended = list(menu.keys())[0]
        price = menu[recommended]
        return {"special": {"name": recommended.capitalize(), "price": price, "recommended": True}}
    price = menu.get(special, "N/A")
    return {"special": {"name": special.capitalize(), "price": price, "recommended": False}}

# --------------------------- CHATBOT WITH COMBO RECOMMENDATIONS ---------------------------
# --------------------------- CHATBOT WITH MEMORY ---------------------------
# Temporary in-memory store for each student's last mentioned item
student_memory = {}

@app.post("/chat")
def chat(payload: ChatModel):
    student_id = payload.studentId
    user_msg = payload.message.strip().lower()
    
    menu = get_menu()
    menu_items = [k.lower() for k in menu.keys()]
    menu_doc = menu_col.find_one({})
    daily_special = menu_doc.get("daily_special") if menu_doc else None

    # Initialize memory for student if it doesn't exist
    if student_id not in student_memory:
     student_memory[student_id] = {
        "last_item": None,
        "last_action": None,
        "last_intent": "normal" ,
        "last_bot_message": "",
        "greeted": False 
     }

    memory = student_memory[student_id]
    if memory["last_intent"] == "normal" and not memory.get("greeted"):
     memory["greeted"] = True
     reply = ("Welcome to our canteen! What can I get for you today? "
             "We've got a wide variety of options to choose from. "
             "Would you like me to recommend something or would you like to take a look at our menu?")
     return {"reply": reply}
    reply = ""

    # ---------- 1. Cancel last order ----------
    if re.search(r"\b(cancel|remove|forget|wrong item)\b", user_msg) and memory.get("last_item") and memory.get("last_action") == "order":
        last_item = memory["last_item"]
        # Remove the last pending order for this student and item
        result = orders_col.delete_one({
            "studentId": student_id,
            "item": last_item,
            "status": "pending"
        })
        if result.deleted_count > 0:
            reply = f"❌ Last order for {last_item.capitalize()} has been cancelled."
        else:
            reply = f"⚠️ No pending order found for {last_item.capitalize()} to cancel."
        # Clear memory for last_item since it's cancelled
        memory["last_item"] = None
        memory["last_action"] = None
        return {"reply": reply}
    
    # ---------- 1. Handle 'yes/order it' using memory ----------
    if memory["last_intent"] == "waiting_confirmation":
     if user_msg in ["yes", "ok", "sure", "haa", "ha", "confirm"]:
        orders_col.insert_one({
            "studentId": student_id,
            "item": memory["last_item"],
            "status": "pending",
            "createdAt": datetime.now()
        })
        reply = f"✅ Order placed successfully for {memory['last_item'].capitalize()}!"
        memory["last_intent"] = "normal"
        memory["last_action"] = "order"
        return {"reply": reply}

    elif user_msg in ["no", "cancel", "nope", "not now"]:
        reply = "❌ Okay, cancelled! Let me know if you need anything else."
        memory["last_intent"] = "normal"
        return {"reply": reply}


    # ---------- 2. Detect mention of menu items ----------
    mentioned_item = None
    for item in menu_items:
        if item in user_msg:
            mentioned_item = item
            break

    if mentioned_item:
        memory["last_item"] = mentioned_item
        memory["last_action"] = "recommend"
        reply = f"👍 You selected {mentioned_item.capitalize()}. Should I place the order?"
        memory["last_intent"] = "waiting_confirmation"


    # ---------- 3. Handle menu inquiry ----------
    # ---------- 3. Handle menu inquiry ----------
    # ---------- 3. Handle menu inquiry ----------
    if "menu" in user_msg:
     menu_lines = [f"{idx+1}. {item.capitalize()} - ₹{price}" for idx, (item, price) in enumerate(menu.items())]
     menu_text = "\n".join(menu_lines)
     reply = f"📋 Here's our current menu:\n{menu_text}\n\nWould you like to order something?"
     return {"reply": reply}  # <--- immediately return here

    # ---------- 4. Recommend daily special / combos ----------
    elif any(word in user_msg for word in ["recommend", "special", "suggest", "best", "tasty", "combo"]):
        past_orders = list(orders_col.find({"studentId": student_id}))
        ordered_items = [o["item"] for o in past_orders]

        if daily_special:
            price = menu.get(daily_special, "N/A")
            reply = f"⭐ Today's special is {daily_special.capitalize()} at ₹{price}. Highly recommended!"
            if len(menu) > 2:
                other_items = [item for item in menu_items if item != daily_special]
                combo_item = other_items[0]
                reply += f"\n💡 Combo suggestion: {daily_special.capitalize()} + {combo_item.capitalize()} for a perfect meal!"
        else:
            # fallback LLM for combo suggestions
            memory["last_intent"] = "normal"
            # Casual yes/no handling when no confirmation is pending
            if user_msg in ["yes", "yep", "ok", "okay", "ha", "haa", "sure"]:
               if memory["last_intent"] != "waiting_confirmation":   # NOT confirming an order
                return {"reply": "🙂 Great! Tell me what you're looking for — menu or recommendation?"}

            if user_msg in ["no", "nope", "not now"]:
               if memory["last_intent"] != "waiting_confirmation":
                 return {"reply": "👍 No problem! I’m here if you need anything."}

            system_prompt = f"""
You are a smart canteen assistant.
Menu: {menu_text}
Student previously ordered: {ordered_items if ordered_items else 'None'}
Suggest a tasty combo or single item for the student.
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ]
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150,
                    top_p=0.9,
                )
                reply = response.choices[0].message.content.strip()
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"

    # ---------- 5. Detect ordering intent ----------
    ordered_items = []
    # Split message by common delimiters like 'and', ',', or just spaces
    possible_items = re.split(r'\band\b|,', user_msg)
    for part in possible_items:
        part = part.strip()
        for item in menu_items:
            if item in part:
                ordered_items.append(item)
    
    # Remove duplicates
    ordered_items = list(set(ordered_items))

    if ordered_items:
        for ordered_item in ordered_items:
            orders_col.insert_one({
                "studentId": student_id,
                "item": ordered_item,
                "status": "pending",
                "createdAt": datetime.now()
            })
        memory["last_item"] = ordered_items  # store last item for memory
        memory["last_action"] = "order"
        reply = f"✅ Order placed successfully for: {', '.join([i.capitalize() for i in ordered_items])}!"
    else:
        # invalid order attempt
        invalid_item_pattern = re.compile(r"\b(order|want|add|get|please|i'd like)\b\s+(.+)")
        match = invalid_item_pattern.search(user_msg)
        if match:
            requested_item = match.group(2).strip().lower()
            if requested_item not in menu_items:
                reply = f"⚠️ Sorry, {requested_item.capitalize()} is not in the menu."
            else:
                reply = "⚠️ Could not understand your order. Try again."
        else:
            # fallback LLM
            system_prompt = f"""
You are a polite and friendly canteen assistant.
Current menu: {menu}
Student previously ordered: {ordered_items if ordered_items else 'None'}
You can suggest combos, menu items, or chat casually.
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ]
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150,
                    top_p=0.9,
                )
                reply = response.choices[0].message.content.strip()
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"


    # ---------- Save chat history ----------
    chat_history_col.insert_one({
        "studentId": student_id,
        "user": payload.message,
        "bot": reply,
        "createdAt": datetime.now()
    })

    return {"reply": reply}


# --------------------------- SEED USERS ---------------------------
@app.get("/seed")
def seed_users():
    users_col.delete_many({})
    users_col.insert_many([
        {"username": "student1", "password": "123", "role": "student"},
        {"username": "staff1", "password": "admin", "role": "staff"},
    ])
    return {"message": "Sample users added"}

# --------------------------- WEBSOCKET ---------------------------
active_connections = {}

@app.websocket("/ws/{student_id}")
async def websocket_endpoint(websocket: WebSocket, student_id: str):
    await websocket.accept()
    active_connections[student_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        del active_connections[student_id]

@app.post("/orders/ready/{order_id}")
async def mark_order_ready(order_id: str):
    order = orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "ready"}})

    student_id = order["studentId"]
    if student_id in active_connections:
        await active_connections[student_id].send_text(f"🍽️ Your order for {order['item'].capitalize()} is ready!")

    return {"message": f"Order {order_id} marked ready."}
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
