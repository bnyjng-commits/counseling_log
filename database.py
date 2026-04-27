import streamlit as st
from supabase import create_client, Client
import anthropic
import json
import datetime
import pytz
import base64

# 보안 설정값
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# --- [저장 함수: 한국 시간 강제 지정] ---
def save_log(grade_class, student_name, content, category, incident_id=None):
    supabase = get_supabase()

    # 한국 시간(KST) 구하기
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.datetime.now(kst).strftime('%Y-%m-%dT%H:%M:%S')

    data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "content": content,
        "category": category,
        "incident_id": incident_id,
        "created_at": now_kst
    }
    return supabase.table("counseling_logs").insert(data).execute()


def fetch_logs():
    supabase = get_supabase()
    return supabase.table("counseling_logs").select("*").order("created_at", desc=True).execute().data


# --- [AI 분석 함수: 텍스트 카테고리 분류] ---
def analyze_category_with_ai(content):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"다음 상담 내용을 보고 [행동, 정서, 학업, 가정] 중 하나로 분류해줘. 단어만 답해:\n\n{content}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


# --- [AI 분석 함수: 음성/텍스트 정보 추출] ---
def extract_info_from_text(text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""다음 문장에서 학생 이름, 반, 상담 내용을 추출해서 JSON으로 답해. 
    형식: {{"name": "이름", "class": "반", "content": "내용"}}
    문장: {text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.content[0].text)


# --- [AI 분석 함수: 사진(OCR) 정보 추출] ---
def analyze_image_with_ai(image_file):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    base64_image = base64.b64encode(image_file.getvalue()).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "이 사진의 손글씨를 읽고 { \"name\": \"학생이름\", \"class\": \"학급\", \"content\": \"내용\" } 형식의 JSON으로만 답하세요. 다른 말은 하지 마세요."
                    }
                ],
            }
        ],
    )

    try:
        raw_text = response.content[0].text
        # JSON 문자열만 추출하는 안전장치
        json_text = raw_text.split('{', 1)[-1].rsplit('}', 1)[0]
        return json.loads('{' + json_text + '}')
    except:
        return {"name": "", "class": "", "content": "이미지 분석에 실패했습니다."}


# 1. 기존 기록 수정 함수
# --- [조회 화면의 요구사항에 맞춰 5개의 인자를 받는 함수로 수정] ---
def update_log(log_id, grade_class, student_name, category, content):
    supabase = get_supabase()

    # 5개의 재료를 하나의 바구니(딕셔너리)에 담습니다.
    updated_data = {
        "grade_class": grade_class,
        "student_name": student_name,
        "category": category,
        "content": content
    }

    # 바구니를 통째로 넘겨서 업데이트를 진행합니다.
    return supabase.table("counseling_logs").update(updated_data).eq("id", log_id).execute()
# 2. 기록 삭제 함수
def delete_log(log_id):
    supabase = get_supabase()
    return supabase.table("counseling_logs").delete().eq("id", log_id).execute()
