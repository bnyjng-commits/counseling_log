import streamlit as st
from supabase import create_client

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

# ── 로그인 전: 사이드바 완전 숨김 ──────────────────────────────────────────
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
                    st.session_state.logged_in = True  # 기존 pages 호환용
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

# ── 로그인 후: 사이드바 + 홈 화면 ──────────────────────────────────────────
st.sidebar.markdown(f"👤 **{st.session_state.user.email}**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 로그아웃"):
    st.session_state.user = None
    st.session_state.logged_in = False
    st.rerun()

st.title("📝 AI 상담일지")
st.write("### 환영합니다, 선생님! 상담 업무를 시작해 보세요.")
st.info("왼쪽 사이드바에서 메뉴를 선택하여 상담을 기록하거나 조회하세요.")
