from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import UserPost, ContentData
from .utils import dlsite_get_ogp_data
import requests
from rest_framework.test import APIRequestFactory
from userpost.views import UserPostViewSet

# Create your tests here.
class TestDLsiteOGPData(TestCase):
    def test_valid_dlsite_url(self):
        """正常なDLSiteのURLでOGPデータが取得できることをテスト"""
        url = 'https://www.dlsite.com/maniax/work/=/product_id/RJ01473335.html'
        ogp_data = dlsite_get_ogp_data(url)
        print(ogp_data)
        
        # 戻り値がNoneでないことを確認
        self.assertIsNotNone(ogp_data)
        
        # 必要なキーが存在することを確認
        expected_keys = ['title', 'description', 'image_url', 'url']
        for key in expected_keys:
            self.assertIn(key, ogp_data)
            
        # URLが正しく保存されていることを確認
        self.assertEqual(ogp_data['url'], url)

    def test_invalid_domain(self):
        """DLSite以外のドメインの場合はNoneが返されることをテスト"""
        url = 'https://example.com/some/path'
        ogp_data = dlsite_get_ogp_data(url)
        self.assertIsNone(ogp_data)

    @patch('requests.get')
    def test_network_error(self, mock_get):
        """ネットワークエラー時にNoneが返されることをテスト"""
        mock_get.side_effect = requests.exceptions.RequestException()
        url = 'https://www.dlsite.com/maniax/work/=/product_id/RJ01473335.html'
        ogp_data = dlsite_get_ogp_data(url)
        self.assertIsNone(ogp_data)

    @patch('requests.get')
    def test_timeout_error(self, mock_get):
        """タイムアウト時にNoneが返されることをテスト"""
        mock_get.side_effect = requests.exceptions.Timeout()
        url = 'https://www.dlsite.com/maniax/work/=/product_id/RJ01473335.html'
        ogp_data = dlsite_get_ogp_data(url)
        self.assertIsNone(ogp_data)

    def test_malformed_url(self):
        """不正なURL形式の場合にNoneが返されることをテスト"""
        url = 'not-a-valid-url'
        ogp_data = dlsite_get_ogp_data(url)
        self.assertIsNone(ogp_data)

class TestUserPostCreate(APITestCase):
    """UserPostのcreateメソッドのテスト"""
    
    def setUp(self):
        """テスト用の初期データを設定"""
        self.url = reverse('userpost-list')  # UserPostViewSetのリストエンドポイント
        self.valid_data = {
            'user_id': 'test_user',
            'description': 'テスト投稿',
            'content_url': 'https://www.dlsite.com/maniax/work/=/product_id/RJ01230861.html'
        }
    
    @patch('userpost.views.dlsite_get_ogp_data')
    def test_create_post_with_existing_content_data(self, mock_ogp):
        """既存のContentDataがある場合の投稿作成テスト"""
        # 既存のContentDataを作成
        ContentData.objects.create(
            content_url=self.valid_data['content_url'],
            title='既存タイトル',
            description='既存説明',
            image='https://example.com/image.jpg'
        )
        
        # OGP取得は呼ばれないことを確認
        mock_ogp.return_value = None
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        # ステータスコードの確認
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # レスポンス内容の確認
        self.assertIn('success', response.data)
        self.assertIn('data', response.data)
        
        # データベースに保存されたことを確認
        self.assertEqual(UserPost.objects.count(), 1)
        post = UserPost.objects.first()
        self.assertEqual(post.user_id, 'test_user')
        self.assertEqual(post.description, 'テスト投稿')
        
        # OGP取得が呼ばれていないことを確認
        mock_ogp.assert_not_called()
    
    @patch('userpost.views.dlsite_get_ogp_data')
    def test_create_post_with_new_content_data(self, mock_ogp):
        """新しいContentDataを作成する場合の投稿作成テスト"""
        # OGPデータをモック
        mock_ogp.return_value = {
            'title': 'OGPタイトル',
            'description': 'OGP説明',
            'image': 'https://example.com/ogp_image.jpg'
        }
        print(self.url)
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        # ステータスコードの確認
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # UserPostが作成されたことを確認
        self.assertEqual(UserPost.objects.count(), 1)
        
        # ContentDataが作成されたことを確認
        self.assertEqual(ContentData.objects.count(), 1)
        content_data = ContentData.objects.first()
        self.assertEqual(content_data.title, 'OGPタイトル')
        self.assertEqual(content_data.description, 'OGP説明')
        self.assertEqual(content_data.image, 'https://example.com/ogp_image.jpg')
        
        # OGP取得が呼ばれたことを確認
        mock_ogp.assert_called_once_with(self.valid_data['content_url'])
    
    @patch('userpost.views.dlsite_get_ogp_data')
    def test_create_post_ogp_failure(self, mock_ogp):
        """OGP取得に失敗した場合のテスト"""
        # OGP取得を失敗させる
        mock_ogp.return_value = None
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        # エラーレスポンスが返されることを確認
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # データが作成されていないことを確認
        self.assertEqual(UserPost.objects.count(), 0)
        self.assertEqual(ContentData.objects.count(), 0)
    
    def test_create_post_missing_content_url(self):
        """content_urlが不足している場合のテスト"""
        data_without_url = {
            'user_id': 'test_user',
            'description': 'テスト投稿'
        }
        
        response = self.client.post(self.url, data_without_url, format='json')
        
        # バリデーションエラーが返されることを確認
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class TestUserPostCreateDirect(APITestCase):
    def test_create_direct(self):
        factory = APIRequestFactory()
        view = UserPostViewSet.as_view({'post': 'create'})
        payload = {
            'user_id': 'test_user',
            'description': 'テスト投稿',
            'content_url': 'https://www.dlsite.com/maniax/work/=/product_id/RJ01230861.html'
        }
        request = factory.post('/userpost/api/posts/', payload, format='json')
        response = view(request)  # 直接呼ぶ
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)