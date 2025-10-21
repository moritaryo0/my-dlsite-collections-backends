from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_username
from django.contrib.auth import get_user_model


User = get_user_model()


class SocialAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # email は保存しない
        user.email = None
        # プロバイダのユーザー名を優先して username に設定
        username = (
            data.get('username')
            or data.get('screen_name')
            or sociallogin.account.extra_data.get('screen_name')
            or sociallogin.account.uid
        )
        if username:
            user_username(user, username)
        return user

    def save_user(self, request, sociallogin, form=None):
        # 保存前に既存かどうかを記録
        was_existing = sociallogin.is_existing
        user = super().save_user(request, sociallogin, form)
        # 新規サインアップだった場合、初回リネーム導線を出すためのフラグを立てる
        if not was_existing:
            try:
                request.session['is_new_social_user'] = True
            except Exception:
                pass
        return user


