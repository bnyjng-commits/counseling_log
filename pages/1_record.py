import streamlit as st
import uuid
import time
from database import save_log, fetch_logs, analyze_category_with_ai, extract_info_from_text, analyze_image_with_ai
from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="상담 기록하기", layout="wide")
st.markdown("""
    <style>
    /* 모든 버튼(음성 녹음 버튼 포함)을 컨테이너 너비에 맞게 100%로 설정 */
    div.stButton > button {
        width: 100% !important;
        height: 3rem !important; /* 높이도 똑같이 맞춤 */
    }
    /* 음성 녹음 위젯 내부의 버튼 스타일 강제 조정 */
    iframe {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- [1. 세션 상태 관리] ---
if "temp_name" not in st.session_state: st.session_state.temp_name = ""
if "temp_content" not in st.session_state: st.session_state.temp_content = ""
if "last_processed_text" not in st.session_state: st.session_state.last_processed_text = ""
if "stt_key_idx" not in st.session_state: st.session_state.stt_key_idx = 0
if "form_reset_idx" not in st.session_state: st.session_state.form_reset_idx = 0
if "show_camera" not in st.session_state: st.session_state.show_camera = False

# --- [2. 사이드바 설정] ---
st.sidebar.title("⚙️ 설정")
if "my_class" not in st.session_state: st.session_state.my_class = ""
st.session_state.my_class = st.sidebar.text_input("내 학급(우리반) 설정", value=st.session_state.my_class)

st.title("✍️ 상담 내용 기록")

# --- [3. 학급 목록 준비] ---
logs = fetch_logs()
existing_classes = sorted(list(set(log['grade_class'] for log in logs if log.get('grade_class')))) if logs else []
class_options = []
if st.session_state.my_class:
    my_class_label = f"⭐ 우리반 ({st.session_state.my_class})"
    class_options = [my_class_label, "직접 입력..."] + [c for c in existing_classes if c != st.session_state.my_class]
else:
    class_options = ["기존 목록에서 선택", "직접 입력..."] + existing_classes

# --- [4. 상단 입력 도구 (음성 & 사진) 섹션 수정] ---
st.subheader("🎤 말로 하거나 📷 사진 찍거나")

# 🌟 col_stt와 col_ocr의 비율을 1:1로 정확히 나눕니다.
col_stt, col_ocr = st.columns(2)

with col_stt:
    stt_key = f"stt_{st.session_state.stt_key_idx}"
    # 💡 녹음 버튼 - 글자 수를 비슷하게 맞추면 더 예쁩니다.
    text_from_voice = speech_to_text(
        language='ko',
        start_prompt="🎤 상담 내용 음성 녹음 시작",  # 글자 길이를 비슷하게 조정
        stop_prompt="🛑 녹음 완료 및 분석하기",
        key=stt_key
    )

    if text_from_voice and text_from_voice != st.session_state.last_processed_text:
        with st.spinner("소넷 비서가 분석 중..."):
            extracted = extract_info_from_text(text_from_voice)
            st.session_state.temp_name = extracted.get("name", "")
            st.session_state.temp_content = extracted.get("content", "")
            st.session_state.last_processed_text = text_from_voice
            st.rerun()

with col_ocr:
    # 🌟 use_container_width=True를 사용하여 칸에 꽉 차게 만듭니다.
    if st.button("📷 사진촬영모드 켜기/끄기", use_container_width=True):
        st.session_state.show_camera = not st.session_state.show_camera

# 카메라 위젯
if st.session_state.show_camera:
    cam_key = f"cam_{st.session_state.form_reset_idx}_{st.session_state.stt_key_idx}"
    captured_image = st.camera_input("메모를 찍어주세요", key=cam_key)
    if captured_image:
        with st.spinner("사진 분석 중..."):
            img_extracted = analyze_image_with_ai(captured_image)
            st.session_state.temp_name = img_extracted.get("name", "")
            st.session_state.temp_content = img_extracted.get("content", "")
            st.session_state.show_camera = False  # 촬영 후 닫기
            st.rerun()

st.markdown("---")

# --- [5. 입력 폼 레이아웃] ---
current_sb_key = f"sb_class_{st.session_state.form_reset_idx}"
selected_class_label = st.selectbox("🏫 학급 선택", class_options, key=current_sb_key)

grade_class = ""
if selected_class_label == "직접 입력...":
    grade_class = st.text_input("새 학급 이름", value=st.session_state.get("new_class_input", ""))
elif selected_class_label.startswith("⭐ 우리반"):
    grade_class = st.session_state.my_class
else:
    grade_class = selected_class_label if selected_class_label != "기존 목록에서 선택" else ""

with st.form("counseling_form", clear_on_submit=True):
    student_names = st.text_input("학생 이름", value=st.session_state.temp_name)
    content = st.text_area("상담 상세 내용", value=st.session_state.temp_content, height=300)
    submit_button = st.form_submit_button("💾 상담 일지 저장하기")

# --- [6. 저장 실행 로직] ---
if submit_button:
    final_class = grade_class if grade_class else st.session_state.my_class
    if not final_class:
        st.warning("학급을 설정해 주세요.")
    elif student_names and content:
        with st.spinner("저장 중..."):
            try:
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

                # 초기화 마법
                st.session_state.temp_name = ""
                st.session_state.temp_content = ""
                st.session_state.last_processed_text = ""
                st.session_state.stt_key_idx += 1
                st.session_state.form_reset_idx += 1

                st.balloons()
                st.success("✅ 저장이 완료되었습니다!")
                time.sleep(2)
                st.rerun()

            except Exception as e:
                st.error(f"저장 오류: {e}")
    else:
        st.warning("이름과 내용을 입력해 주세요.")
