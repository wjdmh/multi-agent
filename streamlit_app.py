"""Streamlit 화면 입출력 — my_agent.py의 핵심 로직을 import하여 사용한다."""

import streamlit as st
import random

# my_agent.py에서 필요한 함수와 상수만 import
from my_agent import (
    load_env,
    extract_facts,
    fetch_external_context,
    enrich_facts,
    classify_items,
    write_output,
    write_user_guides,
    save_user_guides,
    save_markdown_table,
    review_guides,
    USE_EXTERNAL,
    THEORY_SAMPLE_SIZE,
    INTERNAL_SAMPLE_SIZE,
    RANDOM_SEED,
)

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="시니어 스포츠 학습 파트너",
    page_icon="🏋️",
    layout="wide",
)

# ── 환경 변수 로드 (1회) ──────────────────────────────────
load_env()

# ── 기본 입력 샘플 ────────────────────────────────────────
DEFAULT_INPUT = """\
[논문] 시니어 근력 운동이 인지 기능에 미치는 영향
- 초록: 본 연구는 65세 이상 노인을 대상으로 주 3회 근력 운동을 실시하였을 때 인지 기능의 변화를 분석하였다. 결과적으로 인지 기능 점수가 15% 향상되었다.
- 키워드: 시니어, 근력, 인지
- 링크: https://example.com/paper/1

[뉴스] 지역 보건소, 어르신 대상 아쿠아로빅 교실 오픈
- 내용: 다음 달부터 지역 보건소에서 관절에 무리가 가지 않는 아쿠아로빅 교실을 무료로 운영한다.
- 키워드: 어르신, 수영, 보건소
- 링크: https://example.com/news/1

[논문] 노년기 단백질 섭취와 근감소증의 상관관계
- 초록: 단백질 섭취량이 부족한 노년층에서 근감소증 발생 비율이 높게 나타났다. 규칙적인 운동과 함께 충분한 영양 섭취가 필수적이다.
- 키워드: 노년기, 단백질, 근감소증
- 링크: https://example.com/paper/2

[이론] ACSM 노인 운동 가이드라인 (Aerobic)
- 내용: ACSM은 65세 이상 성인에게 주 5일 이상 중강도(RPE 5~6) 유산소 운동을 최소 30분씩 권고한다. 고강도일 경우 주 3일 20분 이상.
- 키워드: ACSM, 유산소, 노인, FITT, 강도
- 링크: https://example.com/theory/acsm-aerobic

[용어] sarcopenia
- 내용: sarcopenia = 근감소증. 노화에 따른 골격근량과 근력의 점진적 감소를 의미한다. 발음 [sɑːrkoʊˈpiːniə].
- 키워드: 영어용어, 근감소증, 노화기전, 학술용어
- 링크: https://example.com/term/sarcopenia
"""


# ── 파이프라인 실행 함수 ──────────────────────────────────
def run_pipeline(raw_text: str):
    """my_agent.py의 main() 파이프라인을 Streamlit용으로 재현한다."""

    # 1. 추출
    all_internal = extract_facts(raw_text)

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    # 이론/용어 샘플링
    theory_vocab = [i for i in all_internal if i["type"] in ("이론", "용어")]
    for item in theory_vocab:
        item["link"] = "링크 없음"
    theory_n = min(THEORY_SAMPLE_SIZE, len(theory_vocab))
    facts = random.sample(theory_vocab, theory_n)

    # 논문/뉴스/케이스: 외부 or 내부
    if USE_EXTERNAL:
        external_facts, _ = fetch_external_context()
        if external_facts:
            facts.extend(external_facts)
        else:
            other_internal = [i for i in all_internal if i["type"] not in ("이론", "용어")]
            other_n = min(INTERNAL_SAMPLE_SIZE - theory_n, len(other_internal))
            facts.extend(random.sample(other_internal, other_n))
    else:
        other_internal = [i for i in all_internal if i["type"] not in ("이론", "용어")]
        other_n = min(INTERNAL_SAMPLE_SIZE - theory_n, len(other_internal))
        facts.extend(random.sample(other_internal, other_n))

    # 2. 보강
    facts = enrich_facts(facts)

    # 3. 파일 저장
    save_markdown_table(facts)

    # 4. 분류
    grouped = classify_items(facts)

    # 5. 최종 출력
    briefing = write_output(grouped)
    guides = write_user_guides(grouped, facts)
    save_user_guides(guides)

    # 6. 검토
    review_report, needs_refetch = review_guides(guides)

    # 7. 피드백 루프
    if needs_refetch and USE_EXTERNAL:
        extra_facts, _ = fetch_external_context(
            query="노인 낙상예방 OR 시니어 재활운동",
            pubmed_query="fall prevention elderly OR balance training older adults",
        )
        if extra_facts:
            extra_facts = enrich_facts(extra_facts)
            facts.extend(extra_facts)
            grouped = classify_items(facts)
            guides = write_user_guides(grouped, facts)
            save_user_guides(guides)
            review_report, _ = review_guides(guides)

    # review_report.md 저장
    from pathlib import Path
    Path("review_report.md").write_text(review_report, encoding="utf-8")

    return facts, grouped, briefing, guides, review_report


