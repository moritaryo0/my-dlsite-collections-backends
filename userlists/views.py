from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import UserList, GootList
from .serializers import UserListSerializer, UserListCreateUpdateSerializer
from django.db import transaction
from userpost.models import UserPost, Good, ContentData


class UserListViewSet(viewsets.ModelViewSet):
    queryset = UserList.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ['retrieve_public', 'retrieve', 'goot']:
            return qs
        if self.request.user and self.request.user.is_authenticated:
            return qs.filter(owner=self.request.user)
        return qs.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserListCreateUpdateSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rename(self, request, pk=None):
        userlist = self.get_object()
        if request.user != userlist.owner:
            return Response({'detail': '権限がありません'}, status=403)
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'detail': 'nameが必要です'}, status=400)
        userlist.name = name
        try:
            userlist.save(update_fields=['name'])
        except Exception:
            return Response({'detail': '同名のリストが存在します'}, status=400)
        return Response(UserListSerializer(userlist, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_public(self, request, pk=None):
        userlist = self.get_object()
        if request.user != userlist.owner:
            return Response({'detail': '権限がありません'}, status=403)
        value = request.data.get('is_public')
        if value is None:
            return Response({'detail': 'is_publicが必要です'}, status=400)
        userlist.is_public = bool(value)
        userlist.save(update_fields=['is_public'])
        return Response({'id': userlist.id, 'is_public': userlist.is_public})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def goot(self, request, pk=None):
        userlist = self.get_object()
        gl = GootList.objects.filter(user=request.user, userlist=userlist).first()
        if gl:
            gl.delete()
            userlist.goot_count = max(0, userlist.goot_count - 1)
            userlist.save(update_fields=['goot_count'])
            return Response({'is_goot': False, 'goot_count': userlist.goot_count})
        # 新規のお気に入り登録は公開リストに限り再開
        if userlist.is_public:
            GootList.objects.create(user=request.user, userlist=userlist)
            userlist.goot_count += 1
            userlist.save(update_fields=['goot_count'])
            return Response({'is_goot': True, 'goot_count': userlist.goot_count})
        return Response({'detail': 'new_favorite_disabled', 'is_goot': False, 'goot_count': userlist.goot_count}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def retrieve_public(self, request, pk=None):
        userlist = self.get_object()
        if not userlist.is_public:
            user = getattr(request, 'user', None)
            from .models import GootList
            if not user or not getattr(user, 'is_authenticated', False) or (user != userlist.owner and not GootList.objects.filter(user=user, userlist=userlist).exists()):
                # 非公開: オーナーとGootList登録者以外は閲覧不可。フロントで申請UIを出せるよう最小情報を返す
                return Response({'detail': 'forbidden', 'id': userlist.id, 'name': userlist.name, 'is_public': userlist.is_public}, status=403)
        serializer = UserListSerializer(userlist, context={'request': request})
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        userlist = self.get_object()
        # 所有者のみ削除可能（念のため）
        if not request.user.is_authenticated or request.user != userlist.owner:
            return Response({'detail': '権限がありません'}, status=403)
        try:
            with transaction.atomic():
                # 紐づく投稿を削除し、ContentDataのカウントを整合
                posts = list(UserPost.objects.filter(list=userlist))
                for p in posts:
                    content_url = p.content_url
                    # Goodの削除（user優先、なければusername_legacy）
                    good_qs = Good.objects.filter(user=p.user, content_url=content_url)
                    if not good_qs.exists():
                        good_qs = Good.objects.filter(username_legacy=p.username_legacy, content_url=content_url)
                    cnt = good_qs.count()
                    if cnt:
                        cd = ContentData.objects.filter(content_url=content_url).first()
                        if cd:
                            cd.good_count -= cnt
                            if cd.good_count <= 0:
                                cd.delete()
                            else:
                                cd.save(update_fields=['good_count'])
                        good_qs.delete()
                    # 投稿本体を削除
                    p.delete()
                # リストを削除
                self.perform_destroy(userlist)
                return Response(status=204)
        except Exception:
            return Response({'detail': '削除に失敗しました'}, status=400)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        qs = UserList.objects.filter(goots__user=request.user).select_related('owner').distinct().order_by('-updated_at')
        serializer = UserListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def by_user(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'detail': 'username is required'}, status=400)
        qs = UserList.objects.filter(owner__username=username)
        # 非オーナーは公開のみ
        if not request.user.is_authenticated or request.user.username != username:
            qs = qs.filter(is_public=True)
        qs = qs.select_related('owner').order_by('-updated_at')
        serializer = UserListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def favorites_by_user(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'detail': 'username is required'}, status=400)
        qs = UserList.objects.filter(goots__user__username=username).select_related('owner').distinct()
        # ビューアが当人でなければ公開のみ
        if not request.user.is_authenticated or request.user.username != username:
            qs = qs.filter(is_public=True)
        qs = qs.order_by('-updated_at')
        serializer = UserListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
