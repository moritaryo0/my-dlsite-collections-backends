from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPost, ContentData

User = get_user_model()

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class UserPostSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    class Meta:
        model = UserPost
        fields = ['id', 'user', 'description', 'content_url', 'created_at', 'good_count']
        read_only_fields = ['id', 'created_at']
    
    def validate_content_url(self, value):
        """URLの検証"""
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value

class UserPostCreateSerializer(serializers.ModelSerializer):
    """投稿作成用のSerializer（必須フィールドのみ）"""
    class Meta:
        model = UserPost
        fields = ['description', 'content_url']

    def validate_content_url(self, value):
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value

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