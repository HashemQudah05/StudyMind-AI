import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import requests
from datetime import datetime

# =====================================================================
# 1. إعدادات الصفحة الأساسية (Page Configuration)
# =====================================================================
st.set_page_config(
    page_title="StudyMind AI", 
    page_icon="🧠", 
    layout="wide"
)

# =====================================================================
# 2. تهيئة الذاكرة (Session State Initialization)
# =====================================================================
if "user_token" not in st.session_state: 
    st.session_state.user_token = None

if "user_email" not in st.session_state: 
    st.session_state.user_email = None

if "chat_history" not in st.session_state: 
    st.session_state.chat_history = []

if "extracted_text" not in st.session_state: 
    st.session_state.extracted_text = ""

if "analysis_done" not in st.session_state: 
    st.session_state.analysis_done = False

if "summary" not in st.session_state: 
    st.session_state.summary = ""

if "quiz_data" not in st.session_state: 
    st.session_state.quiz_data = None

if "simple_exp" not in st.session_state: 
    st.session_state.simple_exp = ""

if "detailed_exp" not in st.session_state: 
    st.session_state.detailed_exp = ""

# =====================================================================
# 3. التحقق من المفاتيح واصطياد النموذج (API Keys & Model Hunter)
# =====================================================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    FIREBASE_API_KEY = st.secrets["FIREBASE_WEB_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("❌ الرجاء التأكد من وجود مفاتيح GEMINI و FIREBASE في ملف secrets.toml.")
    st.stop()

@st.cache_resource
def get_working_model():
    """البحث عن أفضل نموذج ذكاء اصطناعي متاح بصلاحيات المفتاح"""
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if 'models/gemini-1.5-flash' in available: 
            return genai.GenerativeModel('gemini-1.5-flash')
        if 'models/gemini-pro' in available: 
            return genai.GenerativeModel('gemini-pro')
        if available: 
            return genai.GenerativeModel(available[0])
            
        return None
    except Exception:
        return None

model = get_working_model()

if model is None:
    st.error("❌ مفتاح جوجل الخاص بك لا يملك صلاحية لأي نموذج حالياً! الحل: اذهب لموقع Google AI Studio وأنشئ مفتاحاً جديداً.")
    st.stop()

# =====================================================================
# 4. دوال تسجيل الدخول وإنشاء الحساب (Firebase Auth)
# =====================================================================
def check_password_strength(password):
    """التحقق من قوة كلمة المرور"""
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    return True

def sign_up(email, password):
    """إنشاء حساب جديد"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

def sign_in(email, password):
    """تسجيل الدخول"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

# =====================================================================
# 5. التخطيط العلوي للواجهة (Header & Layout Columns)
# =====================================================================
col_left, col_center, col_right = st.columns([1, 2, 1])

with col_right:
    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)
    
    is_dark = st.toggle("🌙 Dark | ليلي", value=True)
    lang_toggle = st.radio("Language", ["العربية", "English"], horizontal=True)
    is_ar = lang_toggle == "العربية"
    
    if st.session_state.user_token is not None:
        st.caption(f"👤 {st.session_state.user_email}")
        if st.button("🚪 Logout | تسجيل خروج"):
            st.session_state.user_token = None
            st.session_state.user_email = None
            st.session_state.analysis_done = False
            st.rerun()

with col_center:
    st.markdown(
        """
        <h1 style='text-align: center; 
                   background: linear-gradient(135deg, #00d4aa, #0284c7); 
                   -webkit-background-clip: text; 
                   -webkit-text-fill-color: transparent; 
                   font-size: 4rem; 
                   font-weight: 900; 
                   margin-bottom: 0;'>
            StudyMind AI 🧠
        </h1>
        """, 
        unsafe_allow_html=True
    )
    
    sub_text = "المساعد الأكاديمي الذكي" if is_ar else "Smart Academic Assistant"
    st.markdown(
        f"""
        <p style='text-align: center; color: #64748b; font-size: 1.2rem; font-weight: 600; margin-bottom: 2rem;'>
            {sub_text}
        </p>
        """, 
        unsafe_allow_html=True
    )

