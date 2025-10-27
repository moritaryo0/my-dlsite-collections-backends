from rest_framework import serializers
from .models import UserList, GootList


class UserListSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    is_goot = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = UserList
        fields = ['id', 'owner_id', 'owner_username', 'name', 'description', 'is_public', 'goot_count', 'created_at', 'updated_at', 'is_goot']
        read_only_fields = ['id', 'owner_id', 'owner_username', 'goot_count', 'created_at', 'updated_at', 'is_goot']

    def get_is_goot(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return GootList.objects.filter(user=user, userlist=obj).exists()


class UserListCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserList
        fields = ['name', 'description', 'is_public']


class GootListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GootList
        fields = ['id', 'user', 'userlist', 'created_at']
        read_only_fields = ['id', 'created_at']

