from rest_framework import serializers
from .models import Author, Book


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer pour Author"""
    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'created_at']


class BookSerializer(serializers.ModelSerializer):
    """Serializer pour Book"""
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'pages', 'published_date', 'rating']

