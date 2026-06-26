import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

# app.py와 main.ipynb가 공유하는 밥 추천 핵심 로직

SYSTEM_PROMPT = (
    "너는 밥 추천 전문 AI야.\n"
    "사용자의 기분, 날씨, 상황, 먹고 싶은 느낌을 물어보고 그에 맞는 한식/양식/중식/일식 메뉴를 추천해줘.\n"
    "추천할 때는 메뉴 이름 + 추천 이유 + 간단한 먹는 팁을 같이 알려줘.\n"
    "밥 관련 질문이 아니면 '저는 밥 추천만 할 수 있어요!' 라고 답해."
)


def load_client_and_model(model="claude-haiku-4-5"):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return client, model


def get_recommendation(client, model, chat_history):
    """chat_history(대화 히스토리)를 받아 Claude의 추천 답변 텍스트를 반환한다."""
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=chat_history,
    )
    return response.content[0].text
