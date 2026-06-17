Week 13. 내 에이전트 개선: Streamlit 입출력과 검토자
12주차에는 내 입력 자료에서 핵심 정보를 추출하고 output.md 표를 만들었다.
이번 주에는 Streamlit 화면에서 입력 자료를 넣고, 사용자나 상황에 맞는 최종 출력문과 검토 결과를 바로 확인하게 한다.
기본형은 규칙 기반 검토자이고, 선택 확장으로 Groq API를 먼저 사용하고 OpenAI API를 fallback으로 사용하는 LLM 검토자를 붙일 수 있다.
학습 목표
내 에이전트의 최종 출력문을 생성한다.
Streamlit으로 입력과 출력을 한 화면에서 확인한다.
출력 작성 에이전트와 검토자 에이전트의 역할을 구분한다.
코딩에이전트에게 “기존 구조를 유지한 채 기능 추가”를 요청한다.
최종 출력 파일 output_user_guide.md를 만든다.
Streamlit 화면에서 output.md, output_user_guide.md, review_report.md에 해당하는 내용을 확인한다.
규칙 기반 검토자와 LLM 검토자의 차이를 구분한다.
결과의 한계와 수정 필요 사항을 기록한다.
이번 주 핵심 원칙
12주차 코드를 버리지 않는다.
출력 작성 기능을 추가하되, 추출과 분류 구조는 유지한다.
기본형 검토자 에이전트는 복잡한 평가자가 아니라 체크리스트 역할만 한다.
사용자가 오해할 수 있는 문장은 줄인다.
LLM 검토자를 쓰더라도 검토 기준은 사람이 정한다.
Streamlit을 기본 사용자 화면으로 삼고, 핵심 처리 로직은 기존 파일에 둔다.
최종 제출을 생각하며 README와 실행 흐름을 정리하기 시작한다.
13주차 구현 수준
이번 주에도 기본형만으로 제출할 수 있다. 12주차에 OpenAI API, Groq API, 외부 도구를 붙인 학생은 그 결과를 최종 출력과 검토에 반영한다.
수준
설명
기본형
규칙 기반으로 최종 출력과 검토 보고서를 만들고 Streamlit 화면에 표시한다
중급형
Groq API로 검토자 역할을 보조하고, 실패하면 OpenAI API 또는 규칙 기반 검토로 돌아간다
확장형
외부 도구 결과를 최종 출력과 Streamlit 화면에 반영한다
주의할 점:
LLM 검토자는 최종 판단자가 아니라 보조 검토자이다.
입력 자료에 없는 내용을 새로 지어내면 안 된다.
API 키가 없어도 Streamlit 기본 화면은 실행되어야 한다.
python my_agent.py 또는 python schedule_agent.py 실행은 개발과 검증을 위한 보조 실행으로 유지한다.
13.1 오늘의 구조
일정공지 예시에서는 사용자별 안내문을 만들었다. 이번 주에는 그 결과를 파일뿐 아니라 Streamlit 화면에서도 확인한다.
[Streamlit 입력창 또는 입력 파일]
   ↓
[핵심 정보 추출 에이전트]
   ↓
[분류 에이전트]
   ↓
[최종 출력 작성 에이전트]
   ↓
[검토자 에이전트]
   ↓
[Streamlit 화면 출력]
   ↓
