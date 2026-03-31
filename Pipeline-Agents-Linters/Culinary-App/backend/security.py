"""
Hasła: bcrypt (wbudowana losowa sól w każdym hashu) + opcjonalny pepper aplikacyjny (HMAC-SHA256).
Bez peppera zachowanie jest zgodne z wcześniejszym bcrypt(plain).
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional, Tuple

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _pepper_bytes() -> Optional[bytes]:
    p = (os.getenv("PASSWORD_PEPPER") or "").strip()
    if not p:
        return None
    return p.encode("utf-8")


def _material_with_pepper(plain: str) -> str:
    """Stała długość przed bcrypt: hex HMAC-SHA256 (64 znaki), mieści się w limicie 72 bajtów bcrypt."""
    key = _pepper_bytes()
    if not key:
        return plain
    return hmac.new(key, plain.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(plain: str) -> str:
    material = _material_with_pepper(plain)
    return pwd_context.hash(material)


def verify_password(plain: str, stored: str) -> Tuple[bool, bool]:
    """
    Zwraca (poprawne, wymaga_rehash).

    - Nowy format (z pepperem): bcrypt(HMAC-SHA256(pepper, password)_hex).
    - Legacy: bcrypt(hasło_jawne) — zapis sprzed wprowadzenia peppera.
    - Gdy legacy zadziałało, a pepper jest ustawiony: needs_rehash=True (przelicz przy logowaniu).
    """
    key = _pepper_bytes()
    if key:
        material = hmac.new(key, plain.encode("utf-8"), hashlib.sha256).hexdigest()
        if pwd_context.verify(material, stored):
            return True, False
    if pwd_context.verify(plain, stored):
        return True, bool(key)
    return False, False
