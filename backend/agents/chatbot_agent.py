from backend.secrets_manager import get_secret


def get_ai_api_key():
    return get_secret("AI_API_KEY")
