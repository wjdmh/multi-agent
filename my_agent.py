from pathlib import Path
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import ssl
import os
import time
import random

# Week-12 선택 확장 토글 (필요 시 False로 끄면 기본 실행만 동작)
USE_LLM = True       # Gemini로 요약/팁 보조
USE_EXTERNAL = True  # PubMed, Google News 등 외부 도구 사용
USE_LLM_REVIEW = False  # True로 바꾸면 Gemini API로 검토 보조
THEORY_SAMPLE_SIZE = 3    # 이론/용어: 항상 포함할 항목 수 (큐레이션된 학습 자료)
INTERNAL_SAMPLE_SIZE = 5  # 외부 데이터 없을 때 내부 샘플로 보충할 총 항목 수
RANDOM_SEED = 42          # None으로 바꾸면 실행마다 다른 결과 (데모용)
LLM_CALL_LIMIT = 6        # Gemini API 비용 통제: 수집 후 보강 최대 호출 횟수
TOP_N = 3                 # 오늘의 핵심 상단 요약에 표시할 항목 수

# 규칙 기반 보강용 판단 기준 (LLM 없을 때도 동작)
TERM_GLOSSARY = {
    "sarcopenia": "근감소증", "resistance training": "저항운동",
    "eccentric exercise": "편심성 운동", "flexibility": "유연성",
    "osteoporosis": "골다공증", "older adults": "노인",
    "elderly": "노인", "stretching": "스트레칭",
    "balance": "균형", "gait": "보행", "frailty": "노쇠",
    "muscle": "근육", "strength": "근력", "aerobic": "유산소",
    "fall prevention": "낙상 예방", "physical activity": "신체활동",
}
STUDY_TYPE_RULES = {
    "randomized controlled trial": "무작위 대조 시험(RCT)",
    "randomized": "무작위 대조 시험(RCT)",
    "systematic review": "체계적 문헌 고찰",
    "meta-analysis": "메타분석",
    "cohort": "코호트 연구",
    "cross-sectional": "횡단 연구",
}
DOMAIN_KEYWORDS = [
    "sarcopenia", "elderly", "older adults", "resistance training",
    "exercise intervention", "근감소증", "노인", "시니어", "운동처방",
    "저항운동", "유산소", "낙상", "근력", "보행속도", "체력",
    "ACSM", "노화", "만성질환", "frailty", "노쇠",
]

def _make_ssl_context():
    """macOS 시스템 인증서 부재 환경에서도 SSL 검증을 정상 수행하도록 certifi를 우선 사용한다."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()

def load_env():
    """외부 패키지 없이 .env 파일을 읽어 환경 변수로 설정합니다."""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip().strip("'").strip('"')
    except FileNotFoundError:
        pass

def summarize_with_gemini(type_, title, content):
    """Gemini API를 호출하여 전문가 수준의 요약과 실전 팁을 생성합니다."""
    if not USE_LLM:
        return "LLM 비활성화 (규칙 기반 결과)", "LLM 비활성화"
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "뉴스/논문 원문을 확인해주세요.", "추후 분석 (API 키 필요)"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
당신은 노인체육 지도자이자 운동처방사입니다.
아래 자료를 분석하여 특수체육 전공생이 아침 공부에 바로 활용할 수 있는 정보를 JSON으로 출력하세요.
제목이 영어라면 반드시 한국어로 설명하세요.

자료 유형: {type_}
제목: {title}
내용: {content if content else "(내용 없음 - 제목만으로 분석)"}

출력 규칙 (백틱 없이 순수 JSON만):
{{
  "korean_summary": "한국어 2~3문장. 영어 제목이면 번역 포함. 핵심 연구결과나 뉴스 내용.",
  "why_important": "노인체육/운동처방 분야에서 이 자료가 왜 중요한지 1문장.",
  "study_point": "오늘 이것만 기억하세요 — 핵심 1가지 (수치나 원칙 포함).",
  "field_tip": "복지관·보건소 현장에서 바로 쓸 수 있는 적용법 1문장 (강도·빈도·주의사항 포함)."
}}
"""
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    ctx = _make_ssl_context()

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        response = urllib.request.urlopen(req, context=ctx, timeout=15)
        res_data = json.loads(response.read())
        text_res = res_data['candidates'][0]['content']['parts'][0]['text']
        # 백틱 등 마크다운 잔재 제거
        text_res = text_res.replace('```json', '').replace('```', '').strip()
        result = json.loads(text_res)
        # 필수 필드 검증
        required = ("korean_summary", "why_important", "study_point", "field_tip")
        if not all(result.get(k) for k in required):
            raise ValueError(f"필수 필드 누락: {[k for k in required if not result.get(k)]}")
        return result
    except Exception as e:
        print(f"    - Gemini API 오류: {e}")
        return None

