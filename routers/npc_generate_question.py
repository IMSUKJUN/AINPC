from fastapi import APIRouter
from NPC.utils.openai_client import ask_gpt
from prompt_utils import build_question_prompt  # ✅ 통합된 프롬프트 함수
import random
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/npc/generate_question")
def generate_npc_question(npc_id: str):
    try:
        # 1. system prompt 구성
        system_prompt = build_question_prompt(npc_id)

        # 2. hint 랜덤 삽입
        hints = [
            "체형이나 다이어트에 대한 불만이나 의문을 자연스럽게 이야기해보세요.",
            "최근 기분이나 감정 상태에 대해 AI에게 하소연하듯 말해보세요.",
            "AI에게 네가 하고 싶은 말 한마디만 해보세요. 짜증나도, 외로워도 괜찮아요."
        ]
        user_prompt = {
            "role": "user",
            "content": (
                "당신은 지금 AI에게 감정을 쏟아내며 질문하거나 고민을 털어놓으려 합니다. "
                + random.choice(hints) +
                " 감정적이고 자연스럽게, AI에게 먼저 말하는 형식으로."
            )
        }

        # 3. GPT 호출
        gpt_messages = [system_prompt, user_prompt]
        question = ask_gpt(gpt_messages).strip()

        return {"npc_id": npc_id, "question": question}

    except Exception as e:
        logger.error("NPC 질문 생성 중 오류", exc_info=True)
        return {"error": "질문 생성에 실패했습니다."}
