from typing import Optional
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def _translate_detail(detail: str) -> str:
    # Minimal mapping; extend as needed
    mappings = {
        'Invalid token': '無効なトークンです',
        'Given token not valid for any token type': 'トークンが無効です',
        'Token is invalid or expired': 'トークンが無効、または有効期限切れです',
        'Authentication credentials were not provided.': '認証情報が指定されていません',
        'Not found.': '見つかりませんでした',
        'Method "GET" not allowed.': 'GETメソッドは許可されていません',
        'Method "POST" not allowed.': 'POSTメソッドは許可されていません',
        'This field is required.': 'このフィールドは必須です',
        'A user with that username already exists.': 'このユーザー名は既に使用されています',
        'No active account found with the given credentials': 'ユーザー名またはパスワードが正しくありません',
        'Unable to log in with provided credentials.': 'ユーザー名またはパスワードが正しくありません',
        'User account is disabled.': 'アカウントが無効です',
    }
    return mappings.get(str(detail), str(detail))


def custom_exception_handler(exc, context) -> Optional[Response]:
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data

    # Standardize to Japanese messages
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                new_data[key] = [_translate_detail(v) for v in value]
            elif isinstance(value, dict):
                new_data[key] = {k: _translate_detail(v) for k, v in value.items()}
            else:
                new_data[key] = _translate_detail(value)
        response.data = new_data
    elif isinstance(data, (list, tuple)):
        response.data = [_translate_detail(v) for v in data]
    else:
        response.data = _translate_detail(data)

    # Ensure a generic Japanese error for 500-range if needed
    if 500 <= response.status_code < 600:
        response.data = {'error': 'サーバーエラーが発生しました'}
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return response