def fetch_external_context(query="시니어 스포츠 OR 보건소 운동 프로그램", pubmed_query="sarcopenia exercise intervention OR older adults resistance training"):
    """구글 뉴스 및 PubMed에서 보조 데이터를 가져옵니다. (외부 도구 - 보강 정보)

    Returns:
        facts: 수집된 항목 리스트
        status: 소스별 성공/실패 상태 딕셔너리
    """
    facts = []
    status = {"google_news": "skipped", "pubmed": "skipped"}

    ctx = _make_ssl_context()

    # 1. 구글 뉴스 (한국어 시니어 스포츠 뉴스)
    try:
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, context=ctx, timeout=5)
        xml_data = response.read()
        root = ET.fromstring(xml_data)

        count = 0
        for item in root.findall('.//item'):
            if count >= 2: break
            title = item.find('title').text
            link = item.find('link').text
            facts.append({
                "type": "뉴스",
                "title": title,
                "content": "",
                "keywords": "시니어, 스포츠, 보건소, 커뮤니티",
                "practical_tip": "추후 분석",
                "link": link,
                "source": "외부(Google News)"
            })
            count += 1
        status["google_news"] = f"success ({count}건)"
        print(f"  - 구글 뉴스 RSS 연동 성공 ✅ ({count}건)")
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "quota" in err_str:
            status["google_news"] = "rate_limit"
        elif isinstance(e, TimeoutError) or "timed out" in err_str or "timeout" in err_str:
            status["google_news"] = "timeout"
        elif isinstance(e, (ConnectionError, OSError)):
            status["google_news"] = "connection_error"
        else:
            status["google_news"] = f"error: {type(e).__name__}"
        print(f"  - 구글 뉴스 연동 실패 ⚠️ [{status['google_news']}]: {e}")

    # 2. PubMed (영어 논문)
    try:
        search_query = urllib.parse.quote(pubmed_query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={search_query}&retmax=2&retmode=json"
        search_res = urllib.request.urlopen(search_url, context=ctx, timeout=5)
        search_data = json.loads(search_res.read())
        id_list = search_data['esearchresult']['idlist']

        count = 0
        if id_list:
            ids = ",".join(id_list)
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids}&retmode=json"
            summary_res = urllib.request.urlopen(summary_url, context=ctx, timeout=5)
            summary_data = json.loads(summary_res.read())

            for pid in id_list:
                article = summary_data['result'][pid]
                title = article.get('title', '')
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"
                # 논문 제목에서 TERM_GLOSSARY로 실제 키워드 추출
                title_lower = title.lower()
                extracted_kw = [v for k, v in TERM_GLOSSARY.items() if k in title_lower]
                keywords = ", ".join(dict.fromkeys(extracted_kw)) if extracted_kw else "노인, 운동처방"
                facts.append({
                    "type": "논문",
                    "title": title,
                    "content": "",
                    "keywords": keywords,
                    "practical_tip": "추후 분석",
                    "link": link,
                    "source": "외부(PubMed)"
                })
                count += 1
        status["pubmed"] = f"success ({count}건)"
        print(f"  - PubMed API 연동 성공 ✅ ({count}건)")
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "quota" in err_str:
            status["pubmed"] = "rate_limit"
        elif isinstance(e, TimeoutError) or "timed out" in err_str or "timeout" in err_str:
            status["pubmed"] = "timeout"
        elif isinstance(e, (ConnectionError, OSError)):
            status["pubmed"] = "connection_error"
        else:
            status["pubmed"] = f"error: {type(e).__name__}"
        print(f"  - PubMed 연동 실패 ⚠️ [{status['pubmed']}]: {e}")

    return facts, status

def extract_facts(raw_text):
    """입력된 텍스트에서 논문/뉴스를 분리하고 제목, 내용, 키워드를 추출합니다."""
    items = []
    skipped = 0
    blocks = raw_text.strip().split("\n\n")

    # 지원하는 자료 유형: 논문, 뉴스, 이론, 케이스, 용어
    type_tag_map = {
        "[논문]": "논문",
        "[뉴스]": "뉴스",
        "[이론]": "이론",
        "[케이스]": "케이스",
        "[용어]": "용어",
    }

    for block in blocks:
        lines = block.strip().split("\n")
        if not lines or not lines[0].strip():
            continue

        title_line = lines[0]
        type_ = None
        title = None
        for tag, label in type_tag_map.items():
            if title_line.startswith(tag):
                type_ = label
                title = title_line.replace(tag, "").strip()
                break

        if type_ is None:
            skipped += 1
            print(f"  [파싱 건너뜀] 인식 불가 형식: {title_line[:40]!r}")
            continue

        content = ""
        keywords = ""
        link = "링크 없음"
        practical_tip = "추후 분석"

        for line in lines[1:]:
            if line.startswith("- 초록:") or line.startswith("- 내용:"):
                content = line.split(":", 1)[1].strip()
            elif line.startswith("- 키워드:"):
                keywords = line.split(":", 1)[1].strip()
            elif line.startswith("- 링크:"):
                link = line.split(":", 1)[1].strip()

        if not content:
            print(f"  [경고] '{title}' — 내용/초록 없음, 분류 정확도 낮아질 수 있음")

        items.append({
            "type": type_,
            "title": title,
            "content": content,
            "keywords": keywords,
            "practical_tip": practical_tip,
            "link": link,
            "source": "내부"
        })

    if skipped:
        print(f"  - 파싱 실패 블록 {skipped}개 건너뜀 (형식 확인 필요) ⚠️")

    return items


