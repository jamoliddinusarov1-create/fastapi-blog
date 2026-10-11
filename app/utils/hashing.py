import bcrypt

def hash_password(password: str) -> str:
    # Parolni baytga o'tkazib, salt hosil qilamiz va xashlaymiz
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Kiritilgan parol bilan bazadagi xashni solishtiramiz
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))