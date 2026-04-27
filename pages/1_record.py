import streamlit as st
import uuid
import time
from database import save_log, fetch_logs, analyze_category_with_ai, extract_info_from_text, analyze_image_with_ai
from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="상담 기록하기", layout="wide")

# --- [0. CSS 마법: 3개 버튼 사이즈 완벽 통일] ---
# 높이 3.5rem -> 2.5rem으로 날렵하게 조정 완료
st.markdown("""
    <style>
    /* 1. 상단 입력 도구 줄의 전체 높이와 수직 정렬 설정 */
    div.row-widget.stHorizontal {
        align-items: center;
        gap: 1.5rem;
    }
    /* 2. 각 버튼이 들어가는 칸(Column)의 폭을 고정하지 않고 유연하게 설정 */
    div.row-widget.stHorizontal > div {
        flex: 1;
        width: auto !important;
        min-width: 0;
    }
    /* 3. 스트림릿 기본 버튼과 사진 업로드 버튼 스타일 강제 통일 (작게 설정) */
    div.stButton > button, div.stFileUploader > label > div[role="button"] {
        width: 12rem !important; /* 고정 폭 (Small size) */
        height: 2.5rem !important; /* 🌟 높이 조정 완료 */
        display: flex;
        justify-content: center;
        align-items: center;
        font-weight: bold;
        font-size: 0.95rem; /* 글씨 크기 살짝 작게 */
        border-radius: 12px !important;
        border: 1px solid #d1d5db !important;
        background-color: white !important;
        color: #31333f !important;
    }
    /* 4. 음성 인식 위젯 내부의 버튼 스타일을 고정 폭에 맞춥니다. */
    div.row-widget.stHorizontal > div > iframe {
        width: 12rem !important;
        height: 2.5rem !important; /* 🌟 높이 조정 완료 */
        border: none !important;
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
# 🌟 추가: 사진 업로더 노출 상태 변수
if "show_uploader" not in st.session_state: st.session_state.show_uploader = False

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

# --- [4. 상단 입력 도구 3종 세트 (나란히 배치)] ---
st.subheader("🎤 말로 하거나 📷 사진 촬영/업로드")

col_stt, col_cam, col_upload = st.columns(3)

with col_stt:
    stt_key = f"stt_{st.session_state.stt_key_idx}"
    # 녹음 버튼
    text_from_voice = speech_to_text(
        language='ko', 
        start_prompt="🎤 상담 내용 음성 녹음 시작",
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

with col_cam:
    # 사진 촬영 버튼
    if st.button("📷 카메라 켜기/끄기", use_container_width=False, key="btn_cam_tool"):
        # 🌟 카메라 켜고 꺼짐을 토글하면서, 업로더는 끕니다.
        st.session_state.show_camera = not st.session_state.show_camera
        st.session_state.show_uploader = False # 업로더 무조건 끔

with col_upload:
    # 🌟 [수정된 버튼 로직: 조건부 노출 토글]
    if st.button("📷 상담록 사진 업로드", use_container_width=False, key="btn_upload_tool"):
        # 🌟 업로더 켜고 꺼짐을 토글하면서, 카메라는 끕니다.
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.session_state.show_camera = False # 카메라 무조건 끔

# --- [4-1. 카메라 위젯 (조건부 노출)] ---
if st.session_state.show_camera:
    cam_key = f"cam_{st.session_state.form_reset_idx}_{st.session_state.stt_key_idx}"
    captured_image = st.camera_input("메모를 찍어주세요", key=cam_key)
    if captured_image:
        with st.spinner("사진 분석 중..."):
            img_extracted = analyze_image_with_ai(captured_image)
            st.session_state.temp_name = img_extracted.get("name", "")
            st.session_state.temp_content = img_extracted.get("content", "")
            st.session_state.show_camera = False # 촬영 후 닫기
            st.rerun()

# --- [4-2. 사진 파일 업로더 (조건부 노출)] ---
# 🌟 [핵심 수정: show_uploader 상태에 따라 노출]
if st.session_state.show_uploader:
    st.markdown("---")
    st.subheader("📁 상담록 사진 파일 업로드")
    
    # key에 form_reset_idx를 넣어 매번 새로운 위젯을 생성 (루프 방지)
    current_uploader_key = f"uploader_{st.session_state.form_reset_idx}_{st.session_state.stt_key_idx}"
    uploaded_file = st.file_uploader(
        "상담록 사진을 업로드하세요 (jpg, jpeg, png)", 
        type=["jpg", "jpeg", "png"], 
        key=current_uploader_key,
        label_visibility="collapsed" # 상단 subheader와 겹치므로 라벨 숨김
    )
    
    if uploaded_file is not None:
        with st.spinner("소넷 비서가 업로드한 사진을 분석 중입니다..."):
            try:
                # 1. 이미지 분석 함수 호출 (상단에서 import되어야 함)
                img_extracted = analyze_image_with_ai(uploaded_file)

                # 2. 분석된 내용을 세션 상태에 저장
                st.session_state.temp_name = img_extracted.get("name", "")
                st.session_state.temp_content = img_extracted.get("content", "")
                
                # 3. 학급 자동 매칭 로직 (기존 로직 재사용)
                e_class = img_extracted.get("class", "").replace(" ", "")
                if e_class:
                    if e_class == st.session_state.my_class:
                        target_label = f"⭐ 우리반 ({e_class})"
                    else:
                        target_label = next((opt for opt in class_options if e_class in opt), "직접 입력...")
                    st.session_state[f"sb_class_{st.session_state.form_reset_idx}"] = target_label
                    if target_label == "직접 입력...":
                        st.session_state["new_class_input"] = e_class

                st.success("✅ 사진 업로드 및 분석 완료! 아래 내용 입력창을 확인하세요.")
                
                # 🌟 [핵심] 분석이 완료되면 업로더를 닫고 새로고침
                st.session_state.show_uploader = False
                st.session_state.stt_key_idx += 1 # fresh widgets
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"사진 파일 분석 중 오류 발생: {e}")

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
                st.session_state.show_camera = False # reset tool mode
                st.session_state.show_uploader = False # 🌟 reset tool mode

                st.balloons()
                st.success("✅ 저장이 완료되었습니다!")
                time.sleep(2)
                st.rerun()

            except Exception as e:
                st.error(f"저장 오류: {e}")
    else:
        st.warning("이름과 내용을 입력해 주세요.")