# ── UI ────────────────────────────────────────────────────
st.title("🏋️ 시니어 스포츠·체육 학습 파트너")
st.caption("논문·뉴스를 입력하면 자동으로 추출 → 분류 → 가이드 작성 → 검토까지 진행합니다.")

# 입력 영역
raw_text = st.text_area(
    "📝 입력 자료 (논문/뉴스/이론/케이스/용어)",
    value=DEFAULT_INPUT,
    height=300,
    help="[논문], [뉴스], [이론], [케이스], [용어] 태그로 시작하는 블록을 입력하세요.",
)

run_btn = st.button("▶ 실행", type="primary", use_container_width=True)

# 실행
if run_btn:
    if not raw_text.strip():
        st.warning("입력 자료를 넣어주세요.")
    else:
        with st.spinner("에이전트 파이프라인 실행 중..."):
            facts, grouped, briefing, guides, review_report = run_pipeline(raw_text)

        st.success("파이프라인 완료! 아래 탭에서 결과를 확인하세요.")

        # 결과 탭
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 추출/분류 결과 (output.md)",
            "📰 브리핑",
            "🎓 학습 가이드 (output_user_guide.md)",
            "🔍 검토 보고서 (review_report.md)",
        ])

        with tab1:
            st.subheader("추출된 항목")
            for f in facts:
                with st.expander(f"[{f.get('type','')}] {f.get('title','')}", expanded=False):
                    st.markdown(f"**키워드:** {f.get('keywords','')}")
                    st.markdown(f"**요약:** {f.get('content','')}")
                    if f.get("study_point"):
                        st.markdown(f"📌 **암기 포인트:** {f['study_point']}")
                    if f.get("practical_tip") and f["practical_tip"] not in ("추후 분석", ""):
                        st.markdown(f"💡 **실전 팁:** {f['practical_tip']}")
                    if f.get("link") and f["link"] != "링크 없음":
                        st.markdown(f"🔗 [원문 링크]({f['link']})")
                    st.caption(f"출처: {f.get('source','내부')} · 관련성 점수: {f.get('relevance_score', '-')}")

            st.divider()
            st.subheader("카테고리 분류")
            category_names = {
                "이론_및_용어학습": "📚 이론 및 용어 학습",
                "운동처방_및_평가": "🏋️‍♂️ 운동처방 및 평가",
                "병태생리_및_질환관리": "🩺 병태생리 및 질환관리",
                "액티브에이징_및_인지심리": "🧠 액티브 에이징 및 인지심리",
                "지도론_및_정책동향": "📋 지도론 및 정책동향",
                "기타": "📌 기타 소식",
            }
            for key, items in grouped.items():
                if items:
                    st.markdown(f"**{category_names.get(key, key)}** ({len(items)}건)")

        with tab2:
            st.text(briefing)

        with tab3:
            st.markdown(guides)

        with tab4:
            st.markdown(review_report)

        st.divider()
        st.caption("💾 파일 저장 완료: output.md · output_user_guide.md · review_report.md")
