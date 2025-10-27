"""
Configuration pytest et pytest-django
"""
import pytest
from django.test import Client
from my_app.models import Person, Car


@pytest.fixture
def api_client():
    """Fixture pour le client de test Django"""
    return Client()


@pytest.fixture
def base_url():
    """Fixture pour l'URL de base de l'API OData"""
    return "/odata"


@pytest.fixture
def person(db):
    """Fixture pour créer une personne de test"""
    return Person.objects.create(
        first_name="Lucie",
        last_name="Marie",
        birth_date="1990-01-15"
    )


@pytest.fixture
def another_person(db):
    """Fixture pour créer une autre personne de test"""
    return Person.objects.create(
        first_name="Alice",
        last_name="Sanchez",
        birth_date="1985-03-20"
    )


@pytest.fixture
def car_data(db, person):
    """Fixture pour créer des voitures de test"""
    cars = [
        Car.objects.create(brand="BMW", model="X5", year=2020, owner=person),
        Car.objects.create(brand="Audi", model="A4", year=2018, owner=person),
        Car.objects.create(brand="Volkswagen", model="Golf", year=2016, owner=person),
    ]
    return cars


