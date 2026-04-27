import streamlit as st
from supabase import create_client, Client
import anthropic
import json
import datetime # 💡 추가: 파이썬 기본 시간 도구
import pytz     # 💡 추가: 세계 시간대 변환 도구


# 1. 보안 설정값 가져오기 (secrets.toml 기반)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# --- [저장 함수] ---
def save_log(grade_class, student_name, content, category, incident_id=None):
    supabase = get_supabase()

    # 💡 한국 시간(KST)으로 현재 시간 구하기
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.datetime.now(kst)

    data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "content": content,
        "category": category,
        "incident_id": incident_id,
        "created_at": now_kst.isoformat()  # 💡 명시적으로 한국 시간 저장
    }
    return supabase.table("counseling_logs").insert(data).execute()


# --- [수정 함수] ---
def update_log(log_id, grade_class, student_name, category, content):
    supabase = get_supabase()
    data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "category": category,
        "content": content
    }
    return supabase.table("counseling_logs").update(data).eq("id", log_id).execute()


# --- [삭제 함수] ---
def delete_log(log_id):
    supabase = get_supabase()
    return supabase.table("counseling_logs").delete().eq("id", log_id).execute()


# --- [불러오기 함수] ---
def fetch_logs():
    supabase = get_supabase()
    response = supabase.table("counseling_logs").select("*").order("created_at", desc=True).execute()
    return response.data


# --- [AI 카테고리 분석 함수] ---
def analyze_category_with_ai(content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"다음 상담 내용을 읽고 [학업, 교우관계, 학교생활, 가정문제, 진로, 기타] 중 하나를 골라 단어만 출력하세요.\n\n상담 내용: {content}"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}]
    )
    result = message.content[0].text.strip()
    allowed = ["학업", "교우관계", "학교생활", "가정문제", "진로", "기타"]
    for cat in allowed:
        if cat in result: return cat
    return "기타"


# --- [💡 핵심: 클로드 소넷 기반 정보 추출 함수] ---
def extract_info_from_text(transcript):
    if not transcript or len(transcript.strip()) < 2:
        return {"class": "", "name": "", "content": ""}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""
    당신은 학교 상담 기록 비서입니다. 입력된 문장을 정교하게 분석하여 [학급, 이름, 상담내용]으로 분류하세요.

    입력 문장: "{transcript}"

    [추출 규칙]
    1. class: 'n학년 n반' 혹은 'n-n'이 보이면 'n-n' 형식으로 추출 (예: 3학년 7반 -> 3-7). 없거나 '우리반'이면 빈칸 "".
    2. name: 문장에서 학생의 이름을 찾아 추출.
    3. content: 학급과 이름을 제외한 실제 상담 상황 내용만 정리.

    반드시 아래 JSON 형식으로만 답변하세요. 다른 설명은 절대 하지 마세요.
    {{"class": "학급", "name": "이름", "content": "내용"}}
    """

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        # JSON 결과 파싱
        return json.loads(message.content[0].text.strip())
    except Exception as e:
        # 실패 시 원본 텍스트를 내용에 담아 반환
        return {"class": "", "name": "추출실패", "content": transcript}
