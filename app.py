import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import requests
from datetime import datetime

# =====================================================================
# 1. Page Configuration (FIXED: Sidebar open by default)
# =====================================================================
st.set_page_config(page_title="StudyMind AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 2. Session State Initialization
# =====================================================================
if "user_token" not in st.session_state: st.session_state.user_token = None
if "user_email" not in st.session_state: st.session_state.user_email = None
if "user_id" not in st.session_state: st.session_state.user_id = None 
if "current_session_id" not in st.session_state: st.session_state.current_session_id = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "extracted_text" not in st.session_state: st.session_state.extracted_text = ""
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "summary" not in st.session_state: st.session_state.summary = ""
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "simple_exp" not in st.session_state: st.session_state.simple_exp = ""
if "detailed_exp" not in st.session_state: st.session_state.detailed_exp = ""

# =====================================================================
# 3. API Keys & Database Links
# =====================================================================
DB_URL = "https://studymind-ai-fdac1-default-rtdb.firebaseio.com"

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    FIREBASE_API_KEY = st.secrets["FIREBASE_WEB_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("❌ الرجاء التأكد من وجود مفاتيح GEMINI و FIREBASE في ملف secrets.toml.")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available: return genai.GenerativeModel('gemini-1.5-flash')
        if 'models/gemini-pro' in available: return genai.GenerativeModel('gemini-pro')
        if available: return genai.GenerativeModel(available[0])
        return None
    except Exception:
        return None

model = get_working_model()
if model is None:
    st.error("❌ مفتاح جوجل الخاص بك لا يملك صلاحية.")
    st.stop()

# =====================================================================
# 4. Firebase Auth Functions
# =====================================================================
def check_password_strength(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    return True

def sign_up(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    return requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}).json()

def sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    return requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}).json()

# =====================================================================
# 5. Sidebar - History & Sessions (FIXED CHAT LOADING)
# =====================================================================
if st.session_state.user_token is not None:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_email}")
        st.markdown("---")
        st.markdown("### 🗂️ أرشيف المحاضرات (History)")
        
        try:
            db_req = requests.get(f"{DB_URL}/users/{st.session_state.user_id}/sessions.json")
            sessions = db_req.json() if db_req.status_code == 200 else None
        except:
            sessions = None

        if sessions:
            for s_id in sorted(sessions.keys(), reverse=True):
                s_data = sessions[s_id]
                btn_label = s_data.get('title', 'محاضرة محفوظة')
                
                if st.button(f"📁 {btn_label}", key=f"btn_{s_id}", use_container_width=True):
                    st.session_state.current_session_id = s_id
                    st.session_state.extracted_text = s_data.get("extracted_text", "")
                    st.session_state.summary = s_data.get("summary", "")
                    st.session_state.simple_exp = s_data.get("simple_exp", "")
                    st.session_state.detailed_exp = s_data.get("detailed_exp", "")
                    st.session_state.quiz_data = s_data.get("quiz_data", None)
                    
                    # FIXED: Robust Chat History Loading from Firebase
                    raw_chat = s_data.get("chat_history", [])
                    if isinstance(raw_chat, dict):
                        # Convert Firebase dict back to a list
                        st.session_state.chat_history = [raw_chat[k] for k in sorted(raw_chat.keys())]
                    elif isinstance(raw_chat, list):
                        st.session_state.chat_history = raw_chat
                    else:
                        st.session_state.chat_history = []
                        
                    st.session_state.analysis_done = True
                    st.rerun()
        else:
            st.caption("لا يوجد محاضرات محفوظة حتى الآن.")
            
        st.markdown("---")
        if st.button("🚪 تسجيل خروج | Logout", use_container_width=True):
            st.session_state.user_token = None
            st.session_state.user_email = None
            st.session_state.user_id = None
            st.session_state.current_session_id = None
            st.session_state.chat_history = []
            st.session_state.analysis_done = False
            st.session_state.quiz_data = None
            st.rerun()

# =====================================================================
# 6. Header
# =====================================================================
col_left, col_center, col_right = st.columns([1, 2, 1])

