from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router設定
router = DefaultRouter()
router.register(r'posts', views.UserPostViewSet, basename='userpost')
router.register(r'contents', views.ContentDataViewSet, basename='content') 

urlpatterns = [
    path("", views.index, name="index"),
    path('api/', include(router.urls)),
]