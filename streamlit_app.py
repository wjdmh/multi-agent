"""Streamlit UI — 맞춤형 운동처방 에이전트 (my_agent.py 핵심 로직 import)"""

import streamlit as st
from my_agent import (
    load_env, extract_user_profile, search_knowledge_base,
    fetch_external_context, enrich_facts, write_prescription_guide,
    review_guide, save_data_table,
)
from knowledge_base import CONTRAINDICATIONS, PRESCRIPTION_GUIDELINES, CONDITION_QUERY_MAP
from pathlib import Path

# ── 페이지 설정 ──
st.set_page_config(page_title="운동처방 에이전트", page_icon="💪", layout="wide")
load_env()

# ── 커스텀 CSS ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Noto Sans KR', sans-serif; }
    .main .block-container { padding-top: 2rem; max-width: 960px; }

    /* 헤더 영역 */
    .hero { text-align: center; padding: 1.5rem 0 1rem; }
    .hero h1 { font-size: 2rem; font-weight: 700; margin: 0; }
    .hero p { color: #6b7280; font-size: 0.95rem; margin-top: 0.3rem; }

    /* 프로필 카드 */
    .profile-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 1rem 0; }
    .profile-card {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8ecf8 100%);
        border-radius: 12px; padding: 1rem; text-align: center;
        border: 1px solid #dde3f0;
    }
    .profile-card .label { font-size: 0.75rem; color: #6b7280; margin-bottom: 0.2rem; }
    .profile-card .value { font-size: 1.4rem; font-weight: 700; color: #1e293b; }

    /* 질환 태그 */
    .cond-tags { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.8rem 0 1.2rem; }
    .cond-tag {
        background: #3b82f6; color: white; padding: 0.3rem 0.8rem;
        border-radius: 20px; font-size: 0.85rem; font-weight: 500;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    .sidebar-section { margin-bottom: 1rem; }
    .sidebar-title { font-weight: 700; font-size: 0.85rem; margin-bottom: 0.3rem; }
    .sidebar-items { font-size: 0.82rem; color: #4b5563; line-height: 1.6; }

    /* 탭 내부 */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 0.5rem 1.2rem; font-weight: 500;
    }

    /* 숨기기: footer만 숨기고 header(Deploy 버튼)는 보이게 유지 */
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ──
_all_conditions = sorted(k for k in PRESCRIPTION_GUIDELINES if "기본" not in k)
with st.sidebar:
    st.markdown("### 📋 지원 질환 (완전 지원)")
    st.markdown(f'<div class="sidebar-section">'
                f'<div class="sidebar-items">{", ".join(_all_conditions)}</div></div>',
                unsafe_allow_html=True)
    st.caption("위 16개 질환은 ACSM 처방+금기사항이 완벽하게 지원되며, 목록에 없는 질환도 PubMed 논문 검색을 시도합니다.")

# ── 메인 헤더 ──
st.markdown('<div class="hero"><h1>💪 맞춤형 운동처방 에이전트</h1>'
            '<p>대상자 정보를 입력하면 ACSM 가이드라인 · 논문 · 이론 기반으로 운동처방을 생성합니다.</p></div>',
            unsafe_allow_html=True)

# ── 입력 영역 ──
user_query = st.text_input(
    "대상자 정보",
    placeholder="예: 고혈압과 비만을 가지고 있는 57세 여성의 운동처방에 대해 설명해줘",
    label_visibility="collapsed",
)
run_btn = st.button("처방 생성 →", type="primary", use_container_width=True)

# ── 실행 ──
if run_btn and user_query.strip():
    with st.spinner("에이전트 파이프라인 실행 중..."):
        profile = extract_user_profile(user_query)
        facts = search_knowledge_base(profile)
        ext_facts, _ = fetch_external_context(profile)
        if ext_facts:
            facts.extend(ext_facts)
        facts = enrich_facts(facts, profile)
        save_data_table(facts)
        guide = write_prescription_guide(facts, profile)
        Path("output_user_guide.md").write_text(guide, encoding="utf-8")
        review = review_guide(guide, profile)
        Path("review_report.md").write_text(review, encoding="utf-8")

    # ── 프로필 카드 ──
    age_str = f"{profile['age']}세" if profile['age'] else "미상"
    gender_str = profile['gender'] or "미상"
    st.markdown(f"""
    <div class="profile-grid">
        <div class="profile-card"><div class="label">나이</div><div class="value">{age_str}</div></div>
        <div class="profile-card"><div class="label">성별</div><div class="value">{gender_str}</div></div>
        <div class="profile-card"><div class="label">질환 수</div><div class="value">{len(profile['conditions'])}</div></div>
        <div class="profile-card"><div class="label">검색 자료</div><div class="value">{len(facts)}건</div></div>
    </div>
    """, unsafe_allow_html=True)

    if profile['conditions']:
        tags = "".join(f'<span class="cond-tag">{c}</span>' for c in profile['conditions'])
        st.markdown(f'<div class="cond-tags">{tags}</div>', unsafe_allow_html=True)

    # ── 결과 탭 ──
    tab1, tab2, tab3 = st.tabs(["🏋️ 운동처방 가이드", "🔍 안전 검토", "📊 근거 자료"])

    with tab1:
        st.markdown(guide)

    with tab2:
        st.markdown(review)

    with tab3:
        for f in facts:
            with st.expander(f"[{f.get('type','')}] {f.get('title','')[:60]}", expanded=False):
                st.markdown(f"**키워드:** {f.get('keywords','')}")
                st.markdown(f"**요약:** {f.get('content','')[:200]}")
                st.caption(f"출처: {f.get('source','')} · 관련성: {f.get('relevance_score', '-')}")
                link = f.get("link", "")
                if link and link != "링크 없음":
                    st.markdown(f"🔗 [원문 링크]({link})")

    st.divider()
    st.caption("💾 output.md · output_user_guide.md · review_report.md 저장 완료")

elif run_btn:
    st.warning("대상자 정보를 입력해주세요.")
