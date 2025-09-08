import re
from typing import Dict
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from phonenumbers import PhoneNumberFormat


def extract_contacts(text: str) -> Dict[str, str]:
    """
    На вход: очищенный текст (str).
    На выход: {'email': str, 'phone': str} — пустые строки, если не найдены.
    """
    email = _find_first_email(text)
    phone = _find_first_phone(text)
    return {'email': email or '', 'phone': phone or ''}

# email

_EMAIL_RE = re.compile(
    r'(?<![\w\.-])([A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9\.\-]+\.[A-Za-z]{2,})(?![\w\.-])',
    re.IGNORECASE | re.UNICODE
)

def _normalize_obfuscated_emails(text: str) -> str:
    """
    ivanov (at) mail (dot) ru, иванов собака почта точка ру -> ivanov@mail.ru
    """
    t = re.sub(r'[\[\]\(\)\{\}]', ' ', text)
    t = re.sub(r'\b(at|собака)\b', '@', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(dot|точка)\b', '.', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*@\s*', '@', t)
    t = re.sub(r'\s*\.\s*', '.', t)
    return t

def _find_first_email(text: str) -> str:
    for m in _EMAIL_RE.finditer(text):
        try:
            return validate_email(m.group(1), allow_smtputf8=True).normalized
        except EmailNotValidError:
            pass
    t2 = _normalize_obfuscated_emails(text)
    if t2 != text:
        for m in _EMAIL_RE.finditer(t2):
            try:
                return validate_email(m.group(1), allow_smtputf8=True).normalized
            except EmailNotValidError:
                pass
    return ''


# phone

_EXT_TAIL_RE = re.compile(r'(?:доб\.?|ext\.?|extension)\s*\d+\s*$', re.IGNORECASE | re.UNICODE)

def _digits_only(s: str) -> str:
    return re.sub(r'\D+', '', s)

def _to_e164_ru_fallback(raw: str) -> str:
    """
    Простейшая нормализация RU:
    8XXXXXXXXXX / 7XXXXXXXXXX / XXXXXXXXXX -> +7XXXXXXXXXX
    иначе возвращаем ''.
    """
    s = _EXT_TAIL_RE.sub('', raw).strip()
    s = re.sub(r'^\s*00', '+', s)
    if s.startswith('+'):
        digits = _digits_only(s)
        if 10 <= len(digits) <= 15:
            return '+' + digits
        return ''

    digits = _digits_only(s)
    if len(digits) == 11 and digits.startswith('8'):
        return '+7' + digits[1:]
    if len(digits) == 11 and digits.startswith('7'):
        return '+7' + digits[1:]
    if len(digits) == 10:
        return '+7' + digits
    return ''

_PHONE_CANDIDATE_RE = re.compile(
    r'(?<!\w)(?:\+?\s*\d[\s().-]*){10,}(?!\w)',
    re.UNICODE
)

def _find_first_phone(text: str) -> str:
    try:
        for match in phonenumbers.PhoneNumberMatcher(text, 'RU'):
            pn = match.number
            if phonenumbers.is_possible_number(pn) and phonenumbers.is_valid_number(pn):
                return phonenumbers.format_number(pn, PhoneNumberFormat.E164)
    except Exception:
        pass

    m = _PHONE_CANDIDATE_RE.search(text)
    if m:
        return _to_e164_ru_fallback(m.group(0))
    return ''