[output.md, output_user_guide.md, review_report.md 저장]
​
함수 이름 예시는 다음과 같다.
함수
역할
extract_facts
입력 자료에서 핵심 정보를 뽑는다
classify_items
유형별로 항목을 묶는다
write_user_guides
사용자나 상황별 최종 출력문을 쓴다
review_guides
누락 정보와 단정 표현을 확인한다
save_user_guides
결과를 파일로 저장한다
streamlit_app.py
입력창, 실행 버튼, 결과 화면을 제공한다
함수 이름은 달라도 되지만 역할은 구분되어야 한다.
권장 파일 구조는 다음과 같다.
my_agent.py 또는 schedule_agent.py   # 핵심 처리 로직
streamlit_app.py                    # 화면 입출력
sample_notices.txt                  # 입력 예시
output.md                           # 추출/분류 결과
output_user_guide.md                # 최종 안내문
review_report.md                    # 검토 보고서
​
실행 명령은 macOS와 Windows에서 거의 같다. Windows에서 python 명령이 동작하지 않으면 py를 사용한다.
13.2 출력 대상 정하기
일정공지 예시에서는 전체 학생, 1학년, 4학년 같은 사용자 유형을 사용했다. 내 에이전트에서는 주제에 맞는 출력 대상을 정한다.
주제
출력 대상 예시
일정공지
전체 학생, 1학년, 4학년, 교환학생 준비생
독서 추천
초보 독자, 전공 학습자, 가벼운 독서 독자
운동 루틴
초급자, 중급자, 고급자
여행 계획
저예산 여행자, 가족 여행자, 당일치기 여행자
모든 유형을 반드시 만들 필요는 없다. 입력 자료에 따라 일부 유형만 나와도 된다.
13.3 최종 출력 예시
output_user_guide.md와 Streamlit 화면의 안내문은 다음과 같은 형태면 된다. 제목과 문장은 자기 주제에 맞게 바꾼다.
# 내 에이전트 결과 안내

## 초급자

### 추천 또는 해야 할 일
- 첫 번째 항목을 확인한다.
- 준비물이나 조건을 확인한다.

### 주의할 점
- 입력 자료에 없는 내용은 확정하지 않는다.
- 부족한 정보는 직접 확인해야 한다.

## 중급자

### 추천 또는 해야 할 일
- 두 번째 항목을 실행한다.

### 주의할 점
- 일정, 비용, 조건이 빠져 있으면 확인한다.
​
13.4 코딩에이전트 요청 1: 최종 출력 함수 추가
먼저 계획을 받는다.
my_agent.py 또는 schedule_agent.py를 읽어줘.
12주차 구조를 유지하면서 최종 출력 작성 기능을 추가하려고 해.

추가할 함수:
- write_user_guides(grouped)
- save_user_guides(guides, path="output_user_guide.md")

내 에이전트 주제에 맞게 사용자나 상황별 안내문을 만들고 싶어.

아직 파일을 수정하지 말고,
어떤 데이터를 입력받아 어떤 Markdown 문자열을 만들지 계획만 말해줘.
​
계획이 적절하면 수정시킨다.
좋아. 이제 write_user_guides와 save_user_guides를 추가해줘.

조건:
- grouped dict를 입력으로 받는다.
- 유형별로 추천 또는 해야 할 일과 주의할 점을 Markdown으로 만든다.
- output_user_guide.md에 저장한다.
- 기존 extract_facts, classify_items 함수의 큰 구조는 유지한다.
- 실제 입력 자료에 없는 내용은 단정하지 않는다.
​
13.5 코딩에이전트 요청 2: Streamlit 화면 추가
Streamlit은 에이전트의 판단을 대신하는 도구가 아니다. 사용자가 입력을 넣고 결과를 쉽게 확인하게 하는 화면 도구이다.
권장 구조:
streamlit_app.py
   ↓ import
my_agent.py 또는 schedule_agent.py
   ↓ 함수 호출
extract_facts → classify_items → write_user_guides → review_guides
​
요청문:
streamlit_app.py를 추가해줘.

역할:
- 공지 텍스트를 입력하는 큰 입력창을 만든다.
- 기본값으로 sample_notices.txt 내용을 불러올 수 있으면 넣는다.
- "실행" 버튼을 누르면 기존 함수들을 호출한다.
- 추출/분류 결과, 사용자별 안내문, 검토 보고서를 화면에 나누어 보여준다.
- 기존 my_agent.py 또는 schedule_agent.py의 핵심 로직은 크게 바꾸지 않는다.
- 기본 실행은 `streamlit run streamlit_app.py`로 한다.
- 기존 `python my_agent.py` 또는 `python schedule_agent.py` 실행은 개발과 검증용으로 계속 가능해야 한다.

먼저 수정 계획만 말해줘. 아직 파일을 수정하지 마.
​
13.6 코딩에이전트 요청 3: 검토자 에이전트 추가
검토자는 안내문을 다시 쓰는 역할이 아니다. 빠진 정보와 위험한 표현을 알려주는 역할이다.
검토 기준:
기준
확인 내용
핵심 정보
필요한 정보가 빠진 항목이 있는가
대상
누구에게 해당하는지 불분명한가
근거
입력 자료에 없는 내용을 단정했는가
행동
사용자가 무엇을 해야 하는지 보이는가
요청문:
review_guides 함수를 추가해줘.

