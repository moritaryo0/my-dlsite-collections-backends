from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializer import RegisterSerializer, UserSerializer, LogoutSerializer, RenameUsernameSerializer
from .utils import get_or_create_guest_user

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class MeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # 認証済みユーザーの場合のみユーザー情報を返す
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        # ゲストユーザーの場合はnullを返す
        return Response(None)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RenameUsernameView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RenameUsernameSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(serializer.instance).data, status=status.HTTP_200_OK)


class PrivacyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'private': bool(getattr(request.user, 'private', False))})

    def post(self, request):
        value = request.data.get('private')
        if isinstance(value, bool) is False:
            # allow string 'true'/'false'
            if isinstance(value, str):
                value = value.lower() in ('1', 'true', 'yes', 'on')
            else:
                return Response({'error': 'private は true/false で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.private = bool(value)
        request.user.save(update_fields=['private'])
        return Response({'private': request.user.private}, status=status.HTTP_200_OK)


class GuestRenameUsernameView(APIView):
    """ゲストユーザーのusernameを設定/変更するエンドポイント"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        if not username:
            return Response({'error': 'ユーザー名は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ゲストIDからユーザーを取得または作成
        guest_id = getattr(request, 'guest_id', None)
        if not guest_id:
            return Response({'error': 'ゲストIDが見つかりません'}, status=status.HTTP_400_BAD_REQUEST)
        
        user, created = get_or_create_guest_user(guest_id)
        if not user:
            return Response({'error': 'ユーザーの取得に失敗しました'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 既存のusernameと競合しないか確認
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return Response({'error': 'すでに存在するユーザー名です'}, status=status.HTTP_400_BAD_REQUEST)
        
        # usernameを設定
        user.username = username
        user.save(update_fields=['username'])
        
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class GuestInfoView(APIView):
    """ゲストの識別情報を返す（ゲストID経由）。フロントで表示名 u-{id} 用に利用。
    認証不要。ミドルウェアが guest_id を生成・付与する。
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        guest_id = getattr(request, 'guest_id', None)
        if not guest_id:
            return Response({'guest_id': None}, status=status.HTTP_200_OK)
        return Response({'guest_id': guest_id}, status=status.HTTP_200_OK)