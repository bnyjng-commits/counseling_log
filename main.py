import streamlit as st
from supabase import create_client
from streamlit_calendar import calendar
import datetime
from database import (
    fetch_logs, fetch_schedules, save_schedule,
    get_user_settings, save_user_settings
)

# 페이지 설정
st.set_page_config(
    page_title="AI 상담일지",
    page_icon="📝",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "my_class" not in st.session_state:
    st.session_state.my_class = ""
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "show_schedule_dialog" not in st.session_state:
    st.session_state.show_schedule_dialog = False
if "session" not in st.session_state:
    st.session_state.session = None


# ── 상담 일정 입력 다이얼로그 ────────────────────────────────────────────────
@st.dialog("📅 상담 일정 입력")
def schedule_dialog():
    sch_date = st.date_input("날짜", value=datetime.date.today())
    sch_name = st.text_input("학생 이름")
    sch_note = st.text_input("메모 (선택)")

    col_s, col_c = st.columns(2)
    with col_s:
        if st.button("저장", use_container_width=True):
            if sch_name:
                try:
                    save_schedule(
                        st.session_state.user.id,
                        sch_date,
                        sch_name,
                        sch_note if sch_note else None
                    )
                    st.session_state.show_schedule_dialog = False
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 오류: {e}")
            else:
                st.warning("학생 이름을 입력해 주세요.")
    with col_c:
        if st.button("취소", use_container_width=True):
            st.session_state.show_schedule_dialog = False
            st.rerun()


# ── 우리반 설정 변경 시 DB 저장 콜백 ─────────────────────────────────────────
def on_class_change():
    if st.session_state.user and "sidebar_my_class" in st.session_state:
        st.session_state.my_class = st.session_state.sidebar_my_class
        save_user_settings(st.session_state.user.id, st.session_state.sidebar_my_class)


# ── 로그인 전: 사이드바 완전 숨김 ────────────────────────────────────────────
if not st.session_state.user:
    st.markdown(
        """<style>[data-testid="stSidebar"]{display:none}</style>""",
        unsafe_allow_html=True
    )

    st.title("🛡️ AI 상담일지")

    tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입"])

    with tab_login:
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_password")

        if st.button("로그인", key="btn_login", use_container_width=True):
            if not email or not password:
                st.warning("이메일과 비밀번호를 입력해 주세요.")
            else:
                try:
                    supabase = get_supabase()
                    result = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state.user = result.user
                    st.session_state.session = result.session  # RLS용 JWT 저장
                    st.session_state.logged_in = True
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 실패: {e}")

    with tab_signup:
        new_email = st.text_input("이메일", key="signup_email")
        new_password = st.text_input("비밀번호 (6자 이상)", type="password", key="signup_password")

        if st.button("회원가입", key="btn_signup", use_container_width=True):
            if not new_email or not new_password:
                st.warning("이메일과 비밀번호를 입력해 주세요.")
            else:
                try:
                    supabase = get_supabase()
                    supabase.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("✅ 회원가입 완료! 이메일 인증 후 로그인해 주세요.")
                except Exception as e:
                    st.error(f"회원가입 실패: {e}")

    st.stop()


# ── 로그인 후 ─────────────────────────────────────────────────────────────────
user_id = st.session_state.user.id

# 우리반 설정: 세션에 없으면 DB에서 로드
if not st.session_state.my_class:
    settings = get_user_settings(user_id)
    if settings and settings.get("my_class"):
        st.session_state.my_class = settings["my_class"]

# ── 사이드바 ──────────────────────────────────────────────────────────────────
st.sidebar.markdown(f"👤 **{st.session_state.user.email}**")
st.sidebar.markdown("---")

st.sidebar.text_input(
    "🏫 우리반 설정",
    value=st.session_state.my_class,
    key="sidebar_my_class",
    on_change=on_class_change,
    placeholder="예: 2-3"
)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 로그아웃"):
    st.session_state.user = None
    st.session_state.session = None
    st.session_state.logged_in = False
    st.session_state.my_class = ""
    st.session_state.selected_date = None
    st.rerun()


# ── 달력 홈 화면 ──────────────────────────────────────────────────────────────
st.title("📝 AI 상담일지")

# DB에서 데이터 로드
logs = fetch_logs(user_id)
schedules = fetch_schedules(user_id)

# 달력 이벤트 구성
events = []
for log in logs:
    date_str = log.get("created_at", "")[:10]
    category = log.get("category", "기타")
    name = log.get("student_name", "")
    events.append({
        "title": f"[{category}] {name}",
        "start": date_str,
        "backgroundColor": "#4a90e2",
        "borderColor": "#4a90e2",
    })

for sch in schedules:
    events.append({
        "title": f"(예정) {sch['student_name']}",
        "start": sch["scheduled_date"],
        "backgroundColor": "#f5a623",
        "borderColor": "#f5a623",
    })

# 달력 옵션
calendar_options = {
    "headerToolbar": {
        "left": "prev",
        "center": "title",
        "right": "next"
    },
    "initialView": "dayGridMonth",
    "locale": "ko",
    "timeZone": "local",
    "height": 650,
    "selectable": True,
    "dayMaxEvents": 3,
}

# 오늘 날짜 파란색 반투명 강조
custom_css = """
.fc-day-today {
    background-color: rgba(70, 130, 255, 0.15) !important;
}
"""

cal_result = calendar(
    events=events,
    options=calendar_options,
    custom_css=custom_css,
    key="home_calendar"
)

# 날짜 클릭 처리 — 라이브러리가 UTC 기준으로 반환하므로 KST(+9) 보정으로 1일 추가
if cal_result and cal_result.get("dateClick"):
    date_info = cal_result["dateClick"]
    clicked = date_info.get("dateStr") or date_info.get("date", "")
    if clicked:
        from datetime import date as dt_date, timedelta
        corrected = (dt_date.fromisoformat(clicked[:10]) + timedelta(days=1)).isoformat()
        st.session_state.selected_date = corrected

# ── 선택 날짜 상담 목록 ────────────────────────────────────────────────────────
if st.session_state.selected_date:
    sel_date = st.session_state.selected_date
    st.markdown("---")
    st.subheader(f"📅 {sel_date} 기록")

    day_logs = [l for l in logs if l.get("created_at", "")[:10] == sel_date]
    day_schedules = [s for s in schedules if s.get("scheduled_date") == sel_date]

    if day_logs:
        for log in day_logs:
            content = log.get("content", "")
            preview = content[:50] + ("..." if len(content) > 50 else "")
            st.info(f"**[{log.get('category')}] {log.get('student_name')}** — {preview}")

    if day_schedules:
        for sch in day_schedules:
            note = f" — {sch['note']}" if sch.get("note") else ""
            st.warning(f"**(예정) {sch['student_name']}**{note}")

    if not day_logs and not day_schedules:
        st.write("이 날짜의 기록이 없습니다.")

    if st.button("✍️ 이 날짜로 상담 기록하기"):
        st.session_state.record_date = sel_date
        st.switch_page("pages/1_record.py")

# ── 하단 버튼 ─────────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("✍️ 상담일지 작성", use_container_width=True):
        st.switch_page("pages/1_record.py")

with col2:
    if st.button("📅 상담 일정 입력", use_container_width=True):
        st.session_state.show_schedule_dialog = True

# 일정 입력 다이얼로그 호출
if st.session_state.show_schedule_dialog:
    schedule_dialog()
