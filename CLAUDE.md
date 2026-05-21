# CLAUDE.md — AI 상담일지 프로젝트

> 이 파일은 Claude Code가 프로젝트를 이해하고 일관되게 개발하기 위한 안내서입니다.
> 코드를 작성하기 전에 반드시 이 파일을 먼저 읽으세요.

---

## 1. 프로젝트 목적 및 주요 기능

**목적:** 중학교 수학 교사가 학생 상담 내용을 기록·관리하고, 학기 말 생활기록부 문구를 AI로 생성하는 웹 앱

**사용자:** 현재는 1인 사용 (추후 다계정 배포 가능한 구조 유지)

**사용 환경:** 교사용 PC + 개인 스마트폰 (반응형 필수)

### 주요 기능 5가지

| 화면 | 기능 요약 |
|------|-----------|
| 🔐 로그인/회원가입 | Supabase Auth 이메일+비밀번호, 로그인 전 사이드바 완전 숨김 |
| 🏠 홈 (달력) | 첫 화면. 상담 기록 + 예정 일정 달력 표시. 날짜 클릭 시 목록 팝업 + 작성 이동 버튼 |
| ✍️ 상담일지 작성 | 음성/카메라/사진 업로드 → AI 분석 → 카테고리 자동 분류 → Supabase 저장 |
| 📂 이력 조회 | 학생별/날짜별/카테고리별 필터, 수정/삭제 |
| 📝 생활기록부 문구 생성 | 학생 선택 → 날짜 범위 지정 → 상담 체크박스 선택 → AI 생기부 문체 문구 생성 → 복사 |

---

## 2. 기술 스택

| 구분 | 선택 | 비고 |
|------|------|------|
| 프레임워크 | **Streamlit** | Python 기반, 빠른 UI 구성 |
| 인증 | **Supabase Auth** | 이메일+비밀번호, 다계정 확장 가능 |
| DB | **Supabase PostgreSQL** | 3개 테이블 사용 |
| AI | **Anthropic API** (claude-sonnet-4-6) | 카테고리 분류, OCR, 생기부 문구 생성 |
| 배포 | **Streamlit Cloud** | secrets.toml로 환경변수 관리 |
| STT | **streamlit-mic-recorder** | 음성 → 텍스트 |

---

## 3. 폴더 구조

```
project/
├── CLAUDE.md                  # 이 파일
├── main.py                    # 앱 진입점 (로그인 + 달력 홈)
├── database.py                # Supabase 연결 및 모든 DB/AI 함수
├── pages/
│   ├── 1_record.py            # 상담일지 작성
│   ├── 2_history.py           # 이력 조회
│   └── 3_report.py            # 생활기록부 문구 생성 (신규)
├── .streamlit/
│   └── secrets.toml           # API 키 (git 제외)
└── requirements.txt
```

---

## 4. DB 테이블 구조

### counseling_logs (기존 + 수정)
```sql
id              uuid primary key default gen_random_uuid()
user_id         uuid references auth.users  -- 다계정 대비
grade_class     text
student_name    text
content         text
category        text  -- AI 자동 분류: 행동/정서/학업/가정
incident_id     text  -- 복수 학생 연관 사건 묶음
created_at      timestamptz default now()
```

### scheduled_counseling (신규)
```sql
id              uuid primary key default gen_random_uuid()
user_id         uuid references auth.users
scheduled_date  date
student_name    text
note            text  -- 선택 입력
created_at      timestamptz default now()
```

### user_settings (신규)
```sql
id              uuid primary key default gen_random_uuid()
user_id         uuid references auth.users unique
my_class        text  -- 우리반 설정
created_at      timestamptz default now()
updated_at      timestamptz default now()
```

---

## 5. 개발 시 지켜야 할 규칙

### 인증 관련
- 모든 pages/ 파일 최상단에 반드시 로그인 검문소 추가
  ```python
  if "user" not in st.session_state or not st.session_state.user:
      st.warning("먼저 로그인해 주세요.")
      st.stop()
  ```
- 로그인 전에는 사이드바를 CSS로 완전히 숨김
- 모든 DB 조회/저장 시 `user_id` 필터 반드시 포함 (다계정 데이터 격리)

### Supabase 관련
- DB 함수는 모두 `database.py`에만 작성, pages에서 직접 쿼리 금지
- 저장 시 한국 시간(KST, Asia/Seoul) 강제 적용
- 에러는 try/except로 처리하고 st.error()로 사용자에게 표시

### AI (Anthropic API) 관련
- 모델명은 항상 `claude-sonnet-4-6` 고정
- JSON 응답 파싱 시 반드시 `{` `}` 슬라이싱 안전 처리 (JSONDecodeError 방지)
- 생기부 문구 생성 프롬프트: "~하였음", "~을 보임" 등 생기부 문체 명시

### UI/UX 관련
- 스마트폰 사용 고려: 버튼 최소 높이 2.5rem, 터치하기 쉬운 크기
- 달력은 `streamlit-calendar` 또는 커스텀 HTML/CSS로 구현
- 사이드바 메뉴: 🏠 홈 / ✍️ 상담 기록 / 📂 이력 조회 / 📝 생기부 문구 (총 4개)
- 통계 페이지는 추후 추가 예정, 지금은 구현하지 않음

### 보안 관련
- API 키, Supabase URL/KEY는 반드시 `st.secrets`에서만 읽기
- 소스코드에 하드코딩 절대 금지
- `.streamlit/secrets.toml`은 `.gitignore`에 포함

### 코드 품질
- 함수마다 한 줄 주석으로 역할 설명
- 세션 상태 키는 파일 상단에 모아서 초기화
- `st.rerun()` 남용 금지 — 꼭 필요한 곳에만 사용
