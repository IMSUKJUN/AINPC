import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def ask_gpt(messages: List[Dict[str, str]]) -> str:
    """
    GPT-4o 모델을 호출하여 응답 텍스트(content)만 반환합니다.

    Args:
        messages (List[Dict]): 채팅 메시지 기록. 예: [{"role": "user", "content": "..."}]

    Returns:
        str: GPT의 assistant 응답 텍스트
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=1.0,
            max_tokens=2048,
            top_p=1.0
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[GPT 호출 오류] {e}")
        return "⚠️ GPT 응답 처리 중 오류가 발생했습니다."