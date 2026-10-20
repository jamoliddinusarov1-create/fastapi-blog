import asyncio
import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from ..config import settings

logger = logging.getLogger(__name__)

# Tozalangan parol (bo'shliqlarsiz)
cleaned_mail_password = (settings.mail_password or "").replace(" ", "").strip()

# FastMail sozlamalari
conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username or "user@example.com",
    MAIL_PASSWORD=cleaned_mail_password or "password",
    MAIL_FROM=settings.mail_from or settings.mail_username or "user@example.com",
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=bool(settings.mail_username and cleaned_mail_password),
)


def _is_real_smtp_configured() -> bool:
    pwd = cleaned_mail_password
    user = (settings.mail_username or "").strip()
    return bool(
        user
        and pwd
        and user != "the_same_email@gmail.com"
        and pwd != "abcdefghijklmnop"
    )


async def send_welcome_email(email: str, username: str):
    """
    Xush kelibsiz emaili.
    Agar haqiqiy pochta paroli sozlangan bo'lsa, SMTP orqali yuboradi,
    aks holda simulyatsiya qilib log yozadi.
    """
    logger.info(f"Email yuborilmoqda: {email}")

    if _is_real_smtp_configured():
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
            logger.info(f"Haqiqiy email yuborildi: {email} → {username}")
            return
        except Exception as e:
            logger.error(f"Email yuborishda xatolik yuz berdi: {e}")

    # Simulyatsiya (agar ulanish bo'lmasa yoki xato bersa)
    await asyncio.sleep(1)
    logger.info(f"Email yuborildi (simulyatsiya): {email} → {username}")


async def send_post_notification(author_email: str, title: str):
    """Post yaratilganda bildirishnoma emaili"""
    logger.info(f"Post bildirishi: {author_email} → {title}")

    if _is_real_smtp_configured():
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
            logger.info(f"Haqiqiy post bildirishi yuborildi: {author_email}")
            return
        except Exception as e:
            logger.error(f"Post bildirishini yuborishda xatolik: {e}")

    # Simulyatsiya
    await asyncio.sleep(1)
    logger.info(f"Bildirish yuborildi (simulyatsiya)!")


def write_log(action: str, user_id: int, details: str = ""):
    """Faoliyat logi"""
    logger.info(f"LOG: user={user_id} | action={action} | {details}")