def save_markdown_table(facts):
    """추출된 항목들을 output.md 파일에 표 형태로 저장합니다."""
    output_path = Path("output.md")
    
    lines = []
    lines.append("# 시니어 스포츠 학습 도우미: 데이터 추출 표\n")
    lines.append("| 자료 유형 | 제목 | 관심 키워드 | 핵심 요약 | 실전 적용 팁 | 원문 링크 |")
    lines.append("|---|---|---|---|---|---|")
    
    for f in facts:
        content = f.get('content', '').replace('\n', ' ')
        practical_tip = f.get('practical_tip', '').replace('\n', ' ')
        title = f.get('title', '').replace('\n', ' ')
        link = f.get('link', '')
        
        # 링크 형식을 마크다운으로 변환
        if link != "링크 없음":
            link_md = f"[이동하기]({link})"
        else:
            link_md = link
            
        lines.append(f"| {f.get('type', '')} | {title} | {f.get('keywords', '')} | {content} | {practical_tip} | {link_md} |")
        
    output_path.write_text("\n".join(lines), encoding="utf-8")


def score_relevance(item):
    """항목의 도메인 관련성과 보강 필요도를 0~10점으로 평가한다.
    점수는 relevance_score 필드로 저장되어 이후 단계에서 추적 가능하다."""
    score = 0
    text = (item.get("title", "") + " " + item.get("content", "") + " " + item.get("keywords", "")).lower()

    # 도메인 키워드 매칭 (최대 4점)
    score += min(sum(1 for kw in DOMAIN_KEYWORDS if kw.lower() in text), 4)
    # 내용 없음 → 보강 필요 (3점)
    if not item.get("content", ""):
        score += 3
    # 외부 자료 → 신선도 가산 (2점)
    if item.get("source", "내부") != "내부":
        score += 2
    # 내부 이론/용어이고 이미 내용 있음 → 우선순위 낮춤 (-1점)
    if item.get("type") in ("이론", "용어") and item.get("content", ""):
        score -= 1

    return max(0, score)


def classify_items(items):
    """전문가 수준의 5대 카테고리로 항목을 분류합니다."""
    grouped = {
        "이론_및_용어학습": [],
        "운동처방_및_평가": [],
        "병태생리_및_질환관리": [],
        "액티브에이징_및_인지심리": [],
        "지도론_및_정책동향": [],
        "기타": []
    }

    for item in items:
        keywords = item["keywords"]
        type_ = item.get("type", "")

        # 자료 유형이 이론/용어면 우선적으로 학습 카테고리에 배치
        if type_ in ("이론", "용어") or any(k in keywords for k in ["영어용어", "학술용어", "ACSM", "FITT", "1RM", "AWGS"]):
            grouped["이론_및_용어학습"].append(item)
        elif any(k in keywords for k in ["근력", "근감소증", "저항운동", "균형", "낙상예방", "유연성", "체력평가", "처방", "보행속도"]):
            grouped["운동처방_및_평가"].append(item)
        elif any(k in keywords for k in ["단백질", "영양", "관절염", "고혈압", "당뇨", "심혈관", "노화기전", "대사증후군", "만성질환", "노년기"]):
            grouped["병태생리_및_질환관리"].append(item)
        elif any(k in keywords for k in ["인지", "치매예방", "이중과제", "우울증", "동기부여", "여가", "커뮤니티", "수영", "레크리에이션", "어르신", "시니어"]):
            grouped["액티브에이징_및_인지심리"].append(item)
        elif any(k in keywords for k in ["보건소", "복지관", "정책", "바우처", "지도법", "안전관리", "지역상권", "이벤트", "할인"]):
            grouped["지도론_및_정책동향"].append(item)
        else:
            grouped["기타"].append(item)

    return grouped


def enrich_rule_based(item):
    """LLM 없이 규칙 기반으로 항목을 보강한다. TERM_GLOSSARY와 STUDY_TYPE_RULES가 판단 기준."""
    title_lower = item.get("title", "").lower()
    content = item.get("content", "")
    type_ = item.get("type", "")

    if type_ == "논문" and not content:
        # 연구 유형 감지 (STUDY_TYPE_RULES 기준)
        study_type = next((v for k, v in STUDY_TYPE_RULES.items() if k in title_lower), "연구")
        # 도메인 키워드 번역 (TERM_GLOSSARY 기준)
        found = [v for k, v in TERM_GLOSSARY.items() if k in title_lower]
        topics = "·".join(found[:3]) if found else "노인 운동"
        item["content"] = f"[규칙 기반] {topics} 관련 {study_type}"
        item["practical_tip"] = "원문 링크에서 구체적인 처방 수치를 확인하세요."

    elif type_ == "뉴스" and not content:
        item["practical_tip"] = "원문 링크에서 최신 시니어 스포츠 동향을 확인하세요."

    elif type_ in ("이론", "용어") and content:
        # 내용에서 처방 수치 추출 (정규식)
        import re
        nums = re.findall(r'주\s*\d+[~\-]?\d*회|RPE\s*[\d~\-]+|\d+분|\d+RM|\d+%', content)
        if nums:
            item["practical_tip"] = f"핵심 수치: {', '.join(nums[:4])}"

    return item


