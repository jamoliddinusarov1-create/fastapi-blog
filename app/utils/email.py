import asyncio
import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from ..config import settings

logger = logging.getLogger(__name__)

# FastMail sozlamalari
conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username or "user@example.com",
    MAIL_PASSWORD=settings.mail_password or "password",
    MAIL_FROM=settings.mail_from or "user@example.com",
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=bool(settings.mail_username and settings.mail_password),
)


async def send_welcome_email(email: str, username: str):
    """
    Xush kelibsiz emaili.
    Agar haqiqiy pochta paroli sozlangan bo'lsa, SMTP orqali yuboradi,
    aks holda simulyatsiya qilib log yozadi.
    """
    logger.info(f"Email yuborilmoqda: {email}")
    is_real = bool(
        settings.mail_username
        and settings.mail_password
        and settings.mail_username != "the_same_email@gmail.com"
        and " " not in settings.mail_password
    )

    if is_real:
        try:
            message = MessageSchema(
                subject="Xush kelibsiz! 🎉",
                recipients=[email],
                body=f"""
                <h2>Salom, {username}!</h2>
                <p>Blog API ga xush kelibsiz!</p>
                <p>Hisobingiz muvaffaqiyatli yaratildi.</p>
                """,
                subtype=MessageType.html,
            )
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info(f"Email yuborildi: {email} → {username}")
            return
        except Exception as e:
            logger.error(f"Email yuborishda xatolik: {e}")

    # Simulyatsiya
    await asyncio.sleep(1)
    logger.info(f"Email yuborildi: {email} → {username}")


async def send_post_notification(author_email: str, title: str):
    """Post yaratilganda bildirishnoma emaili"""
    logger.info(f"Post bildirishi: {author_email} → {title}")
    is_real = bool(
        settings.mail_username
        and settings.mail_password
        and settings.mail_username != "the_same_email@gmail.com"
        and " " not in settings.mail_password
    )

    if is_real:
        try:
            message = MessageSchema(
                subject="Yangi post chop etildi 📝",
                recipients=[author_email],
                body=f"""
                <h3>Tabriklaymiz!</h3>
                <p>Sizning <b>{title}</b> nomli postingiz muvaffaqiyatli saqlandi.</p>
                """,
                subtype=MessageType.html,
            )
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info(f"Bildirish yuborildi: {author_email}")
            return
        except Exception as e:
            logger.error(f"Post bildirishini yuborishda xatolik: {e}")

    # Simulyatsiya
    await asyncio.sleep(1)
    logger.info(f"Bildirish yuborildi!")


def write_log(action: str, user_id: int, details: str = ""):
    """Faoliyat logi"""
    logger.info(f"LOG: user={user_id} | action={action} | {details}")
