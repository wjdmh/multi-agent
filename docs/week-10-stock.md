# Week 10. 코딩에이전트 도구 사용법 (주식 분석 및 매매 에이전트 편)

> 9주차 멀티에이전트 설계 과제를 이어 받아, 11~14주차 주식 분석 및 매매 에이전트 프로젝트를 만들 준비를 한다.  
> 이번 주의 목표는 코드를 많이 짜는 것이 아니라, 코딩에이전트에게 일을 맡기고 결과를 검토하는 기본 절차를 익히는 것이다.

---

## 학습 목표

- GitHub Copilot, Gemini CLI, Antigravity의 작업 방식을 구분한다.
- 같은 작업을 세 도구에 지시해 보고 결과 차이를 비교한다.
- `.github/copilot-instructions.md`, `context.md`, `todo.md`의 역할을 이해한다.
- 9주차 설계 과제를 11주차 프로젝트 시작 문서로 바꾼다.
- 코딩에이전트가 만든 결과를 그대로 믿지 않고, 계획과 변경 내용을 확인한다.

---

## 이번 주 핵심 원칙

1. 새 프로젝트를 시작하지 않는다. 9주차 과제를 이어 쓴다.
2. 세 도구를 깊게 파지 않는다. 공통 작업 흐름을 익힌다.
3. 코드는 최소화한다. 오늘의 산출물은 지시문, 컨텍스트 문서, 작업 기록이다.
4. 자동 적용보다 검토를 우선한다. 계획을 보고, 변경 내용을 보고, 실행 결과를 본다.
5. 11주차부터 만들 주식 분석 및 매매 에이전트의 준비 문서를 만든다.

---

## 10.1 9주차 과제에서 출발하기

9주차 과제는 멀티에이전트 프로젝트의 설계 초안이다. 이번 주에는 그 과제를 실제 개발에 쓸 수 있는 문서로 바꾼다.

| 9주차 과제 항목 | 10주차에서 바꿀 문서 |
|---|---|
| 관심 도메인 | `context.md`의 프로젝트 배경 |
| 단일 에이전트의 한계 | `context.md`의 문제 정의 |
| 역할 분리 | `context.md`의 에이전트 역할 |
| 입력과 출력 | `context.md`의 입출력 명세 |
| 실패 조건 | `todo.md`의 검증 항목 |

11~14주차 프로젝트는 “주식 분석 및 매매 에이전트”이다. 시장 데이터와 최신 뉴스를 수집하고 분석하여 매매 시그널과 리포트를 생성하는 에이전트다.

---

## 10.2 이번 프로젝트: 주식 분석 및 매매 에이전트

주식 분석 및 매매 에이전트는 관심 종목의 데이터를 읽고, 기술적/기본적 분석을 한 뒤, 구체적인 매매 액션을 제안하는 멀티에이전트 프로그램이다.

기본 흐름은 다음과 같다.

```text
[종목 정보 입력]
   ↓
[데이터 수집 에이전트 (차트, 뉴스, 재무제표)]
   ↓
[시장 분석 에이전트 (기술적/기본적 지표)]
   ↓
[매매 결정 에이전트 (매수/매도 제안)]
   ↓
[리스크 검토 에이전트 (검증 및 다듬기)]
   ↓
[리포트 및 시그널 출력]
```

처음에는 복잡한 실거래 API나 모델 호출을 붙이지 않는다. Python 모듈 여러 개를 에이전트 역할처럼 나누고, 코딩에이전트에게 그 뼈대와 데이터 흐름을 만들게 한다.

---

## 10.3 세 도구의 역할

이번 주에는 세 도구를 모두 한 번씩 사용한다.

| 도구 | 수업에서의 역할 | 강점 | 주의점 |
|---|---|---|---|
| GitHub Copilot | VS Code 안에서 빠르게 코드와 문서 초안 작성 | 접근이 쉽고 편집 흐름이 자연스럽다 | 지시가 넓으면 불필요한 파일을 만들 수 있다 |
| Gemini CLI | 터미널에서 프로젝트 파일을 읽고 작업 | 명령 실행과 파일 단위 작업을 시키기 좋다 | 계획 없이 바로 수정하게 두면 추적이 어렵다 |
| Antigravity | Agent Manager로 작업 단위를 관리 | 여러 단계 작업과 변경 검토가 편하다 | 도구 UI에 익숙해지는 시간이 필요하다 |
| Playwright CLI | 브라우저에서 HTML과 결과 화면을 확인 | 화면 확인과 스크린샷에 좋다 | MCP가 아니라 CLI로만 사용한다 |

