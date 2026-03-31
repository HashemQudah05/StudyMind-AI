import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import requests  # <-- مكتبة جديدة لـ Firebase

# 1. إعدادات الصفحة
st.set_page_config(page_title="StudyMind AI", page_icon="🧠", layout="wide")

# 2. إعداد الـ API (بالطريقة الآمنة المخفية)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    FIREBASE_API_KEY = st.secrets["FIREBASE_WEB_API_KEY"]  # <-- مفتاح فايربيس
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("❌ المفاتيح غير موجودة! يرجى إضافة GEMINI_API_KEY و FIREBASE_WEB_API_KEY في إعدادات Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'vision' not in m.name:
                return genai.GenerativeModel(m.name)
        return genai.GenerativeModel('gemini-pro')
    except Exception:
        return None

model = get_working_model()

# ==========================================
# 3. دوال تسجيل الدخول (Firebase Auth)
# ==========================================
def check_password_strength(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    return True

def sign_up(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

def sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

# ==========================================
# 4. تهيئة الذاكرة
# ==========================================
if "user_token" not in st.session_state: st.session_state.user_token = None
if "user_email" not in st.session_state: st.session_state.user_email = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "extracted_text" not in st.session_state: st.session_state.extracted_text = ""
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "summary" not in st.session_state: st.session_state.summary = ""
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "simple_exp" not in st.session_state: st.session_state.simple_exp = ""
if "detailed_exp" not in st.session_state: st.session_state.detailed_exp = ""

# ==========================================
# 5. شاشة تسجيل الدخول (بوابة العبور)
# ==========================================
if st.session_state.user_token is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #00d4aa; font-family: sans-serif; font-size: 4rem;'>StudyMind AI 🧠</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 1.2rem;'>الرجاء تسجيل الدخول للبدء / Please Login to start</p><br>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 1.5, 1])
    with col_m:
        auth_mode = st.radio("Choose Action:", ["Login (تسجيل دخول)", "Sign Up (حساب جديد)"], horizontal=True)
        email = st.text_input("Email (البريد الإلكتروني)")
        password = st.text_input("Password (كلمة المرور)", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Submit 🚀", use_container_width=True):
            if auth_mode == "Sign Up (حساب جديد)":
                if not check_password_strength(password):
                    st.error("⚠️ كلمة المرور يجب أن تكون 8 أحرف على الأقل، وتحتوي على حرف كبير (Capital) ورقم.")
                else:
                    with st.spinner("جاري إنشاء الحساب..."):
                        res = sign_up(email, password)
                        if "error" in res:
                            st.error(res["error"]["message"])
                        else:
                            st.success("✅ تم إنشاء الحساب بنجاح! الرجاء تسجيل الدخول الآن.")
            else:
                with st.spinner("جاري تسجيل الدخول..."):
                    res = sign_in(email, password)
                    if "error" in res:
                        st.error("❌ البريد الإلكتروني أو كلمة المرور غير صحيحة.")
                    else:
                        st.session_state.user_token = res["idToken"]
                        st.session_state.user_email = res["email"]
                        st.rerun()
    # إيقاف الكود هنا إذا لم يسجل دخول
    st.stop()

# ==========================================
# 6. التخطيط العلوي (Header & Settings) بعد تسجيل الدخول
# ==========================================
col_empty, col_center, col_settings = st.columns([1, 2, 1])

with col_settings:
    # ترتيب الإعدادات فوق بعض بشكل أنيق ومختصر
    st.markdown("<div style='padding-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # إظهار إيميل المستخدم وزر تسجيل الخروج
    st.caption(f"👤 {st.session_state.user_email}")
    if st.button("🚪 Logout | تسجيل خروج"):
        st.session_state.user_token = None
        st.session_state.user_email = None
        st.session_state.analysis_done = False
        st.rerun()
        
    is_dark = st.toggle("🌙 Dark | ليلي", value=True)
    lang_toggle = st.radio("Language", ["العربية", "English"], horizontal=True, label_visibility="collapsed")
    is_ar = lang_toggle == "العربية"

with col_center:
    st.markdown("""
        <h1 class='main-title'>
            StudyMind AI 🧠
        </h1>
    """, unsafe_allow_html=True)
    
    sub_text = "المساعد الأكاديمي الذكي" if is_ar else "Smart Academic Assistant"
    st.markdown(f"""
        <p style='text-align: center; color: #64748b !important; font-size: 1.2rem; font-weight: 600; margin-top: -10px; margin-bottom: 2.5rem;'>
            {sub_text}
        </p>
    """, unsafe_allow_html=True)

# ==========================================
# 7. محرك الألوان الصارم (The BULLETPROOF CSS)
# ==========================================
bg_color = "#0e1117" if is_dark else "#f4f6f9"
text_color = "#e2e8f0" if is_dark else "#1e293b"
card_bg = "#161b22" if is_dark else "#ffffff"
border_color = "rgba(0, 212, 170, 0.3)" if is_dark else "rgba(0, 212, 170, 0.8)"
tab_bg = "rgba(255,255,255,0.02)" if is_dark else "#e2e8f0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;600;700&display=swap');
    
    /* الأساسيات */
    * {{ font-family: 'IBM Plex Sans Arabic', sans-serif !important; }}
    .stApp {{ background-color: {bg_color} !important; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 1.5rem !important; max-width: 1100px; }}
    
    /* إجبار لون النص العام */
    h1, h2, h3, h4, h5, h6, p, span, label, li {{ color: {text_color} !important; }}
    
    /* منطقة الرفع */
    div[data-testid="stFileUploader"] > section {{
        background-color: {card_bg} !important;
        border: 2px dashed #00d4aa !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }}
    div[data-testid="stFileUploader"] * {{ color: {text_color} !important; }}
    div[data-testid="stFileUploader"] svg {{ fill: #00d4aa !important; color: #00d4aa !important; }}
    div[data-testid="stFileUploader"] button {{
        background-color: transparent !important; border: 1px solid #00d4aa !important; color: #00d4aa !important; border-radius: 8px !important;
    }}
    div[data-testid="stFileUploader"] button:hover {{ background-color: #00d4aa !important; color: white !important; }}
    
    /* العنوان الرئيسي */
    .main-title {{
        background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        color: transparent !important; 
        text-align: center; font-size: 4rem; font-weight: 900; margin-bottom: 0; padding-bottom: 10px;
    }}
    
    /* بطاقات الكويز */
    .quiz-card {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        padding: 25px; border-radius: 12px; margin-bottom: 20px;
    }}
    .quiz-card, .quiz-card * {{ color: {text_color} !important; }}
    
    /* التبويبات */
    .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; gap: 8px; justify-content: center; border-bottom: 1px solid {border_color}; }}
    .stTabs [data-baseweb="tab"] {{ background-color: transparent; border: none; padding: 10px 25px; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 3px solid #00d4aa !important; }}
    .stTabs [aria-selected="true"] span {{ color: #00d4aa !important; font-weight: 700 !important; }}
    
    /* 🔴🔴 إصلاح الأزرار (الرئيسية + زر إرسال الإجابات) 🔴🔴 */
    .stButton>button, div[data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
        border: none !important; border-radius: 12px !important; height: 3.5rem; width: 100% !important;
        transition: all 0.3s ease;
    }}
    .stButton>button *, div[data-testid="stFormSubmitButton"] > button * {{
        color: white !important; font-weight: bold !important; font-size: 1.1rem !important;
    }}
    .stButton>button:hover, div[data-testid="stFormSubmitButton"] > button:hover {{
        box-shadow: 0 6px 15px rgba(0, 212, 170, 0.4); transform: translateY(-2px);
    }}
    
    /* أزرار التحميل */
    div[data-testid="stDownloadButton"] button {{
        background-color: {card_bg} !important;
        border: 2px solid #00d4aa !important;
        border-radius: 8px !important; height: 2.8rem; width: auto !important; padding: 0 20px !important; margin-bottom: 15px;
    }}
    div[data-testid="stDownloadButton"] button * {{ color: #00d4aa !important; font-weight: 600 !important; }}
    div[data-testid="stDownloadButton"] button:hover {{ background-color: #00d4aa !important; }}
    div[data-testid="stDownloadButton"] button:hover * {{ color: white !important; }}
    
    /* مربع الشات */
    [data-testid="stChatInput"] {{ background-color: {card_bg} !important; border: 1px solid {border_color} !important; }}
    [data-testid="stChatInput"] * {{ color: {text_color} !important; }}
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 8. دوال المعالجة
# ==========================================
def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() or "" for page in reader.pages])
        return str(file.read(), "utf-8")
    except Exception:
        return ""

def clean_text(text):
    return re.sub(r'^(القسم|الجزء|Part|Section).*?:', '', text, flags=re.MULTILINE).strip()

def format_quiz(quiz_data, is_ar):
    if not quiz_data: return ""
    txt = "StudyMind AI Quiz\n" + "="*20 + "\n\n"
    for i, q in enumerate(quiz_data):
        txt += f"Q{i+1}: {q['question']}\n"
        for opt in q['options']: txt += f" - {opt}\n"
        ans_lbl = "الإجابة الصحيحة" if is_ar else "Correct Answer"
        exp_lbl = "الشرح" if is_ar else "Explanation"
        txt += f"\n✅ {ans_lbl}: {q['correct_answer']}\n💡 {exp_lbl}: {q.get('explanation', '')}\n" + "-"*30 + "\n"
    return txt

def format_chat(chat_hist):
    txt = "StudyMind AI Chat\n" + "="*30 + "\n\n"
    for m in chat_hist:
        role = "Student" if m["role"] == "user" else "AI Tutor"
        txt += f"[{role}]:\n{m['content']}\n\n"
    return txt

# ==========================================
# 9. قاموس الواجهة
# ==========================================
ui = {
    "upload": "📂 ارفع ملف المحاضرة (PDF/TXT)" if is_ar else "📂 Upload Lecture (PDF/TXT)",
    "level": "🎯 مستوى التبسيط للمفاهيم:" if is_ar else "🎯 Simplification Level:",
    "levels": ["مبتدئ جداً", "متوسط", "متقدم"] if is_ar else ["Beginner", "Intermediate", "Advanced"],
    "btn": "✨ ابدأ المعالجة الذكية" if is_ar else "✨ Start Smart Processing",
    "tabs": ["📝 الملخص", "📚 شرح مفصل", "💡 شرح مبسط", "❓ اختبار", "💬 شات بوت"] if is_ar else ["📝 Summary", "📚 Detailed", "💡 Simple", "❓ Quiz", "💬 Chatbot"],
    "dl_btn": "📥 تحميل" if is_ar else "📥 Download",
    "processing": "الذكاء الاصطناعي يحلل البيانات... 🤖" if is_ar else "AI is analyzing... 🤖",
    "ask": "اسألني أي شيء عن المحتوى..." if is_ar else "Ask me anything...",
    "submit_q": "إرسال الإجابات 🚀" if is_ar else "Submit Answers 🚀"
}

# ==========================================
# 10. منطقة المعالجة والرفع
# ==========================================
if model is None:
    st.error("❌ API Connection Failed.")
else:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        uploaded_file = st.file_uploader(ui["upload"], type=["pdf", "txt"])
        level = st.select_slider(ui["level"], options=ui["levels"])
        
        if st.button(ui["btn"]):
            if uploaded_file:
                with st.spinner(ui["processing"]):
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
                                st.session_state.summary = clean_text(parts[0])
                                match = re.search(r'\[.*\]', parts[1], re.DOTALL)
                                if match: st.session_state.quiz_data = json.loads(match.group(0))
                                else: st.session_state.quiz_data = None
                                st.session_state.simple_exp = clean_text(parts[2])
                                st.session_state.detailed_exp = clean_text(parts[3])
                                st.session_state.analysis_done = True
                                st.balloons()
                            else:
                                st.error("خطأ في قراءة البيانات من الذكاء الاصطناعي.")
                        except Exception as e:
                            st.error(f"Processing Error: {e}")
            else:
                st.warning("الرجاء رفع ملف أولاً!" if is_ar else "Please upload a file!")

# ==========================================
# 11. النتائج التفاعلية والتبويبات
# ==========================================
if st.session_state.analysis_done:
    st.markdown("---")
    t_sum, t_det, t_simp, t_quiz, t_chat = st.tabs(ui["tabs"])
    
    with t_sum:
        st.markdown(f'<div class="dl-btn">', unsafe_allow_html=True)
        st.download_button(ui["dl_btn"], st.session_state.summary, file_name="Summary.txt", key="dl1")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(st.session_state.summary)
        
    with t_det:
        st.markdown(f'<div class="dl-btn">', unsafe_allow_html=True)
        st.download_button(ui["dl_btn"], st.session_state.detailed_exp, file_name="Detailed_Explanation.txt", key="dl2")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(st.session_state.detailed_exp)

    with t_simp:
        st.markdown(f'<div class="dl-btn">', unsafe_allow_html=True)
        st.download_button(ui["dl_btn"], st.session_state.simple_exp, file_name="Simple_Explanation.txt", key="dl3")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(st.session_state.simple_exp)
        
    with t_quiz:
        if st.session_state.quiz_data:
            st.markdown(f'<div class="dl-btn">', unsafe_allow_html=True)
            st.download_button(ui["dl_btn"], format_quiz(st.session_state.quiz_data, is_ar), file_name="Quiz.txt", key="dl4")
            st.markdown('</div>', unsafe_allow_html=True)
            
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"<div class='quiz-card'><strong>Q{i+1}:</strong> {q['question']}</div>", unsafe_allow_html=True)
                    user_answers[i] = st.radio("Choose:", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.markdown("<br>", unsafe_allow_html=True)
                
                if st.form_submit_button(ui["submit_q"]):
                    score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['correct_answer']])
                    st.markdown("---")
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] != q['correct_answer']:
                            st.error(f"❌ Q{i+1}: {q['question']}")
                            st.info(f"**Answer:** {q['correct_answer']}\n**Reason:** {q.get('explanation', '')}")
                    st.success(f"Score: {score} / {len(st.session_state.quiz_data)}")
        else:
            st.error("Quiz generation failed.")
    
    with t_chat:
        st.markdown(f'<div class="dl-btn">', unsafe_allow_html=True)
        st.download_button(ui["dl_btn"], format_chat(st.session_state.chat_history), file_name="Chat.txt", key="dl5")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # إضافة قاموس للأيقونات
        avatars = {"user": "👤", "assistant": "🤖"}
        
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"], avatar=avatars.get(m["role"])): 
                st.markdown(m["content"])

        if user_query := st.chat_input(ui["ask"]):
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user", avatar="👤"): 
                st.markdown(user_query)
            with st.spinner('...'):
                out_lang = "Arabic" if is_ar else "English"
                chat_p = f"Context: {st.session_state.extracted_text[:4000]}\nAnswer in {out_lang}: {user_query}"
                try:
                    ans = model.generate_content(chat_p).text
                    with st.chat_message("assistant", avatar="🤖"): 
                        st.markdown(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})
                except Exception:
                    st.error("Error generating response.")

# Force Reboot