import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import requests

# =====================================================================
# 1. إعدادات الصفحة الأساسية
# =====================================================================
st.set_page_config(
    page_title="StudyMind AI", 
    page_icon="🧠", 
    layout="wide"
)

# =====================================================================
# 2. تهيئة الذاكرة (Session State) - مفصلة بالكامل
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
# 3. التخطيط العلوي الثابت (يظهر دائماً للجميع)
# =====================================================================
col_empty, col_center, col_settings = st.columns([1, 2, 1])

with col_settings:
    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)
    
    # أزرار اللغة والوضع الليلي
    is_dark = st.toggle("🌙 Dark | ليلي", value=True)
    lang_toggle = st.radio(
        "Language", 
        ["العربية", "English"], 
        horizontal=True
    )
    is_ar = lang_toggle == "العربية"
    
    # زر تسجيل الخروج (يظهر فقط إذا كان المستخدم مسجل دخول)
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
        <p style='text-align: center; 
                  color: #64748b; 
                  font-size: 1.2rem; 
                  font-weight: 600; 
                  margin-bottom: 2rem;'>
            {sub_text}
        </p>
        """, 
        unsafe_allow_html=True
    )

# =====================================================================
# 4. محرك الألوان الشامل (CSS) - مفصل سطر بسطر
# =====================================================================
bg_color = "#0e1117" if is_dark else "#f4f6f9"
text_color = "#e2e8f0" if is_dark else "#1e293b"
card_bg = "#161b22" if is_dark else "#ffffff"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap');
    
    * {{ 
        font-family: 'IBM Plex Sans Arabic', sans-serif !important; 
    }}
    
    .stApp {{ 
        background-color: {bg_color} !important; 
    }}
    
    p, span, label, li {{ 
        color: {text_color} !important; 
    }}
    
    header {{ 
        visibility: hidden; 
    }}
    
    /* التبويبات Tabs */
    .stTabs [data-baseweb="tab-list"] {{ 
        justify-content: center; 
    }}
    
    .stTabs [aria-selected="true"] {{ 
        border-bottom: 3px solid #00d4aa !important; 
    }}
    
    .stTabs [aria-selected="true"] span {{ 
        color: #00d4aa !important; 
        font-weight: 700 !important; 
    }}
    
    /* الأزرار الرئيسية */
    .stButton>button, div[data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
        border: none !important; 
        border-radius: 12px !important; 
        color: white !important; 
        font-weight: bold !important;
        height: 3.5rem;
    }}
    
    /* منطقة رفع الملفات */
    div[data-testid="stFileUploader"] > section {{ 
        background-color: {card_bg} !important; 
        border: 2px dashed #00d4aa !important; 
        border-radius: 16px !important; 
        padding: 20px !important;
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
# 5. التحقق من المفاتيح (API Keys)
# =====================================================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    FIREBASE_API_KEY = st.secrets["FIREBASE_WEB_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("❌ الرجاء التأكد من وجود مفاتيح GEMINI و FIREBASE في ملف secrets.toml.")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

# =====================================================================
# 6. دوال تسجيل الدخول وإنشاء الحساب (Firebase)
# =====================================================================
def check_password_strength(password):
    """التحقق من قوة كلمة المرور"""
    if len(password) < 8: 
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"\d", password): 
        return False
    return True

def sign_up(email, password):
    """إرسال طلب إنشاء حساب جديد لفايربيس"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email, 
        "password": password, 
        "returnSecureToken": True
    }
    return requests.post(url, json=payload).json()