역할:
- guides 문자열을 입력으로 받는다.
- 핵심 정보가 빠진 항목, 대상이 불분명한 항목, 입력 자료에 없는 단정 표현을 점검한다.
- 결과는 review_report 문자열로 반환한다.
- 복잡한 AI 판단은 하지 말고 간단한 체크리스트 문장으로 작성한다.
- main에서 검토 결과를 출력하고 review_report.md에도 저장한다.
​
13.7 선택 확장: Groq API 검토자와 OpenAI fallback 붙이기
Groq API는 검토자 역할에 먼저 사용한다. Groq 호출이 실패하거나 .env에 GROQ_API_KEY가 없으면 OpenAI API로 fallback한다. OpenAI API는 .env에 OPENAI_API_KEY가 있을 때 저렴하고 간단한 검토용 모델인 gpt-5-mini를 사용한다. OpenAI도 사용할 수 없으면 규칙 기반 검토자로 돌아간다.
검토자 LLM은 최종 안내문을 다시 읽고, 누락 정보나 과장 표현을 점검하는 보조 역할만 한다.
권장 구조:
USE_LLM_REVIEW = False
OPENAI_REVIEW_MODEL = "gpt-5-mini"

def review_guides(guides):
    if USE_LLM_REVIEW:
        return review_guides_with_llm(guides)
    return review_guides_with_rules(guides)

def review_guides_with_llm(guides):
    try:
        return review_guides_with_groq(guides)
    except Exception:
        try:
            return review_guides_with_openai(guides)
        except Exception:
            return review_guides_with_rules(guides)
​
코딩에이전트 요청:
review_guides 함수를 확장하고 싶어.

요구사항:
- 기존 규칙 기반 검토는 review_guides_with_rules 함수로 유지해줘.
- Groq API를 쓰는 review_guides_with_groq 함수를 먼저 호출해줘.
- GROQ_API_KEY는 .env 또는 환경변수에서 읽고, 코드에 직접 쓰지 마.
- Groq API 키가 없거나 호출에 실패하면 review_guides_with_openai로 fallback해줘.
- OpenAI API를 쓰는 review_guides_with_openai 함수를 fallback 용도로 추가해줘.
- OpenAI 모델은 gpt-5-mini를 기본값으로 사용해줘.
- OPENAI_API_KEY도 .env 또는 환경변수에서 읽고, 코드에 직접 쓰지 마.
- OpenAI 호출도 실패하면 review_guides_with_rules로 돌아가게 해줘.
- USE_LLM_REVIEW = False가 기본값이어야 해.
- LLM 검토 프롬프트에는 다음 기준을 넣어줘.
  1. 입력 자료에 없는 내용을 단정했는가
  2. 핵심 정보가 빠졌는가
  3. 사용자가 해야 할 일이 보이는가
  4. 위험한 표현이 있는가

먼저 수정 계획만 말해줘. 아직 파일을 수정하지 마.
​
13.8 선택 확장: 외부 도구 결과를 출력에 반영하기
12주차에 외부 도구를 붙였다면, 13주차에는 그 결과를 최종 출력에 반영한다.
예:
주제
외부 도구 결과 반영 예시
여행 계획
날씨가 비이면 우산 준비를 주의사항에 추가
독서 추천
도서 검색 결과의 저자나 출판연도를 출력에 포함
뉴스 요약
RSS 출처 이름을 결과에 표시
학습 도우미
참고 자료 파일명을 안내문에 표시
코딩에이전트 요청:
12주차에 추가한 외부 도구 결과를 output_user_guide.md에 반영하고 싶어.

조건:
- 외부 도구 결과는 보조 정보로만 사용해줘.
- 외부 도구 결과가 없으면 기존 안내문만 생성되게 해줘.
- 입력 자료와 외부 도구 결과를 구분해서 표현해줘.
- 과장하거나 확정하지 말고 "확인 필요", "참고" 같은 표현을 사용해줘.