def enrich_facts(facts):
    """[에이전트 2] 보강 에이전트: relevance_score 순으로 정렬 후 LLM 또는 규칙 기반으로 보강."""
    # 1. 관련성 점수 계산 및 저장 (추적 가능)
    for f in facts:
        f["relevance_score"] = score_relevance(f)
    facts.sort(key=lambda f: f["relevance_score"], reverse=True)

    # 2. LLM 또는 규칙 기반 분기
    if USE_LLM and os.environ.get("GEMINI_API_KEY"):
        print(f"-> [에이전트 2] LLM 보강 중... (최대 {LLM_CALL_LIMIT}건, relevance_score 순)")
        boosted = 0
        for f in facts:
            if boosted >= LLM_CALL_LIMIT:
                break
            if f.get("practical_tip", "") in ("추후 분석", "", None):
                if boosted > 0:  # 첫 호출 전엔 sleep 불필요, 이후 호출 간격 확보
                    time.sleep(2)
                result = summarize_with_gemini(f.get("type", ""), f.get("title", ""), f.get("content", ""))
                if result:
                    f["content"] = result["korean_summary"]
                    f["why_important"] = result["why_important"]
                    f["study_point"] = result["study_point"]
                    f["practical_tip"] = result["field_tip"]
                    boosted += 1
        print(f"  - {boosted}개 항목 LLM 보강 완료 ✅")
    else:
        print("-> [에이전트 2] 규칙 기반 보강 (LLM 없음)")
        for f in facts:
            enrich_rule_based(f)
        print(f"  - {len(facts)}개 항목 규칙 기반 보강 완료 ✅")

    # 3. LLM 후 미보강 항목은 규칙으로 fallback
    for f in facts:
        if f.get("practical_tip", "") in ("추후 분석", "", None):
            enrich_rule_based(f)

    return facts


def write_output(grouped):
    """선정된 항목을 바탕으로 전문가 수준의 카테고리별 브리핑 텍스트를 작성합니다."""
    lines = []
    lines.append("===================================")
    lines.append("  [오늘의 시니어 스포츠 전문 브리핑]  ")
    lines.append("===================================")
    
    category_names = {
        "이론_및_용어학습": "📚 이론 및 용어 학습",
        "운동처방_및_평가": "🏋️‍♂️ 운동처방 및 평가",
        "병태생리_및_질환관리": "🩺 병태생리 및 질환관리",
        "액티브에이징_및_인지심리": "🧠 액티브 에이징 및 인지심리",
        "지도론_및_정책동향": "📋 지도론 및 정책동향",
        "기타": "📌 기타 소식"
    }
    
    for key, items in grouped.items():
        if not items:
            continue
            
        lines.append(f"\n▶ {category_names.get(key, key)}")
        for item in items:
            lines.append(f"  [{item['type']}] {item['title']}")
            short_content = item['content'][:40] + "..." if len(item['content']) > 40 else item['content']
            lines.append(f"  - 요약: {short_content}")
            if item.get('link') and item.get('link') != '링크 없음':
                lines.append(f"  - 링크: {item['link']}")
                
    lines.append("\n===================================")
    
    return "\n".join(lines)

def _render_section_items(lines, internal_items, external_items, empty_msg):
    """섹션 내 내부/외부 자료를 구분하여 마크다운에 렌더링하는 헬퍼입니다."""
    if internal_items:
        for item in internal_items:
            study_point = item.get('study_point', '')
            tip = item.get('practical_tip', '')
            content = item.get('content', '')
            display = study_point or tip or content[:60]
            link = item.get('link', '')
            link_md = f" → [원문]({link})" if link and link != "링크 없음" else ""
            lines.append(f"- [{item['type']}] **{item['title']}**{link_md}")
            if display and display not in ("추후 분석", "팁 생성 실패"):
                lines.append(f"  - {display}")
    elif not external_items:
        lines.append(f"- {empty_msg}")

    if external_items:
        lines.append("\n### 📡 외부 참고 자료")
        for item in external_items:
            source_tag = item.get('source', '외부')
            # 새 필드 우선, 없으면 기존 필드 fallback
            summary = item.get('content', '') or item.get('practical_tip', '')
            study_point = item.get('study_point', '')
            link = item.get('link', '')
            link_md = f" → [원문]({link})" if link and link != "링크 없음" else ""
            lines.append(f"- [{item['type']}] **{item['title']}** (출처: {source_tag}){link_md}")
            if summary:
                lines.append(f"  - {summary[:120]}")
            if study_point:
                lines.append(f"  - 📌 {study_point}")


