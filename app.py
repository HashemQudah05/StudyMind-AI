import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import requests
from datetime import datetime

# =====================================================================
# 1. Page Configuration
# =====================================================================
st.set_page_config(page_title="StudyMind AI", page_icon="🧠", layout="wide")

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
if "uploaded_filename" not in st.session_state: st.session_state.uploaded_filename = ""
if "processing_step" not in st.session_state: st.session_state.processing_step = 0

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
# 5. Global CSS — Upload UI + Sidebar Redesign
# =====================================================================
def inject_css(is_dark, is_ar):
    bg_color   = "#0e1117" if is_dark else "#f4f6f9"
    text_color = "#e2e8f0" if is_dark else "#1e293b"
    card_bg    = "#161b22" if is_dark else "#ffffff"
    sidebar_bg = "#0d1117" if is_dark else "#f0f4f8"
    input_bg   = "#1c2333" if is_dark else "#f8fafc"
    border_col = "rgba(0,212,170,0.25)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap');

    html, body, p, span, label, li, h1, h2, h3, button {{
        font-family: 'IBM Plex Sans Arabic', sans-serif !important;
    }}
    .stApp {{ background-color: {bg_color} !important; }}
    .stApp header {{ background-color: transparent !important; }}
    p, span, label, li, h1, h2, h3 {{ color: {text_color} !important; }}

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_col};
    }}
    [data-testid="stSidebar"] * {{ color: {text_color} !important; }}

    .sidebar-header {{
        background: linear-gradient(135deg,rgba(0,212,170,0.15),rgba(2,132,199,0.1));
        border: 1px solid {border_col};
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 16px;
    }}
    .sidebar-header .user-name {{
        font-size: 0.95rem;
        font-weight: 700;
        color: #00d4aa !important;
    }}
    .sidebar-header .user-email {{
        font-size: 0.75rem;
        color: #64748b !important;
        margin-top: 2px;
    }}
    
    .history-title {{
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #64748b !important;
        margin: 16px 0 8px;
        padding-right: 4px;
    }}

    .session-btn {{
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        background: {card_bg};
        border: 1px solid {border_col};
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: all 0.2s;
        text-align: right;
    }}
    .session-btn:hover {{
        border-color: #00d4aa;
        background: rgba(0,212,170,0.06);
    }}
    .session-btn.active {{
        border-color: #00d4aa;
        background: rgba(0,212,170,0.1);
    }}
    .session-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
    .session-info {{ flex: 1; overflow: hidden; }}
    .session-title {{
        font-size: 0.85rem;
        font-weight: 600;
        color: {text_color} !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .session-date {{
        font-size: 0.72rem;
        color: #64748b !important;
        margin-top: 2px;
    }}
    .session-active-dot {{
        width: 7px; height: 7px;
        border-radius: 50%;
        background: #00d4aa;
        flex-shrink: 0;
    }}
    .no-history {{
        text-align: center;
        padding: 24px 16px;
        background: {card_bg};
        border: 1px dashed {border_col};
        border-radius: 12px;
        color: #64748b !important;
        font-size: 0.82rem;
        line-height: 1.6;
    }}

    /* ── UPLOAD ZONE ── */
    div[data-testid="stFileUploader"] > section {{
        border: 2px dashed #00d4aa !important;
        border-radius: 18px !important;
        padding: 3rem 1rem !important;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}
    div[data-testid="stFileUploader"] > section:hover {{
        border-color: #00f5c4 !important;
        background: rgba(0,212,170,0.08) !important;
        transform: scale(1.01);
    }}
    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {{
        font-size: 1rem !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stFileUploader"] svg path {{ fill: #00d4aa !important; }}

    /* ── FILE PREVIEW CARD ── */
    .file-preview-card {{
        display: flex;
        align-items: center;
        gap: 14px;
        background: {card_bg};
        border: 1px solid {border_col};
        border-radius: 14px;
        padding: 14px 18px;
        margin-top: 12px;
        animation: slideIn 0.3s ease;
    }}
    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateY(-8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .file-preview-icon {{ font-size: 2.2rem; }}
    .file-preview-info {{ flex: 1; }}
    .file-preview-name {{
        font-weight: 700;
        font-size: 0.9rem;
        color: {text_color} !important;
        word-break: break-all;
    }}
    .file-preview-meta {{
        font-size: 0.75rem;
        color: #64748b !important;
        margin-top: 3px;
    }}
    .file-ready-badge {{
        background: rgba(0,212,170,0.15);
        color: #00d4aa !important;
        border: 1px solid rgba(0,212,170,0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.72rem;
        font-weight: 700;
    }}

    /* ── PROGRESS STEPS ── */
    .progress-wrap {{
        background: {card_bg};
        border: 1px solid {border_col};
        border-radius: 16px;
        padding: 20px 24px;
        margin: 16px 0;
    }}
    .progress-step {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        font-size: 0.88rem;
        color: #64748b !important;
    }}
    .progress-step.done {{ color: {text_color} !important; }}
    .progress-step.active {{ color: #00d4aa !important; font-weight: 600; }}
    .step-dot {{
        width: 22px; height: 22px;
        border-radius: 50%;
        border: 2px solid #334155;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.65rem;
        flex-shrink: 0;
        color: #334155 !important;
    }}
    .step-dot.done {{ background: #00d4aa; border-color: #00d4aa; color: white !important; }}
    .step-dot.active {{
        border-color: #00d4aa;
        color: #00d4aa !important;
        animation: pulseDot 1.2s infinite;
    }}
    @keyframes pulseDot {{
        0%,100% {{ box-shadow: 0 0 0 0 rgba(0,212,170,0.4); }}
        50%      {{ box-shadow: 0 0 0 6px rgba(0,212,170,0); }}
    }}
    
    /* ── MAIN BUTTON ── */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {{
       background: linear-gradient(135deg, #00d4aa, #0284c7) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    height: 3.2rem;
    width: 100% !important;
    letter-spacing: 0.03em;
    transition: all 0.25s !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0,212,170,0.35) !important;
    }}

    div[data-testid="stDownloadButton"] button {{
        background: transparent !important;
        border: 2px solid #00d4aa !important;
        color: #00d4aa !important;
        border-radius: 10px !important;
        height: 2.8rem !important;
        margin-bottom: 15px !important;
    }}
    div[data-testid="stDownloadButton"] button:hover {{
        background: #00d4aa !important;
        color: white !important;
    }}

    .quiz-card {{
        background-color: {card_bg} !important;
        border: 1px solid rgba(0,212,170,0.3) !important;
        padding: 25px;
        border-radius: 14px;
        margin-bottom: 20px;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{ justify-content: center; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 3px solid #00d4aa !important; }}
    .stTabs [aria-selected="true"] span {{ color: #00d4aa !important; font-weight: 700 !important; }}

    .stSelectSlider [data-baseweb="slider"] {{ padding: 0 8px; }}
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 6. Sidebar — redesigned history panel
# =====================================================================
def render_sidebar(is_dark, card_bg, text_color):
    if st.session_state.user_token is None:
        return

    with st.sidebar:

        # ── Safe user data ──
        user_email = st.session_state.get("user_email", "")
        initials = user_email[:2].upper() if user_email else "??"

        # ── User header ──
        st.markdown(f"""
        <div class="sidebar-header">
            <div style="display:flex;align-items:center;gap:10px;direction:rtl;">
                
                <div style="
                    width:40px;
                    height:40px;
                    border-radius:50%;
                    background:linear-gradient(135deg,#00d4aa,#0284c7);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-weight:700;
                    font-size:1rem;
                    color:white;">
                    {initials}
                </div>

                <div style="flex:1;">
                    <div class="user-name">👤 حسابي</div>
                    <div class="user-email">{user_email}</div>
                </div>

            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── History title ──
        st.markdown('<div class="history-title">🗂️ أرشيف المحاضرات</div>', unsafe_allow_html=True)

        # ── Fetch sessions ──
        try:
            db_req = requests.get(f"{DB_URL}/users/{st.session_state.user_id}/sessions.json")
            sessions = db_req.json() if db_req.status_code == 200 and db_req.json() else None
        except:
            sessions = None

        if sessions:
            sorted_ids = sorted(sessions.keys(), reverse=True)
            for s_id in sorted_ids:
                s_data   = sessions[s_id]
                title    = s_data.get('title', 'محاضرة محفوظة')
                # Try to extract a clean name from the title
                display  = title.replace("Lecture - ", "").strip()
                is_active = (s_id == st.session_state.current_session_id)

                active_dot = '<div class="session-active-dot"></div>' if is_active else ""
                active_cls = "active" if is_active else ""

                # Render styled card; use a real button underneath for click
                st.markdown(f"""
                <div class="session-btn {active_cls}">
                    <span class="session-icon">📁</span>
                    <div class="session-info">
                        <div class="session-title">{display}</div>
                        <div class="session-date">{s_id[:4]}-{s_id[4:6]}-{s_id[6:8]} {s_id[9:11]}:{s_id[11:13]}</div>
                    </div>
                    {active_dot}
                </div>
                """, unsafe_allow_html=True)

                if st.button("تحميل", key=f"load_{s_id}", use_container_width=True):
                    st.session_state.current_session_id  = s_id
                    st.session_state.extracted_text      = s_data.get("extracted_text", "")
                    st.session_state.summary             = s_data.get("summary", "")
                    st.session_state.simple_exp          = s_data.get("simple_exp", "")
                    st.session_state.detailed_exp        = s_data.get("detailed_exp", "")
                    st.session_state.quiz_data           = s_data.get("quiz_data", None)
                    st.session_state.chat_history        = s_data.get("chat_history", [])
                    st.session_state.uploaded_filename   = s_data.get("title", "محاضرة محفوظة")
                    st.session_state.analysis_done       = True
                    st.rerun()
        else:
            st.markdown("""
            <div class="no-history">
                📭<br><br>
                لا توجد محاضرات محفوظة بعد.<br>
                ارفع ملفك الأول وسيظهر هنا!
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Stats ──
        if sessions:
            st.markdown(f"""
            <div style="display:flex;gap:8px;margin-bottom:12px;">
                <div style="flex:1;background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.2);
                            border-radius:10px;padding:10px;text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#00d4aa;">{len(sessions)}</div>
                    <div style="font-size:0.7rem;color:#64748b;">محاضرة</div>
                </div>
                <div style="flex:1;background:rgba(2,132,199,0.08);border:1px solid rgba(2,132,199,0.2);
                            border-radius:10px;padding:10px;text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#0284c7;">
                        {sum(len(s.get('chat_history',[])) for s in sessions.values())}
                    </div>
                    <div style="font-size:0.7rem;color:#64748b;">رسالة</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚪 تسجيل خروج", use_container_width=True):
            for key in ["user_token","user_email","user_id","current_session_id",
                        "chat_history","analysis_done","quiz_data","uploaded_filename"]:
                st.session_state[key] = None if key not in ["chat_history"] else []
            st.session_state.analysis_done = False
            st.rerun()

# =====================================================================
# 7. Header toggle (lang / dark)
# =====================================================================
col_left, col_center, col_right = st.columns([1, 2, 1])

with col_right:
    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)
    is_dark    = st.toggle("🌙 Dark | ليلي", value=True)
    lang_toggle = st.radio("Language", ["العربية", "English"], horizontal=True)
    is_ar = lang_toggle == "العربية"

with col_center:
    st.markdown("<h1 style='text-align:center;background:linear-gradient(135deg,#00d4aa,#0284c7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:4rem;font-weight:900;margin-bottom:0;'>StudyMind AI 🧠</h1>", unsafe_allow_html=True)
    sub_text = "المساعد الأكاديمي الذكي" if is_ar else "Smart Academic Assistant"
    st.markdown(f"<p style='text-align:center;color:#64748b;font-size:1.2rem;font-weight:600;margin-bottom:2rem;'>{sub_text}</p>", unsafe_allow_html=True)

card_bg    = "#161b22" if is_dark else "#ffffff"
text_color = "#e2e8f0" if is_dark else "#1e293b"

inject_css(is_dark, is_ar)
render_sidebar(is_dark, card_bg, text_color)

# =====================================================================
# 8. Login Screen
# =====================================================================
if st.session_state.user_token is None:
    _, col_auth, _ = st.columns([1, 1.5, 1])
    with col_auth:
        tab_login, tab_signup = st.tabs(["🔐 Login (تسجيل دخول)", "📝 Sign Up (حساب جديد)"])

        with tab_login:
            log_email = st.text_input("البريد الإلكتروني / Email", key="log_e")
            log_pass  = st.text_input("كلمة المرور / Password", type="password", key="log_p")
            st.write("")
            if st.button("دخول 🚀", use_container_width=True):
                with st.spinner("جاري التحقق..."):
                    res = sign_in(log_email, log_pass)
                    if "error" in res:
                        st.error("❌ بيانات الدخول خاطئة.")
                    else:
                        st.session_state.user_token    = res["idToken"]
                        st.session_state.user_email    = res["email"]
                        st.session_state.user_id       = res["localId"]
                        st.session_state.chat_history  = []
                        st.rerun()

        with tab_signup:
            st.info("🔒 **شروط كلمة المرور:**\n- 8 أحرف على الأقل\n- حرف إنجليزي كبير (Capital)\n- رقم واحد على الأقل")
            reg_email = st.text_input("البريد الإلكتروني / Email", key="reg_e")
            reg_pass  = st.text_input("كلمة المرور / Password", type="password", key="reg_p")
            st.write("")
            if st.button("تسجيل ✨", use_container_width=True):
                if not check_password_strength(reg_pass):
                    st.error("⚠️ كلمة المرور لا تطابق الشروط.")
                else:
                    with st.spinner("جاري الإنشاء..."):
                        res = sign_up(reg_email, reg_pass)
                        if "error" in res: st.error(res["error"]["message"])
                        else: st.success("✅ تم إنشاء الحساب! انتقل لتبويب Login.")
    st.stop()

# =====================================================================
# 9. Upload UI — redesigned
# =====================================================================
def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() or "" for page in reader.pages])
        return str(file.read(), "utf-8")
    except:
        return ""

col_main = st.container()

with col_main:

    # ── Upload label ──
    upload_lbl = "📂 ارفع ملف المحاضرة (PDF أو TXT)" if is_ar else "📂 Upload Lecture File (PDF or TXT)"
    st.markdown(f"<p style='font-size:0.9rem;font-weight:600;color:#64748b;margin-bottom:4px;'>{upload_lbl}</p>", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center; margin-bottom:12px;">
    <div style="font-size:1.05rem; font-weight:700;">📂 اسحب الملف هنا</div>
    <div style="font-size:0.8rem; color:#64748b;">PDF أو TXT • حتى 200MB</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "",
    type=["pdf", "txt"],
    label_visibility="collapsed"
)

# --- File preview card ---
if uploaded_file:
    file_size_kb = round(uploaded_file.size / 1024, 1)
    file_icon = "📄" if uploaded_file.type == "application/pdf" else "📝"
    file_type = "PDF Document" if uploaded_file.type == "application/pdf" else "Text File"

    st.session_state.uploaded_filename = uploaded_file.name

    st.markdown(f"""
    <div class="file-preview-card">
        <span class="file-preview-icon">{file_icon}</span>
        <div class="file-preview-info">
            <div class="file-preview-name">{uploaded_file.name}</div>
            <div class="file-preview-meta">{file_type} · {file_size_kb} KB</div>
        </div>
        <span class="file-ready-badge">✓ جاهز</span>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# --- Level slider ---
level_lbl = "🎯 مستوى التبسيط:" if is_ar else "🎯 Simplification Level:"
levels = ["مبتدئ جداً", "متوسط", "متقدم"] if is_ar else ["Beginner", "Intermediate", "Advanced"]

level = st.select_slider(level_lbl, options=levels)

st.write("")

    # ── Process button ──
btn_lbl = "✨ ابدأ المعالجة الذكية" if is_ar else "✨ Start AI Processing"

if st.button(btn_lbl, use_container_width=True):
        if not uploaded_file:
            st.warning("⚠️ الرجاء رفع ملف أولاً!" if is_ar else "⚠️ Please upload a file first!")
        else:
            # ── Progress steps UI ──
            progress_placeholder = st.empty()

            def show_progress(step):
                steps_ar = [
                    ("استخراج النص من الملف", "📖"),
                    ("تحليل المحتوى بالذكاء الاصطناعي", "🤖"),
                    ("إنشاء الملخص والأسئلة", "📝"),
                    ("حفظ الجلسة في قاعدة البيانات", "💾"),
                ]
                steps_en = [
                    ("Extracting text from file", "📖"),
                    ("Analyzing with AI", "🤖"),
                    ("Generating summary & quiz", "📝"),
                    ("Saving session to database", "💾"),
                ]
                steps = steps_ar if is_ar else steps_en
                html  = '<div class="progress-wrap">'
                for i, (label, icon) in enumerate(steps):
                    if i < step:
                        cls  = "done"
                        dot  = f'<div class="step-dot done">✓</div>'
                    elif i == step:
                        cls  = "active"
                        dot  = f'<div class="step-dot active">⟳</div>'
                    else:
                        cls  = ""
                        dot  = f'<div class="step-dot">{i+1}</div>'
                    html += f'<div class="progress-step {cls}">{dot}{icon} {label}</div>'
                html += "</div>"
                progress_placeholder.markdown(html, unsafe_allow_html=True)

            # Step 1 — extract
            show_progress(0)
            text = extract_text(uploaded_file)
            st.session_state.extracted_text = text

            if not text.strip():
                progress_placeholder.empty()
                st.error("❌ لم نتمكن من استخراج النص من الملف." if is_ar else "❌ Could not extract text from file.")
            else:
                # Step 2 — AI
                show_progress(1)
                target_lang = "Arabic" if is_ar else "English"
                prompt = f"""
                Analyze this text: {text[:8000]}
                ALL output MUST be in {target_lang}.
                Generate EXACTLY 4 parts separated strictly by |||. No introductory text.
                [Part 1]: Professional bulleted summary.
                |||
                [Part 2]: 10 Multiple Choice Questions. Output MUST be a strict JSON array. Keys in English: "question","options","correct_answer","explanation". Values in {target_lang}.
                |||
                [Part 3]: Simplified explanation for {level} level.
                |||
                [Part 4]: Deep academic explanation.
                """
                try:
                    # Step 3 — parse
                    show_progress(2)
                    response = model.generate_content(prompt)
                    parts    = response.text.split("|||")

                    if len(parts) >= 4:
                        st.session_state.summary      = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[0], flags=re.MULTILINE).strip()
                        match = re.search(r'\[.*\]', parts[1], re.DOTALL)
                        if match:
                            try: st.session_state.quiz_data = json.loads(match.group(0).replace('\\','\\\\'), strict=False)
                            except: st.session_state.quiz_data = None
                        else: st.session_state.quiz_data = None
                        st.session_state.simple_exp   = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[2], flags=re.MULTILINE).strip()
                        st.session_state.detailed_exp = re.sub(r'^(القسم|الجزء|Part).*?:', '', parts[3], flags=re.MULTILINE).strip()
                        st.session_state.analysis_done = True
                        st.session_state.chat_history  = []

                        # Step 4 — save
                        show_progress(3)
                        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.session_state.current_session_id = session_id

                        clean_name = uploaded_file.name.rsplit(".", 1)[0][:30]
                        session_data = {
                            "title":          clean_name,
                            "extracted_text": st.session_state.extracted_text,
                            "summary":        st.session_state.summary,
                            "simple_exp":     st.session_state.simple_exp,
                            "detailed_exp":   st.session_state.detailed_exp,
                            "quiz_data":      st.session_state.quiz_data,
                            "chat_history":   [],
                        }
                        try:
                            requests.put(f"{DB_URL}/users/{st.session_state.user_id}/sessions/{session_id}.json", json=session_data)
                        except: pass

                        progress_placeholder.empty()
                        st.balloons()
                        st.rerun()
                    else:
                        progress_placeholder.empty()
                        st.error("خطأ في تنسيق البيانات المسترجعة.")
                except Exception as e:
                    progress_placeholder.empty()
                    st.error(f"حدث خطأ: {e}")

# =====================================================================
# 10. Results Tabs
# =====================================================================
if st.session_state.analysis_done:

    # Session banner
    if st.session_state.uploaded_filename:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;background:rgba(0,212,170,0.07);
                    border:1px solid rgba(0,212,170,0.2);border-radius:12px;padding:12px 18px;margin:16px 0;">
            <span style="font-size:1.3rem;">📂</span>
            <div>
                <div style="font-weight:700;font-size:0.9rem;">{st.session_state.uploaded_filename}</div>
                <div style="font-size:0.75rem;color:#64748b;">تم التحليل بنجاح ✓</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    tabs = st.tabs(
        ["📝 الملخص", "📚 شرح مفصل", "💡 شرح مبسط", "❓ اختبار", "💬 شات بوت"]
        if is_ar else
        ["📝 Summary", "📚 Detailed", "💡 Simple", "❓ Quiz", "💬 Chat"]
    )

    with tabs[0]:
        st.download_button("📥 تحميل الملخص", st.session_state.summary, file_name="Summary.txt")
        st.markdown(st.session_state.summary)

    with tabs[1]:
        st.download_button("📥 تحميل الشرح المفصل", st.session_state.detailed_exp, file_name="Detailed.txt")
        st.markdown(st.session_state.detailed_exp)

    with tabs[2]:
        st.download_button("📥 تحميل الشرح المبسط", st.session_state.simple_exp, file_name="Simple.txt")
        st.markdown(st.session_state.simple_exp)

    with tabs[3]:
        if st.session_state.quiz_data:
            quiz_text = "".join([
                f"Q{i+1}: {q['question']}\nAnswers: {', '.join(q['options'])}\nCorrect: {q['correct_answer']}\n\n"
                for i, q in enumerate(st.session_state.quiz_data)
            ])
            st.download_button("📥 تحميل الاختبار", quiz_text, file_name="Quiz.txt")
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"<div class='quiz-card'><strong>Q{i+1}:</strong> {q['question']}</div>", unsafe_allow_html=True)
                    user_answers[i] = st.radio("", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.write("")
                if st.form_submit_button("إرسال الإجابات 🚀" if is_ar else "Submit 🚀"):
                    score = sum(1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['correct_answer'])
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] != q['correct_answer']:
                            st.error(f"❌ Q{i+1}: {q['question']}\n\n**Answer:** {q['correct_answer']}\n**Reason:** {q.get('explanation','')}")
                    st.success(f"النتيجة: {score} / {len(st.session_state.quiz_data)}")
        else:
            st.info("لم يتمكن الذكاء الاصطناعي من توليد الاختبار لهذا الملف.")

    with tabs[4]:
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"], avatar="👤" if m["role"] == "user" else "🤖"):
                if m.get("time"): st.caption(f"🕒 {m['time']}")
                st.markdown(m["content"])

        if user_query := st.chat_input("اسألني عن محتوى المحاضرة..." if is_ar else "Ask me anything about the lecture..."):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.chat_history.append({"role": "user", "content": user_query, "time": now})
            with st.chat_message("user", avatar="👤"):
                st.caption(f"🕒 {now}")
                st.markdown(user_query)

            with st.spinner("جاري التفكير..." if is_ar else "Thinking..."):
                try:
                    ans = model.generate_content(
                        f"Context: {st.session_state.extracted_text[:4000]}\nQuestion: {user_query}\nAnswer in {'Arabic' if is_ar else 'English'}."
                    ).text
                    bot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with st.chat_message("assistant", avatar="🤖"):
                        st.caption(f"🕒 {bot_time}")
                        st.markdown(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans, "time": bot_time})

                    if st.session_state.current_session_id:
                        requests.put(
                            f"{DB_URL}/users/{st.session_state.user_id}/sessions/{st.session_state.current_session_id}/chat_history.json",
                            json=st.session_state.chat_history
                        )
                    st.rerun()
                except Exception:
                    st.error("حدث خطأ أثناء الاتصال بالمساعد.")
