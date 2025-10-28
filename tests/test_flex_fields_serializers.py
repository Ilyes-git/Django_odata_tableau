import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request as DRFRequest
from my_app.models import Person, Car
from my_app.serializers import CarSerializer, PersonSerializer


@pytest.fixture
def api_factory():
    """Fixture pour APIRequestFactory"""
    return APIRequestFactory()


@pytest.fixture
def test_data(db):
    """Fixture pour créer les données de test"""
    person = Person.objects.create(first_name="Test", last_name="Person")
    car = Car.objects.create(brand="BMW", model="X5", year=2020, owner=person)
    return {"person": person, "car": car}


class TestCarSerializerFlexFields:
    """Tests pour CarSerializer avec flex fields"""

    def test_car_serializer_sans_expand(self, api_factory, test_data):
        """Test CarSerializer sans expand"""
        car = test_data["car"]
        request = api_factory.get('/')
        drf_request = DRFRequest(request)
        context = {'request': drf_request}

        serializer = CarSerializer(car, context=context)
        data = serializer.data

        # Vérifier que les champs de base sont présents
        assert 'id' in data
        assert data['brand'] == 'BMW'
        assert data['model'] == 'X5'
        assert data['year'] == 2020
        # Sans expand, owner devrait être un ID
        assert data['owner'] == car.owner.id

    def test_car_serializer_avec_expand_owner(self, api_factory, test_data):
        """Test CarSerializer avec expand=owner"""
        car = test_data["car"]
        request = api_factory.get('/', {'expand': 'owner'})
        drf_request = DRFRequest(request)
        context = {'request': drf_request}

        serializer = CarSerializer(car, context=context)
        data = serializer.data

        # Vérifier que les champs de base sont présents
        assert 'id' in data
        assert data['brand'] == 'BMW'
        assert data['model'] == 'X5'
        # Avec expand, owner devrait être un objet
        assert isinstance(data['owner'], dict)
        assert data['owner']['first_name'] == 'Test'
        assert data['owner']['last_name'] == 'Person'

    def test_person_serializer_avec_expand_cars(self, api_factory, test_data):
        """Test PersonSerializer avec expand=cars"""
        person = test_data["person"]
        request = api_factory.get('/', {'expand': 'cars'})
        drf_request = DRFRequest(request)
        context = {'request': drf_request}

        serializer = PersonSerializer(person, context=context)
        data = serializer.data

        # Vérifier que les champs de base sont présents
        assert 'id' in data
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'Person'
        # Avec expand, cars devrait être une liste d'objets
        assert isinstance(data['cars'], list)
        assert len(data['cars']) == 1
        assert data['cars'][0]['brand'] == 'BMW'
        assert data['cars'][0]['model'] == 'X5'