def sign_in(email, password):
    """إرسال طلب تسجيل دخول لفايربيس"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email, 
        "password": password, 
        "returnSecureToken": True
    }
    return requests.post(url, json=payload).json()

# =====================================================================
# 7. شاشة تسجيل الدخول (التوقف هنا إذا لم يسجل)
# =====================================================================
if st.session_state.user_token is None:
    _, col_auth, _ = st.columns([1, 1.5, 1])
    
    with col_auth:
        # التبويبات الخاصة بتسجيل الدخول وإنشاء الحساب
        tab_login, tab_signup = st.tabs(["🔐 Login (تسجيل دخول)", "📝 Sign Up (حساب جديد)"])
        
        # --- تبويب تسجيل الدخول ---
        with tab_login:
            st.write("تسجيل الدخول لحسابك:")
            log_email = st.text_input("البريد الإلكتروني", key="log_e")
            log_pass = st.text_input("كلمة المرور", type="password", key="log_p")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("دخول 🚀", use_container_width=True):
                with st.spinner("جاري التحقق..."):
                    res = sign_in(log_email, log_pass)
                    if "error" in res: 
                        st.error("❌ بيانات الدخول خاطئة.")
                    else:
                        st.session_state.user_token = res["idToken"]
                        st.session_state.user_email = res["email"]
                        st.rerun()
                        
        # --- تبويب إنشاء حساب جديد ---
        with tab_signup:
            st.write("إنشاء حساب جديد:")
            st.info("🔒 **شروط كلمة المرور:**\n- 8 أحرف على الأقل\n- حرف إنجليزي كبير واحد (Capital)\n- رقم واحد على الأقل")
            
            reg_email = st.text_input("البريد الإلكتروني", key="reg_e")
            reg_pass = st.text_input("كلمة المرور", type="password", key="reg_p")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("تسجيل ✨", use_container_width=True):
                if not check_password_strength(reg_pass):
                    st.error("⚠️ كلمة المرور لا تطابق الشروط المذكورة أعلاه.")
                else:
                    with st.spinner("جاري الإنشاء..."):
                        res = sign_up(reg_email, reg_pass)
                        if "error" in res: 
                            st.error(res["error"]["message"])
                        else: 
                            st.success("✅ تم الإنشاء بنجاح! انتقل لتبويب Login للدخول.")
                            
    # إيقاف الكود هنا إجبارياً حتى يتم تسجيل الدخول
    st.stop() 

# =====================================================================
# 8. الكود الأساسي (الرفع والمعالجة) - يظهر بعد الدخول
# =====================================================================
def extract_text(file):
    """استخراج النص من ملفات PDF أو TXT"""
    try:
        if file.type == "application/pdf":
            return "".join([page.extract_text() or "" for page in PyPDF2.PdfReader(file).pages])
        return str(file.read(), "utf-8")
    except Exception: 
        return ""

_, col_main, _ = st.columns([1, 2, 1])

with col_main:
    # واجهة الرفع
    upload_label = "📂 ارفع ملف المحاضرة (PDF/TXT)" if is_ar else "📂 Upload Lecture"
    uploaded_file = st.file_uploader(upload_label, type=["pdf", "txt"])
    
    # مستوى التبسيط
    level_label = "🎯 مستوى التبسيط للمفاهيم:" if is_ar else "🎯 Simplification Level:"
    level_options = ["مبتدئ جداً", "متوسط", "متقدم"] if is_ar else ["Beginner", "Intermediate", "Advanced"]
    level = st.select_slider(level_label, options=level_options)
    
    # زر المعالجة
    process_btn = "✨ ابدأ المعالجة الذكية" if is_ar else "✨ Start Processing"
    
    if st.button(process_btn, use_container_width=True):
        if uploaded_file:
            with st.spinner("الذكاء الاصطناعي يحلل البيانات... 🤖"):
                text = extract_text(uploaded_file)
                st.session_state.extracted_text = text
                
                if text.strip():
                    target_lang = "Arabic" if is_ar else "English"
                    
                    # هندسة الأوامر (Prompt Engineering)
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
                            st.error("خطأ في قراءة البيانات من النموذج.")
                    except Exception as e: 
                        st.error(f"Error processing data: {e}")
        else:
            st.warning("الرجاء رفع ملف أولاً!")

# =====================================================================
# 9. النتائج التفاعلية والتبويبات
# =====================================================================
if st.session_state.analysis_done:
    st.markdown("---")
    
    tab_titles = ["📝 الملخص", "📚 شرح مفصل", "💡 شرح مبسط", "❓ اختبار", "💬 شات بوت"] if is_ar else ["📝 Summary", "📚 Detailed", "💡 Simple", "❓ Quiz", "💬 Chat"]
    tabs = st.tabs(tab_titles)
    
    # 1. تبويب الملخص
    with tabs[0]: 
        st.markdown(st.session_state.summary)
        
    # 2. تبويب الشرح المفصل
    with tabs[1]: 
        st.markdown(st.session_state.detailed_exp)
        
    # 3. تبويب الشرح المبسط
    with tabs[2]: 
        st.markdown(st.session_state.simple_exp)
        
    # 4. تبويب الاختبار التفاعلي
    with tabs[3]:
        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                user_answers = {}
                
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"<div class='quiz-card'><strong>Q{i+1}:</strong> {q['question']}</div>", unsafe_allow_html=True)
                    user_answers[i] = st.radio("Choose:", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                submit_btn = "إرسال الإجابات 🚀" if is_ar else "Submit 🚀"
                if st.form_submit_button(submit_btn):
                    score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['correct_answer']])
                    
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] != q['correct_answer']:
                            st.error(f"❌ Q{i+1}: {q['question']}\n\n**Answer:** {q['correct_answer']}\n**Reason:** {q.get('explanation', '')}")
                            
                    st.success(f"Score: {score} / {len(st.session_state.quiz_data)}")
                    
    # 5. تبويب الشات بوت
    with tabs[4]:
        for m in st.session_state.chat_history:
            avatar = "👤" if m["role"] == "user" else "🤖"
            with st.chat_message(m["role"], avatar=avatar): 
                st.markdown(m["content"])
                
        chat_prompt = "اسألني أي شيء عن المحتوى..." if is_ar else "Ask me anything..."
        if user_query := st.chat_input(chat_prompt):
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            with st.chat_message("user", avatar="👤"): 
                st.markdown(user_query)
                
            with st.spinner('...'):
                chat_context = f"Context: {st.session_state.extracted_text[:4000]}\nAnswer in {'Arabic' if is_ar else 'English'}: {user_query}"
                ans = model.generate_content(chat_context).text
                
                with st.chat_message("assistant", avatar="🤖"): 
                    st.markdown(ans)
                    
                st.session_state.chat_history.append({"role": "assistant", "content": ans})

# نهاية الكود