def write_user_guides(grouped, facts=None):
    """정무현 예비 특수체육 지도자를 위한 상황/목적별 실전 가이드를 작성합니다."""
    lines = []
    lines.append("# 🎓 정무현 전공생을 위한 오늘의 특수체육 학습 가이드\n")

    # TOP N 요약 — relevance_score 상위 항목 중 논문/뉴스 우선
    if facts:
        top_candidates = sorted(
            [f for f in facts if f.get("type") in ("논문", "뉴스")],
            key=lambda f: f.get("relevance_score", 0), reverse=True
        )[:TOP_N]
        if not top_candidates:
            top_candidates = sorted(facts, key=lambda f: f.get("relevance_score", 0), reverse=True)[:TOP_N]

        lines.append("## 📌 오늘의 핵심\n")
        for i, item in enumerate(top_candidates, 1):
            sp = item.get("study_point") or item.get("content", "")[:60]
            link = item.get("link", "")
            link_md = f" → [원문]({link})" if link and link != "링크 없음" else ""
            lines.append(f"{i}. [{item['type']}] **{item['title'][:60]}**{link_md}")
            if sp:
                lines.append(f"   {sp}")
        lines.append("")
    
    # 섹션별 카테고리 매핑
    section_map = [
        {
            "title": "## 📖 1. 전공 심화 학습 (이론 및 병태생리)",
            "keys": ["이론_및_용어학습", "병태생리_및_질환관리"],
            "empty_msg": "오늘 수집된 심화 학습 자료가 없습니다.",
            "warnings": [
                "- 논문의 연구 결과는 특정 통제된 환경에서의 결과이므로 무조건적인 일반화는 피해야 합니다.",
                "- 교재에 나오지 않는 최신 이론은 반드시 원문을 통해 타당성을 교차 검증하세요."
            ]
        },
        {
            "title": "## 🏃\u200d♂️ 2. 실전 처방 케이스 스터디 (현장 실습 대비)",
            "keys": ["운동처방_및_평가", "액티브에이징_및_인지심리"],
            "empty_msg": "오늘 수집된 실전 처방 자료가 없습니다.",
            "warnings": [
                "- 이론적 처방을 실제 시니어 회원에게 적용할 때는 개인별 체력 수준과 금기 사항(안전) 파악이 최우선되어야 합니다.",
                "- 입력 자료에 부작용이나 주의사항이 빠져 있다면, 임의로 확정하지 말고 실습 전에 질문하여 보완하세요."
            ]
        },
        {
            "title": "## 📰 3. 특수체육 업계 동향 (정책 및 커뮤니티)",
            "keys": ["지도론_및_정책동향", "기타"],
            "empty_msg": "오늘 수집된 업계 동향 자료가 없습니다.",
            "warnings": [
                "- 기사에 언급된 정책이나 예산 지원 등은 지역과 시기에 따라 다르므로 섣불리 단정짓지 마세요."
            ]
        }
    ]
    
    for section in section_map:
        lines.append(section["title"])

        # 해당 섹션의 모든 항목을 모아서 내부/외부 분리
        all_items = []
        for key in section["keys"]:
            all_items.extend(grouped.get(key, []))
        
        internal = [i for i in all_items if i.get("source", "내부") == "내부"]
        external = [i for i in all_items if i.get("source", "내부") != "내부"]

        if internal or not external:
            lines.append("### 추천 학습 가이드")

        _render_section_items(lines, internal, external, section["empty_msg"])
        
        lines.append("\n### 주의할 점")
        for w in section["warnings"]:
            lines.append(w)
        lines.append("")

    lines.append("---")
    lines.append("> 본 가이드는 학습 보조 자료입니다. 실제 운동 지도 전 개인별 체력 평가와 건강 상태 확인이 필요합니다. (ACSM 가이드라인 참고)")

    return "\n".join(lines)


def save_user_guides(guides, path="output_user_guide.md"):
    """작성된 실전 가이드를 마크다운 파일로 저장합니다."""
    output_path = Path(path)
    output_path.write_text(guides, encoding="utf-8")


