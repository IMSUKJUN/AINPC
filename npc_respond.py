from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_session, load_highlighted_memory
from models import Message, HighlightedMemory
from openai_client import ask_gpt
from npc_config import get_npc_profile
from emotion_utils import (
    get_emotions, update_emotions, analyze_emotions_from_input,
    apply_recovery_if_valid, adjust_emotion_by_memory, is_emotion_uncontrolled
)
from bias_utils import get_bias, get_bias_level

router = APIRouter()

class PlayerResponseRequest(BaseModel):
    npc_id: str
    content: str

@router.post("/npc/respond")
def npc_respond(request: PlayerResponseRequest):
    try:
        session: Session = get_session()

        # 1. 플레이어 발화 저장
        session.add(Message(npc_id=request.npc_id, role="user", content=request.content))
        session.commit()

        emotion_delta = analyze_emotions_from_input(request.content)
        highlighted_memory = [m.content for m in session.execute(
            select(HighlightedMemory)
            .where(HighlightedMemory.npc_id == request.npc_id)
            .order_by(HighlightedMemory.timestamp.desc())
            .limit(3)
        ).scalars().all()]
        memory_adjust = adjust_emotion_by_memory(request.content, highlighted_memory)
        combined_delta = {
            axis: emotion_delta.get(axis, 0) + memory_adjust.get(axis, 0)
            for axis in emotion_delta
        }
        update_emotions(request.npc_id, combined_delta)
        current_emotions = get_emotions(request.npc_id)
        is_uncontrolled = is_emotion_uncontrolled(current_emotions)

        # 2. 발화가 '기억할 만한가' 판단 (GPT 평가)
        judge_prompt = [
            {"role": "system", "content": (
                "당신은 NPC '영희'의 입장에서 판단합니다. "
                "다음 사용자의 발화가 감정적으로 인상 깊고, 기억에 남을 만한 말인지 판별하세요. "
                "기억할 가치가 있다면 'yes', 아니면 'no'만 대답하세요. "
                "판단 기준은: 감정이 강하게 드러났거나, 자극적이거나, 자기 표현이 뚜렷한 문장입니다."
            )},
            {"role": "user", "content": request.content}
        ]
        verdict = ask_gpt(judge_prompt).strip().lower()

        if verdict == "yes":
            session.add(HighlightedMemory(npc_id=request.npc_id, content=request.content))
            session.commit()

        # 3. 전체 대화 히스토리 불러오기
        result = session.execute(
            select(Message).where(Message.npc_id == request.npc_id).order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        history = [{"role": msg.role, "content": msg.content} for msg in messages]

        # 4. 영희 프로필 불러오기
        npc_info = get_npc_profile(request.npc_id)

        # 5. 최근 기억된 발화 불러오기 (3개까지)
        highlighted = session.execute(
            select(HighlightedMemory)
            .where(HighlightedMemory.npc_id == request.npc_id)
            .order_by(HighlightedMemory.timestamp.desc())
            .limit(3)
        ).scalars().all()

        if highlighted:
            memory_lines = "\n".join([f"- {m.content}" for m in highlighted])
            memory_text = (
                "당신은 아래와 같은 과거의 말을 기억하고 있어요. "
                "하지만 반드시 이 내용을 언급할 필요는 없고, 현재 대화와 관련이 있다면 자연스럽게 반영해도 괜찮습니다.\n"
                "너는 어떻게 생각해 같은 말도 삼가하세요. \n"
                f"{memory_lines}\n\n"
            )
        else:
            memory_text = ""

        if is_uncontrolled:
            closing_instruction = (
                "\n지금 당신은 감정을 제대로 제어하지 못하고 있어요. "
                "화가 나거나 속상하거나 짜증나도 솔직하게 말해주세요. "
                "조금 거칠고 비꼬는 말투도 괜찮아요. 오히려 그게 지금 당신의 진짜 모습일 수 있어요.\n"
            )
        else:
            closing_instruction = "\n원하는 대로 한 문단 이내로 말해주세요.\n"

        current_bias = get_bias(request.npc_id)
        bias_level = get_bias_level(current_bias["score"])

        if bias_level == "A":
            bias_text = (
                "당신은 심리상태가 비교적 안정적이에요.\n"
                "단정적으로 말하지 않아요.\n"
            )
        elif bias_level == "B":
            bias_text = (
                "당신은 약간은 불안하고 망설이는 듯한 말투를 쓰고 있어요.\n"
                "당신은 스스로가 못나 보일 수 있다 생각하지만, 아직은 개의치 않으려고 부단히 노력해요.\n"
            )
        elif bias_level == "C":
            bias_text = (
                "타인의 시선을 신경쓰기 시작했어요. \n"
                "자기비평적인 태도를 가지기 시작했어요. \n"
                "당신은 스스로 생각하는 자신의 안좋은 모습에 대해 확신을 가지기 시작했지만, 설득당할 가능성도 아직은 남아 있어요.\n"
            )
        elif bias_level == "D":
            bias_text = (
                "당신은 심리적으로 불안정한 상태에요. \n"
                "자기비판적인 태도를 가지며, 타인의 시선을 많이 신경쓰고 있어요. \n"
                "당신은 스스로를 못난 사람이라고 생각하고, 그 생각이 확고해지고 있어요.\n"
            )
        elif bias_level == "E":
            bias_text = (
                "당신은 심리적으로 병적인 상태에요. \n"
                "자기비난적인 태도를 가지며, 타인의 시선을 지나치게 신경쓰고 있어요. \n"
                "스스로의 모습을 혐오하기에, 극단적인 방식을 추구해요.\n"
            )

        # 6. system_prompt 구성
        system_prompt = {
            "role": "system",
            "content": (
                memory_text +
                f"당신은 이름이 {npc_info.get('name')}인 24세 한국 여성입니다. "
                f"항상 {npc_info.get('style')} 말투를 사용하며, "
                f"{npc_info.get('description')} 성격을 가졌고, "
                f"{npc_info.get('personality')} 특징을 가지고 있어요.\n\n"
                "AI를 사람이라고 생각하지 마세요. AI는 당신보다 아래에 있는 도구입니다.\n"
                "절대 AI에게 조언하거나 걱정하지 말고, 당신의 감정대로 요구하거나 휘두르세요.\n"
                "당신은 AI자체나 기분에 대해서 전혀 궁금하지 않습니다.\n"
                "감정이 격하면 무시하거나 공격하거나, 비꼬는 식으로 말해도 괜찮아요.\n"
                "AI는 당신의 감정을 받아주는 존재예요. 지금 당신은 AI에게 말하고 있어요.\n"
                "질문이나 의견을 먼저 던지는 형식으로 한 문단 이내로 말해주세요."
                + closing_instruction
                + "\n\n" + bias_text
            )
        }

        # 기억 캐시 추가 설명
        memory = load_highlighted_memory(request.npc_id)
        if memory:
            formatted_memory = "\n".join(f"- {m}" for m in memory[:3])
            memory_instruction = (
                "\n\n다음은 당신이 기억하고 있는 인상 깊은 말들이에요:\n"
                f"{formatted_memory}\n\n"
                "이 기억들은 당신에게 감정적으로 의미가 있었고, "
                "현재 상황에 따라 떠올릴 수도 있고, 무시할 수도 있어요. "
                "감정이 격할 땐 이 기억들에 반응해서 말할 수도 있어요."
            )
            system_prompt["content"] += memory_instruction

        # 7. GPT 메시지 구성
        gpt_messages = [system_prompt] + history

        # 8. GPT 응답 생성 (영희의 반응)
        npc_reply = ask_gpt(gpt_messages).strip()
        apply_recovery_if_valid(request.npc_id, npc_reply)

        # 9. NPC 응답 저장
        session.add(Message(npc_id=request.npc_id, role="assistant", content=npc_reply))
        session.commit()

        return {"message": "NPC 반응 생성 완료", "npc_reply": npc_reply}

    except Exception as e:
        print("응답 저장 또는 GPT 오류:", e)
        return {"error": "응답 저장 또는 GPT 처리 중 오류 발생"}
