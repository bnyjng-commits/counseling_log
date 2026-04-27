import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="AI 상담일지",
    page_icon="📝",
    layout="wide"
)
# 1️⃣ 가장 먼저: 페이지 설정 (항상 1순위입니다)
st.set_page_config(page_title="선생님용 상담 비서", layout="centered")

# 2️⃣ 세션 상태 초기화: 로그인 배지 발급 준비
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 3️⃣ 로그인 로직
if not st.session_state.logged_in:
    st.title("🛡️ 상담 관리 시스템 접속")
    password_input = st.text_input("관리자 비밀번호를 입력하세요", type="password")

    if st.button("접속하기"):
        # Secrets에서 비번 가져오기 (없으면 '1234'를 기본값으로 사용)
        correct_password = st.secrets.get("ADMIN_PASSWORD", "1234")

        if password_input == correct_password:
            st.session_state.logged_in = True
            st.success("인증 성공!")
            st.rerun()  # 화면을 새로고침해서 메뉴를 활성화함
        else:
            st.error("비밀번호가 틀렸습니다.")

    # 로그인 안 되었으면 여기서 코드 실행 중단 (옆문 차단과 동일한 원리)
    st.stop()
    
# 메인 화면 제목
st.title("📝 나만의 스마트 AI 상담일지")

st.info("왼쪽 사이드바에서 메뉴를 선택하여 상담을 기록하거나 조회하세요.")

# 간단한 보안 장치 (나중에 더 강화할 수 있어요)
password = st.sidebar.text_input("관리자 비밀번호", type="password")

if password == "1234": # 선생님만의 비밀번호로 바꾸세요
    st.sidebar.success("인증되었습니다.")
    st.write("### 환영합니다, 선생님! 상담 업무를 시작해 보세요.")
else:
    st.sidebar.warning("비밀번호를 입력해주세요.")
    st.stop() # 비밀번호가 틀리면 여기서 프로그램 멈춤
