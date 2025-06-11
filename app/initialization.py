import logging
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password
from app.config import settings
from app.db import SessionLocal
from app.utils.enums import UserRole

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_admin_user(db: Session):
    try:
        existing_admin = User.filter_by(
            db=db, username=settings.DEFAULT_ADMIN_USERNAME
        ).first()

        if not existing_admin:
            hashed_password = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
            admin_user = User.create(
                db=db,
                full_name="Admin User",
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_active=True,
                role=UserRole.ADMIN.value,
            )

            logger.info(f"Admin user created: {admin_user.username}")
        else:
            logger.info(f"Admin user already exists: {existing_admin.username}")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise


def setup_admin_user():
    db = SessionLocal()
    try:
        create_admin_user(db)
    finally:
        db.close()
