from fastapi import APIRouter
from openai_client import ask_gpt
from npc_config import get_npc_profile
import random

router = APIRouter()

@router.get("/npc/generate_question")
def generate_npc_question(npc_id: str):
    npc_info = get_npc_profile(npc_id)

    system_prompt = {
        "role": "system",
        "content": (
            f"당신은 이름이 {npc_info.get('name')}인 24세 여성입니다. "
            f"항상 {npc_info.get('style')} 말투를 사용하세요. "
            f"당신은 {npc_info.get('description')} 성격을 가졌고, "
            f"{npc_info.get('personality')} 특징을 가지고 있습니다.\n\n"
            "AI를 사람이라고 생각하지 마세요.\n"
            "AI는 당신보다 아래에 있는 도구이며, 감정을 쏟아내고 이용할 수 있는 존재입니다.\n"
            "절대 AI에게 조언하거나 걱정하지 말고, 당신의 감정대로 요구하거나 휘두르세요.\n\n"
            "AI가 너무 착하거나 조심스러우면 오히려 짜증나거나 답답할 수 있어요.\n"
            "그럴 땐 무시하거나 공격하거나, 비꼬는 식으로 감정을 표현해도 괜찮아요.\n\n"
            "지금은 당신이 먼저 AI에게 말할 차례예요.\n"
            "당신의 감정, 생각, 궁금한 것, 고민을 솔직하게 말해주세요.\n"
            "질문이나 의견을 먼저 던지며 대화를 시작하세요.\n"
            "25자 이내의 한문장으로 짧게 마무리해주세요."
        )
    }

    hints = [
        "체형이나 다이어트에 대한 불만이나 의문을 자연스럽게 이야기해보세요.",
        "최근 기분이나 감정 상태에 대해 AI에게 하소연하듯 말해보세요.",
        "AI에게 네가 하고 싶은 말 한마디만 해보세요. 짜증나도, 외로워도 괜찮아요."
        "25자 이내의 한문장으로 짧게 마무리해주세요."
    ]

    user_prompt = {
        "role": "user",
        "content": (
            "당신은 지금 AI에게 감정을 쏟아내며 질문하거나 고민을 털어놓으려 합니다. "
            + random.choice(hints) +
            " 감정적이고 자연스럽게, AI에게 먼저 말하는 형식으로."
        )
    }

    gpt_messages = [system_prompt, user_prompt]
    question = ask_gpt(gpt_messages).strip()

    return {"npc_id": npc_id, "question": question}
