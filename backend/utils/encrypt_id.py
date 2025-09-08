import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_PASSWORD = os.getenv("SERCRET_PASSWORD")
SALT = os.getenv("SALT") 
def derive_key(password: bytes, salt: bytes) -> bytes:
    """Производный ключ из пароля и соли используя KDF"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


key = derive_key(SECRET_PASSWORD, SALT)
cipher_suite = Fernet(key)

async def encrypt_user_id(user_id: int) -> str:
    """
    Шифрует user_id в строку, пригодную для URL.
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        Строка в base64, содержащая зашифрованный user_id.
    """
    # Преобразуем user_id в bytes
    data = str(user_id).encode('utf-8')
    # Шифруем
    encrypted_data = cipher_suite.encrypt(data)
    # Кодируем в base64 для URL
    token = base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    return token

async def decrypt_user_id(token: str) -> int:
    """
    Расшифровывает строку из URL и возвращает user_id.
    Выбрасывает исключение, если токен невалидный или подпись не совпадает.
    
    Args:
        token: Строка, полученная из URL
        
    Returns:
        Идентификатор пользователя (int)
        
    Raises:
        InvalidToken: Если токен неверный или подпись не совпадает.
    """
    # Декодируем из base64
    encrypted_data = base64.urlsafe_b64decode(token.encode('utf-8'))
    # Дешифруем
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    # Преобразуем bytes обратно в int
    user_id = int(decrypted_data.decode('utf-8'))
    return user_id

# Пример использования
if __name__ == "__main__":
    # 1. Допустим, у нас есть пользователь с id = 123
    user_id = 123
    
    # 2. Шифруем его ID для URL
    encrypted_token = encrypt_user_id(user_id)
    print(f"Зашифрованный токен для URL: {encrypted_token}")
    # Пример: encrypted_token = "gAAAAABmY5... (безопасная для URL строка)"
    
    # 3. Формируем URL (пример)
    base_url = "https://flint.ru/invite?ref="
    invite_url = base_url + encrypted_token
    print(f"Сгенерированный URL: {invite_url}")
    
    # 4. Когда пользователь переходит по URL, мы получаем token из параметра `ref`
    received_token = encrypted_token  # Это имитация получения token из запроса
    
    try:
        decrypted_user_id = decrypt_user_id(received_token)
        print(f"Расшифрованный user_id: {decrypted_user_id}")
        # Теперь вы уверены, что этот user_id был зашифрован вами
        # Можете использовать его в логике (начислить бонусы и т.д.)
        
    except Exception as e:
        print(f"Ошибка расшифровки: {e}. URL подделан или поврежден.")