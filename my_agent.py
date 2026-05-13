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
INTERNAL_SAMPLE_SIZE = 5  # 내부 풀에서 무작위로 뽑을 항목 수

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
    당신은 최고 수준의 [노인체육 지도자]이자 [운동처방사]입니다. 만성질환과 근감소증 등 노화의 생리학적 기전을 완벽히 이해하고 있으며, 실제 현장에서 시니어 회원을 안전하고 효과적으로 지도하는 실무 감각을 갖추고 있습니다.

    태스크:
    제공된 논문/뉴스의 제목과 내용을 분석하여, 현장 지도자들이 즉시 적용할 수 있는 핵심 요약과 운동 처방 팁을 도출하세요.

    입력 데이터:
    - 자료 유형: {type_}
    - 제목: {title}
    - 내용: {content}

    출력 규칙 (반드시 JSON 형식, 백틱 없이 순수 JSON만 출력):
    {{
      "summary": "논문/뉴스의 핵심 결과를 생리학적/운동학적 관점에서 1~2줄로 전문적으로 요약할 것.",
      "practical_tip": "실제 시니어 체육 현장(복지관 등)에서 적용할 구체적인 운동 처방 가이드(강도, 주의사항 등)를 1줄로 제시할 것."
    }}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    ctx = _make_ssl_context()

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        time.sleep(2)  # 무료 티어 API 동시 요청 제한을 피하기 위해 2초 대기
        response = urllib.request.urlopen(req, context=ctx, timeout=15)
        res_data = json.loads(response.read())
        text_res = res_data['candidates'][0]['content']['parts'][0]['text']
        # 백틱 등 마크다운 잔재 제거
        text_res = text_res.replace('```json', '').replace('```', '').strip()
        result = json.loads(text_res)
        return result.get("summary", "요약 생성 실패"), result.get("practical_tip", "팁 생성 실패")
    except Exception as e:
        print(f"    - Gemini API 오류: {e}")
        return "뉴스/논문 원문을 확인해주세요.", "추후 분석 (API 호출 실패)"

def fetch_external_context(query="시니어 스포츠 OR 보건소 운동 프로그램", pubmed_query="sarcopenia OR elderly exercise"):
    """구글 뉴스 및 PubMed에서 보조 데이터를 가져옵니다. (외부 도구 - 보강 정보)"""
    facts = []

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
            
            # Gemini를 활용한 고도화 요약 및 팁 생성
            summary, practical_tip = summarize_with_gemini("뉴스", title, title)
            
            facts.append({
                "type": "뉴스",
                "title": title,
                "content": summary,
                "keywords": "시니어, 스포츠, 보건소, 커뮤니티",
                "practical_tip": practical_tip,
                "link": link
            })
            count += 1
        print("  - 구글 뉴스 RSS 연동 성공 ✅")
    except Exception as e:
        print(f"  - 구글 뉴스 연동 실패 ⚠️: {e}")

    # 2. PubMed (영어 논문)
    try:
        search_query = urllib.parse.quote(pubmed_query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={search_query}&retmax=2&retmode=json"
        search_res = urllib.request.urlopen(search_url, context=ctx, timeout=5)
        search_data = json.loads(search_res.read())
        id_list = search_data['esearchresult']['idlist']
        
        if id_list:
            ids = ",".join(id_list)
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids}&retmode=json"
            summary_res = urllib.request.urlopen(summary_url, context=ctx, timeout=5)
            summary_data = json.loads(summary_res.read())
            
            for pid in id_list:
                article = summary_data['result'][pid]
                title = article.get('title', '')
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"
                
                # Gemini를 활용한 고도화 요약 및 팁 생성
                summary, practical_tip = summarize_with_gemini("논문", title, title)
                
                facts.append({
                    "type": "논문",
                    "title": title,
                    "content": summary,
                    "keywords": "근감소증, 노년기, 운동처방",
                    "practical_tip": practical_tip,
                    "link": link
                })
        print("  - PubMed API 연동 성공 ✅")
    except Exception as e:
        print(f"  - PubMed 연동 실패 ⚠️: {e}")
        
    return facts