with col_right:
    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)
    is_dark = st.toggle("🌙 Dark | ليلي", value=True)
    lang_toggle = st.radio("Language", ["العربية", "English"], horizontal=True)
    is_ar = lang_toggle == "العربية"

with col_center:
    st.markdown("<h1 style='text-align: center; background: linear-gradient(135deg, #00d4aa, #0284c7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 4rem; font-weight: 900; margin-bottom: 0;'>StudyMind AI 🧠</h1>", unsafe_allow_html=True)
    sub_text = "المساعد الأكاديمي الذكي" if is_ar else "Smart Academic Assistant"
    st.markdown(f"<p style='text-align: center; color: #64748b; font-size: 1.2rem; font-weight: 600; margin-bottom: 2rem;'>{sub_text}</p>", unsafe_allow_html=True)

# =====================================================================
# 7. Global CSS Engine (FIXED SIDEBAR TOGGLE)
# =====================================================================
bg_color = "#0e1117" if is_dark else "#f4f6f9"
text_color = "#e2e8f0" if is_dark else "#1e293b"
card_bg = "#161b22" if is_dark else "#ffffff"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap');
    
    html, body, p, span:not(.material-icons):not([class*="icon"]), label, li, h1, h2, h3, button {{ 
        font-family: 'IBM Plex Sans Arabic', sans-serif !important; 
    }}
    .material-icons, [class*="icon"], svg {{ font-family: 'Material Icons', sans-serif !important; }}
    .stApp {{ background-color: {bg_color} !important; }}
    p, span:not(.material-icons), label, li, h1, h2, h3 {{ color: {text_color} !important; }}
    
    /* FIXED: Sidebar Arrow visibility */
    .stApp header {{ background-color: transparent !important; pointer-events: none; }}
    .stApp header > div {{ pointer-events: auto; }}
    [data-testid="collapsedControl"] {{
        z-index: 999999 !important;
        background-color: {card_bg} !important;
        border-radius: 8px !important;
        border: 1px solid #00d4aa !important;
        margin-top: 10px;
        margin-left: 10px;
    }}
    [data-testid="collapsedControl"] svg {{ fill: #00d4aa !important; color: #00d4aa !important; }}
    
    .stTabs [data-baseweb="tab-list"] {{ justify-content: center; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 3px solid #00d4aa !important; }}
    .stTabs [aria-selected="true"] span {{ color: #00d4aa !important; font-weight: 700 !important; }}
    
    .stButton>button, div[data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
        border: none !important; border-radius: 12px !important; color: white !important; font-weight: bold !important; height: 3.5rem; width: 100% !important;
    }}
    
    div[data-testid="stFileUploader"] > section {{ border: 2px dashed #00d4aa !important; border-radius: 16px !important; }}
    div[data-testid="stFileUploader"] svg, div[data-testid="stFileUploader"] button svg path {{ fill: #00d4aa !important; color: #00d4aa !important; }}
    div[data-testid="stFileUploader"] span[data-testid="stIconMaterial"] {{ display: none !important; }}
    
    div[data-testid="stDownloadButton"] button {{ background: transparent !important; border: 2px solid #00d4aa !important; color: #00d4aa !important; border-radius: 8px !important; height: 2.8rem !important; margin-bottom: 15px !important; }}
    div[data-testid="stDownloadButton"] button:hover {{ background: #00d4aa !important; color: white !important; }}
    .quiz-card {{ background-color: {card_bg} !important; border: 1px solid rgba(0, 212, 170, 0.3) !important; padding: 25px; border-radius: 12px; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 8. Login Screen
# =====================================================================
if st.session_state.user_token is None:
    _, col_auth, _ = st.columns([1, 1.5, 1])
    with col_auth:
        tab_login, tab_signup = st.tabs(["🔐 Login (تسجيل دخول)", "📝 Sign Up (حساب جديد)"])
        
        with tab_login:
            log_email = st.text_input("البريد الإلكتروني / Email", key="log_e")
            log_pass = st.text_input("كلمة المرور / Password", type="password", key="log_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("دخول 🚀", use_container_width=True):
                with st.spinner("جاري التحقق..."):
                    res = sign_in(log_email, log_pass)
                    if "error" in res: st.error("❌ بيانات الدخول خاطئة.")
                    else:
                        st.session_state.user_token = res["idToken"]
                        st.session_state.user_email = res["email"]
                        st.session_state.user_id = res["localId"]
                        st.session_state.chat_history = [] 
                        st.rerun()
                        
        with tab_signup:
            st.info("🔒 **شروط كلمة المرور:**\n- 8 أحرف على الأقل\n- حرف إنجليزي كبير واحد (Capital)\n- رقم واحد على الأقل")
            reg_email = st.text_input("البريد الإلكتروني / Email", key="reg_e")
            reg_pass = st.text_input("كلمة المرور / Password", type="password", key="reg_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("تسجيل ✨", use_container_width=True):
                if not check_password_strength(reg_pass): st.error("⚠️ كلمة المرور لا تطابق الشروط.")
                else:
                    with st.spinner("جاري الإنشاء..."):
                        res = sign_up(reg_email, reg_pass)
                        if "error" in res: st.error(res["error"]["message"])
                        else: st.success("✅ تم إنشاء الحساب بنجاح! الرجاء الانتقال لتبويب Login.")
    st.stop()

# =====================================================================
# 9. Main Processing (Upload & AI)
# =====================================================================
def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() or "" for page in reader.pages])
        return str(file.read(), "utf-8")
    except: return ""

_, col_main, _ = st.columns([1, 2, 1])

with col_main:
    upload_lbl = "📂 ارفع ملف المحاضرة (PDF/TXT)" if is_ar else "📂 Upload Lecture"
    uploaded_file = st.file_uploader(upload_lbl, type=["pdf", "txt"])
    
    level_lbl = "🎯 مستوى التبسيط للمفاهيم:" if is_ar else "🎯 Simplification Level:"
    levels = ["مبتدئ جداً", "متوسط", "متقدم"] if is_ar else ["Beginner", "Intermediate", "Advanced"]
    level = st.select_slider(level_lbl, options=levels)
    
    btn_lbl = "✨ ابدأ المعالجة الذكية" if is_ar else "✨ Start Processing"
    
    if st.button(btn_lbl, use_container_width=True):
        if uploaded_file:
            with st.spinner("الذكاء الاصطناعي يحلل البيانات... 🤖"):
                text = extract_text(uploaded_file)
                st.session_state.extracted_text = text
                
                if text.strip():
                    target_lang = "Arabic" if is_ar else "English"
                    prompt = f"""
                    Analyze this text: {text[:8000]}
                    ALL output MUST be in {target_lang}.
                    Generate EXACTLY 4 parts separated strictly by |||. No introductory text.
                    [Part 1]: Professional bulleted summary.
                    |||
                    [Part 2]: 10 Multiple Choice Questions. Output MUST be a strict JSON array of objects. Keys MUST remain in English: "question", "options", "correct_answer", "explanation". Escape any special characters properly. Values in {target_lang}.
                    |||
                    [Part 3]: Simplified, practical explanation for {level} level.
                    |||
                    [Part 4]: Deep, detailed academic explanation.
                    """
                    try:
                        response = model.generate_content(prompt)
                        parts = response.text.split("|||")
                        if len(parts) >= 4:
                            st.session_state.summary = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[0], flags=re.MULTILINE).strip()
                            
                            match = re.search(r'\[.*\]', parts[1], re.DOTALL)
                            if match:
                                json_str = match.group(0).replace('\\', '\\\\')
                                try: st.session_state.quiz_data = json.loads(json_str, strict=False)
                                except Exception: st.session_state.quiz_data = None
                            else: st.session_state.quiz_data = None
                                
                            st.session_state.simple_exp = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[2], flags=re.MULTILINE).strip()
                            st.session_state.detailed_exp = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[3], flags=re.MULTILINE).strip()
                            st.session_state.analysis_done = True
                            st.session_state.chat_history = [] 
                            
                            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                            st.session_state.current_session_id = session_id
                            
                            session_data = {
                                "title": f"Lecture - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                "extracted_text": st.session_state.extracted_text,
                                "summary": st.session_state.summary,
                                "simple_exp": st.session_state.simple_exp,
                                "detailed_exp": st.session_state.detailed_exp,
                                "quiz_data": st.session_state.quiz_data,
                                "chat_history": st.session_state.chat_history
                            }
                            try:
                                requests.put(f"{DB_URL}/users/{st.session_state.user_id}/sessions/{session_id}.json", json=session_data)
                            except: pass
                            
                            st.balloons()
                        else: st.error("خطأ في تنسيق البيانات المسترجعة.")
                    except Exception as e: st.error(f"حدث خطأ أثناء المعالجة: {e}")
        else:
            st.warning("الرجاء رفع ملف المحاضرة أولاً!")

# =====================================================================
# 10. Tabs & Results
# =====================================================================
if st.session_state.analysis_done:
    st.markdown("---")
    tabs = st.tabs(["📝 الملخص", "📚 شرح مفصل", "💡 شرح مبسط", "❓ اختبار", "💬 شات بوت"] if is_ar else ["📝 Summary", "📚 Detailed", "💡 Simple", "❓ Quiz", "💬 Chat"])
    
    with tabs[0]: 
        st.download_button("📥 تحميل الملخص", st.session_state.summary, file_name="Summary.txt")
        st.markdown(st.session_state.summary)
        
    with tabs[1]: 
        st.download_button("📥 تحميل الشرح المفصل", st.session_state.detailed_exp, file_name="Detailed_Explanation.txt")
        st.markdown(st.session_state.detailed_exp)
        
    with tabs[2]: 
        st.download_button("📥 تحميل الشرح المبسط", st.session_state.simple_exp, file_name="Simple_Explanation.txt")
        st.markdown(st.session_state.simple_exp)
        
    with tabs[3]:
        if st.session_state.quiz_data:
            quiz_text_format = "".join([f"Q{i+1}: {q['question']}\nAnswers: {', '.join(q['options'])}\nCorrect Answer: {q['correct_answer']}\n\n" for i, q in enumerate(st.session_state.quiz_data)])
            st.download_button("📥 تحميل الاختبار", quiz_text_format, file_name="Quiz.txt")
            
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"<div class='quiz-card'><strong>Q{i+1}:</strong> {q['question']}</div>", unsafe_allow_html=True)
                    user_answers[i] = st.radio("Choose:", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                if st.form_submit_button("إرسال الإجابات 🚀" if is_ar else "Submit Answers 🚀"):
                    score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['correct_answer']])
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] != q['correct_answer']:
                            st.error(f"❌ Q{i+1}: {q['question']}\n\n**Answer:** {q['correct_answer']}\n**Reason:** {q.get('explanation', '')}")
                    st.success(f"النتيجة النهائية (Score): {score} / {len(st.session_state.quiz_data)}")
        else:
            st.info("لم يتمكن الذكاء الاصطناعي من توليد الاختبار لهذا الملف.")
                    
    with tabs[4]:
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"], avatar="👤" if m["role"] == "user" else "🤖"): 
                if "time" in m and m["time"]: st.caption(f"🕒 {m['time']}")
                st.markdown(m["content"])
                
        if user_query := st.chat_input("اسألني أي شيء عن محتوى المحاضرة..." if is_ar else "Ask me anything..."):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            st.session_state.chat_history.append({"role": "user", "content": user_query, "time": current_time})
            with st.chat_message("user", avatar="👤"): 
                st.caption(f"🕒 {current_time}")
                st.markdown(user_query)
                
            with st.spinner('جاري التفكير...'):
                try:
                    ans = model.generate_content(f"Context: {st.session_state.extracted_text[:4000]}\nUser Question: {user_query}\nAnswer purely in {'Arabic' if is_ar else 'English'}.").text
                    bot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    with st.chat_message("assistant", avatar="🤖"): 
                        st.caption(f"🕒 {bot_time}")
                        st.markdown(ans)
                        
                    st.session_state.chat_history.append({"role": "assistant", "content": ans, "time": bot_time})
                    
                    if st.session_state.current_session_id:
                        requests.put(f"{DB_URL}/users/{st.session_state.user_id}/sessions/{st.session_state.current_session_id}/chat_history.json", json=st.session_state.chat_history)
                    
                    st.rerun()
                    
                except Exception:
                    st.error("حدث خطأ أثناء الاتصال بالمساعد الذكي.")