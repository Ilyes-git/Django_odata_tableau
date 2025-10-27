from rest_flex_fields import FlexFieldsModelSerializer
from .models import Author, Book


class AuthorSerializer(FlexFieldsModelSerializer):
    """Serializer pour Author avec support $expand"""
    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'created_at', 'books']
        expandable_fields = {
            'books': ('second_app.serializers.BookSerializer', {'many': True})
        }


class BookSerializer(FlexFieldsModelSerializer):
    """Serializer pour Book avec support $expand"""
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'pages', 'published_date', 'rating']
        expandable_fields = {
            'author': ('second_app.serializers.AuthorSerializer', {})
        }

