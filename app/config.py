import configparser

config = configparser.ConfigParser()
config.read("config.ini")

BASE_URL = config.get("DEFAULT", "Url")
LISTEN_PORT = config.getint("DEFAULT", "Port")

AUTHORIZATION_TOKEN_PREFIX = config.get("AUTH", "AuthorizationTokenPrefix")
AUTHORIZATION_REFRESH_TOKEN_PREFIX = config.get(
    "AUTH", "AuthorizationRefreshTokenPrefix"
)
JWT_SECRET = config.get("AUTH", "JwtSecret")
JWT_EXPIRY_SECONDS = config.getint("AUTH", "JwtExpirySeconds")
JWT_REFRESH_EXPIRY_SECONDS = config.getint("AUTH", "JwtRefreshExpirySeconds")
VERIFICATION_TOKEN_SECRET = config.get("AUTH", "VerificationTokenSecret")
VERIFICATION_TOKEN_EXPIRY_SECONDS = config.getint(
    "AUTH", "VerificationTokenExpirySeconds"
)

MONGO_URL = config.get("DB", "Url")
MONGO_PORT = config.getint("DB", "Port")
DATABASE_NAME = config.get("DB", "Name")

SMTP_SERVER = config.get("SMTP", "Server")
SMTP_PORT = config.getint("SMTP", "Port")
SMTP_LOGIN = config.get("SMTP", "Login")
SMTP_PASSWORD = config.get("SMTP", "Password")
SMTP_FROM = config.get("SMTP", "From")
