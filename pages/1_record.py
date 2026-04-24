import streamlit as st
import uuid
from database import save_log, fetch_logs, analyze_category_with_ai, extract_info_from_text
from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="상담 기록하기", layout="wide")

# --- [1. 세션 상태 관리] ---
if "temp_name" not in st.session_state: st.session_state.temp_name = ""
if "temp_content" not in st.session_state: st.session_state.temp_content = ""
if "last_processed_text" not in st.session_state: st.session_state.last_processed_text = ""

# --- [2. 사이드바 설정] ---
st.sidebar.title("⚙️ 설정")
if "my_class" not in st.session_state: st.session_state.my_class = ""
st.session_state.my_class = st.sidebar.text_input("내 학급(우리반) 설정", value=st.session_state.my_class)

st.title("✍️ 상담 내용 기록")

# --- [3. 학급 목록 미리 준비] ---
# (드롭다운을 그리기 전에 목록이 있어야 AI 결과와 대조해볼 수 있습니다.)
logs = fetch_logs()
existing_classes = sorted(list(set(log['grade_class'] for log in logs if log.get('grade_class')))) if logs else []

class_options = []
if st.session_state.my_class:
    my_class_label = f"⭐ 우리반 ({st.session_state.my_class})"
    class_options = [my_class_label, "직접 입력..."] + [c for c in existing_classes if c != st.session_state.my_class]
else:
    class_options = ["기존 목록에서 선택", "직접 입력..."] + existing_classes

# --- [4. 🎤 음성 인식 및 분석] ---
st.subheader("🎤 말로 입력하기")
text_from_voice = speech_to_text(language='ko', start_prompt="🎤 녹음 시작하기", stop_prompt="🛑 녹음 끝내기", key='STT_final_v4')

if text_from_voice and text_from_voice != st.session_state.last_processed_text:
    with st.spinner("소넷 비서가 정보를 분류 중입니다..."):
        try:
            extracted = extract_info_from_text(text_from_voice)
            st.session_state.temp_name = extracted.get("name", "")
            st.session_state.temp_content = extracted.get("content", "")

            # 💡 [학급 자동 매칭 로직 강화]
            e_class = extracted.get("class", "").replace(" ", "")  # 공백 제거 (예: 3-7)

            if e_class:
                found_match = False
                # 1. 우리반인지 확인
                if e_class == st.session_state.my_class:
                    st.session_state["sb_class_record"] = f"⭐ 우리반 ({e_class})"
                    found_match = True
                # 2. 기존 반 목록에 있는지 확인
                else:
                    for option in class_options:
                        if e_class == option:
                            st.session_state["sb_class_record"] = option
                            found_match = True
                            break

                # 3. 목록에 없는 새로운 반이라면 '직접 입력'으로 보내고 값 설정
                if not found_match:
                    st.session_state["sb_class_record"] = "직접 입력..."
                    st.session_state["new_class_input"] = e_class  # 아래 직접입력 칸을 위해 저장

            st.session_state.last_processed_text = text_from_voice
            st.success(f"✅ 분석 완료! ({st.session_state.temp_name} / {e_class if e_class else '반 미지정'})")
            st.rerun()
        except Exception as e:
            st.error(f"분석 실패: {e}")

st.markdown("---")

# --- [5. 입력 폼 레이아웃] ---
col_m1, col_m2 = st.columns(2)
with col_m1:
    record_mode = st.radio("기록 모드", ["개별 상담", "👥 공동 사건"], horizontal=True)

with col_m2:
    # 드롭다운
    selected_class_label = st.selectbox("🏫 학급 선택", class_options, key="sb_class_record")

# 직접 입력 칸 처리
grade_class = ""
if selected_class_label == "직접 입력...":
    # AI가 새로운 반을 찾았다면 그 값을 기본값으로 넣어줌
    default_new = st.session_state.get("new_class_input", "")
    grade_class = st.text_input("새 학급 이름", value=default_new)
elif selected_class_label.startswith("⭐ 우리반"):
    grade_class = st.session_state.my_class
else:
    grade_class = selected_class_label if selected_class_label != "기존 목록에서 선택" else ""

with st.form("counseling_form", clear_on_submit=True):
    student_names = st.text_input("학생 이름", value=st.session_state.temp_name)
    content = st.text_area("상담 상세 내용", value=st.session_state.temp_content, height=300)
    submit_button = st.form_submit_button("💾 상담 일지 저장하기")

if submit_button:
    final_class = grade_class if grade_class else st.session_state.my_class
    if not final_class:
        st.warning("학급을 설정해 주세요.")
    elif student_names and content:
        with st.spinner("저장 중..."):
            ai_category = analyze_category_with_ai(content)
            name_list = [n.strip() for n in student_names.split(",") if n.strip()]
            incident_id = str(uuid.uuid4())[:8] if len(name_list) > 1 else None

            for entry in name_list:
                if "(" in entry and ")" in entry:
                    actual_name = entry.split("(")[0].strip()
                    actual_class = entry.split("(")[1].split(")")[0].strip()
                else:
                    actual_name = entry
                    actual_class = final_class
                save_log(actual_class, actual_name, content, ai_category, incident_id)

            st.balloons()
            st.success("✅ 저장 완료!")
            # 초기화
            st.session_state.temp_name = ""
            st.session_state.temp_content = ""
            st.session_state.last_processed_text = ""
            if "new_class_input" in st.session_state: del st.session_state.new_class_input
            st.rerun()
    else:
        st.warning("이름과 내용을 입력해 주세요.")