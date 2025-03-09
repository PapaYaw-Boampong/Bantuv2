from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, TIMESTAMP, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
import torch
from unsloth import FastLanguageModel
from transformers import AutoTokenizer

# Database setup
DATABASE_URL = "postgresql://user:password@localhost/translation_db" # dummy for now
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Loading fine-tuned DeepSeek model
MODEL_PATH = "./fine_tuned_deepseek_r1"
fine_tuned_model, fine_tuned_tokenizer = FastLanguageModel.from_pretrained(MODEL_PATH)
FastLanguageModel.for_inference(fine_tuned_model)

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    reputation = Column(Float, default=1.0)

class Translation(Base):
    __tablename__ = "translations"
    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text, nullable=False)
    translation = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    frequency = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=func.now())
    user = relationship("User")

class FinalTranslation(Base):
    __tablename__ = "final_translations"
    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text, nullable=False)
    final_translation = Column(Text, nullable=False)
    reviewed_by = Column(String, default='DeepSeek-R1')
    created_at = Column(TIMESTAMP, default=func.now())

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to correct translation using fine-tuned DeepSeek model
def correct_translation(final_translation: str) -> str:
    prompt = f"""
    You are an expert linguist ensuring grammatical accuracy and fluency.
    Correct the following translation:
    
    [START TRANSLATION]
    {final_translation}
    [END TRANSLATION]
    """
    
    inputs = fine_tuned_tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
    with torch.no_grad():
        outputs = fine_tuned_model.generate(inputs.input_ids, max_new_tokens=100)
    
    return fine_tuned_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

@app.post("/submit_translation/")
def submit_translation(source_text: str, translation: str, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    existing_translation = db.query(Translation).filter_by(source_text=source_text, translation=translation).first()
    if existing_translation:
        existing_translation.frequency += 1
    else:
        new_translation = Translation(source_text=source_text, translation=translation, user_id=user.id)
        db.add(new_translation)
    
    db.commit()
    return {"message": "Translation submitted successfully."}

@app.post("/finalize_translation/")
def finalize_translation(source_text: str, top_translation: str, db: Session = Depends(get_db)):
    corrected_translation = correct_translation(top_translation)
    final_translation = FinalTranslation(source_text=source_text, final_translation=corrected_translation)
    db.add(final_translation)
    db.commit()
    return {"final_translation": corrected_translation}
