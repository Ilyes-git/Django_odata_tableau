from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AuthorViewSet, BookViewSet

router = DefaultRouter()
router.register(r'Authors', AuthorViewSet, basename='author')
router.register(r'Books', BookViewSet, basename='book')

urlpatterns = router.urls

