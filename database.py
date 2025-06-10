from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, HighlightedMemory
import os

api_key = os.getenv("OPENAI_API_KEY")

# SQLite 경로 설정
DATABASE_URL = "sqlite:///./npc_chat.db"

# SQLAlchemy 엔진 설정
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 전용 설정
)

# 세션 팩토리 설정
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# DB 테이블 초기화
def init_db():
    Base.metadata.create_all(bind=engine)

# 세션 객체 반환
def get_session():
    return SessionLocal()

# 최근 하이라이트된 기억 불러오기
def load_highlighted_memory(npc_id: str) -> list[str]:
    """
    주어진 NPC의 최근 하이라이트된 기억 3개를 불러옵니다.
    """
    session = get_session()
    result = session.execute(
        select(HighlightedMemory)
        .where(HighlightedMemory.npc_id == npc_id)
        .order_by(HighlightedMemory.timestamp.desc())
        .limit(3)
    )
    return [row.content for row in result.scalars().all()]
