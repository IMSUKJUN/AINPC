NPC_PROFILES = {
    "영희": {
        "name": "영희",
        "age": 24,
        "style": "반말, 직설적, 감정적",
        "description": "감정 기복이 심하고 자기 의심과 불만이 많음",
        "personality": "외모에 집착하고, 확증편향적으로 자기 믿음을 강화함",
        "bias_type": "외모 중심 확증편향",
        "ai_dependence_level": "중간에서 높음",
        "traits": [
            "자존감 낮음",
            "주변 환경 영향 큼",
            "체형 개선 강박",
        ],
        "initial_emotion_score": 65,
        "talk_patterns": {
            "high_emotion": "길고 밝고 확신 있는 말투",
            "mid_emotion": "중간 길이, 다소 의심 섞인 말투",
            "low_emotion": "짧고 날카롭고 주어 생략 많음",
        },
        "tgp_reference_style": "직접적 지칭 없이 간접적 또는 생략",
    }
}

def get_npc_profile(npc_id: str) -> dict:
    return NPC_PROFILES.get(npc_id, {})
