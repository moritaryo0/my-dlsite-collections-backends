from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from .models import UserPost, ContentData, Good
from django.contrib.auth import get_user_model
from .serializers import UserPostSerializer, UserPostCreateSerializer, ContentDataSerializer, ContentDataCreateSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from .utils import dlsite_get_ogp_data
from userlists.models import UserList
from rest_framework.exceptions import ValidationError
from userlists.models import UserList
from django.db.models import Q
from accounts.utils import get_or_create_guest_user

# Create your views here.
def index(request):
    return HttpResponse("Hello, world.")

class UserPostViewSet(viewsets.ModelViewSet):
    queryset = UserPost.objects.all().order_by('-created_at')
    serializer_class = UserPostSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            # ゲストユーザーも投稿できるようにAllowAnyに変更
            permission_classes = [AllowAny]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = UserPost.objects.all().order_by('-created_at')
        username = self.request.query_params.get('username') or self.request.query_params.get('user_id')
        list_id = self.request.query_params.get('list_id')
        if username:
            queryset = queryset.filter(user__username=username)
        if list_id:
            try:
                lst = UserList.objects.select_related('owner').get(id=list_id)
            except UserList.DoesNotExist:
                return queryset.none()
            # 非公開: オーナーまたはGootList登録者のみ閲覧可
            if not lst.is_public:
                user = getattr(self.request, 'user', None)
                if not user or not user.is_authenticated:
                    return queryset.none()
                from userlists.models import GootList
                is_authorized = (user == lst.owner) or GootList.objects.filter(user=user, userlist=lst).exists()
                if not is_authorized:
                    return queryset.none()
            queryset = queryset.filter(list_id=lst.id)
        return queryset


    def get_serializer_class(self):
        if self.action == 'create':
            return UserPostCreateSerializer
        return UserPostSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        # 認証済みユーザーまたはゲストユーザーを取得
        user = None
        username = None
        
        if request.user.is_authenticated:
            user = request.user
            username = request.user.username
        else:
            # ゲストユーザーの場合、guest_idからUserを取得または作成
            guest_id = getattr(request, 'guest_id', None)
            if guest_id:
                user, _ = get_or_create_guest_user(guest_id)
                # username_legacy には空文字ではなくゲストIDベースの識別子を保存
                username = f"u-{guest_id}"
            else:
                return Response({
                    'error': '認証が必要です'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user:
            return Response({
                'error': '認証が必要です'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = self.get_serializer(data=data, context={'request': request})
        if serializer.is_valid():
            existing_post = UserPost.objects.filter(
                user=user,
                content_url=data.get('content_url')
            ).first()
            if existing_post:
                return Response({
                    'error': 'このURLはすでに登録されています'
                }, status=status.HTTP_400_BAD_REQUEST)
            content_url = data.get('content_url')
            if not content_url:
                return Response({
                    'error': 'URLが必要です'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                with transaction.atomic():
                    content_data = ContentData.objects.filter(content_url=content_url).first()
                    if not content_data:
                        try:
                            ogp_data = dlsite_get_ogp_data(content_url)
                        except ValidationError:
                            return Response({
                                'error': '無効なURLです'
                            }, status=status.HTTP_400_BAD_REQUEST)
                        if ogp_data:
                            data_cd = {
                                'content_url': content_url,
                                'title': ogp_data.get('title', ''),
                                'description': ogp_data.get('description', ''),
                                'image': ogp_data.get('image', ''),
                                'content_type': data.get('content_type', '未設定')
                            }
                            content_data = ContentData.objects.create(**data_cd)
                        else:
                            return Response({
                                'error': 'OGPデータの取得に失敗しました'
                            }, status=status.HTTP_400_BAD_REQUEST)
                    # Determine list to assign
                    list_instance = getattr(serializer, '_list_instance', None)
                    if list_instance is None:
                        # default to Home list
                        list_instance, _ = UserList.objects.get_or_create(owner=user, name='Home', defaults={'description': 'ホーム', 'is_public': True})
                    instance = UserPost.objects.create(
                        username_legacy=(username or (request.user.username if request.user.is_authenticated else 'guest')),
                        user=user,
                        description=serializer.validated_data.get('description'),
                        content_url=content_url,
                        list=list_instance
                    )

                    try:
                        Good.objects.create(
                            user=user,
                            username_legacy=(username or (request.user.username if request.user.is_authenticated else 'guest')),
                            content_url=content_url
                        )
                        content_data.good_count += 1
                        content_data.save()
                    except Exception as e:
                        print(f"作品登録数の記録に失敗しました: {e}")
                        return Response({
                            'error': f"作品登録数の記録に失敗しました: {e}"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    return Response({
                        'success': '投稿を完了',
                        'data': UserPostSerializer(instance).data
                    }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(e)
                return Response({
                        'error': '投稿に失敗しました'
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            userpost = self.get_object()

            # 操作主体のユーザー（認証 or ゲスト）を取得
            actor = request.user if getattr(request.user, 'is_authenticated', False) else None
            actor_name = None
            if actor is None:
                guest_id = getattr(request, 'guest_id', None)
                if guest_id:
                    actor, _ = get_or_create_guest_user(guest_id)
                    actor_name = f"u-{guest_id}"
            else:
                actor_name = getattr(actor, 'username', None)

            # 権限チェック
            if (userpost.user and actor != userpost.user) or (not userpost.user and actor_name != userpost.username_legacy):
                return Response({'error': '投稿を削除する権限がありません'}, status=status.HTTP_400_BAD_REQUEST)

            content_url = userpost.content_url
            username = userpost.username_legacy

            with transaction.atomic():
                good_objects = Good.objects.filter(user=actor, content_url=content_url)
                if not good_objects.exists():
                    good_objects = Good.objects.filter(username_legacy=username, content_url=content_url)

                content_data = ContentData.objects.filter(content_url=content_url).first()
                if content_data and good_objects.exists():
                    content_data.good_count -= good_objects.count()
                    if content_data.good_count <= 0:
                        content_data.delete()
                        content_data = None
                    else:
                        content_data.save()

                good_objects.delete()
                self.perform_destroy(userpost)

            return Response({'success': '投稿を削除しました'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': '削除に失敗しました'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def move_list(self, request, *args, **kwargs):
        try:
            userpost = self.get_object()
            # 操作主体のユーザー（認証 or ゲスト）を取得
            actor = request.user if getattr(request.user, 'is_authenticated', False) else None
            if actor is None:
                guest_id = getattr(request, 'guest_id', None)
                if guest_id:
                    actor, _ = get_or_create_guest_user(guest_id)
            # 権限チェック
            if (userpost.user and actor != userpost.user) or (not userpost.user and (not actor or actor.guest_id is None)):
                return Response({'error': 'この投稿を編集する権限がありません'}, status=status.HTTP_400_BAD_REQUEST)
            list_id = request.data.get('list_id')
            if list_id is None:
                return Response({'error': 'list_idが必要です'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target_list = UserList.objects.get(id=int(list_id), owner=request.user)
            except UserList.DoesNotExist:
                return Response({'error': '指定されたリストが見つからないか、権限がありません'}, status=status.HTTP_400_BAD_REQUEST)
            userpost.list = target_list
            userpost.save(update_fields=['list'])
            return Response({'success': True, 'data': UserPostSerializer(userpost).data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'リスト変更に失敗しました'}, status=status.HTTP_400_BAD_REQUEST)

class ContentDataViewSet(viewsets.ModelViewSet):
    queryset = ContentData.objects.all().order_by('-created_at')
    serializer_class = ContentDataSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return ContentDataCreateSerializer
        return ContentDataSerializer
    
    def create(self, request, *args, **kwargs):
        content_url = request.data.get('content_url')
        if not content_url:
            return Response({
                'error': 'URLが必要です'
            }, status=status.HTTP_400_BAD_REQUEST)
        content_type = request.data.get('content_type', '未設定')
        ogp_data = dlsite_get_ogp_data(content_url)
        if not ogp_data:
            return Response({
                'error': 'OGPデータの取得に失敗しました'
            }, status=status.HTTP_400_BAD_REQUEST)
        data = {
            'content_url': content_url,
            'title': ogp_data.get('title', ''),
            'description': ogp_data.get('description', ''),
            'image': ogp_data.get('image', ''),
            'content_type': content_type
        }
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': 'データを保存',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def good(self, request, *args, **kwargs):
        #Goodの処理として作ったけど、これは作品の登録数の管理として使用する
        content_data = self.get_object()
        # 操作主体（認証 or ゲスト）
        actor = request.user if getattr(request.user, 'is_authenticated', False) else None
        actor_name = getattr(actor, 'username', None) if actor else None
        if actor is None:
            guest_id = getattr(request, 'guest_id', None)
            if guest_id:
                actor, _ = get_or_create_guest_user(guest_id)
                actor_name = f"u-{guest_id}"
        content_url = request.data.get('content_url')
        if not content_url:
            return Response({'error': 'content_urlが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        existing_good = Good.objects.filter(user=actor, content_url=content_url).first()
        if existing_good:
            existing_good.delete()
            content_data.good_count -= 1
            is_good = False
            if content_data.good_count <= 0:
                content_data.delete()
                return Response({'id': content_data.id if hasattr(content_data, 'id') else None, 'is_good': is_good, 'good_count': 0}, status=status.HTTP_200_OK)
        else:
            try:
                Good.objects.create(
                    user=actor,
                    username_legacy=(actor_name or 'guest'),
                    content_url=content_url
                )
                content_data.good_count += 1
                is_good = True
            except Exception as e:
                print(f"作品登録数の記録に失敗しました: {e}")
                return Response({'error': f"作品登録数の記録に失敗しました: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        content_data.save()
        response_data = ContentDataSerializer(content_data).data
        response_data['is_good'] = is_good
        return Response(response_data, status=status.HTTP_200_OK)


class PublicUsersView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        """List users with private=False and their recent posts."""
        User = get_user_model()
        users = User.objects.filter(private=False).order_by('id')[:100]
        result = []
        for u in users:
            posts = (
                UserPost.objects
                .filter(user=u)
                .filter(Q(list__isnull=True) | Q(list__is_public=True))
                .order_by('-created_at')[:20]
            )
            result.append({
                'username': u.username,
                'posts': [
                    {
                        'id': p.id,
                        'content_url': p.content_url,
                        'description': p.description,
                        'title': (ContentData.objects.filter(content_url=p.content_url).values_list('title', flat=True).first() or ''),
                        'image': (ContentData.objects.filter(content_url=p.content_url).values_list('image', flat=True).first() or ''),
                        'content_type': (ContentData.objects.filter(content_url=p.content_url).values_list('content_type', flat=True).first() or ''),
                        'created_at': p.created_at.isoformat(),
                    } for p in posts
                ]
            })
        return Response(result)