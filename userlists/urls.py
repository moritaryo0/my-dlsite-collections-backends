from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserListViewSet

router = DefaultRouter()
router.register(r'lists', UserListViewSet, basename='userlist')

urlpatterns = [
    path('api/', include(router.urls)),
]

