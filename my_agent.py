from pathlib import Path
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import ssl
import os
import re
import time

from knowledge_base import (
    CONDITION_QUERY_MAP, CONTRAINDICATIONS, PRESCRIPTION_GUIDELINES,
    GENDER_ADJUSTMENTS, KNOWLEDGE_ITEMS, CONDITION_ALIASES,
)

# ── 설정 토글 ──
USE_LLM = True       # OpenAI로 요약/팁 보조
USE_EXTERNAL = True  # PubMed 외부 논문 검색
USE_LLM_REVIEW = True
LLM_CALL_LIMIT = 4
TOP_N = 3

# 규칙 기반 보강용 용어 사전
TERM_GLOSSARY = {
    "sarcopenia": "근감소증", "resistance training": "저항운동",
    "eccentric exercise": "편심성 운동", "flexibility": "유연성",
    "osteoporosis": "골다공증", "older adults": "노인",
    "elderly": "노인", "stretching": "스트레칭",
    "balance": "균형", "gait": "보행", "frailty": "노쇠",
    "muscle": "근육", "strength": "근력", "aerobic": "유산소",
    "fall prevention": "낙상 예방", "physical activity": "신체활동",
    "hypertension": "고혈압", "obesity": "비만", "diabetes": "당뇨",
}
STUDY_TYPE_RULES = {
    "randomized controlled trial": "무작위 대조 시험(RCT)",
    "randomized": "무작위 대조 시험(RCT)",
    "systematic review": "체계적 문헌 고찰",
    "meta-analysis": "메타분석",
    "cohort": "코호트 연구",
    "cross-sectional": "횡단 연구",
}


def _make_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def load_env():
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip().strip("'").strip('"')
    except FileNotFoundError:
        pass


# ═══════════════════════════════════════════
# [에이전트 1] 입력 분석: 사용자 케이스 → 프로필 dict
# ═══════════════════════════════════════════

def extract_user_profile(query):
    """사용자 자연어 입력에서 대상자 프로필(나이, 성별, 질환)을 추출한다.
    규칙 기반이므로 LLM 없이도 동작한다."""
    profile = {"age": None, "gender": None, "conditions": [], "raw_query": query}

    # 나이 추출: "57세", "57살", "57 여성", "57세 남성" 등 다양한 패턴 지원
    age_match = re.search(r'(\d{2,3})\s*(?:세|살|여성|남성|여자|남자)', query)
    if age_match:
        profile["age"] = int(age_match.group(1))

    # 성별 추출
    if "여성" in query or "여자" in query:
        profile["gender"] = "여성"
    elif "남성" in query or "남자" in query:
        profile["gender"] = "남성"

    # 질환 추출 (CONDITION_ALIASES 기반 매칭)
    query_lower = query.lower()
    found = set()
    for alias, condition in CONDITION_ALIASES.items():
        if alias.lower() in query_lower:
            found.add(condition)
    profile["conditions"] = sorted(found)

    # 연령대 카테고리 결정
    age = profile["age"]
    if age and age >= 65:
        profile["age_group"] = "65세_이상_기본"
    elif age and age >= 50:
        profile["age_group"] = "50~64세_기본"
    elif age and age < 50:
        profile["age_group"] = "19~49세_기본"
    else:
        profile["age_group"] = "65세_이상_기본"  # 나이 정보가 아예 없을 때의 기본값

    return profile


# ═══════════════════════════════════════════
# [에이전트 2] 지식 검색: 로컬 RAG + 외부 PubMed
# ═══════════════════════════════════════════

def search_knowledge_base(profile):
    """내부 지식 베이스에서 프로필과 관련된 항목을 키워드 매칭으로 검색한다."""
    conditions = profile.get("conditions", [])
    if not conditions:
        return KNOWLEDGE_ITEMS[:]  # 질환 미지정 시 전체 반환

    results = []
    for item in KNOWLEDGE_ITEMS:
        text = (item["title"] + " " + item["content"] + " " + item["keywords"]).lower()
        # 질환 키워드와 매칭되면 포함
        if any(c in text for c in [c.lower() for c in conditions]):
            results.append(dict(item, source="내부(지식베이스)", link="링크 없음"))
        # 이론/용어는 항상 포함 (기본 학습 자료)
        elif item["type"] in ("이론", "용어"):
            results.append(dict(item, source="내부(지식베이스)", link="링크 없음"))

    return results


