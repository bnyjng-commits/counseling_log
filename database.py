import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import json
import datetime
import pytz
import io
from PIL import Image

# 보안 설정값
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# ── Supabase에서 실행해야 할 테이블 생성 SQL (참고용) ──────────────────────
#
# -- scheduled_counseling 테이블
# create table scheduled_counseling (
#   id uuid primary key default gen_random_uuid(),
#   user_id uuid references auth.users,
#   scheduled_date date not null,
#   student_name text not null,
#   note text,
#   created_at timestamptz default now()
# );
#
# -- user_settings 테이블
# create table user_settings (
#   id uuid primary key default gen_random_uuid(),
#   user_id uuid references auth.users unique,
#   my_class text,
#   created_at timestamptz default now(),
#   updated_at timestamptz default now()
# );
#
# -- counseling_logs 에 user_id 컬럼 추가 (기존 테이블)
# alter table counseling_logs add column if not exists user_id uuid references auth.users;
# ──────────────────────────────────────────────────────────────────────────────


def get_supabase() -> Client:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # RLS가 올바르게 동작하도록 로그인 사용자의 JWT 토큰을 클라이언트에 설정
    session = st.session_state.get("session")
    if session:
        try:
            client.auth.set_session(
                access_token=session.access_token,
                refresh_token=session.refresh_token
            )
        except Exception:
            pass
    return client


# --- [저장 함수: 한국 시간 강제 지정] ---
def save_log(grade_class, student_name, content, category, incident_id=None, user_id=None, created_at=None):
    supabase = get_supabase()

    kst = pytz.timezone('Asia/Seoul')
    if created_at is not None:
        now_kst = created_at.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        now_kst = datetime.datetime.now(kst).strftime('%Y-%m-%dT%H:%M:%S')

    data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "content": content,
        "category": category,
        "incident_id": incident_id,
        "created_at": now_kst,
        "user_id": user_id
    }
    return supabase.table("counseling_logs").insert(data).execute()


# --- [조회 함수: 해당 유저 데이터만 반환] ---
def fetch_logs(user_id):
    supabase = get_supabase()
    return (
        supabase.table("counseling_logs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


# --- [수정 함수] ---
def update_log(log_id, grade_class, student_name, category, content):
    supabase = get_supabase()
    updated_data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "category": category,
        "content": content
    }
    return supabase.table("counseling_logs").update(updated_data).eq("id", log_id).execute()


# --- [삭제 함수] ---
def delete_log(log_id):
    supabase = get_supabase()
    return supabase.table("counseling_logs").delete().eq("id", log_id).execute()


# ── user_settings 함수 ────────────────────────────────────────────────────────

# --- [우리반 설정 불러오기] ---
def get_user_settings(user_id):
    supabase = get_supabase()
    try:
        result = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception:
        return None


# --- [우리반 설정 저장 (없으면 insert, 있으면 update)] ---
def save_user_settings(user_id, my_class):
    supabase = get_supabase()
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.datetime.now(kst).strftime('%Y-%m-%dT%H:%M:%S')

    data = {
        "user_id": user_id,
        "my_class": my_class,
        "updated_at": now_kst
    }
    return supabase.table("user_settings").upsert(data, on_conflict="user_id").execute()


# ── scheduled_counseling 함수 ─────────────────────────────────────────────────

# --- [예정 상담 일정 저장] ---
def save_schedule(user_id, scheduled_date, student_name, note=None):
    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "scheduled_date": str(scheduled_date),
        "student_name": student_name,
        "note": note
    }
    return supabase.table("scheduled_counseling").insert(data).execute()


# --- [예정 상담 일정 전체 조회] ---
def fetch_schedules(user_id):
    supabase = get_supabase()
    return supabase.table("scheduled_counseling").select("*").eq("user_id", user_id).order("scheduled_date").execute().data


# --- [예정 상담 일정 삭제] ---
def delete_schedule(schedule_id):
    supabase = get_supabase()
    return supabase.table("scheduled_counseling").delete().eq("id", schedule_id).execute()


# ── AI 분석 함수 ──────────────────────────────────────────────────────────────

# --- [AI 생성 함수: 생활기록부 문구 생성] ---
def generate_report_with_ai(student_name, selected_logs):
    model = genai.GenerativeModel('gemini-1.5-flash')
    logs_text = "\n".join([
        f"- [{log.get('category', '기타')}] {log.get('content', '')}"
        for log in selected_logs
    ])
    prompt = f"""다음은 {student_name} 학생의 상담 기록입니다. 이를 바탕으로 중학교 학교생활기록부 행동특성 및 종합의견 문구를 작성해주세요.

상담 기록:
{logs_text}

작성 규칙:
- 생활기록부 문체 사용: "~하였음", "~을 보임", "~하는 모습이 관찰됨", "~에 노력하는 태도를 보임" 등
- 학생의 성장 가능성과 긍정적인 면 중심으로 작성
- 3~5문장, 200자 내외
- 학생 이름("{student_name}")을 문두에 포함
- 부정적 표현은 긍정적으로 순화하여 작성
- 다른 설명 없이 문구만 출력"""

    response = model.generate_content(prompt)
    return response.text.strip()


# --- [AI 분석 함수: 텍스트 카테고리 분류] ---
def analyze_category_with_ai(content):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"다음 상담 내용을 보고 [행동, 정서, 학업, 가정, 진로, 기타] 중 하나로 분류해줘. 행동/정서/학업/가정/진로 중 어디에도 해당하지 않으면 기타로 분류해. 단어만 답해:\n\n{content}"
    response = model.generate_content(prompt)
    return response.text.strip()


# --- [AI 분석 함수: 음성/텍스트 정보 추출] ---
def extract_info_from_text(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""다음 문장에서 학생 이름, 반, 상담 내용을 추출해서 JSON으로 답해.
    형식: {{"name": "이름", "class": "반", "content": "내용"}}
    문장: {text}"""

    response = model.generate_content(prompt)
    raw_text = response.text
    try:
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_text = raw_text[start_idx:end_idx]
            return json.loads(json_text)
        else:
            return {"name": "", "class": "", "content": raw_text}
    except Exception:
        return {"name": "", "class": "", "content": "정보 추출에 실패했습니다. 직접 입력해 주세요."}


# --- [AI 분석 함수: 사진(OCR) 정보 추출] ---
def analyze_image_with_ai(image_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    image = Image.open(io.BytesIO(image_file.getvalue()))
    prompt = "이 사진의 손글씨를 읽고 { \"name\": \"학생이름\", \"class\": \"학급\", \"content\": \"내용\" } 형식의 JSON으로만 답하세요. 다른 말은 하지 마세요."

    response = model.generate_content([prompt, image])
    raw_text = response.text
    try:
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            json_text = raw_text[start_idx:end_idx]
            return json.loads(json_text)
        else:
            return {"name": "", "class": "", "content": "내용을 읽지 못했습니다."}
    except Exception:
        return {"name": "", "class": "", "content": "사진 분석 중 오류가 발생했습니다."}
