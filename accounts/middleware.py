from django.utils.deprecation import MiddlewareMixin
from .utils import GUEST_ID_COOKIE_NAME, generate_guest_id

GUEST_ID_COOKIE_AGE = 365 * 24 * 60 * 60  # 1年間


class GuestIdMiddleware(MiddlewareMixin):
    """
    ゲストIDをクッキーで管理するミドルウェア
    ゲストIDはクッキーにのみ保存し、Userテーブルには実際の操作時に保存される
    """
    
    def process_request(self, request):
        # 既に認証済みのユーザーはスキップ
        if request.user.is_authenticated:
            return None
        
        # クッキーからゲストIDを取得
        guest_id_str = request.COOKIES.get(GUEST_ID_COOKIE_NAME)
        
        # ゲストIDが存在しない場合は新しく生成
        if not guest_id_str:
            guest_id_str = generate_guest_id()
            # クッキーを設定するためにrequestに保存
            request.set_guest_id_cookie = guest_id_str
        else:
            # ゲストIDの形式を検証（UUID形式かどうか）
            try:
                import uuid
                uuid.UUID(guest_id_str)
            except (ValueError, TypeError):
                # 無効なUUIDの場合は新しく生成
                guest_id_str = generate_guest_id()
                request.set_guest_id_cookie = guest_id_str
        
        # requestにゲストIDを保存（後で使用可能にするため）
        request.guest_id = guest_id_str
        
        return None
    
    def process_response(self, request, response):
        # クッキーを設定する必要がある場合
        if hasattr(request, 'set_guest_id_cookie'):
            # localhost/127.0.0.1の場合はsecure=False、それ以外はsecure=True
            is_secure = not (
                request.get_host().startswith('localhost') or 
                request.get_host().startswith('127.0.0.1')
            )
            response.set_cookie(
                GUEST_ID_COOKIE_NAME,
                request.set_guest_id_cookie,
                max_age=GUEST_ID_COOKIE_AGE,
                httponly=True,
                samesite='Lax',
                secure=is_secure,
            )
        return response

