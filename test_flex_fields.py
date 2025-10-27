#!/usr/bin/env python
import os
import django
from urllib.parse import urlencode

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_odata_tableau.settings')
django.setup()

# Faire les migrations
from django.core.management import call_command
call_command('migrate', '--run-syncdb', verbosity=0)

from my_app.models import Person, Car
from my_app.serializers import CarSerializer, PersonSerializer
from rest_framework.test import APIRequestFactory

# Créer test data
person = Person.objects.create(first_name="Test", last_name="Person")
car = Car.objects.create(brand="BMW", model="X5", year=2020, owner=person)

# Créer une factory DRF
factory = APIRequestFactory()

# Test 1: Sans expand
print("CarSerializer - Sans expand:")
request = factory.get('/')
context = {'request': request}
serializer = CarSerializer(car, context=context)
print(serializer.data)
print()

# Test 2: Avec expand=owner
print("CarSerializer - Avec expand=owner:")
request = factory.get('/', {'expand': 'owner'})
context = {'request': request}
serializer = CarSerializer(car, context=context)
print(serializer.data)
print()

# Test 3: PersonSerializer avec expand=cars
print("PersonSerializer - Avec expand=cars:")
request = factory.get('/', {'expand': 'cars'})
context = {'request': request}
serializer = PersonSerializer(person, context=context)
print(serializer.data)