def build_pubmed_query(profile):
    """프로필 기반으로 PubMed 검색 쿼리를 동적 생성한다."""
    parts = []
    for cond in profile.get("conditions", []):
        q = CONDITION_QUERY_MAP.get(cond)
        if q:
            parts.append(f"({q})")
    if not parts:
        return "exercise prescription older adults"
    return " OR ".join(parts)


def fetch_external_context(profile):
    """PubMed에서 프로필 기반 동적 쿼리로 논문을 검색한다.
    Returns: (facts_list, status_dict)"""
    facts, status = [], {"pubmed": "skipped"}
    if not USE_EXTERNAL:
        return facts, status

    ctx = _make_ssl_context()
    query = build_pubmed_query(profile)
    print(f"  - PubMed 검색 쿼리: {query}")

    try:
        encoded = urllib.parse.quote(query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax=3&retmode=json"
        res = urllib.request.urlopen(search_url, context=ctx, timeout=8)
        ids = json.loads(res.read())["esearchresult"]["idlist"]

        if ids:
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
            sdata = json.loads(urllib.request.urlopen(summary_url, context=ctx, timeout=8).read())
            for pid in ids:
                art = sdata["result"][pid]
                title = art.get("title", "")
                title_lower = title.lower()
                kw = [v for k, v in TERM_GLOSSARY.items() if k in title_lower]
                facts.append({
                    "type": "논문", "title": title, "content": "",
                    "keywords": ", ".join(dict.fromkeys(kw)) or "노인, 운동처방",
                    "practical_tip": "추후 분석",
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    "source": "외부(PubMed)",
                })
        status["pubmed"] = f"success ({len(ids)}건)"
        print(f"  - PubMed 연동 성공 ✅ ({len(ids)}건)")
    except Exception as e:
        status["pubmed"] = f"error: {e}"
        print(f"  - PubMed 연동 실패 ⚠️: {e}")

    return facts, status


# ═══════════════════════════════════════════
# [에이전트 3] 관련성 점수 + 보강
# ═══════════════════════════════════════════

def score_relevance(item, profile):
    """프로필 기반 관련성 점수 (0~10)."""
    score = 0
    text = (item.get("title", "") + " " + item.get("content", "") + " " + item.get("keywords", "")).lower()
    # 질환 매칭 (핵심 가중치)
    for cond in profile.get("conditions", []):
        if cond.lower() in text:
            score += 3
    # 내용 없음 → 보강 필요
    if not item.get("content"):
        score += 2
    # 외부 자료 신선도 가산
    if item.get("source", "내부") != "내부(지식베이스)":
        score += 1
    # 케이스 자료는 실전 적용도 높음
    if item.get("type") == "케이스":
        score += 1
    return min(score, 10)


def enrich_rule_based(item):
    """LLM 없이 규칙 기반으로 항목을 보강한다."""
    title_lower = item.get("title", "").lower()
    if item.get("type") == "논문" and not item.get("content"):
        study_type = next((v for k, v in STUDY_TYPE_RULES.items() if k in title_lower), "연구")
        topics = "·".join([v for k, v in TERM_GLOSSARY.items() if k in title_lower][:3]) or "노인 운동"
        item["content"] = f"[규칙 기반] {topics} 관련 {study_type}"
        item["practical_tip"] = "원문 링크에서 구체적인 처방 수치를 확인하세요."
    return item


def summarize_with_openai(type_, title, content):
    """OpenAI API로 전문가 수준 요약을 생성한다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = f"""당신은 노인체육 지도자이자 운동처방사입니다.
아래 자료를 분석하여 JSON으로 출력하세요. 영어 제목은 한국어로 설명하세요.
자료 유형: {type_} | 제목: {title} | 내용: {content or '(제목만으로 분석)'}

출력 (백틱 없이 순수 JSON만):
{{"korean_summary": "한국어 2~3문장 핵심 요약", "study_point": "핵심 1가지", "field_tip": "현장 적용법 1문장"}}"""

    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}}
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                                data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        res = urllib.request.urlopen(req, context=_make_ssl_context(), timeout=15)
        text = json.loads(res.read())['choices'][0]['message']['content']
        return json.loads(text.replace('```json', '').replace('```', '').strip())
    except Exception as e:
        print(f"    - OpenAI API 오류: {e}")
        return None


def enrich_facts(facts, profile):
    """관련성 점수 순 정렬 후 LLM 또는 규칙 기반 보강."""
    for f in facts:
        f["relevance_score"] = score_relevance(f, profile)
    facts.sort(key=lambda f: f["relevance_score"], reverse=True)

    if USE_LLM and os.environ.get("OPENAI_API_KEY"):
        print(f"-> [에이전트 3] LLM 보강 중... (최대 {LLM_CALL_LIMIT}건)")
        boosted = 0
        for f in facts:
            if boosted >= LLM_CALL_LIMIT:
                break
            if f.get("practical_tip") in ("추후 분석", "", None):
                if boosted > 0:
                    time.sleep(2)
                result = summarize_with_openai(f.get("type", ""), f.get("title", ""), f.get("content", ""))
                if result:
                    f["content"] = result.get("korean_summary", f["content"])
                    f["study_point"] = result.get("study_point", "")
                    f["practical_tip"] = result.get("field_tip", "")
                    boosted += 1
        print(f"  - {boosted}개 항목 LLM 보강 완료 ✅")
    else:
        print("-> [에이전트 3] 규칙 기반 보강")
        for f in facts:
            enrich_rule_based(f)

    # LLM 후 미보강 항목 fallback
    for f in facts:
        if f.get("practical_tip") in ("추후 분석", "", None):
            enrich_rule_based(f)
    return facts


# ═══════════════════════════════════════════
# [에이전트 4] 맞춤형 처방 생성
# ═══════════════════════════════════════════

def synthesize_expert_advice(profile, guide_text):
    """OpenAI API를 사용하여 대상자의 프로필과 1차 생성된 처방을 바탕으로 상세한 종합 처방 및 영양/라이프스타일 조언을 생성한다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not USE_LLM or not api_key:
        return "> 💡 전문가 코멘트: 각 질환별 개별 가이드라인을 준수하되, 중복되는 금기사항을 최우선으로 지켜주세요. 점진적인 강도 증가가 핵심입니다."

    age = profile.get("age", "미상")
    gender = profile.get("gender", "미상")
    conditions = ", ".join(profile.get("conditions", [])) or "특이사항 없음"

    prompt = f"""당신은 ACSM 인증 수석 임상운동생리학자입니다.
다음 대상자 프로필과 기본 처방안을 바탕으로, 대상자가 여러 질환을 복합적으로 가지고 있을 경우의 우선순위, 상호작용, 그리고 영양 및 라이프스타일에 대한 "통합 전문가 조언"을 작성해주세요.

[대상자 프로필]
나이: {age}세 | 성별: {gender} | 감지된 질환: {conditions}

[기본 처방안]
{guide_text}

[요청 사항]
1. 친절하고 전문적인 톤으로 작성하세요 (존댓말 사용).
2. 여러 질환이 겹칠 경우 운동 시 주의해야 할 시너지나 상충되는 부분(예: 고혈압과 당뇨가 같이 있을 때의 운동 타이밍 등)을 구체적으로 짚어주세요.
3. 운동뿐만 아니라 식단/영양, 수분 섭취, 수면 등 라이프스타일 팁을 1문단 추가해주세요.
4. 전체 분량은 2~3문단으로 구성하며, 마크다운(bold 등)을 활용해 가독성 있게 작성하세요.
5. "전문가 종합 처방 조언"이라는 제목은 제외하고 내용만 작성하세요."""

    data = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5, "max_tokens": 800}
    try:
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                                     data=json.dumps(data).encode("utf-8"),
                                     headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'})
        with urllib.request.urlopen(req, context=_make_ssl_context(), timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"    - 종합 조언 생성 실패: {e}")
        return "> 💡 전문가 코멘트: 각 질환별 가이드라인을 꼼꼼히 확인하고, 안전을 최우선으로 점진적으로 운동량을 늘려주세요."

