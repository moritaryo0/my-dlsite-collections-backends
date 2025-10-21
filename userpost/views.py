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
from rest_framework.exceptions import ValidationError

# Create your views here.
def index(request):
    return HttpResponse("Hello, world.")

class UserPostViewSet(viewsets.ModelViewSet):
    queryset = UserPost.objects.all().order_by('-created_at')
    serializer_class = UserPostSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = UserPost.objects.all().order_by('-created_at')
        username = self.request.query_params.get('username') or self.request.query_params.get('user_id')
        if username:
            queryset = queryset.filter(user__username=username)
        return queryset


    def get_serializer_class(self):
        if self.action == 'create':
            return UserPostCreateSerializer
        return UserPostSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        username = request.user.username
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            existing_post = UserPost.objects.filter(
                user=request.user,
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
                            data = {
                                'content_url': content_url,
                                'title': ogp_data.get('title', ''),
                                'description': ogp_data.get('description', ''),
                                'image': ogp_data.get('image', ''),
                                'content_type': data.get('content_type', '未設定')
                            }
                            content_data = ContentData.objects.create(**data)
                        else:
                            return Response({
                                'error': 'OGPデータの取得に失敗しました'
                            }, status=status.HTTP_400_BAD_REQUEST)
                    instance = serializer.save(username_legacy=username, user=request.user)

                    try:
                        Good.objects.create(
                            user=request.user,
                            username_legacy=username,
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

            if (userpost.user and request.user != userpost.user) or (not userpost.user and request.user.username != userpost.username_legacy):
                return Response({'error': '投稿を削除する権限がありません'}, status=status.HTTP_400_BAD_REQUEST)

            content_url = userpost.content_url
            username = userpost.username_legacy

            with transaction.atomic():
                good_objects = Good.objects.filter(user=request.user, content_url=content_url)
                if not good_objects.exists():
                    good_objects = Good.objects.filter(username_legacy=username, content_url=content_url)

                content_data = ContentData.objects.filter(content_url=content_url).first()
                if content_data and good_objects.exists():
                    content_data.good_count -= good_objects.count()
                    content_data.save()

                good_objects.delete()
                self.perform_destroy(userpost)

            return Response({'success': '投稿を削除しました'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': '削除に失敗しました'}, status=status.HTTP_400_BAD_REQUEST)

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
    
    @action(detail=True, methods=['post'])
    def good(self, request, *args, **kwargs):
        #Goodの処理として作ったけど、これは作品の登録数の管理として使用する
        content_data = self.get_object()
        if not request.user or not request.user.is_authenticated:
            return Response({'error': '認証が必要です'}, status=status.HTTP_401_UNAUTHORIZED)
        content_url = request.data.get('content_url')
        if not content_url:
            return Response({'error': 'content_urlが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        existing_good = Good.objects.filter(user=request.user, content_url=content_url).first()
        if existing_good:
            existing_good.delete()
            content_data.good_count -= 1
            is_good = False
        else:
            try:
                Good.objects.create(
                    user=request.user,
                    username_legacy=request.user.username,
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
            posts = UserPost.objects.filter(user=u).order_by('-created_at')[:20]
            result.append({
                'username': u.username,
                'posts': [
                    {
                        'id': p.id,
                        'content_url': p.content_url,
                        'description': p.description,
                        'title': (ContentData.objects.filter(content_url=p.content_url).values_list('title', flat=True).first() or ''),
                        'image': (ContentData.objects.filter(content_url=p.content_url).values_list('image', flat=True).first() or ''),
                        'created_at': p.created_at.isoformat(),
                    } for p in posts
                ]
            })
        return Response(result)