중요한 것은 특정 도구의 메뉴를 외우는 것이 아니다. 세 도구 모두 다음 흐름으로 쓴다.

```text
컨텍스트 제공 → 계획 요청 → 계획 검토 → 실행 요청 → 변경 확인 → 실행 검증
```

---

## 10.4 Playwright CLI 설치

이번 수업에서는 Playwright MCP를 붙이지 않는다. 대신 Playwright CLI를 설치해 HTML 자료, README 미리보기, 나중에 만들 간단한 시각화 화면을 브라우저에서 확인한다.

공식 Playwright Agent CLI 기준 설치 명령은 다음과 같다.

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
playwright-cli install-browser
```

Windows PowerShell에서도 같은 명령을 사용한다.

```powershell
npm install -g @playwright/cli@latest
playwright-cli --help
playwright-cli install-browser
```

설치 확인:

```bash
playwright-cli --help
```

사용 예시는 다음 정도만 다룬다.

```bash
playwright-cli open docs/week-10-stock.html
```

브라우저가 열리면 성공이다. 이번 주에는 자동 테스트 코드를 만들지 않는다. 목적은 “브라우저 확인을 CLI로 할 수 있다”를 경험하는 것이다.

---

## 10.5 공통 준비 파일

프로젝트 루트에 다음 파일을 만든다. (일부는 이미 수정됨)

```text
AGENTS.md
.github/copilot-instructions.md
GEMINI.md
.agents/skills/stock-agent/SKILL.md (새로 만들 예정)
.agents/skills/playwright-check/SKILL.md
context.md
todo.md
week10_tool_practice.md
```

운영 방식은 단순하다.

| 도구 | 자동/수동 사용 방식 |
|---|---|
| GitHub Copilot | VS Code에서는 `AGENTS.md`를 인식할 수 있다. 그래도 `.github/copilot-instructions.md`에서 `AGENTS.md`를 다시 가리키게 둔다 |
| Gemini CLI | `GEMINI.md`를 읽게 하고, 그 안에서 `AGENTS.md`를 공통 규칙으로 지정한다 |
| Antigravity | 프로젝트 루트의 `AGENTS.md`를 읽게 하거나, 첫 요청에서 “먼저 AGENTS.md를 읽어라”라고 지시한다 |

도구를 바꿀 때마다 첫 요청은 다음처럼 통일한다.

```text
먼저 AGENTS.md, context.md, todo.md를 읽어줘.
아직 파일을 수정하지 말고, 오늘 할 작업 계획만 말해줘.
```

### `AGENTS.md`

세 도구가 공통으로 참고할 규칙 파일이다. Copilot, Gemini CLI, Antigravity를 번갈아 쓰더라도 같은 규칙을 유지하기 위해 루트에 둔다.

```markdown
# AGENTS.md

이 파일은 GitHub Copilot, Gemini CLI, Antigravity에서 공통으로 참고할 프로젝트 규칙이다. 무료 사용량이 남아 있는 도구를 번갈아 쓰더라도 같은 규칙으로 작업한다.

## 프로젝트

- 이름: 주식 분석 및 매매 에이전트 (Stock Analysis & Trading Agent)
- 기본 실행: `python stock_agent.py`
- 기본 작업 파일: `stock_agent.py`

## 작업 방식

1. 파일을 수정하기 전에 먼저 계획을 제시한다.
2. 한 번에 많은 파일을 바꾸지 않는다.
3. 오류가 나면 새 기능을 추가하지 말고 오류만 고친다.
4. 변경 후 실행 명령과 확인 결과를 보고한다.

## 금지

- 불필요한 패키지 설치
- API 키 하드코딩
- 복잡한 실거래 API 연결 (시뮬레이션 위주)
- Playwright MCP 연결
```

### `.github/copilot-instructions.md`

GitHub Copilot용 연결 파일이다. 공통 규칙을 길게 반복하지 않고 `AGENTS.md`를 읽게 한다.

```markdown
# Copilot Instructions

