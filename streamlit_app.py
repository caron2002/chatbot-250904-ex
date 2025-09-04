import streamlit as st
from openai import OpenAI
import os
import json
from datetime import date

# -------------------------------
# Page Config & Minimal CSS
# -------------------------------
st.set_page_config(page_title="여행 추천 챗봇", page_icon="🧭", layout="wide")
CHAT_BUBBLE_CSS = """
<style>
/* ChatGPT-like width & spacing */
.block-container {padding-top: 2rem; max-width: 980px;}
/* Message bubbles */
.user-bubble, .assistant-bubble {
  padding: 14px 16px; border-radius: 14px; margin: 6px 0; line-height: 1.6;
  border: 1px solid rgba(0,0,0,0.08);
}
.user-bubble { background: #f6f8fa; }
.assistant-bubble { background: #ffffff; }
.role-tag { font-size: 0.85rem; opacity: 0.7; margin-bottom: 2px; }
.tool-chip {
  display: inline-block; padding: 6px 10px; border-radius: 999px;
  border: 1px solid rgba(0,0,0,0.1); margin: 3px; font-size: 0.9rem; cursor: pointer;
}
.hr-soft { border: none; height: 1px; background: rgba(0,0,0,0.07); margin: 8px 0 16px; }
</style>
"""
st.markdown(CHAT_BUBBLE_CSS, unsafe_allow_html=True)

# -------------------------------
# Sidebar (Settings)
# -------------------------------
st.sidebar.title("⚙️ 설정")
openai_api_key = st.sidebar.text_input("OpenAI API 키", type="password")
model = st.sidebar.selectbox("모델 선택", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"], index=0)
temperature = st.sidebar.slider("창의성(temperature)", 0.0, 1.2, 0.6, 0.1)

if st.sidebar.button("💬 대화 초기화"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("💡 *한국어 → 영어 순서로 답변합니다. 여행 관련 질문만 응답하도록 시스템 프롬프트로 제한되어 있습니다.*")

if not openai_api_key:
    st.info("왼쪽 사이드바에 OpenAI API 키를 입력하세요.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# -------------------------------
# Session State
# -------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": (
            "규칙:\n"
            "1) 먼저 한국어로 설명하고, 다음 줄에 영어로도 간단히 설명해줘.\n"
            "2) 당신은 오직 '여행' 관련 질문에만 응답해. 비여행 질문은 공손히 거절해.\n"
            "3) 모르는 정보는 지어내지 말고, 불확실하면 추가 정보(도시/기간/예산 등)를 요청해.\n"
            "4) 여행 준비물, 문화, 음식, 교통, 일정, 숙소, 안전, 예산 등에 대해 친절하고 실용적으로 안내해.\n"
            "5) 한국 사용자 기준으로 팁을 제시하되, 일반화 가능한 조언으로 표현해."
        )
    }]

if "quick_itinerary_md" not in st.session_state:
    st.session_state.quick_itinerary_md = ""

# -------------------------------
# Header
# -------------------------------
st.title("🧭 여행 추천 챗봇")
st.caption("깔끔한 ChatGPT 스타일 UI · 한국어/영어 이중 답변 · 여행 특화 도우미")

# -------------------------------
# (추가 기능 #1) 퀵 트립 위저드
# -------------------------------
with st.expander("✨ 퀵 트립 위저드 (간단 입력으로 일정 제안 받기)"):
    col_a, col_b = st.columns([1,1])
    with col_a:
        dest = st.text_input("여행지(도시/국가)", placeholder="예: 도쿄, 오사카, 파리")
        start = st.date_input("출발일", value=date.today())
    with col_b:
        days = st.number_input("여행 일수", min_value=1, max_value=60, value=4)
        budget = st.selectbox("예산 감각", ["저예산", "보통", "프리미엄"], index=1)
    interests = st.multiselect(
        "관심사(복수 선택)", 
        ["맛집", "카페/디저트", "역사/문화", "자연/하이킹", "쇼핑", "가족", "야경", "사진 명소", "테마파크"],
        default=["맛집","사진 명소"]
    )
    if st.button("🗺️ 일정 제안 받기", use_container_width=True, type="primary"):
        if not dest:
            st.warning("여행지를 입력해주세요.")
        else:
            wizard_prompt = (
                f"퀵 트립 위저드 요청:\n"
                f"- 여행지: {dest}\n"
                f"- 출발일: {start}\n"
                f"- 일수: {days}일\n"
                f"- 예산: {budget}\n"
                f"- 관심사: {', '.join(interests) if interests else '미선택'}\n\n"
                "요청사항:\n"
                "1) 하루 단위(아침/점심/오후/저녁)로 동선이 자연스럽게 이어지도록 2안 이상 비교 제안\n"
                "2) 이동시간/티켓 이슈/혼잡시간 등 현실 팁 포함\n"
                "3) 한국어 → 영어 요약 순서로 작성\n"
            )
            st.session_state.messages.append({"role": "user", "content": wizard_prompt})
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=st.session_state.messages
            )
            answer = resp.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.quick_itinerary_md = answer
            st.success("일정 제안을 받았어요! 아래 대화 영역에서 확인하거나, 우측 사이드의 내보내기를 활용하세요.")

