
import streamlit as st # type: ignore
import json
import os
import hashlib
import time
from textwrap import shorten
from PIL import Image # type: ignore
import fitz  # PyMuPDF for PDFs
import google.generativeai as genai
import google.api_core.exceptions as google_exceptions
import sqlite3
from datetime import datetime
# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()


# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="StudyBuddy AI", page_icon="🧠", layout="wide")

# ---------- STYLING ----------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
        color: #f1f1f1;
        font-family: 'Poppins', sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #0f3460, #16213e);
        color: #f8f9fa;
        border-right: 2px solid #1a1a2e;
    }
    .stButton button {
        background: linear-gradient(90deg, #00f5d4, #00bbf9);
        color: black;
        border-radius: 12px;
        border: none;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.3s ease-in-out;
    }
    .stButton button:hover {
        background: linear-gradient(90deg, #00bbf9, #00f5d4);
        transform: scale(1.05);
    }
    .glow-text {
        color: #f8f9fa;
        animation: glow 2.5s ease-in-out infinite alternate;
        font-weight: 700;
        font-size: 2.3rem;
        text-align: center;
        margin-bottom: 15px;
    }
    @keyframes glow {
        0% { text-shadow: 0 0 5px #00f5d4, 0 0 10px #00bbf9, 0 0 20px #00bbf9; }
        50% { text-shadow: 0 0 15px #00f5d4, 0 0 30px #00bbf9, 0 0 45px #00f5d4; }
        100% { text-shadow: 0 0 5px #00f5d4, 0 0 10px #00bbf9, 0 0 20px #00bbf9; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------- GOOGLE API CONFIG ----------
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))  # Loaded from .env

# ---------- UTILITIES ----------

# ---------- DATABASE SETUP ----------
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/activity_log.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()
def log_user_action(email, action):
    conn = sqlite3.connect("data/activity_log.db")
    c = conn.cursor()
    c.execute("INSERT INTO user_logs (email, action, timestamp) VALUES (?, ?, ?)",
              (email, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


# Initialize DB on app start
init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def save_user_data(user_info):
    os.makedirs("data", exist_ok=True)
    with open("data/user_data.json", "w") as f:
        json.dump(user_info, f)

def load_user_data():
    if os.path.exists("data/user_data.json"):
        with open("data/user_data.json", "r") as f:
            return json.load(f)
    return None

def save_user_credentials(email, password, fav_place):
    os.makedirs("data", exist_ok=True)
    users_file = "data/users.json"
    users = {}
    if os.path.exists(users_file):
        with open(users_file, "r") as f:
            users = json.load(f)
    users[email] = {"password": hash_password(password), "fav_place": fav_place}
    with open(users_file, "w") as f:
        json.dump(users, f, indent=4)

def verify_credentials(email, password):
    users_file = "data/users.json"
    if not os.path.exists(users_file):
        return False
    with open(users_file, "r") as f:
        users = json.load(f)
    return email in users and users[email]["password"] == hash_password(password)

# ---------- AUTH ----------
user = load_user_data()

if not user:
    st.title("🧠 StudyBuddy AI Login / Sign Up")

    tab_login, tab_signup = st.tabs(["🔑 Login", "🆕 Sign Up"])

    # ---- SIGN UP ----
    with tab_signup:
        st.markdown("### ✨ Create your account")
        email = st.text_input("📧 Email", key="signup_email")
        password = st.text_input("🔒 Password", type="password", key="signup_pass")
        fav_place = st.text_input("🏝 Favorite Place (for password recovery)", key="signup_fav")
        name = st.text_input("👤 Your Name", key="signup_name")
        college = st.text_input("🏫 College Name", key="signup_college")
        dept = st.text_input("📘 Department", key="signup_dept")
        subject = st.text_input("📖 Main Subject", key="signup_subject")

        if st.button("Sign Up 🚀"):
            if email and password and fav_place and name and college and dept and subject:
                save_user_credentials(email, password, fav_place)
                user = {
                    "email": email,
                    "name": name,
                    "college": college,
                    "dept": dept,
                    "subject": subject,
                    "score": 0
                }
                save_user_data(user)
                st.success("✅ Account created! Please switch to Login tab to continue.")
            else:
                st.warning("⚠ Please fill all fields before signing up.")

    # ---- LOGIN ----
    with tab_login:
        st.markdown("### 🔑 Login to your account")
        email = st.text_input("📧 Email", key="login_email")
        password = st.text_input("🔒 Password", type="password", key="login_pass")

        if st.button("Login ✅"):
            if verify_credentials(email, password):
                st.success("🎉 Login successful! Loading your dashboard...")
                log_user_action(email, "Login")

                if os.path.exists("data/user_data.json"):
                    with open("data/user_data.json", "r") as f:
                        user = json.load(f)
                else:
                    user = {
                        "email": email,
                        "name": "",
                        "college": "",
                        "dept": "",
                        "subject": "",
                        "score": 0
                    }
                    save_user_data(user)
                st.session_state.user = user
                st.rerun()
            else:
                st.error("❌ Invalid email or password!")

        st.markdown("---")
        st.markdown("### ❓ Forgot Password")
        with st.expander("🔑 Reset Password"):
            reset_email = st.text_input("📧 Registered Email")
            reset_place = st.text_input("🏝 Favorite Place")
            new_pass = st.text_input("🔒 New Password", type="password")
            if st.button("Reset Password 🔁"):
                users_file = "data/users.json"
                if os.path.exists(users_file):
                    with open(users_file, "r") as f:
                        users = json.load(f)
                    if (
                        reset_email in users
                        and users[reset_email]["fav_place"].lower().strip() == reset_place.lower().strip()
                    ):
                        users[reset_email]["password"] = hash_password(new_pass)
                        with open(users_file, "w") as f:
                            json.dump(users, f, indent=4)
                        st.success("✅ Password reset successful! Please login again.")
                    else:
                        st.error("❌ Incorrect email or favorite place.")
                else:
                    st.warning("⚠ No registered users found.")
    st.stop()

# ---------- HEADER ----------
st.markdown('<h1 class="glow-text">🎒 StudyBuddy AI – Made for Students ✨</h1>', unsafe_allow_html=True)
st.markdown(f"""
<div style='text-align:center; background:#16213e; border-radius:10px; padding:12px; margin-top:10px; color:#00f5d4;'>
👋 Welcome, <b>{user['name']}</b>!<br>
🏫 {user['college']} | 💻 {user['dept']} Dept | 📘 {user['subject']}<br>
🎯 Current Score: <b>{user.get('score', 'score')}</b>
</div>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=180)
else:
    st.sidebar.markdown("🧠 StudyBuddy AI")

st.sidebar.markdown(f"👩‍🎓 {user['name']}\n\n🏫 {user['college']}\n📘 {user['dept']} Dept")
st.sidebar.markdown("---")

mode = st.sidebar.radio("Choose a Mode 🎯", [
    "📚 Explain Topic",
    "🧩 Quiz Me",
    "🧠 Summarize Notes",
    "💬 Ask Anything",
    "🗓 Study Planner" 
])

# ---------- MODEL ----------
model = genai.GenerativeModel("gemini-pro-latest")

# ---------- SAFE CALL ----------
def safe_generate_content(model, prompt):
    try:
        return model.generate_content(prompt)
    except google_exceptions.ResourceExhausted:
        st.warning("⚠ Gemini limit reached. Try again later.")
        time.sleep(45)
        return None

# ---------- EXPLAIN TOPIC ----------
if mode == "📚 Explain Topic":
    topic = st.text_input("Enter a topic:")
    if st.button("Explain 🔍"):
        if topic:
            with st.spinner("AI is thinking..."):
                response = model.generate_content(f"Explain {topic} in simple words for students.")
                st.markdown(f"🧠 Explanation:\n\n{response.text}")

# ---------- SUMMARIZE NOTES ----------
def extract_text_from_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            text += page.get_text()
    return text

def extract_text_from_image(file):
    image = Image.open(file)
    vision_model = genai.GenerativeModel("gemini-1.5-flash")
    response = vision_model.generate_content(["Summarize this study-related image:", image])
    return response.text

if mode == "🧠 Summarize Notes":
    st.subheader("🧠 Smart Note Summarizer")
    uploaded = st.file_uploader("📁 Upload .txt, .pdf, .jpg, or .png (max 200 MB):", type=["txt", "pdf", "jpg", "jpeg", "png"])
    if uploaded:
        if uploaded.size / (1024 * 1024) > 200:
            st.error("⚠ File exceeds 200MB limit.")
            st.stop()
        extracted_text = ""
        if "text" in uploaded.type:
            extracted_text = uploaded.read().decode("utf-8", errors="ignore")
        elif "pdf" in uploaded.type:
            extracted_text = extract_text_from_pdf(uploaded)
        elif any(ext in uploaded.type for ext in ["jpeg", "jpg", "png"]):
            extracted_text = extract_text_from_image(uploaded)
        if extracted_text.strip():
            with st.spinner("🤖 Summarizing..."):
                response = model.generate_content(f"Summarize this document in student-friendly terms:\n{extracted_text}")
                summary = response.text
                st.success("✅ Summary generated!")
                st.write(summary)
                st.download_button("⬇ Download Summary", summary, file_name="summary.txt")
        else:
            st.warning("⚠ No readable content found.")

# ---------- QUIZ ME ----------
elif mode == "🧩 Quiz Me":
    st.subheader("🧩 Interactive Quiz")

    topic = st.text_input("🎯 Enter a quiz topic:")
    num_questions = st.radio("Select number of questions:", [5, 10, 20], index=1)

    if st.button("Generate Quiz 🧠"):
        if topic:
            with st.spinner("🤖 Generating quiz..."):
                prompt = f"""
                Create {num_questions} multiple-choice questions about "{topic}".
                Return valid JSON like:
                [
                  {{"question": "...", "options": ["A. ...","B. ...","C. ...","D. ..."], "answer": "A. ..."}}
                ]
                """
                response = safe_generate_content(model, prompt)
                if response:
                    try:
                        # Parse JSON safely
                        data = json.loads(response.text[response.text.find("["):response.text.rfind("]")+1])
                        st.session_state.quiz_data = data[:num_questions]
                        st.session_state.current_question = 0
                        st.session_state.user_answers = {}
                        st.session_state.show_results = False
                        st.session_state.num_questions = num_questions
                        st.success(f"✅ {num_questions} questions generated! Scroll down ⬇")
                    except:
                        st.error("❌ Invalid JSON from AI. Try again.")
        else:
            st.warning("⚠ Please enter a topic first!")

    # ---------- QUIZ RUNNING ----------
    if st.session_state.get("quiz_data") and not st.session_state.get("show_results"):
        quiz = st.session_state.quiz_data
        q_i = st.session_state.current_question
        q = quiz[q_i]

        st.markdown(f"#### Q{q_i+1}. {q['question']}")
        selected = st.radio("Select your answer:", q["options"], index=None, key=f"q_{q_i}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅ Prev", disabled=q_i == 0):
                st.session_state.current_question -= 1
                st.rerun()
        with col2:
            if st.button("➡ Next", disabled=q_i == len(quiz)-1):
                st.session_state.user_answers[q_i] = selected
                st.session_state.current_question += 1
                st.rerun()

        # Finish Button
        if q_i == len(quiz)-1 and st.button("🏁 Finish Quiz"):
            st.session_state.user_answers[q_i] = selected
            st.session_state.show_results = True
            st.rerun()

    # ---------- SHOW RESULTS ----------
    elif st.session_state.get("show_results"):
        quiz = st.session_state.quiz_data
        user_ans = st.session_state.user_answers
        score = 0
        num_questions = st.session_state.get("num_questions", len(quiz))

        st.markdown("## 🏁 Quiz Results")
        for i, q in enumerate(quiz):
            correct = q["answer"].strip().lower()
            chosen = (user_ans.get(i) or "").strip().lower()
            if chosen == correct:
                st.markdown(f"✅ Q{i+1}: {q['question']}")
                score += 10
            else:
                st.markdown(f"❌ Q{i+1}: {q['question']}")
                st.caption(f"Your answer: {user_ans.get(i) or 'Not answered'}")
                st.caption(f"Correct answer: {q['answer']}")

        # --- Update user's profile score ---
        st.success(f"🎯 Final Score: {score} / {num_questions * 10}")
        user["score"] = score
        save_user_data(user)

        st.balloons()
        if st.button("🔁 Try Again"):
            for key in ["quiz_data", "show_results", "user_answers", "current_question", "num_questions"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# ---------- STUDY PLANNER ----------
if mode == "🗓 Study Planner":
    st.subheader("🗓 Smart Study Planner")

    planner_file = "data/study_plan.json"
    if os.path.exists(planner_file):
        with open(planner_file, "r") as f:
            plans = json.load(f)
    else:
        plans = []

    with st.expander("➕ Add Task"):
        task = st.text_input("📖 Study Task")
        subject = st.text_input("📘 Subject")
        deadline = st.date_input("📅 Deadline")
        if st.button("✅ Add Task"):
            if task and subject:
                plans.append({
                    "task": task,
                    "subject": subject,
                    "deadline": str(deadline),
                    "status": "Pending"
                })
                with open(planner_file, "w") as f:
                    json.dump(plans, f, indent=4)
                st.success("🎯 Task added!")
                st.rerun()
            else:
                st.warning("⚠ Please fill all fields!")

    st.markdown("---")
    if not plans:
        st.info("🕒 No tasks yet! Add one above.")
    else:
        for i, t in enumerate(plans):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.markdown(f"{t['task']}")
            col2.markdown(f"📘 {t['subject']}")
            col3.markdown(f"📅 {t['deadline']}")
            if col4.checkbox("✅ Done", key=i):
                t["status"] = "Completed"
            if st.button("🗑 Delete", key=f"del_{i}"):
                plans.pop(i)
                with open(planner_file, "w") as f:
                    json.dump(plans, f, indent=4)
                st.success("🗑 Task deleted!")
                st.rerun()

        with open(planner_file, "w") as f:
            json.dump(plans, f, indent=4)

# ---------- ASK ANYTHING ----------
elif mode == "💬 Ask Anything":
    query = st.text_input("💭 Ask me anything:")
    if st.button("Ask 🤔"):
        if query:
            with st.spinner("Thinking..."):
                response = model.generate_content(query)
                st.write(response.text)





# ---------- LOGOUT ----------
if st.sidebar.button("🚪 Logout"):
    if os.path.exists("data/user_data.json"):
        with open("data/user_data.json", "r") as f:
            user_data = json.load(f)
        log_user_action(user_data.get("email", "Unknown"), "Logout")
        os.remove("data/user_data.json")
    st.session_state.clear()
    st.success("👋 Logged out successfully!")
    st.rerun()
