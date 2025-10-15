from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from .models import UserPost, ContentData, Good
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
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset


    def get_serializer_class(self):
        if self.action == 'create':
            return UserPostCreateSerializer
        return UserPostSerializer

    def create(self, request, *args, **kwargs):
        user_id = request.user.username
        data = request.data.copy()
        data['user_id'] = user_id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            existing_post = UserPost.objects.filter(
                user_id=user_id,
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
                    serializer.save()

                    try:
                        Good.objects.create(
                            user_id=user_id,
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
                        'data': serializer.data
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

            if request.user.username != userpost.user_id:
                return Response({
                    'error': '投稿を削除する権限がありません'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            content_url = userpost.content_url
            user_id = userpost.user_id
            
            with transaction.atomic():  
                good_objects = Good.objects.filter(
                    user_id=user_id,
                    content_url=content_url
                )
                
                
                content_data = ContentData.objects.filter(content_url=content_url).first()
                if content_data and good_objects.exists():
                    content_data.good_count -= good_objects.count()
                    content_data.save()
                
                good_objects.delete()
                
                self.perform_destroy(userpost)
                
            return Response({
                'success': '投稿を削除しました'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': '削除に失敗しました'
            }, status=status.HTTP_400_BAD_REQUEST)

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
        user_id = request.data.get('user_id')
        content_url = request.data.get('content_url')
        if not user_id:
            return Response({'error': 'ユーザーIDが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        existing_good = Good.objects.filter(
            user_id=user_id,
            content_url=content_url
        ).first()
        if existing_good:
            existing_good.delete()
            content_data.good_count -= 1
            is_good = False
        else:   
            try:
                Good.objects.create(
                    user_id=user_id,
                    content_url=content_url
                )
                content_data.good_count += 1
                is_good = True
            except Exception as e:
                print(f"作品登録数の記録に失敗しました: {e}")
                return Response({
                    'error': f"作品登録数の記録に失敗しました: {e}"
                }, status=status.HTTP_400_BAD_REQUEST)
        content_data.save()
        response_data = ContentDataSerializer(content_data).data
        response_data['is_good'] = is_good
        return Response(response_data, status=status.HTTP_200_OK)