def write_prescription_guide(facts, profile):
    """프로필 기반 맞춤형 운동처방 가이드를 Markdown으로 생성한다."""
    lines = []
    age = profile.get("age", "미상")
    gender = profile.get("gender", "미상")
    conditions = profile.get("conditions", [])
    age_group = profile.get("age_group", "65세_이상_기본")

    lines.append(f"# 🏋️ 맞춤형 운동처방 가이드\n")
    lines.append(f"**대상자**: {age}세 {gender}, 질환: {', '.join(conditions) or '없음'}\n")
    lines.append("---\n")

    # 1. 기본 가이드라인 (연령대별)
    base = PRESCRIPTION_GUIDELINES.get(age_group, {})
    if base:
        lines.append(f"## 📋 기본 가이드라인 ({age_group.replace('_', ' ')})\n")
        for k, v in base.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    # 2. 질환별 처방
    for cond in conditions:
        guide = PRESCRIPTION_GUIDELINES.get(cond, {})
        contra = CONTRAINDICATIONS.get(cond, {})
        if guide or contra:
            lines.append(f"## 🩺 {cond} 운동처방\n")
            if guide:
                lines.append("### FITT 처방")
                for k, v in guide.items():
                    lines.append(f"- **{k}**: {v}")
            if contra:
                lines.append("\n### ⚠️ 안전 관리")
                for level, items in contra.items():
                    if items:
                        lines.append(f"- **{level}**: {' / '.join(items)}")
            lines.append("")

    # 3. 성별 보정
    gender_adj = GENDER_ADJUSTMENTS.get(gender, [])
    if gender_adj:
        lines.append(f"## 👤 {gender} 특이사항\n")
        for adj in gender_adj:
            lines.append(f"- {adj}")
        lines.append("")
        
    # [에이전트 4.5] 전문가 종합 조언 (LLM)
    raw_guide_so_far = "\n".join(lines)
    expert_advice = synthesize_expert_advice(profile, raw_guide_so_far)
    
    # 조언을 "기본 가이드라인" 직후, 질환별 처방 앞에 삽입하기 위해 리스트 재배치
    final_lines = []
    final_lines.extend(lines[:4]) # 제목과 대상자 정보까지
    
    final_lines.append(f"## 🩺 전문가 종합 처방 조언\n\n{expert_advice}\n\n---\n")
    
    final_lines.extend(lines[4:]) # 나머지 섹션들
    lines = final_lines

    # 4. 근거 자료 (관련성 상위)
    top = [f for f in facts if f.get("relevance_score", 0) >= 2][:TOP_N]
    if top:
        lines.append("## 📚 근거 자료 (관련성 상위)\n")
        for i, item in enumerate(top, 1):
            link = item.get("link", "")
            link_md = f" → [원문]({link})" if link and link != "링크 없음" else ""
            lines.append(f"{i}. [{item['type']}] **{item['title'][:80]}**{link_md}")
            sp = item.get("study_point") or item.get("content", "")[:100]
            if sp and sp not in ("추후 분석",):
                lines.append(f"   - {sp}")
        lines.append("")

    # 5. 기타 참고 자료
    others = [f for f in facts if f not in top]
    if others:
        lines.append("## 📎 추가 참고 자료\n")
        for item in others:
            link = item.get("link", "")
            link_md = f" → [원문]({link})" if link and link != "링크 없음" else ""
            lines.append(f"- [{item['type']}] {item['title'][:60]}{link_md}")
        lines.append("")

    lines.append("---")
    lines.append("> ⚠️ 본 가이드는 학습 보조 자료입니다. 실제 운동 지도 전 개인별 체력 평가와 건강 상태 확인이 필요합니다. (ACSM 가이드라인 참고)")
    return "\n".join(lines)


