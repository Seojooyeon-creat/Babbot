# 오늘 뭐 먹지? — 코드 분석 노트

> AI 밥 추천 앱의 코드를 단계별로 따라가며 분석한 실습 노트.
> 구성: `recommender.py`(공용 로직) → `app.py`(웹 프론트) → `main.ipynb`(CLI)

---

## 1. 공용 로직 모듈 만들기

가장 먼저 app.py와 노트북이 함께 쓸 핵심 로직을 한 파일로 모은다.
`.env`에서 API 키를 불러오고, AI의 역할을 정의하는 시스템 프롬프트를 상수로 둔다.

```python
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "너는 밥 추천 전문 AI야.\n"
    "사용자의 기분, 날씨, 상황, 먹고 싶은 느낌을 물어보고 그에 맞는 한식/양식/중식/일식 메뉴를 추천해줘.\n"
    "추천할 때는 메뉴 이름 + 추천 이유 + 간단한 먹는 팁을 같이 알려줘.\n"
    "밥 관련 질문이 아니면 '저는 밥 추천만 할 수 있어요!' 라고 답해."
)
```

`load_dotenv()`가 모듈을 import하는 순간 실행되므로, app.py든 노트북이든 import만 하면 API 키가 환경변수로 준비된다.

---

## 2. 클라이언트와 모델 준비

Anthropic 클라이언트를 생성하고 사용할 모델명과 함께 반환한다.

```python
def load_client_and_model(model="claude-haiku-4-5"):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return client, model
```

기본 모델은 `claude-haiku-4-5`. 클라이언트(연결 객체)와 모델명을 한 번에 돌려주므로 호출부가 간결해진다.

**분석 포인트**: API 키가 `None`이어도 이 함수는 성공한다. 실제 오류는 호출 시점에 발생 → 조기 검증이 없다는 한계.

---

## 3. 추천 답변 생성 — 핵심 함수

대화 히스토리를 받아 Claude API를 호출하고, 응답 텍스트만 뽑아서 반환한다.

```python
def get_recommendation(client, model, chat_history):
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=chat_history,
    )
    return response.content[0].text
```

이 함수가 앱 전체에서 **API를 호출하는 유일한 지점**이다. 인자로 받은 `chat_history`만 사용하므로 순수 함수에 가깝고 테스트하기 쉽다.

**실행 결과 예시** — 직접 호출해보면:

```python
client, model = load_client_and_model()
history = [{"role": "user", "content": "비 와서 우울한데 혼자 따뜻한 거 먹고 싶어"}]
print(get_recommendation(client, model, history))
```

```
오, 그런 날씨에는 따뜻한 음식이 정말 필요하네요! 🌧️
...
1️⃣ 얼마나 배고픈가요?
2️⃣ 어떤 종류의 따뜻함이 좋아요?
...
```

→ 시스템 프롬프트대로 기분·상황을 되묻는 대화형 응답이 정상 출력된다.

**분석 포인트**: `response.content[0].text`는 첫 응답 블록이 항상 텍스트라고 가정한다. 현재 구성에선 안전하지만, tool use 등이 섞이면 깨질 수 있다.

---

## 4. 웹 프론트엔드 — 상태 초기화

`app.py`는 Streamlit으로 채팅 UI를 만든다. 먼저 클라이언트를 준비하고 대화 히스토리를 세션에 저장한다.

```python
client, model = load_client_and_model()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
```

`st.session_state`는 입력 사이에 값을 유지해주는 저장소다. 여기에 대화 히스토리를 넣어 **멀티턴 대화**가 끊기지 않게 한다.

**분석 포인트**: Streamlit은 입력마다 스크립트를 처음부터 재실행한다. 그래서 `load_client_and_model()`이 매번 호출된다 → `@st.cache_resource`로 캐싱하면 효율적.

---

## 5. 웹 프론트엔드 — 입력과 응답 표시

이전 대화를 그려주고, 자유 텍스트 입력을 받아 추천을 요청한다.

```python
# 이전 대화 표시
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("예: 비 와서 우울한데 혼자 먹어. 따뜻한 거 먹고 싶어")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("추천 중..."):
            try:
                reply = get_recommendation(client, model, st.session_state.chat_history)
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")
```

라디오 버튼 대신 `st.chat_input`을 써서 사용자가 **자연어로 자유롭게** 기분·상황을 입력한다. 입력이 들어오면 히스토리에 추가 → 공용 함수로 추천을 받아 화면에 출력한다.

**분석 포인트**: API 호출이 실패하면 user 메시지만 히스토리에 남는다. 다음 호출 때 user 메시지가 연달아 쌓일 수 있어, 실패 시 user 메시지를 되돌리는 처리가 있으면 더 안전하다.

---

## 6. CLI 버전 — 노트북

`main.ipynb`도 같은 공용 모듈을 import해서 동일한 로직으로 동작한다. 차이는 입출력이 `input()`/`print()`라는 점뿐이다.

```python
from recommender import load_client_and_model, get_recommendation

def generate_response(client, model, chat_round, chat_history):
    user_input = input(">>You: ")
    chat_history.append({"role": "user", "content": user_input})

    assistant_message = get_recommendation(client, model, chat_history)

    chat_history.append({"role": "assistant", "content": assistant_message})
    print(f"Claude: {assistant_message}")
    return chat_history

def chat_for_n_rounds(n=5):
    client, model = load_client_and_model()
    chat_history = []
    for chat_round in range(n):
        chat_history = generate_response(client, model, chat_round, chat_history)
```

웹이든 CLI든 추천 로직은 `get_recommendation` 하나로 통일되어 있다.

**분석 포인트**: 대화가 `n=5`회로 고정되어 있고("그만" 같은) 종료 조건이 없다. 또 `chat_round` 인자는 받기만 하고 함수 안에서 쓰이지 않는다.

---

## 7. 종합 정리

| 구분 | 강점 | 개선할 점 |
|------|------|-----------|
| `recommender.py` | API 호출 단일 진입점, 순수 함수에 가까움 | 키 부재 조기 검증·예외 처리 없음 |
| `app.py` | 세션으로 멀티턴 유지, 자유 텍스트 입력 | 클라이언트 매번 재생성, 실패 시 히스토리 정합성 |
| `main.ipynb` | 공용 모듈 재사용으로 일관성 | 고정 라운드, 미사용 인자, 예외 미처리 |

**결론**: 공용 로직 모듈을 중심으로 웹/CLI 두 진입점이 같은 코드를 공유하는 깔끔한 구조다. 핵심 기능은 정상 동작하며, 프로덕션 수준으로는 예외 처리·리소스 캐싱·히스토리 정합성 보강이 권장된다.