이 저장소의 공통 작업 규칙은 루트의 `AGENTS.md`에 있다.

작업을 시작할 때 먼저 `AGENTS.md`, `context.md`, `todo.md`를 읽고 따른다.

요약:
- 기본 실행 명령은 `python stock_agent.py`이다.
- 파일을 수정하기 전에 먼저 계획을 제시한다.
- 한 번에 많은 파일을 바꾸지 않는다.
```

### `GEMINI.md`

Gemini CLI용 연결 파일이다. Gemini CLI는 `GEMINI.md`를 잘 읽으므로, 여기서 `AGENTS.md`를 공통 규칙으로 지정한다.

```markdown
# GEMINI.md

이 저장소의 공통 작업 규칙은 루트의 `AGENTS.md`에 있다.

작업을 시작할 때 먼저 `AGENTS.md`, `context.md`, `todo.md`를 읽고 따른다.

요약:
- 기본 실행 명령은 `python stock_agent.py`이다.
- 파일을 수정하기 전에 먼저 계획을 제시한다.
- 한 번에 많은 파일을 바꾸지 않는다.
```

---

## 10.6 프로젝트 Skills

이번 수업에서 말하는 skill은 거창한 플러그인이 아니다. 코딩에이전트가 반복해서 참고할 작업 절차 문서이다. 프로젝트에는 두 개만 둔다.

```text
.agents/skills/stock-agent/SKILL.md
.agents/skills/playwright-check/SKILL.md
```

### Skill 1. 주식 분석 및 매매 에이전트 제작

```markdown
---
name: stock-agent
description: 주식 분석 및 매매 에이전트의 기능을 만들거나 수정할 때 사용한다.
---

# Stock Agent Skill

## 목표
종목 코드를 입력받아 데이터를 수집하고, 분석 리포트와 매매 시그널을 생성한다.

## 기본 흐름
1. 데이터 수집: 가격 차트, 재무제표, 뉴스를 모은다.
2. 시장 분석: 기술적 지표(MA, RSI 등) 및 기본적 분석을 수행한다.
3. 매매 결정: 종합된 데이터를 통해 매수/매도/보유 시그널과 목표가를 제안한다.
4. 리스크 검토: 매매 근거의 적절성을 검증하고 Markdown 리포트로 다듬는다.

## 작업 원칙
- 먼저 계획을 제시한다.
- `stock_agent.py` 중심으로 수정한다.
- 불필요한 패키지는 추가하지 않으며, API Key는 환경변수로 처리한다.
- 변경 후 `python stock_agent.py` 실행 결과를 보고한다.
```

### Skill 2. Playwright 화면 확인

~~~markdown
---
name: playwright-check
description: HTML 자료나 출력 화면을 브라우저로 확인할 때 사용한다.
---

# Playwright Check Skill

## 목표
Playwright CLI로 HTML 또는 로컬 페이지가 열리는지 확인한다.

## 기본 명령
```bash
playwright-cli open docs/week-10-stock.html
```

## 작업 원칙
- Playwright MCP를 설정하지 않는다.
- 브라우저 확인이 필요한 경우에만 사용한다.
- 화면 확인 결과를 한두 문장으로 보고한다.
~~~

### Skills 사용 방법

skill 파일을 만들었다고 해서 모든 도구가 항상 자동으로 정확히 적용하는 것은 아니다. 처음에는 요청문에서 어떤 skill을 사용할지 직접 말해 주는 방식이 가장 안전하다.

주식 분석 에이전트 기능을 만들거나 고칠 때는 다음처럼 요청한다.

```text
stock-agent skill을 사용해서 작업해줘.
먼저 AGENTS.md, context.md, todo.md를 읽고, 아직 파일을 수정하지 말고 계획만 말해줘.
이번 작업은 특정 Ticker를 입력받아 yfinance로 데이터를 가져오는 기본 흐름을 설계하는 것이다.
```

계획을 확인한 뒤 실제 수정을 요청할 때는 다음처럼 이어서 말한다.

```text
좋아. 계획대로 진행해줘.
수정은 stock_agent.py 중심으로 하고, 끝나면 python stock_agent.py 실행 결과를 보고해줘.
```

HTML 자료나 출력 화면을 브라우저에서 확인할 때는 `playwright-check` skill을 사용한다.

```text
playwright-check skill을 사용해서 docs/week-10-stock.html이 브라우저에서 열리는지 확인해줘.
Playwright MCP는 쓰지 말고 playwright-cli 명령만 사용해줘.
```

도구별로는 다음처럼 말하면 된다.

| 도구 | 요청 예시 |
|---|---|
| GitHub Copilot | `stock-agent skill 기준으로 context.md와 todo.md를 읽고 작업 계획을 세워줘.` |
| Gemini CLI | `먼저 AGENTS.md와 .agents/skills/stock-agent/SKILL.md를 읽고, 파일 수정 전 계획만 말해줘.` |
| Antigravity | `stock-agent skill을 사용한다는 전제로 Agent Manager에 작업 계획을 나눠줘.` |

핵심은 skill 이름만 부르는 것이 아니라, 관련 파일을 읽고 어떤 작업에 적용할지 함께 말하는 것이다.

---

### `context.md`

코딩에이전트가 읽을 프로젝트 설명서이다.

```markdown
# 주식 분석 및 매매 에이전트 프로젝트

