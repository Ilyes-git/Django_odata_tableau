from rest_framework.serializers import ALL_FIELDS

from .models import Person, Car
from rest_framework import serializers
from .models import Product


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ALL_FIELDS


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ALL_FIELDS



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ALL_FIELDS