# -------------------------------
# (추가 기능 #2) 패킹 체크리스트 생성기
# -------------------------------
with st.expander("🧳 패킹 체크리스트 생성기"):
    col1, col2 = st.columns(2)
    with col1:
        season = st.selectbox("시즌", ["봄", "여름", "가을", "겨울", "우기/장마", "건기"])
        who = st.selectbox("여행 유형", ["혼자", "커플", "가족(아이포함)", "부모님 모시고"], index=0)
    with col2:
        style = st.selectbox("여행 스타일", ["가벼운 배낭", "표준", "장비 많음"])
        activities = st.multiselect("활동", ["도시 투어", "하이킹", "수영/온천", "테마파크", "비즈니스 미팅"], default=["도시 투어"])
    if st.button("📝 체크리스트 만들기", use_container_width=True):
        pack_prompt = (
            "아래 조건에 맞는 패킹 체크리스트를 만들어줘. 한국어 본문 뒤에 영어 요약도 추가해줘.\n"
            f"- 시즌: {season}\n- 동행: {who}\n- 스타일: {style}\n- 활동: {', '.join(activities) if activities else '일반 관광'}\n"
            "구성: 필수 / 선택 / 건강/의약 / 전자기기 / 서류 / 그 밖의 팁으로 나눠 표 형태로 간결하게."
        )
        st.session_state.messages.append({"role": "user", "content": pack_prompt})
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=st.session_state.messages
        )
        answer = resp.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.success("체크리스트가 생성되었습니다! 아래 대화 영역에서 확인하세요.")

# -------------------------------
# (추가 기능 #3) 내보내기(Export)
# -------------------------------
def _export_md() -> str:
    lines = ["# 여행 추천 챗봇 대화 내역\n"]
    for m in st.session_state.messages:
        if m["role"] == "system":
            continue
        prefix = "### 사용자" if m["role"] == "user" else "### 챗봇"
        lines.append(prefix + "\n")
        lines.append(m["content"] + "\n")
    return "\n".join(lines)

# 버튼 동일 크기 CSS
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] button {
        width: 100% !important;
        min-height: 60px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hr-soft"></div>', unsafe_allow_html=True)
exp_col1, exp_col2, exp_col3 = st.columns(3)

with exp_col1:
    st.download_button(
        "⬇️ 대화 내역(Markdown) 저장", 
        data=_export_md().encode("utf-8"),
        file_name="travel_chat_history.md", 
        mime="text/markdown",
        use_container_width=True
    )
with exp_col2:
    if st.session_state.quick_itinerary_md:
        st.download_button(
            "⬇️ 최근 일정 제안만 저장", 
            data=st.session_state.quick_itinerary_md.encode("utf-8"),
            file_name="itinerary_suggestion.md", 
            mime="text/markdown",
            use_container_width=True
        )
with exp_col3:
    raw_json = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
    st.download_button(
        "⬇️ 원본 JSON 저장", 
        data=raw_json.encode("utf-8"),
        file_name="travel_chat_raw.json", 
        mime="application/json",
        use_container_width=True
    )

# -------------------------------
# Suggested prompt chips (UX sugar)
# -------------------------------
st.markdown('<div class="hr-soft"></div>', unsafe_allow_html=True)
st.subheader("🧩 추천 질문")
chip_cols = st.columns(4)
chips = [
    "오사카 3박4일 맛집 + 쇼핑 동선 짜줘",
    "혼자 파리 2박3일, 예산 70만원으로 핵심만",
    "부모님 모시고 도쿄, 걷기 적은 코스 추천",
    "제주도 렌터카 없이 1박2일 대중교통 코스"
]
for i, c in enumerate(chip_cols):
    with c:
        if st.button(f"• {chips[i]}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": chips[i]})
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=st.session_state.messages
            )
            answer = resp.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

# -------------------------------
# Chat Area
# -------------------------------
st.markdown('<div class="hr-soft"></div>', unsafe_allow_html=True)
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    if m["role"] == "user":
        st.markdown('<div class="role-tag">👤 사용자</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="user-bubble">{m["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="role-tag">🤖 챗봇</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="assistant-bubble">{m["content"]}</div>', unsafe_allow_html=True)

# -------------------------------
# Chat Input (bottom)
# -------------------------------
user_text = st.chat_input("여행 관련 무엇이든 물어보세요… (한국어/영어 가능)")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=st.session_state.messages
    )
    answer = resp.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