## 목표
사용자가 관심 있는 종목(Ticker)을 입력하면, 시장 데이터와 뉴스를 종합적으로 수집·분석하여 신뢰할 수 있는 투자 리포트와 매매 시그널을 생성한다.

## 입력
- 종목 코드 (예: AAPL, TSLA, 005930 등)
- 조회 기간 또는 사용자의 투자 성향(단기/장기 등)

## 출력
- 해당 종목의 현재 상태 요약
- 기술적/기본적 분석 결과
- 구체적 매매 전략 (목표가, 손절가, 액션 플랜)
- 출력 형식: Markdown 리포트 (`stock_report.md`)

## 에이전트 역할
1. 데이터 수집 에이전트: yfinance, 뉴스 API 등을 활용해 주식에 필요한 데이터를 확보.
2. 시장 분석 에이전트: 이동평균선(MA), RSI 등의 기술적 지표 계산 및 감성 분석.
3. 매매 결정 에이전트: 분석 결과를 바탕으로 최적의 매수/매도 포지션 추천.
4. 리스크 검토 에이전트: 추천된 매매 전략 검증 및 최종 리포트 다듬기.

## 제약
- 초기 개발은 Python 기본 코드와 핵심 라이브러리(`yfinance`, `pandas`)로 가볍게 만든다.
- 코드는 `stock_agent.py` 하나에서 시작한다.
- 자동 매매는 초기에 넣지 않고, 리포트 출력(모의 투자)에 집중한다.
- 외부 API Key는 환경변수를 사용한다.
```

### `todo.md`

작업 목록이다. 코딩에이전트에게 “무엇부터 할지”를 알려준다.

```markdown
# Todo

