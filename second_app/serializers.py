from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import ALL_FIELDS

from .models import Author, Book


class AuthorSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Author
        fields = ALL_FIELDS
        expandable_fields = {
            'books': ('second_app.serializers.BookSerializer', {'many': True})
        }


class BookSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Book
        fields = ALL_FIELDS
        expandable_fields = {
            'author': ('second_app.serializers.AuthorSerializer', {})
        }

