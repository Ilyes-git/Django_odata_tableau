from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import ALL_FIELDS
from .models import Person, Car, Product


class PersonSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Person
        fields = ALL_FIELDS
        expandable_fields = {
            'cars': ('my_app.serializers.CarSerializer', {'many': True})
        }


class CarSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Car
        fields = ALL_FIELDS
        expandable_fields = {
            'owner': ('my_app.serializers.PersonSerializer', {})
        }


class ProductSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Product
        fields = ALL_FIELDS