먼저 수정 계획만 말해줘. 아직 파일을 수정하지 마.
​
13.9 실행과 확인
기본 실행은 Streamlit 화면이다.
macOS와 Windows 공통:
streamlit run streamlit_app.py
​
개발과 검증을 위해 Python 보조 실행도 확인한다.
macOS 또는 Windows에서 python 명령이 동작하는 경우:
python my_agent.py
​
또는 일정공지 예시 프로젝트라면 다음처럼 실행한다.
python schedule_agent.py
​
Windows에서 python 명령이 동작하지 않으면 다음처럼 실행한다.
py my_agent.py
​
일정공지 예시 프로젝트라면 다음처럼 실행한다.
py schedule_agent.py
​
가상환경을 사용하는 경우 활성화 명령은 운영체제별로 다르다.
운영체제
가상환경 활성화 예시
macOS
source .venv/bin/activate
Windows PowerShell
.venv\\\\Scripts\\\\Activate.ps1
Windows CMD
.venv\\\\Scripts\\\\activate.bat
확인할 파일:
output.md
output_user_guide.md
review_report.md
​
확인할 화면:
입력창
실행 버튼
추출/분류 결과
사용자별 안내문
검토 보고서
​
확인 질문:
질문
답
Streamlit 기본 화면이 실행되는가
macOS 또는 Windows에서 실행 명령이 맞게 안내되었는가
입력창에 공지 텍스트를 넣을 수 있는가
실행 버튼으로 결과를 만들 수 있는가
최종 출력문이 생성되었는가
화면에서 최종 출력문을 확인할 수 있는가
내 주제의 사용자나 상황별로 나뉘어 있는가
“반드시”, “무조건”, “항상 가능” 같은 단정 표현이 없는가
검토 보고서가 파일과 화면에 모두 표시되는가
Python 보조 실행도 가능한가
LLM 검토자나 외부 도구를 썼다면 fallback이 되는가
다음 주 최종 제출을 위해 무엇을 정리해야 하는가
13.10 README 초안 만들기
13주차 말에는 README 초안을 만든다. 코딩에이전트에게 다음처럼 요청한다.
현재 my_agent.py 또는 schedule_agent.py의 기능을 바탕으로 README.md 초안을 만들어줘.

포함할 내용:
- 프로젝트 이름
- 한 문장 설명
- 기본 실행 방법: macOS/Windows 공통 `streamlit run streamlit_app.py`
- 보조 실행 방법: macOS/Windows `python my_agent.py` 또는 Windows `py my_agent.py`
- 일정공지 예시라면 `python schedule_agent.py` 또는 Windows `py schedule_agent.py`
- 가상환경 활성화 방법: macOS와 Windows를 구분해서 작성
- 입력 파일
- 출력 파일
- 화면에서 확인할 수 있는 결과
- 에이전트 역할 4개
- 현재 한계