# =====================================================================
# 6. محرك الألوان الشامل (Global CSS Styling)
# =====================================================================
bg_color = "#0e1117" if is_dark else "#f4f6f9"
text_color = "#e2e8f0" if is_dark else "#1e293b"
card_bg = "#161b22" if is_dark else "#ffffff"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap');
    
    * {{ font-family: 'IBM Plex Sans Arabic', sans-serif !important; }}
    .stApp {{ background-color: {bg_color} !important; }}
    p, span, label, li, h1, h2, h3 {{ color: {text_color} !important; }}
    header {{ visibility: hidden; }}
    
    /* التبويبات */
    .stTabs [data-baseweb="tab-list"] {{ justify-content: center; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 3px solid #00d4aa !important; }}
    .stTabs [aria-selected="true"] span {{ color: #00d4aa !important; font-weight: 700 !important; }}
    
    /* الأزرار الرئيسية */
    .stButton>button, div[data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
        border: none !important; 
        border-radius: 12px !important; 
        color: white !important; 
        font-weight: bold !important; 
        height: 3.5rem; 
        width: 100% !important;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover, div[data-testid="stFormSubmitButton"] > button:hover {{
        box-shadow: 0 4px 12px rgba(0, 212, 170, 0.4);
        transform: translateY(-2px);
    }}
    
    /* صندوق الرفع */
    div[data-testid="stFileUploader"] > section {{ 
        background-color: {card_bg} !important; 
        border: 2px dashed #00d4aa !important; 
        border-radius: 16px !important; 
        padding: 20px !important;
    }}
    
    /* أزرار التحميل (Download) */
    div[data-testid="stDownloadButton"] button {{
        background: transparent !important;
        border: 2px solid #00d4aa !important;
        color: #00d4aa !important;
        border-radius: 8px !important;
        height: 2.8rem !important;
        margin-bottom: 15px !important;
    }}
    div[data-testid="stDownloadButton"] button:hover {{
        background: #00d4aa !important;
        color: white !important;
    }}
    
    /* بطاقات الكويز */
    .quiz-card {{ 
        background-color: {card_bg} !important; 
        border: 1px solid rgba(0, 212, 170, 0.3) !important; 
        padding: 25px; 
        border-radius: 12px; 
        margin-bottom: 20px; 
    }}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 7. شاشة تسجيل الدخول وإنشاء الحساب (Authentication UI)
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
                with st.spinner("جاري التحقق من البيانات..."):
                    res = sign_in(log_email, log_pass)
                    if "error" in res: 
                        st.error("❌ البريد الإلكتروني أو كلمة المرور غير صحيحة.")
                    else:
                        st.session_state.user_token = res["idToken"]
                        st.session_state.user_email = res["email"]
                        st.rerun()
                        
        with tab_signup:
            st.info("🔒 **شروط كلمة المرور:**\n- 8 أحرف على الأقل\n- حرف إنجليزي كبير واحد (Capital)\n- رقم واحد على الأقل")
            reg_email = st.text_input("البريد الإلكتروني / Email", key="reg_e")
            reg_pass = st.text_input("كلمة المرور / Password", type="password", key="reg_p")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("تسجيل ✨", use_container_width=True):
                if not check_password_strength(reg_pass):
                    st.error("⚠️ كلمة المرور لا تطابق الشروط المذكورة أعلاه.")
                else:
                    with st.spinner("جاري إنشاء الحساب..."):
                        res = sign_up(reg_email, reg_pass)
                        if "error" in res: 
                            st.error(res["error"]["message"])
                        else: 
                            st.success("✅ تم إنشاء الحساب بنجاح! الرجاء الانتقال لتبويب Login لتسجيل الدخول.")
                            
    st.stop()

# =====================================================================
# 8. التطبيق الرئيسي: معالجة النصوص والذكاء الاصطناعي (Main App)
# =====================================================================
def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() or "" for page in reader.pages])
        return str(file.read(), "utf-8")
    except Exception:
        return ""

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
                    [Part 2]: 10 Multiple Choice Questions. Output MUST be a strict JSON array of objects. Keys MUST remain in English: "question", "options", "correct_answer", "explanation". Values in {target_lang}.
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
                            st.session_state.quiz_data = json.loads(match.group(0)) if match else None
                                
                            st.session_state.simple_exp = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[2], flags=re.MULTILINE).strip()
                            st.session_state.detailed_exp = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[3], flags=re.MULTILINE).strip()
                            
                            st.session_state.analysis_done = True
                            st.balloons()
                        else: 
                            st.error("خطأ في تنسيق البيانات المسترجعة من الذكاء الاصطناعي.")
                    except Exception as e: 
                        st.error(f"حدث خطأ أثناء المعالجة: {e}")
        else:
            st.warning("الرجاء رفع ملف المحاضرة أولاً قبل بدء المعالجة!")

# =====================================================================
# 9. عرض النتائج التفاعلية والتبويبات (Results & Tabs)
# =====================================================================
if st.session_state.analysis_done:
    st.markdown("---")
    
    tab_names = ["📝 الملخص", "📚 شرح مفصل", "💡 شرح مبسط", "❓ اختبار", "💬 شات بوت"] if is_ar else ["📝 Summary", "📚 Detailed", "💡 Simple", "❓ Quiz", "💬 Chat"]
    tabs = st.tabs(tab_names)
    
    # --- 1. تبويب الملخص ---
    with tabs[0]: 
        st.download_button("📥 تحميل الملخص (Download)", st.session_state.summary, file_name="Summary.txt")
        st.markdown(st.session_state.summary)
        
    # --- 2. تبويب الشرح المفصل ---
    with tabs[1]: 
        st.download_button("📥 تحميل الشرح المفصل (Download)", st.session_state.detailed_exp, file_name="Detailed_Explanation.txt")
        st.markdown(st.session_state.detailed_exp)
        
    # --- 3. تبويب الشرح المبسط ---
    with tabs[2]: 
        st.download_button("📥 تحميل الشرح المبسط (Download)", st.session_state.simple_exp, file_name="Simple_Explanation.txt")
        st.markdown(st.session_state.simple_exp)
        
    # --- 4. تبويب الاختبار التفاعلي ---
    with tabs[3]:
        if st.session_state.quiz_data:
            # زر التحميل للكويز
            quiz_text_format = ""
            for i, q in enumerate(st.session_state.quiz_data):
                quiz_text_format += f"Q{i+1}: {q['question']}\nAnswers: {', '.join(q['options'])}\nCorrect Answer: {q['correct_answer']}\n\n"
            st.download_button("📥 تحميل الاختبار (Download Quiz)", quiz_text_format, file_name="Quiz.txt")
            
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"<div class='quiz-card'><strong>Q{i+1}:</strong> {q['question']}</div>", unsafe_allow_html=True)
                    user_answers[i] = st.radio("Choose:", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                submit_text = "إرسال الإجابات 🚀" if is_ar else "Submit Answers 🚀"
                if st.form_submit_button(submit_text):
                    score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['correct_answer']])
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] != q['correct_answer']:
                            st.error(f"❌ Q{i+1}: {q['question']}\n\n**Answer:** {q['correct_answer']}\n**Reason:** {q.get('explanation', '')}")
                    st.success(f"النتيجة النهائية (Score): {score} / {len(st.session_state.quiz_data)}")
                    
    # --- 5. تبويب الشات بوت الأكاديمي ---
    with tabs[4]:
        # زر التحميل للشات
        if st.session_state.chat_history:
            chat_export = "\n\n".join([f"[{m['time']}] {m['role'].upper()}:\n{m['content']}" for m in st.session_state.chat_history])
            st.download_button("📥 تحميل سجل المحادثة (Download Chat)", chat_export, file_name="Chat_History.txt")
        
        # عرض المحادثة مع التاريخ
        for m in st.session_state.chat_history:
            avatar_icon = "👤" if m["role"] == "user" else "🤖"
            with st.chat_message(m["role"], avatar=avatar_icon): 
                st.caption(f"🕒 {m['time']}")
                st.markdown(m["content"])
                
        chat_placeholder = "اسألني أي شيء عن محتوى المحاضرة..." if is_ar else "Ask me anything about the lecture..."
        
        if user_query := st.chat_input(chat_placeholder):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.chat_history.append({"role": "user", "content": user_query, "time": current_time})
            
            with st.chat_message("user", avatar="👤"): 
                st.caption(f"🕒 {current_time}")
                st.markdown(user_query)
                
            with st.spinner('جاري التفكير...'):
                chat_context = f"Context from uploaded file: {st.session_state.extracted_text[:4000]}\n\nUser Question: {user_query}\nAnswer purely in {'Arabic' if is_ar else 'English'}."
                try:
                    ans = model.generate_content(chat_context).text
                    bot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    with st.chat_message("assistant", avatar="🤖"): 
                        st.caption(f"🕒 {bot_time}")
                        st.markdown(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans, "time": bot_time})
                except Exception:
                    st.error("عذراً، حدث خطأ أثناء الاتصال بالمساعد الذكي.")