import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="AI 상담일지",
    page_icon="📝",
    layout="wide"
)

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