from django.urls import path
from .views import RegisterView, MeView, LogoutView, RenameUsernameView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('rename/', RenameUsernameView.as_view(), name='rename'),
]