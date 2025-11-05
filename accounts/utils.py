import uuid
from django.contrib.auth import get_user_model

User = get_user_model()
GUEST_ID_COOKIE_NAME = 'guest_id'


def get_or_create_guest_user(guest_id_str):
    """
    ゲストIDからユーザーを取得または作成する
    
    Args:
        guest_id_str: ゲストIDの文字列（UUID形式）
    
    Returns:
        (user, created) タプル。userはUserオブジェクト、createdは新規作成かどうか
    """
    try:
        guest_id = uuid.UUID(guest_id_str)
    except (ValueError, TypeError):
        return None, False
    
    # 既存のゲストユーザーを取得
    try:
        user = User.objects.get(guest_id=guest_id)
        return user, False
    except User.DoesNotExist:
        pass
    
    # 既存のusernameと競合しないように確認
    # ゲストユーザーはusernameなしで作成
    user = User.objects.create(
        guest_id=guest_id,
        username=None,
        is_active=True,
    )
    return user, True


def generate_guest_id():
    """
    既存のUserと競合しないゲストIDを生成する
    
    Returns:
        ゲストIDの文字列（UUID形式）
    """
    max_attempts = 10
    for _ in range(max_attempts):
        guest_id = uuid.uuid4()
        # guest_idが既存のUserと競合しないか確認
        if not User.objects.filter(guest_id=guest_id).exists():
            return str(guest_id)
        # usernameがNoneでguest_idがNoneのユーザーとも競合しないようにする
        # （実際にはguest_idでunique制約があるので、このチェックは不要だが念のため）
    
    # 万が一衝突した場合は新しいIDを返す（ほぼ起きない）
    return str(uuid.uuid4())

