from .models import Person, Car
from rest_framework import serializers
from .models import Product


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'birth_date']


class CarSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Car
        fields = ['id', 'brand', 'model', 'year', 'owner']



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'quantity', 'category', 'created_at']