import smtplib
from socket import gaierror
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.config import (
    BASE_URL,
    LISTEN_PORT,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_LOGIN,
    SMTP_PASSWORD,
    SMTP_FROM,
)
from app.auth import get_verification_token


def send_verification_email(username: str, email: str, user_id: int):
    token = get_verification_token(user_id)

    # Construct the verification url from base url and token
    verification_url = f"{BASE_URL}:{LISTEN_PORT}/verify/{token}"
    message = f"""\
            From: Admin <{SMTP_FROM}>
            To: {username} <{email}>
            Subject: Verification

            Welcome {username}!

            Thanks for signing up. Please follow this link to activate your account:
            {verification_url}

            Kind Regards,
            Admin
            """

    try:
        # send your message with credentials specified above
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [email], message)

    # except:
    # raise HTTPException(
    # status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    # detail="Failed to send verification email",
    # )
    except (gaierror, ConnectionRefusedError):
        print("Failed to connect to the server. Bad connection settings?")
        raise
    except smtplib.SMTPServerDisconnected:
        print("Failed to connect to the server. Wrong user/password?")
        raise
    except smtplib.SMTPException as e:
        print("SMTP error occurred: " + str(e))
        raise
