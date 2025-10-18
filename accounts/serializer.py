from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        username = validated_data['username']
        email = validated_data.get('email') or None
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password)
        return user

class RenameUsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']
    username = serializers.CharField(max_length=255)
    
    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('ユーザー名は必須です')
        request = self.context.get('request')
        if request.user.username == value:
            raise serializers.ValidationError('現在と同じユーザー名です')
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('すでに存在するユーザー名です')
        return value
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.username = self.validated_data['username']
        user.save(update_fields=['username'])
        return user

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError('無効なトークンです')