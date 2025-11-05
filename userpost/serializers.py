from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPost, ContentData
from userlists.models import UserList
from accounts.utils import get_or_create_guest_user

User = get_user_model()

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class UserPostSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    list_id = serializers.IntegerField(source='list.id', read_only=True)
    class Meta:
        model = UserPost
        fields = ['id', 'user', 'description', 'content_url', 'created_at', 'good_count', 'list_id']
        read_only_fields = ['id', 'created_at']
    
    def validate_content_url(self, value):
        """URLの検証"""
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value

class UserPostCreateSerializer(serializers.ModelSerializer):
    """投稿作成用のSerializer（必須フィールドのみ）"""
    list_id = serializers.IntegerField(required=False, allow_null=True)
    class Meta:
        model = UserPost
        fields = ['description', 'content_url', 'list_id']

    def validate_content_url(self, value):
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value

    def validate(self, attrs):
        list_id = attrs.pop('list_id', None) if 'list_id' in attrs else None
        self._list_instance = None
        request = self.context.get('request')
        # 現在の操作主体ユーザーを取得（認証済み or ゲスト）
        user = None
        if request is not None:
            req_user = getattr(request, 'user', None)
            if req_user is not None and getattr(req_user, 'is_authenticated', False):
                user = req_user
            else:
                guest_id = getattr(request, 'guest_id', None)
                if guest_id:
                    user, _ = get_or_create_guest_user(guest_id)
        if list_id is not None:
            try:
                lst = UserList.objects.get(id=list_id)
            except UserList.DoesNotExist:
                raise serializers.ValidationError({'list_id': '指定されたリストが存在しません'})
            if not user or (lst.owner_id != user.id):
                raise serializers.ValidationError({'list_id': 'このリストに投稿する権限がありません'})
            self._list_instance = lst
        return attrs

class ContentDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentData
        fields = ['id', 'content_url', 'title', 'description', 'image', 'created_at', 'content_type', 'good_count']
        read_only_fields = ['id', 'created_at']
    
    def validate_content_url(self, value):
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value

class ContentDataCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentData
        fields = ['content_url', 'title', 'description', 'image', 'content_type']
    
    def validate_content_url(self, value):
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value