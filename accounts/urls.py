from django.urls import path
from .views import RegisterView, MeView, LogoutView, RenameUsernameView, PrivacyView, GuestRenameUsernameView, GuestInfoView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('rename/', RenameUsernameView.as_view(), name='rename'),
    path('guest/rename/', GuestRenameUsernameView.as_view(), name='guest-rename'),
    path('guest/info/', GuestInfoView.as_view(), name='guest-info'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
]