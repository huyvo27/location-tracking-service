import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.utils.enums import UserRole

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def create_admin_user(db: AsyncSession):
    try:
        existing_admin = await User.find_by(
            db=db, username=settings.DEFAULT_ADMIN_USERNAME
        )

        if not existing_admin:
            hashed_password = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
            admin_user = await User.create(
                db=db,
                full_name="Admin User",
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_active=True,
                role=UserRole.SYS_ADMIN.value,
            )

            logger.info(f"Admin user created: {admin_user.username}")
        else:
            logger.info(f"Admin user already exists: {existing_admin.username}")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise


async def setup_system_admin():
    async with AsyncSessionLocal() as db:
        await create_admin_user(db)
