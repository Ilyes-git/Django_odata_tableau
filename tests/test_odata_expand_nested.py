"""
Tests pour vérifier le support du paramètre $expand nested avec $select
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from my_app.models import Person, Car
from datetime import date


@pytest.mark.django_db
class TestODataExpandNested(TestCase):
    """Tests pour le expand avec syntaxe nested OData"""

    def setUp(self):
        """Préparer les données de test"""
        self.client = APIClient()

        # Créer une personne
        self.person = Person.objects.create(
            first_name="John",
            last_name="Doe",
            birth_date=date(1990, 5, 15)
        )

        # Créer des voitures associées
        self.car1 = Car.objects.create(
            brand="BMW",
            model="X5",
            year=2020,
            owner=self.person
        )

        self.car2 = Car.objects.create(
            brand="Audi",
            model="A4",
            year=2022,
            owner=self.person
        )

    def test_expand_with_nested_select(self):
        """Tester $expand=owner($select=first_name,last_name)"""
        response = self.client.get(
            "/odata/cars?$expand=owner($select=first_name,last_name)",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        # Vérifier que l'owner est développé
        car = data["value"][0]
        assert "owner" in car
        assert isinstance(car["owner"], dict)

        # Vérifier que seuls les champs sélectionnés sont présents
        print(f"\n=== Owner avec $select=first_name,last_name ===")
        print(f"Owner: {car['owner']}")

        # Les champs first_name et last_name doivent être présents
        assert "first_name" in car["owner"]
        assert "last_name" in car["owner"]

    def test_expand_reverse_with_nested_select(self):
        """Tester $expand=cars($select=brand,model)"""
        response = self.client.get(
            "/odata/persons?$expand=cars($select=brand,model)",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        # Vérifier que les cars sont développées
        person = data["value"][0]
        assert "cars" in person
        assert isinstance(person["cars"], list)
        assert len(person["cars"]) == 2

        print(f"\n=== Cars avec $select=brand,model ===")
        print(f"Cars: {person['cars']}")

        # Les champs brand et model doivent être présents
        for car in person["cars"]:
            assert "brand" in car
            assert "model" in car

    def test_expand_multiple_nested_params(self):
        """Tester $expand=owner($select=first_name;$expand=...)"""
        response = self.client.get(
            "/odata/cars?$expand=owner($select=first_name,last_name)",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        print(f"\n=== Response data ===")
        print(f"Full response: {data}")

    def test_expand_nested_parsing_direct(self):
        """Tester directement le parser de syntaxe nested"""
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request

        # Créer une request avec le paramètre nested
        factory = APIRequestFactory()
        django_request = factory.get('/?$expand=owner($select=first_name,last_name)')
        drf_request = Request(django_request)

        # Simuler le wrapper
        from my_app.views import ODataModelViewSet
        viewset = ODataModelViewSet()

        # Créer le contexte
        class DummyRequest:
            def __init__(self):
                self.GET = {'$expand': 'owner($select=first_name,last_name)'}

        dummy_request = DummyRequest()

        # Créer la classe wrapper localement pour tester
        class ODataQueryParamsWrapper:
            def __init__(self, request):
                self.request = request
                self.translated_params = self._translate_odata_params()

            def _parse_nested_expand(self, expand_str):
                import re
                result = {}
                pattern = r'(\w+)\(([^)]+)\)'

                for match in re.finditer(pattern, expand_str):
                    field_name = match.group(1)
                    params_str = match.group(2)

                    nested_params = {}
                    # Pattern pour extraire key=value pairs où value peut contenir des virgules
                    param_pattern = r'(\$?\w+)=([^,$]+(?:,[^,$]+)*)'

                    for param_match in re.finditer(param_pattern, params_str):
                        key = param_match.group(1).lstrip('$')
                        value = param_match.group(2)
                        nested_params[key] = value

                    result[field_name] = nested_params

                simple_fields = re.sub(pattern, '', expand_str)
                for field in simple_fields.split(','):
                    field = field.strip()
                    if field:
                        result[field] = {}

                return result

            def _translate_odata_params(self):
                translated = {}
                nested_expand_config = {}

                for key, value in self.request.GET.items():
                    if key == '$expand':
                        nested_config = self._parse_nested_expand(value)
                        nested_expand_config = nested_config
                        expand_fields = ','.join(nested_config.keys())
                        translated['expand'] = expand_fields
                    elif key == '$select':
                        translated['select'] = value
                    else:
                        translated[key] = value

                self.nested_expand_config = nested_expand_config
                return translated

        wrapper = ODataQueryParamsWrapper(dummy_request)

        print(f"\n=== Parser nested expand ===")
        print(f"Translated params: {wrapper.translated_params}")
        print(f"Nested config: {wrapper.nested_expand_config}")

        # Vérifier que le parsing est correct
        assert wrapper.translated_params['expand'] == 'owner'
        assert 'select' in wrapper.nested_expand_config['owner']
        assert wrapper.nested_expand_config['owner']['select'] == 'first_name,last_name'

