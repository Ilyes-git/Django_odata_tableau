from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import ALL_FIELDS
from .models import Person, Car, Product


class PersonSerializer(FlexFieldsModelSerializer):
    """Serializer pour Person avec support $expand via drf-flex-fields"""
    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'birth_date', 'cars']
        expandable_fields = {
            'cars': ('my_app.serializers.CarSerializer', {'many': True})
        }


class CarSerializer(FlexFieldsModelSerializer):
    """Serializer pour Car avec support $expand via drf-flex-fields"""
    class Meta:
        model = Car
        fields = ['id', 'brand', 'model', 'year', 'owner']
        expandable_fields = {
            'owner': ('my_app.serializers.PersonSerializer', {})
        }


class ProductSerializer(FlexFieldsModelSerializer):
    """Serializer pour Product avec support $expand"""
    class Meta:
        model = Product
        fields = ALL_FIELDS