def review_guides_with_rules(guides):
    """규칙 기반으로 실전 가이드에 누락된 정보나 위험한 단정 표현이 없는지 점검합니다."""
    report = []
    report.append("# 🔍 검토자 에이전트 리포트\n")
    report.append("> 검토 방식: **규칙 기반 체크리스트**\n")
    report.append("## 📋 체크리스트 점검 결과")
    
    # 1. 핵심 정보 및 행동 점검
    if "오늘 수집된" in guides and "자료가 없습니다" in guides:
        report.append("- [⚠️ 주의] 일부 섹션에 수집된 자료가 없습니다. (핵심 정보 부족 가능성)")
    else:
        report.append("- [✅ 통과] 모든 섹션에 추천/해야 할 일(행동)이 포함되어 있습니다.")
        
    # 2. 대상 불분명 확인
    if "정무현 전공생" in guides or "특수체육 학습 가이드" in guides:
        report.append("- [✅ 통과] 안내 대상(특수체육 전공생/예비 지도자)이 명확합니다.")
    else:
        report.append("- [⚠️ 주의] 안내 대상이 누구인지 불분명합니다.")
        
    # 3. 위험한 단정 표현 점검
    # '주의할 점' 섹션(경고 문구)과 '📌'로 시작하는 study_point 줄은 검사 제외
    danger_words = ["무조건", "항상", "완벽한", "100%", "모든 사람에게"]
    in_warning = False
    check_lines = []
    for line in guides.split('\n'):
        if '주의할 점' in line:
            in_warning = True
        elif line.startswith('##'):
            in_warning = False
        if not in_warning and not line.strip().startswith('📌'):
            check_lines.append(line)
    check_text = '\n'.join(check_lines)

    found_dangers = [word for word in danger_words if word in check_text]

    if found_dangers:
        report.append(f"- [⚠️ 주의] 추천 본문에 단정적인 표현 발견: {', '.join(found_dangers)}")
    else:
        report.append("- [✅ 통과] 추천 본문에 위험하거나 단정적인 표현이 발견되지 않았습니다.")
    
    # 4. 외부 참고 자료 구분 확인
    if "📡 외부 참고 자료" in guides:
        report.append("- [✅ 통과] 외부 도구 결과가 내부 자료와 구분되어 표시되었습니다.")
    
    report.append("\n## 📝 최종 권고사항")
    report.append("- 제공된 가이드는 보조 수단입니다. 실제 현장 실습 및 처방 전에는 전문가와 논의하세요.")

    report_str = "\n".join(report)
    needs_refetch = "오늘 수집된" in report_str and "자료가 없습니다" in report_str
    return report_str, needs_refetch


def review_guides_with_llm(guides):
    """Gemini API를 활용하여 실전 가이드를 4가지 기준으로 검토합니다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  - GEMINI_API_KEY 없음 → 규칙 기반 검토로 전환")
        return None
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    당신은 시니어 스포츠·체육 학습 가이드의 전문 검토자입니다.
    아래 가이드를 읽고, 다음 4가지 기준으로 점검하세요.

    검토 기준:
    1. 입력 자료에 없는 내용을 단정했는가
    2. 핵심 정보가 빠졌는가
    3. 사용자가 해야 할 일이 보이는가
    4. 위험한 표현이 있는가

    가이드 전문:
    {guides}

    출력 규칙 (반드시 JSON 형식, 백틱 없이 순수 JSON만 출력):
    {{
      "unfounded_claims": "입력 자료에 없는 내용을 단정한 부분이 있다면 구체적으로 지적. 없으면 '발견되지 않음'",
      "missing_info": "빠진 핵심 정보가 있다면 구체적으로 지적. 없으면 '발견되지 않음'",
      "action_visible": "사용자가 해야 할 일(행동)이 명확한지 여부. 명확하면 '명확함', 아니면 개선 포인트 제시",
      "dangerous_expressions": "위험하거나 단정적인 표현이 있다면 구체적으로 지적. 없으면 '발견되지 않음'"
    }}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    ctx = _make_ssl_context()
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        response = urllib.request.urlopen(req, context=ctx, timeout=20)
        res_data = json.loads(response.read())
        text_res = res_data['candidates'][0]['content']['parts'][0]['text']
        text_res = text_res.replace('```json', '').replace('```', '').strip()
        result = json.loads(text_res)
        
        report = []
        report.append("# 🔍 검토자 에이전트 리포트\n")
        report.append("> 검토 방식: **Gemini API (LLM 보조 검토)**\n")
        report.append("## 📋 LLM 검토 결과")
        
        labels = {
            "unfounded_claims": "근거 없는 단정",
            "missing_info": "핵심 정보 누락",
            "action_visible": "행동 명확성",
            "dangerous_expressions": "위험한 표현"
        }
        for key, label in labels.items():
            value = result.get(key, "확인 불가")
            icon = "✅" if "발견되지 않음" in str(value) or "명확" in str(value) else "⚠️"
            report.append(f"- [{icon}] **{label}**: {value}")
        
        report.append("\n## 📝 최종 권고사항")
        report.append("- LLM 검토 결과는 보조 의견입니다. 최종 판단은 사용자가 직접 하세요.")

        report_str = "\n".join(report)
        needs_refetch = "발견되지 않음" not in report_str  # LLM이 문제를 발견하면 재수집 신호
        return report_str, needs_refetch
    except Exception as e:
        print(f"  - Gemini 검토 API 오류: {e} → 규칙 기반 검토로 전환")
        return None


def send_to_telegram(guides):
    """오늘의 핵심 요약을 텔레그램으로 전송합니다. 실패해도 기본 실행에 영향 없음."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("  - 텔레그램 설정 없음 (TELEGRAM_BOT_TOKEN/CHAT_ID 미설정)")
        return

    # 오늘의 핵심 섹션만 추출 (4096자 제한 대응)
    lines = guides.split('\n')
    msg_lines = []
    in_top = False
    for line in lines:
        if '📌 오늘의 핵심' in line:
            in_top = True
        if in_top:
            msg_lines.append(line)
        # 핵심 섹션 끝 (다음 ## 섹션 시작)
        if in_top and line.startswith('## ') and '핵심' not in line:
            break

    message = '\n'.join(msg_lines).strip()
    if not message:
        message = guides[:2000]

    # 텔레그램은 Markdown 특수문자 일부를 이스케이프해야 함
    for ch in ['[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        message = message.replace(ch, f'\\{ch}')

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message[:4096],
        "parse_mode": "MarkdownV2"
    }).encode('utf-8')

    ctx = _make_ssl_context()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, context=ctx, timeout=10)
        print("  - 텔레그램 전송 완료 ✅")
    except Exception as e:
        print(f"  - 텔레그램 전송 실패 ⚠️: {e}")