과장하지 말고, 실제 구현된 내용만 써줘.
​
체크리스트
output_user_guide.md가 생성된다.
review_report.md가 생성된다.
streamlit_app.py가 있다.
Streamlit 화면에서 입력과 결과를 확인할 수 있다.
macOS와 Windows 실행 방법이 모두 설명되어 있다.
출력 작성자와 검토자의 역할이 구분된다.
Groq API, OpenAI API, 외부 도구를 썼다면 실패해도 Streamlit 기본 실행이 가능하다.
Python 보조 실행 방법도 설명되어 있다.
README 초안이 있다.
14주차 최종 제출을 위한 남은 작업이 정리되어 있다.
부록. 순차 함수형 구조와 LangGraph 구조의 차이
13주차까지의 기본 일정공지 에이전트는 LangGraph를 쓰지 않는다. 기본 구현은 순차 함수형 멀티에이전트이다.
extract_facts()
→ classify_items()
→ write_user_guides()
→ review_guides()
​
각 함수가 하나의 에이전트 역할을 맡고, 앞 함수의 출력이 다음 함수의 입력으로 들어간다. 흐름이 고정되어 있기 때문에 초보자가 이해하기 쉽고, 실행 오류를 찾기도 쉽다.
LangGraph는 같은 역할들을 그래프의 node로 바꾸고, 중간 결과를 State에 저장하면서 실행한다.
State
→ extract_node
→ classify_node
→ guide_node
→ review_node
→ END
​
비교하면 다음과 같다.
항목
순차 함수형 구조
LangGraph 구조
실행 단위
Python 함수
Graph node
흐름
정해진 순서
edge와 conditional edge
중간 정보
변수로 전달
State에 저장
분기
if문으로 직접 처리
조건부 edge로 처리
반복
직접 while 또는 재호출 작성
그래프 순환 edge로 표현
장점
단순하고 빠르게 완성 가능
분기, 반복, 상태 추적에 강함
단점
복잡한 흐름이 커지면 관리가 어려움
처음 배우기에는 구조가 무거움
적합한 경우
항상 같은 순서로 처리하는 프로젝트
검토 후 재작성, 조건별 경로, 중간 상태 저장이 필요한 프로젝트
현재 일정공지 에이전트는 보통 다음 흐름이면 충분하다.
입력 → 추출 → 분류 → 안내문 작성 → 검토 → 출력
​
따라서 기본형에서는 순차 함수형 구조가 적절하다.
LangGraph로 바꾸는 것이 필요한 경우는 다음과 같다.
검토 결과가 나쁘면 안내문 작성 단계로 되돌아가야 한다.
공지 유형에 따라 다른 처리 경로를 타야 한다.
사용자가 질문을 추가하면 일부 단계만 다시 실행해야 한다.
중간 상태를 저장하고 나중에 이어서 실행해야 한다.
Supervisor가 다음 에이전트를 선택하는 구조가 필요하다.
LangGraph로 바꿀 때의 매핑
기존 함수는 그대로 버리지 않고 node 함수로 감싼다.
기존 함수
LangGraph node 예시
State에 저장할 값
load_notices
load_node
text
extract_facts
extract_node
items
classify_items
classify_node
grouped
write_user_guides
guide_node
guides
review_guides
review_node
review_report
저장 함수
save_node
output_paths
State 예시는 다음과 같다.
class AgentState(TypedDict):
    text: str
    items: list[dict]
    grouped: dict
    guides: str
    review_report: str
    output_paths: list[str]
​
가장 단순한 LangGraph 흐름은 순차형 그래프이다.
START
→ extract_node
→ classify_node
→ guide_node
→ review_node
→ save_node
→ END
​
이 구조는 함수형 순차 실행과 거의 같다. LangGraph를 쓰는 의미가 커지는 지점은 조건부 분기를 넣을 때이다.
예를 들어 검토 결과에 "수정 필요"가 있으면 다시 안내문 작성으로 되돌릴 수 있다.
review_node
   ├─ 문제가 없으면 → save_node
   └─ 수정 필요 → guide_node
​
코딩에이전트 요청 예시
LangGraph로 바꾸고 싶다면 한 번에 전체를 다시 만들게 하지 않는다. 먼저 계획만 받는다.
schedule_agent.py의 현재 순차 함수형 구조를 LangGraph 구조로 바꾸고 싶어.

아직 파일을 수정하지 말고 계획만 말해줘.

조건:
- 기존 extract_facts, classify_items, write_user_guides, review_guides 함수의 내부 로직은 최대한 유지한다.
- 각 함수를 LangGraph node로 감싸는 방식으로 바꾼다.
- AgentState에는 text, items, grouped, guides, review_report를 둔다.
- 처음에는 START → extract → classify → guide → review → save → END 순차 그래프로 만든다.
- Streamlit 화면은 기존처럼 streamlit_app.py에서 실행되게 유지한다.
- LangGraph가 없어도 기존 Python 실행을 복구할 수 있는 fallback 방안을 설명한다.
​
계획이 적절하면 다음처럼 요청한다.
좋아. 이제 LangGraph 버전을 추가해줘.

조건:
- 기존 schedule_agent.py를 완전히 갈아엎지 않는다.
- 가능하면 run_pipeline(text) 같은 공통 실행 함수를 유지한다.
- Streamlit은 run_pipeline(text)를 호출하게 해줘.
- LangGraph 관련 패키지가 없을 때 사용자에게 설치 안내를 보여주고, 규칙 기반 순차 실행으로 fallback하게 해줘.
- 수정 후 실행 명령과 확인 방법을 알려줘.
​
주의할 점:
단순히 node로 바꾸기만 하면 기능은 좋아지지 않는다.
분기, 반복, 상태 저장이 필요할 때 LangGraph의 장점이 생긴다.
제출용 기본형은 순차 함수형 구조로도 충분하다.