- [ ] 테스트용 Ticker(예: AAPL)를 정한다.
- [ ] 데이터 수집 에이전트(함수)를 만들어 기초 데이터를 가져온다.
- [ ] 시장 분석 에이전트(함수)를 만들어 기술적 지표를 계산한다.
- [ ] 매매 결정 에이전트(함수)를 만들어 시그널을 생성한다.
- [ ] 리스크 검토 에이전트(함수)를 만들어 검증한다.
- [ ] 전체 흐름을 연결하는 main 함수를 만든다.
- [ ] 결과를 Markdown 리포트(`stock_report.md`)로 출력한다.
- [ ] README에 실행 방법을 쓴다.
```

---

## 10.7 GitHub Copilot 실습

### 목표

Copilot에게 프로젝트 규칙과 컨텍스트를 읽히고, 11주차 개발을 위한 문서 초안을 만들게 한다.

### 절차

1. VS Code에서 프로젝트 루트를 연다.
2. `.github/copilot-instructions.md`를 만든다.
3. `context.md`, `todo.md`를 만든다.
4. Copilot Chat에 다음과 같이 요청한다.

```text
context.md와 todo.md를 읽고, 11주차에 만들 주식 분석 및 매매 에이전트의 개발 순서를 더 쉽게 정리해줘.
코드는 아직 만들지 말고, todo.md를 수업 실습 단계로 다듬어줘.
```

### 확인할 것

| 확인 항목 | 질문 |
|---|---|
| 범위 | Copilot이 주식 분석 에이전트 범위를 벗어나지 않았는가 |
| 난이도 | 갑자기 복잡한 백테스팅 툴이나 실거래 연동을 넣지 않았는가 |
| 실행 가능성 | 11주차에 시작할 수 있는 파이썬 스크립트 작성 수준의 순서인가 |

---

## 10.8 Gemini CLI 실습

### 목표

터미널에서 프로젝트 파일을 읽고, 계획을 먼저 받은 뒤 작업을 시키는 습관을 만든다.

### 기본 흐름

```bash
gemini
```

Gemini CLI 안에서 다음과 같이 요청한다.

```text
이 프로젝트의 context.md와 todo.md를 읽어줘.
아직 파일을 수정하지 말고, 주식 분석 및 매매 에이전트를 만들기 위한 5단계 계획만 제시해줘.
각 단계는 수업 초보자가 따라 할 수 있게 짧게 써줘.
```

계획이 적절하면 다음 요청을 한다.

```text
좋아. 이제 todo.md만 수정해줘.
11주차에는 뼈대와 데이터 수집, 12주차에는 시장 분석 지표 계산, 13주차에는 매매 시그널 생성, 14주차에는 리스크 검증 및 리포트 완성으로 나누어줘.
```

### 확인할 것

Gemini CLI는 명령 실행이나 파일 수정이 편하다. 대신 바로 수정시키기 전에 반드시 계획을 먼저 받는다.

```text
먼저 계획만 말해줘. 아직 파일을 수정하지 마.
```

이 문장을 자주 사용한다.

---

## 10.9 Antigravity 실습

### 목표

Agent Manager에서 하나의 작업을 만들고, 변경 내용을 검토하는 흐름을 익힌다.

### 절차

1. Antigravity에서 프로젝트 루트를 연다.
2. Agent Manager를 연다.
3. 새 작업을 만든다.
4. 다음 지시를 입력한다.

```text
context.md와 todo.md를 읽고, 주식 분석 및 매매 에이전트 프로젝트를 위한 README 초안을 작성해줘.
아직 코드는 만들지 말고, 프로젝트 목표, 실행 예정 파일, 주차별 개발 계획만 정리해줘.
```

5. 계획 또는 작업 단계를 먼저 확인한다.
6. 변경된 파일을 검토한다.
7. 마음에 들지 않으면 다음처럼 다시 지시한다.

```text
내용이 너무 어렵다. 자동 매매나 실거래 내용은 빼고, Python 기본 코드로 데이터를 수집하고 분석 리포트를 생성하는 설명만 남겨줘.
```

---

## 10.10 같은 작업을 세 도구에 시켜 보기

세 도구에 같은 작업을 시킨다.

```text
9주차 설계 과제를 바탕으로, 주식 분석 및 매매 에이전트 프로젝트의 context.md 초안을 만들어줘.
초보자가 이해할 수 있게 입력, 출력, 역할 4개, 제약사항을 구분해줘.
```

결과를 비교한다.

| 비교 항목 | Copilot | Gemini CLI | Antigravity |
|---|---|---|---|
| 지시를 잘 지켰는가 |  |  |  |
| 너무 어려운 내용을 넣었는가 |  |  |  |
| 파일 변경을 확인하기 쉬웠는가 |  |  |  |
| 다시 수정시키기 쉬웠는가 |  |  |  |
| 내가 계속 쓸 도구로 적합한가 |  |  |  |

---

## 10.12 Homework

본인들 깃허브 주소를 제출한다. 

## 다음 주 예고

11주차에는 주식 분석 및 매매 에이전트의 첫 번째 버전을 만든다. 처음부터 복잡한 LangGraph나 실거래 연동을 하지 않는다. 먼저 Python 함수들로 `데이터 수집 → 시장 분석 → 매매 결정 → 리포트 생성` 흐름을 만들고, 코딩에이전트에게 그 뼈대를 생성하게 한다.