def review_guides(guides):
    """검토자 에이전트 라우터. USE_LLM_REVIEW 플래그에 따라 분기하고, 실패 시 규칙 기반으로 fallback합니다.
    Returns: (report_str, needs_refetch) 튜플
    """
    if USE_LLM_REVIEW:
        result = review_guides_with_llm(guides)
        if result is not None:
            return result
        print("  - LLM 검토 실패 → 규칙 기반 검토로 fallback")
    return review_guides_with_rules(guides)


def main():
    load_env()
    
    # 1. 입력 자료 (내부 자료 풀 - 외부 도구 실패해도 의미 있는 결과를 보장)
    SAMPLE_INPUT = """
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

[뉴스] 프로 스포츠 구단, 지역 상권 활성화 이벤트
- 내용: 지역 주민들을 위해 야구장 인근 식당 방문 시 티켓을 할인해준다.
- 키워드: 프로야구, 지역상권, 할인
- 링크: https://example.com/news/2

[이론] ACSM 노인 운동 가이드라인 (Aerobic)
- 내용: ACSM은 65세 이상 성인에게 주 5일 이상 중강도(RPE 5~6) 유산소 운동을 최소 30분씩 권고한다. 고강도일 경우 주 3일 20분 이상.
- 키워드: ACSM, 유산소, 노인, FITT, 강도
- 링크: https://example.com/theory/acsm-aerobic

[이론] FITT-VP 원칙과 시니어 저항운동 처방
- 내용: 빈도(Frequency) 주 2~3회, 강도(Intensity) 1RM의 60~80%, 시간(Time) 8~10종목 1~3세트, 형태(Type) 대근육군 우선이 시니어 저항운동의 기본이다.
- 키워드: FITT, 저항운동, 근력, 처방, 1RM
- 링크: https://example.com/theory/fitt-vp

[이론] 근감소증(Sarcopenia) 진단 기준 - AWGS 2019
- 내용: 아시아근감소증워킹그룹(AWGS) 2019 기준은 악력(남<28kg, 여<18kg), 보행속도(<1.0m/s), 근육량(SMI) 감소를 종합 평가한다.
- 키워드: 근감소증, 진단, AWGS, 악력, 보행속도, 노화기전
- 링크: https://example.com/theory/awgs-2019

[케이스] 고혈압 시니어 저항운동 처방 사례
- 내용: 수축기 140~159mmHg 회원에게는 발살바 호흡 금지, 1RM 40~60% 저강도부터 시작, 운동 전후 혈압 측정을 필수로 한다.
- 키워드: 고혈압, 저항운동, 만성질환, 안전관리, 처방
- 링크: https://example.com/case/htn-resistance

[케이스] 무릎관절염 회원 아쿠아 운동 적용
- 내용: KL grade 2 이상의 무릎 골관절염 회원은 체중부하를 줄인 수중 운동(수온 30~32℃, 30~45분)이 통증 없이 근력을 키우는 데 효과적이다.
- 키워드: 관절염, 수영, 무릎, 만성질환, 처방
- 링크: https://example.com/case/knee-aqua

[용어] sarcopenia
- 내용: sarcopenia = 근감소증. 노화에 따른 골격근량과 근력의 점진적 감소를 의미한다. 발음 [sɑːrkoʊˈpiːniə].
- 키워드: 영어용어, 근감소증, 노화기전, 학술용어
- 링크: https://example.com/term/sarcopenia

[용어] frailty
- 내용: frailty = 노쇠. 생리적 예비력 감소로 외부 스트레스에 취약해진 상태. Fried criteria 5개 중 3개 이상 해당 시 진단.
- 키워드: 영어용어, 노쇠, 노화기전, 학술용어
- 링크: https://example.com/term/frailty

[용어] gait speed
- 내용: gait speed = 보행속도. 4m 또는 6m 거리를 걷는 시간으로 측정. 1.0m/s 미만이면 근감소증/낙상 위험 지표.
- 키워드: 영어용어, 보행속도, 체력평가, 낙상예방, 학술용어
- 링크: https://example.com/term/gait-speed

[용어] balance training
- 내용: balance training = 균형훈련. 한 발 서기, 태극권, BOSU 등. 시니어 낙상예방에 주 2~3회 권장.
- 키워드: 영어용어, 균형, 낙상예방, 학술용어
- 링크: https://example.com/term/balance-training
"""

    print(f"-> 설정: USE_LLM={USE_LLM}, USE_EXTERNAL={USE_EXTERNAL}, INTERNAL_SAMPLE_SIZE={INTERNAL_SAMPLE_SIZE}")

    # [에이전트 1] 핵심 정보 추출
    print("\n[에이전트 1] 자료 추출 중...")
    all_internal = extract_facts(SAMPLE_INPUT)

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    # 이론/용어: 큐레이션된 학습 자료로 항상 포함, 링크는 불필요
    theory_vocab = [i for i in all_internal if i["type"] in ("이론", "용어")]
    for item in theory_vocab:
        item["link"] = "링크 없음"
    theory_n = min(THEORY_SAMPLE_SIZE, len(theory_vocab))
    facts = random.sample(theory_vocab, theory_n)
    print(f"  - 이론/용어 {theory_n}개 추출 ✅")

    # 논문/뉴스/케이스: 외부 데이터가 있으면 외부 사용, 없으면 내부로 보충
    if USE_EXTERNAL:
        print("  - 외부 API에서 보조 데이터 가져오는 중...")
        external_facts, ext_status = fetch_external_context()
        for source, state in ext_status.items():
            print(f"    [{source}] {state}")
        if external_facts:
            facts.extend(external_facts)
            print(f"  - 외부 도구에서 {len(external_facts)}개 항목 추가 ✅")
        else:
            other_internal = [i for i in all_internal if i["type"] not in ("이론", "용어")]
            other_n = min(INTERNAL_SAMPLE_SIZE - theory_n, len(other_internal))
            facts.extend(random.sample(other_internal, other_n))
            print(f"  - 외부 데이터 없음, 내부 샘플 {other_n}개로 보충 ⚠️")
    else:
        other_internal = [i for i in all_internal if i["type"] not in ("이론", "용어")]
        other_n = min(INTERNAL_SAMPLE_SIZE - theory_n, len(other_internal))
        facts.extend(random.sample(other_internal, other_n))
        print(f"  - 외부 도구 비활성화, 내부 샘플 {other_n}개 추가")

    print("\n=== facts ===")
    for f in facts:
        print(f)

    # [에이전트 2] LLM 보강
    facts = enrich_facts(facts)

    save_markdown_table(facts)
    print("  - output.md 저장 완료 ✅")

    # [에이전트 3] 분류
    print("\n[에이전트 3] 분류 중...")
    grouped = classify_items(facts)
    print("=== grouped ===")
    print(grouped)

    # [에이전트 4] 최종 출력 작성
    print("\n[에이전트 4] 최종 출력 작성 중...")
    result = write_output(grouped)
    print("=== result ===")
    print(result)
    guides = write_user_guides(grouped, facts)
    save_user_guides(guides)
    print("  - output_user_guide.md 저장 완료 ✅")

    # [에이전트 5] 검토자
    print("\n[에이전트 5] 검토자 점검 중...")
    review_report, needs_refetch = review_guides(guides)
    print("=== review_report ===")
    print(review_report)

    # 피드백 루프: 자료 부족 감지 시 다른 쿼리로 1회 재수집
    if needs_refetch and USE_EXTERNAL:
        print("\n[검토자 → 에이전트 1] 자료 부족 감지 → 다른 쿼리로 재수집 중...")
        extra_facts, extra_status = fetch_external_context(
            query="노인 낙상예방 OR 시니어 재활운동",
            pubmed_query="fall prevention elderly OR balance training older adults"
        )
        for source, state in extra_status.items():
            print(f"    [{source}] {state}")
        if extra_facts:
            extra_facts = enrich_facts(extra_facts)
            facts.extend(extra_facts)
            grouped = classify_items(facts)
            guides = write_user_guides(grouped, facts)
            save_user_guides(guides)
            print("  - 재수집 후 가이드 갱신 완료 ✅")
            review_report, _ = review_guides(guides)  # 갱신된 가이드 재검토
        else:
            print("  - 재수집도 데이터 없음, 기존 가이드 유지 ⚠️")

    Path("review_report.md").write_text(review_report, encoding="utf-8")
    print("  - review_report.md 저장 완료 ✅")

    # 텔레그램 전송
    print("\n텔레그램으로 오늘의 핵심 전송 중...")
    send_to_telegram(guides)


if __name__ == "__main__":
    main()