# ═══════════════════════════════════════════
# [에이전트 5] 안전 검토
# ═══════════════════════════════════════════

def review_prescription_with_rules(guide_text, profile):
    """규칙 기반 처방 안전 검토. 금기사항 위반 여부를 점검한다."""
    report = ["# 🔍 처방 안전 검토 리포트\n", f"> 대상자: {profile.get('age')}세 {profile.get('gender')}, "
              f"질환: {', '.join(profile.get('conditions', []))}\n"]
    issues = []

    # 질환별 금기사항 검사 — "금지"/"금기" 문맥이 아닌 곳에서 사용된 경우만 위험 판정
    for cond in profile.get("conditions", []):
        contra = CONTRAINDICATIONS.get(cond, {})
        for forbidden in contra.get("금지", []):
            keyword = forbidden[:4]
            for line in guide_text.split('\n'):
                if keyword in line and not any(w in line for w in ("금지", "금기", "⚠️", "안전")):
                    issues.append(f"[⛔ 위험] {cond} 환자에게 금기인 '{forbidden}'이 처방 본문에서 권장됨")
                    break

    # 위험 표현 점검
    danger_words = ["무조건", "항상", "완벽한", "100%", "모든 사람에게"]
    found = [w for w in danger_words if w in guide_text]
    if found:
        issues.append(f"[⚠️ 주의] 단정적 표현 발견: {', '.join(found)}")

    # 결과 출력
    report.append("## 📋 점검 결과\n")
    if issues:
        for issue in issues:
            report.append(f"- {issue}")
    else:
        report.append("- ✅ 금기사항 위반 및 위험 표현이 발견되지 않았습니다.")

    # 필수 체크 항목
    report.append("\n## 📝 필수 확인 사항\n")
    for cond in profile.get("conditions", []):
        must = CONTRAINDICATIONS.get(cond, {}).get("필수", [])
        for m in must:
            icon = "✅" if m[:4] in guide_text else "⚠️"
            report.append(f"- [{icon}] {cond}: {m}")

    report.append("\n---")
    report.append("> 본 검토는 규칙 기반 자동 점검입니다. 최종 판단은 전문가가 확인하세요.")
    return "\n".join(report)


