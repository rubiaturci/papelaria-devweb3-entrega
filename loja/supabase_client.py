import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    chave = os.environ.get("SUPABASE_KEY")
    if not url or not chave:
        raise ImproperlyConfigured("Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env.")
    return create_client(url, chave)