def extract_facts(raw_text):
    """입력된 텍스트에서 논문/뉴스를 분리하고 제목, 내용, 키워드를 추출합니다."""
    items = []
    blocks = raw_text.strip().split("\n\n")
    
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
            
        title_line = lines[0]
        # 지원하는 자료 유형: 논문, 뉴스, 이론, 케이스, 용어
        type_tag_map = {
            "[논문]": "논문",
            "[뉴스]": "뉴스",
            "[이론]": "이론",
            "[케이스]": "케이스",
            "[용어]": "용어",
        }
        type_ = None
        title = None
        for tag, label in type_tag_map.items():
            if title_line.startswith(tag):
                type_ = label
                title = title_line.replace(tag, "").strip()
                break
        if type_ is None:
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
        
        items.append({
            "type": type_,
            "title": title,
            "content": content,
            "keywords": keywords,
            "practical_tip": practical_tip,
            "link": link
        })
        
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
    print("1. 자료 추출 중...")

    # 베이스: 내부 자료 풀 (규칙 기반 추출 - 외부 도구가 실패해도 동작)
    all_internal = extract_facts(SAMPLE_INPUT)
    # 매 실행마다 다른 결과가 나오도록 풀에서 무작위 샘플링
    sample_n = min(INTERNAL_SAMPLE_SIZE, len(all_internal))
    facts = random.sample(all_internal, sample_n)
    print(f"  - 내부 풀 {len(all_internal)}개에서 {sample_n}개 무작위 추출 ✅")

    # 부가: 외부 도구로 보강 (실패해도 베이스 facts는 유지)
    if USE_EXTERNAL:
        print("-> 외부 API에서 보조 데이터를 가져오는 중...")
        external_facts = fetch_external_context()
        if external_facts:
            facts.extend(external_facts)
            print(f"  - 외부 도구에서 {len(external_facts)}개 항목 추가 ✅")
        else:
            print("  - 외부 데이터 없음 (베이스 자료로 진행) ⚠️")
    else:
        print("-> 외부 도구 비활성화 (USE_EXTERNAL=False)")

    # LLM 보강: practical_tip이 비어있는 내부 자료에도 Gemini 요약/팁 적용
    # 무료 티어 Rate Limit(분당 10회) 회피를 위해 보강 항목 수를 제한한다.
    LLM_BOOST_LIMIT = 2
    if USE_LLM and os.environ.get("GEMINI_API_KEY"):
        print(f"-> LLM으로 내부 자료의 요약/팁 보강 중... (최대 {LLM_BOOST_LIMIT}건)")
        boosted = 0
        for f in facts:
            if boosted >= LLM_BOOST_LIMIT:
                break
            if f.get("practical_tip", "") in ("추후 분석", "", None):
                _, tip = summarize_with_gemini(f.get("type", ""), f.get("title", ""), f.get("content", ""))
                if tip and "실패" not in tip and "비활성화" not in tip:
                    f["practical_tip"] = tip
                    boosted += 1
        print(f"  - {boosted}개 항목에 LLM 팁 보강 완료 ✅")
        
    print("\n=== facts ===")
    for f in facts:
        print(f)
    print("\n")
    
    print("-> output.md 파일에 Markdown 표를 저장합니다...")
    save_markdown_table(facts)
    print("✅ output.md 저장 완료!\n")
    
    print("2. 관련성 점수 분류 및 선정 중...")
    grouped = classify_items(facts)
    print("=== grouped ===")
    print(grouped)
    print("\n")
    
    print("3. 브리핑 결과 생성 중...")
    result = write_output(grouped)
    print("=== result ===")
    print(result)


if __name__ == "__main__":
    main()
