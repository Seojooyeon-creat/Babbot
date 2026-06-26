import os
import streamlit as st
from recommender import load_client_and_model, get_recommendation

# 배포(Streamlit Cloud) 환경에서는 secrets에 저장한 키를 환경변수로 넘겨준다.
# (로컬에서는 .env가 사용되므로 secrets가 없어도 그냥 넘어간다.)
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

st.set_page_config(page_title="오늘 뭐 먹지?", page_icon="🍽️")

st.markdown("""
<style>
    .main { max-width: 480px; margin: auto; }
    .title-sub { color: #aaa; font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="title-sub">AI 밥 추천</p>', unsafe_allow_html=True)
st.markdown("## 오늘 뭐 먹지?")
st.caption("기분, 날씨, 상황을 자유롭게 적어주면 메뉴를 추천해줄게요.")
st.markdown("---")

client, model = load_client_and_model()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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
