from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.security import hash_password, verify_password


class AuthService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower().strip()).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @classmethod
    def create_user(cls, db: Session, email: str, password: str) -> User:
        clean_email = email.lower().strip()
        existing = cls.get_user_by_email(db, clean_email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        password_hash = hash_password(password)
        user = User(email=clean_email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        user = cls.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