def review_with_openai(guide_text, profile):
    """OpenAI API로 처방 안전 검토."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    conditions_str = ", ".join(profile.get("conditions", []))
    prompt = f"""당신은 운동처방 안전 검토 전문가입니다.
대상자: {profile.get('age')}세 {profile.get('gender')}, 질환: {conditions_str}

아래 처방 가이드에서 위험한 부분을 점검하세요.
{guide_text[:3000]}

출력 (백틱 없이 순수 JSON만):
{{"safety_issues": "위험한 처방이 있으면 지적, 없으면 '없음'",
  "missing_precautions": "빠진 주의사항, 없으면 '없음'",
  "overall_verdict": "안전/주의필요/위험 중 하나"}}"""

    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}}
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                                data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        res = urllib.request.urlopen(req, context=_make_ssl_context(), timeout=20)
        result = json.loads(json.loads(res.read())['choices'][0]['message']['content']
                          .replace('```json', '').replace('```', '').strip())
        report = [f"# 🔍 LLM 처방 안전 검토\n",
                  f"> 대상자: {profile.get('age')}세 {profile.get('gender')}, 질환: {conditions_str}\n",
                  "## 📋 LLM 검토 결과\n"]
        for k, v in result.items():
            icon = "✅" if v in ("없음", "안전") else "⚠️"
            report.append(f"- [{icon}] **{k}**: {v}")
        report.append("\n> LLM 검토 결과는 보조 의견입니다.")
        return "\n".join(report)
    except Exception as e:
        print(f"  - LLM 검토 실패: {e}")
        return None


def review_guide(guide_text, profile):
    """검토 라우터: LLM 우선, 실패 시 규칙 기반 fallback."""
    if USE_LLM_REVIEW:
        result = review_with_openai(guide_text, profile)
        if result:
            return result
    return review_prescription_with_rules(guide_text, profile)


# ═══════════════════════════════════════════
# [에이전트 6] 텔레그램 전송 (선택)
# ═══════════════════════════════════════════

def send_to_telegram(text):
    """텔레그램으로 결과 전송. 실패해도 기본 실행에 영향 없음."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(ch, f'\\{ch}')

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ctx = _make_ssl_context()
    # 4096자 단위 분할 전송
    chunks, current, cur_len = [], [], 0
    for line in text.split('\n'):
        ll = len(line) + 1
        if cur_len + ll > 4096:
            chunks.append('\n'.join(current))
            current, cur_len = [line], ll
        else:
            current.append(line)
            cur_len += ll
    if current:
        chunks.append('\n'.join(current))

    for i, chunk in enumerate(chunks, 1):
        payload = json.dumps({"chat_id": chat_id, "text": chunk, "parse_mode": "MarkdownV2"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        try:
            urllib.request.urlopen(req, context=ctx, timeout=10)
            print(f"  - 텔레그램 전송 ✅ ({i}/{len(chunks)})")
            if i < len(chunks):
                time.sleep(1)
        except Exception as e:
            print(f"  - 텔레그램 전송 실패 ⚠️: {e}")


# ═══════════════════════════════════════════
# 메인 파이프라인
# ═══════════════════════════════════════════

def main():
    load_env()

    print("=" * 50)
    print("  맞춤형 운동처방 에이전트")
    print("=" * 50)
    print("\n대상자 정보를 입력하세요.")
    print("예: 고혈압과 비만을 가지고 있는 57세 여성의 운동처방에 대해 설명해줘")
    print("-" * 50)

    user_query = input("\n> ").strip()
    if not user_query:
        user_query = "고혈압과 비만을 가지고 있는 57세 여성의 운동처방에 대해 설명해줘"
        print(f"(기본 예시 사용: {user_query})")

    # [에이전트 1] 프로필 추출
    print(f"\n[에이전트 1] 대상자 프로필 분석 중...")
    profile = extract_user_profile(user_query)
    print(f"  - 나이: {profile['age']}세")
    print(f"  - 성별: {profile['gender']}")
    print(f"  - 질환: {profile['conditions']}")
    print(f"  - 연령대: {profile['age_group']}")

    # [에이전트 2] 지식 검색 (로컬 RAG + 외부 PubMed)
    print(f"\n[에이전트 2] 관련 자료 검색 중...")
    facts = search_knowledge_base(profile)
    print(f"  - 내부 지식 베이스: {len(facts)}건 매칭")

    ext_facts, ext_status = fetch_external_context(profile)
    if ext_facts:
        facts.extend(ext_facts)
        print(f"  - 외부 논문 추가: {len(ext_facts)}건")
    elif USE_EXTERNAL:
        print(f"  - 외부 논문 없음, 내부 자료만 사용 ⚠️")

    # [에이전트 3] 관련성 점수 + 보강
    print(f"\n[에이전트 3] 관련성 평가 및 보강 중...")
    facts = enrich_facts(facts, profile)

    # output.md 저장 (데이터 추출 표)
    save_data_table(facts)
    print(f"  - output.md 저장 완료 ✅")

    # [에이전트 4] 맞춤형 처방 생성
    print(f"\n[에이전트 4] 맞춤형 운동처방 작성 중...")
    guide = write_prescription_guide(facts, profile)
    Path("output_user_guide.md").write_text(guide, encoding="utf-8")
    print(f"  - output_user_guide.md 저장 완료 ✅")

    # [에이전트 5] 안전 검토
    print(f"\n[에이전트 5] 처방 안전 검토 중...")
    review = review_guide(guide, profile)
    Path("review_report.md").write_text(review, encoding="utf-8")
    print(f"  - review_report.md 저장 완료 ✅")

    # 최종 결과 출력
    print("\n" + "=" * 50)
    print(guide)
    print("\n" + "=" * 50)
    print(review)

    # 텔레그램 전송 (선택)
    print("\n텔레그램 전송 시도 중...")
    send_to_telegram(guide)

    print("\n✅ 모든 에이전트 실행 완료!")


def save_data_table(facts):
    """추출된 항목을 output.md 표로 저장한다."""
    lines = ["# 시니어 스포츠 학습 도우미: 데이터 추출 표\n",
             "| 유형 | 제목 | 키워드 | 요약 | 관련성 | 출처 |",
             "|---|---|---|---|---|---|"]
    for f in facts:
        content = (f.get('content', '') or '')[:60].replace('\n', ' ')
        score = f.get('relevance_score', 0)
        lines.append(f"| {f.get('type','')} | {f.get('title','')[:50]} | {f.get('keywords','')} | {content} | {score} | {f.get('source','')} |")
    Path("output.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
