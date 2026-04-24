import streamlit as st
from database import fetch_logs, update_log, delete_log
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="상담 이력 조회", layout="wide")

# --- [1. 알림 메시지 처리] ---
if "status_msg" in st.session_state:
    st.success(st.session_state.status_msg)
    del st.session_state.status_msg

# --- [2. 사이드바 설정] ---
st.sidebar.title("⚙️ 설정")
if "my_class" not in st.session_state: st.session_state.my_class = ""
st.session_state.my_class = st.sidebar.text_input("내 학급(우리반) 설정", value=st.session_state.my_class)

st.title("📂 상담 이력 조회")

# --- [3. 데이터 로드] ---
logs = fetch_logs()
if not logs:
    st.info("기록이 없습니다.");
    st.stop()

all_classes = sorted(list(set(log['grade_class'] for log in logs if log.get('grade_class'))))
all_categories = ["학업", "교우관계", "학교생활", "가정문제", "진로", "기타"]

# 💡 4. 학급 드롭다운 라벨 생성 로직 (디자인 통일)
class_display_map = {"전체": "전체"}
for c in all_classes:
    if c == st.session_state.my_class:
        class_display_map[f"⭐ 우리반 ({c})"] = c
    else:
        class_display_map[c] = c

class_options = list(class_display_map.keys())

# --- [5. 이동(Jump) 및 기본값 로직] ---
# 외부 이동(링크 버튼) 요청 처리
if "jump_to_class" in st.session_state:
    target = st.session_state.jump_to_class
    # 라벨들 중에서 실제 반 이름과 매칭되는 것을 찾아 선택합니다.
    for label, real_val in class_display_map.items():
        if real_val == target:
            st.session_state["sb_class"] = label
            break
    del st.session_state.jump_to_class
# 처음 접속 시 기본값 설정
elif "sb_class" not in st.session_state:
    if st.session_state.my_class:
        st.session_state["sb_class"] = f"⭐ 우리반 ({st.session_state.my_class})"
    else:
        st.session_state["sb_class"] = "전체"

# --- [6. 필터 레이아웃] ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    # 💡 이제 드롭다운에 "⭐ 우리반"이 예쁘게 뜹니다.
    selected_label = st.selectbox("🏫 학급 선택", class_options, key="sb_class")
    # 내부 계산을 위해 실제 반 이름 추출
    selected_class = class_display_map[selected_label]

with col_f2:
    selected_category = st.selectbox("🏷️ 카테고리 선택", ["전체"] + all_categories)

# 데이터 필터링
filtered_logs = [log for log in logs if
                 (selected_class == "전체" or log.get('grade_class') == selected_class) and
                 (selected_category == "전체" or log.get('category') == selected_category)]

# --- [7. 화면 분할] ---
col_list, col_detail = st.columns([1, 3])

with col_list:
    st.subheader("👥 학생 명렬")
    unique_students = sorted(list(set((log['student_name'], log['grade_class']) for log in filtered_logs)))

    if not unique_students:
        st.write("해당 학생 없음");
        target_student_info = None
    else:
        name_counts = Counter(name for name, cls in unique_students)
        display_names = [f"{name} ({cls})" if selected_class == "전체" and name_counts[name] > 1 else name for name, cls
                         in unique_students]

        if "jump_to_student" in st.session_state:
            if st.session_state.jump_to_student in display_names:
                st.session_state["radio_stu"] = st.session_state.jump_to_student
            del st.session_state.jump_to_student

        selected_label_stu = st.radio("학생 선택", display_names, key="radio_stu")

        if selected_label_stu in display_names:
            target_student_info = unique_students[display_names.index(selected_label_stu)]
        else:
            target_student_info = unique_students[0]

with col_detail:
    if target_student_info:
        t_name, t_class = target_student_info
        st.subheader(f"🔍 {t_name} ({t_class}) 학생의 상담 이력")
        stu_logs = [l for l in filtered_logs if l['student_name'] == t_name and l['grade_class'] == t_class]
        stu_logs.sort(key=lambda x: x['created_at'], reverse=True)

        for log in stu_logs:
            raw_date = log.get('created_at', '')
            try:
                dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                d_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                d_str = raw_date

            with st.expander(f"📅 {d_str} [{log.get('category', '기타')}]"):
                with st.popover("📝 기록 관리"):
                    u_name = st.text_input("이름 수정", value=log['student_name'], key=f"n_{log['id']}")
                    u_class = st.text_input("학급 수정", value=log['grade_class'], key=f"c_{log['id']}")
                    u_cat = st.selectbox("카테고리 수정", all_categories, index=all_categories.index(log['category']) if log[
                                                                                                                       'category'] in all_categories else 5,
                                         key=f"t_{log['id']}")
                    u_cont = st.text_area("내용 수정", value=log['content'], height=200, key=f"txt_{log['id']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("💾 저장", key=f"sv_{log['id']}"):
                            update_log(log['id'], u_class, u_name, u_cat, u_cont)
                            st.session_state.status_msg = f"✅ {u_name} 학생의 기록이 수정되었습니다.";
                            st.rerun()
                    with c2:
                        if st.button("🗑️ 삭제", key=f"dl_{log['id']}"):
                            delete_log(log['id']);
                            st.session_state.status_msg = f"🗑️ {t_name} 학생의 기록이 삭제되었습니다.";
                            st.rerun()

                if log.get('incident_id'):
                    related = [l for l in logs if l['incident_id'] == log['incident_id'] and not (
                                l['student_name'] == t_name and l['grade_class'] == t_class)]
                    if related:
                        st.write("---")
                        st.markdown("🔗 **연관된 학생:**")
                        r_unique = {(l['student_name'], l['grade_class']) for l in related}
                        cols = st.columns(len(r_unique) if len(r_unique) < 5 else 5)
                        for i, (rn, rc) in enumerate(r_unique):
                            if cols[i % 5].button(f"{rn}({rc})", key=f"lk_{log['id']}_{rn}"):
                                st.session_state.jump_to_class = rc
                                st.session_state.jump_to_student = rn if selected_class != "전체" else f"{rn} ({rc})"
                                st.rerun()

                st.write(f"**학급:** {log.get('grade_class')}")
                st.write("**내용:**")
                st.info(log.get('content'))