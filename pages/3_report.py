import streamlit as st
import streamlit.components.v1 as components
import json
from database import fetch_logs, get_user_settings, generate_report_with_ai
from datetime import datetime, date
from zoneinfo import ZoneInfo

# 🔒 검문소 설치
if "user" not in st.session_state or not st.session_state.user:
    st.warning("먼저 로그인해 주세요.")
    st.stop()
user_id = st.session_state.user.id

st.set_page_config(page_title="생활기록부 문구 생성", layout="wide")
st.title("📝 생활기록부 문구 생성")

# 우리반 설정 (DB에서 로드)
if "my_class" not in st.session_state:
    settings = get_user_settings(user_id)
    st.session_state.my_class = settings.get("my_class", "") if settings else ""

# 전체 로그 로드
logs = fetch_logs(user_id)
if not logs:
    st.info("저장된 상담 기록이 없습니다.")
    st.stop()

all_classes = sorted(set(log['grade_class'] for log in logs if log.get('grade_class')))
if not all_classes:
    st.info("저장된 학급 정보가 없습니다.")
    st.stop()

# --- [1. 학급 + 학생 선택] ---
col1, col2 = st.columns(2)
with col1:
    default_idx = all_classes.index(st.session_state.my_class) if st.session_state.my_class in all_classes else 0
    selected_class = st.selectbox("🏫 학급 선택", all_classes, index=default_idx)

students = sorted(set(
    log['student_name'] for log in logs
    if log.get('grade_class') == selected_class and log.get('student_name')
))

with col2:
    if not students:
        st.info("해당 학급의 상담 기록이 없습니다.")
        st.stop()
    selected_student = st.selectbox("👤 학생 선택", students)

# --- [2. 날짜 범위 선택] ---
today = datetime.now(ZoneInfo("Asia/Seoul")).date()
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input("📅 시작 날짜", value=date(today.year, 3, 1))
with col_d2:
    end_date = st.date_input("📅 종료 날짜", value=today)

# --- [3. 해당 학생 기록 필터링] ---
def get_log_date(log):
    try:
        return datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).date()
    except Exception:
        return None

student_logs = [
    log for log in logs
    if log.get('student_name') == selected_student and log.get('grade_class') == selected_class
]

filtered = []
for log in student_logs:
    d = get_log_date(log)
    if d and start_date <= d <= end_date:
        filtered.append(log)
filtered.sort(key=lambda x: x['created_at'], reverse=True)

if not filtered:
    st.warning("선택한 기간에 해당 학생의 상담 기록이 없습니다.")
    st.stop()

# --- [4. 체크박스로 기록 선택] ---
st.subheader(f"📋 포함할 상담 기록 선택 — {selected_student}")
st.caption(f"총 {len(filtered)}건 · 생성에 포함할 기록을 선택하세요.")

selected_ids = set()
for log in filtered:
    d = get_log_date(log)
    date_str = d.strftime('%Y-%m-%d') if d else ''
    preview = log.get('content', '')[:50].replace('\n', ' ')
    label = f"[{log.get('category', '기타')}] {date_str}  {preview}..."
    if st.checkbox(label, value=True, key=f"chk_{log['id']}"):
        selected_ids.add(log['id'])

chosen = [log for log in filtered if log['id'] in selected_ids]

st.markdown("---")

# 세션 상태 초기화 — 문구 버전(새로 생성 시 text_area 리셋용)
if "report_edit_version" not in st.session_state:
    st.session_state.report_edit_version = 0

# --- [5. 생성 버튼] ---
if st.button("✨ 생활기록부 문구 생성", type="primary", disabled=not chosen):
    with st.spinner("AI가 생기부 문구를 작성 중..."):
        try:
            result = generate_report_with_ai(selected_student, chosen)
            st.session_state.report_result = result
            st.session_state.report_for = selected_student
            st.session_state.report_edit_version += 1  # text_area 리셋 트리거
        except Exception as e:
            st.error(f"생성 오류: {e}")

# --- [6. 결과 출력 (수동 편집 + 복사)] ---
if st.session_state.get("report_result") and st.session_state.get("report_for") == selected_student:
    st.subheader("📄 생성된 생기부 문구")

    # 버전 키로 새 생성 시 text_area 초기화
    edit_key = f"report_edit_{st.session_state.report_edit_version}"
    edited = st.text_area(
        "생성된 문구 (직접 수정 가능)",
        value=st.session_state.report_result,
        height=150,
        key=edit_key
    )
    st.session_state.report_result = edited  # 수정 내용 세션에 반영

    # 클립보드 복사 버튼 (JS — Streamlit Cloud 호환)
    copy_js = json.dumps(edited)
    components.html(f"""
    <script>
    function copyText() {{
        var text = {copy_js};
        navigator.clipboard.writeText(text).then(function() {{
            document.getElementById('cbtn').innerText = '✅ 복사됨!';
            setTimeout(function() {{ document.getElementById('cbtn').innerText = '📋 클립보드에 복사'; }}, 2000);
        }}).catch(function() {{
            var ta = document.createElement('textarea');
            ta.value = text; document.body.appendChild(ta);
            ta.select(); document.execCommand('copy');
            document.body.removeChild(ta);
            document.getElementById('cbtn').innerText = '✅ 복사됨!';
            setTimeout(function() {{ document.getElementById('cbtn').innerText = '📋 클립보드에 복사'; }}, 2000);
        }});
    }}
    </script>
    <button id="cbtn" onclick="copyText()" style="
        background:#0068C9;color:white;border:none;
        padding:0.4rem 1.2rem;border-radius:6px;
        cursor:pointer;font-size:0.9rem;font-weight:bold;
    ">📋 클립보드에 복사</button>
    """, height=45)

    if st.button("🔄 다시 생성"):
        del st.session_state.report_result
        st.rerun()
