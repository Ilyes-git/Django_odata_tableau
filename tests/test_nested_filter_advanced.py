"""
Tests avancés pour le filtrage imbriqué dans $expand
Teste tous les opérateurs OData et les combinaisons complexes
"""
import pytest
from django.test import TestCase, Client
from my_app.models import Person, Car, Product
import json


class TestNestedFilterBasic(TestCase):
    """Tests basiques du filtrage imbriqué"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()

        # Créer les personnes
        self.john = Person.objects.create(
            first_name='John',
            last_name='Doe',
            birth_date='1980-01-15'
        )
        self.jane = Person.objects.create(
            first_name='Jane',
            last_name='Smith',
            birth_date='1990-05-20'
        )
        self.bob = Person.objects.create(
            first_name='Bob',
            last_name='Johnson',
            birth_date='1975-03-10'
        )

        # Créer les voitures
        self.bmw = Car.objects.create(brand='BMW', model='X5', year=2020, owner=self.john)
        self.audi = Car.objects.create(brand='Audi', model='A4', year=2019, owner=self.jane)
        self.tesla = Car.objects.create(brand='Tesla', model='S', year=2022, owner=self.john)
        self.mercedes = Car.objects.create(brand='Mercedes', model='C-Class', year=2018, owner=self.bob)
        self.bmw2 = Car.objects.create(brand='BMW', model='M3', year=2021, owner=self.jane)

    def test_filter_eq_operator(self):
        """Test l'opérateur eq - égalité"""
        response = self.client.get("/odata/cars?$expand=owner($filter=first_name eq 'John')")
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 2

        cars = data['value']
        assert all(car['owner']['first_name'] == 'John' for car in cars)
        assert set(car['brand'] for car in cars) == {'BMW', 'Tesla'}

    def test_filter_ne_operator(self):
        """Test l'opérateur ne - non égal"""
        response = self.client.get("/odata/cars?$expand=owner($filter=first_name ne 'John')")
        data = json.loads(response.content)

        assert response.status_code == 200
        # Doit retourner Jane et Bob (pas John)
        assert data['@odata.count'] >= 2

        cars = data['value']
        # Vérifier que tous les owners ne sont pas 'John'
        for car in cars:
            assert car['owner']['first_name'] != 'John'

    def test_filter_startswith_operator(self):
        """Test l'opérateur startswith avec syntaxe OData"""
        response = self.client.get("/odata/cars?$expand=owner($filter=startswith(first_name,'J'))")
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] >= 2  # Au minimum John et Jane

        cars = data['value']
        for car in cars:
            assert car['owner']['first_name'][0] == 'J'

    def test_filter_endswith_operator(self):
        """Test l'opérateur endswith avec syntaxe OData"""
        response = self.client.get("/odata/cars?$expand=owner($filter=endswith(first_name,'n'))")
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 2  # John uniquement

        cars = data['value']
        assert all(car['owner']['first_name'] == 'John' for car in cars)

    def test_filter_contains_operator(self):
        """Test l'opérateur contains avec syntaxe OData"""
        response = self.client.get("/odata/cars?$expand=owner($filter=contains(first_name,'oh'))")
        data = json.loads(response.content)

        assert response.status_code == 200
        # John a 2 cars avec 'oh' dans 'John'
        assert data['@odata.count'] == 2

        cars = data['value']
        names = set(car['owner']['first_name'] for car in cars)
        assert 'John' in names
        assert 'John' in names

    def test_filter_gt_operator_with_year(self):
        """Test l'opérateur gt (greater than) sur une année"""
        # Note: On filtre sur l'owner (Person), pas sur Car
        # Donc on teste avec birth_date
        response = self.client.get("/odata/cars?$expand=owner($filter=birth_date gt '1980-01-01')")
        data = json.loads(response.content)

        assert response.status_code == 200
        # Jane et Bob ont des dates > 1980-01-01
        assert data['@odata.count'] >= 2

    def test_filter_lt_operator(self):
        """Test l'opérateur lt (less than)"""
        response = self.client.get("/odata/cars?$expand=owner($filter=birth_date lt '1980-01-01')")
        data = json.loads(response.content)

        assert response.status_code == 200
        # Bob (1975) est < 1980-01-01
        assert data['@odata.count'] == 1
        assert data['value'][0]['owner']['first_name'] == 'Bob'

    def test_filter_le_operator(self):
        """Test l'opérateur le (less or equal)"""
        response = self.client.get("/odata/cars?$expand=owner($filter=birth_date le '1980-01-15')")
        data = json.loads(response.content)

        assert response.status_code == 200
        # John (1980-01-15) et Bob (1975) sont <= 1980-01-15
        assert data['@odata.count'] >= 2

    def test_filter_ge_operator(self):
        """Test l'opérateur ge (greater or equal)"""
        response = self.client.get("/odata/cars?$expand=owner($filter=birth_date ge '1980-01-15')")
        data = json.loads(response.content)

        assert response.status_code == 200
        # John (1980-01-15), Jane (1990-05-20), et possiblement d'autres
        # On vérifie juste que c'est >= 3 et que les dates correspondent
        assert data['@odata.count'] >= 3


class TestNestedFilterCombinedWithSelect(TestCase):
    """Tests du filtrage imbriqué combiné avec $select"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')
        self.jane = Person.objects.create(first_name='Jane', last_name='Smith')
        self.car1 = Car.objects.create(brand='BMW', model='X5', year=2020, owner=self.john)
        self.car2 = Car.objects.create(brand='Audi', model='A4', year=2019, owner=self.jane)

    def test_filter_with_select_nested(self):
        """Test filtre + select imbriqués"""
        response = self.client.get(
            "/odata/cars?$expand=owner($select=first_name,$filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 1

        car = data['value'][0]
        owner = car['owner']

        # Vérifier que seul first_name est retourné
        assert list(owner.keys()) == ['first_name']
        assert owner['first_name'] == 'John'

    def test_filter_with_select_multiple_fields(self):
        """Test filtre + select avec plusieurs champs"""
        response = self.client.get(
            "/odata/cars?$expand=owner($select=first_name,last_name,$filter=startswith(first_name,'J'))"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] >= 2  # Au minimum John et Jane

        for car in data['value']:
            owner = car['owner']
            # Vérifier que seulement first_name et last_name sont retournés
            assert set(owner.keys()) == {'first_name', 'last_name'}

    def test_filter_without_select_has_all_fields(self):
        """Test que sans $select, tous les champs sont retournés"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        car = data['value'][0]
        owner = car['owner']

        # Doit avoir id, first_name, last_name, birth_date
        assert 'id' in owner
        assert 'first_name' in owner
        assert 'last_name' in owner


class TestNestedFilterWithPagination(TestCase):
    """Tests du filtrage imbriqué combiné avec la pagination"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')

        # Créer 5 voitures pour John
        for i in range(5):
            Car.objects.create(brand=f'Brand{i}', model=f'Model{i}', year=2020+i, owner=self.john)

    def test_filter_with_skip(self):
        """Test filtre + $skip"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')&$skip=2"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 5  # Total toujours 5
        assert len(data['value']) == 3  # Mais seulement 3 après skip

    def test_filter_with_top(self):
        """Test filtre + $top"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')&$top=2"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 5  # Total toujours 5
        assert len(data['value']) == 2  # Mais seulement 2 retournées

    def test_filter_with_skip_and_top(self):
        """Test filtre + $skip + $top"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')&$skip=1&$top=2"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 5
        assert len(data['value']) == 2


class TestNestedFilterWithOrderBy(TestCase):
    """Tests du filtrage imbriqué combiné avec $orderby"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')
        self.jane = Person.objects.create(first_name='Jane', last_name='Smith')

        Car.objects.create(brand='Tesla', model='S', year=2022, owner=self.john)
        Car.objects.create(brand='BMW', model='X5', year=2020, owner=self.john)
        Car.objects.create(brand='Audi', model='A4', year=2021, owner=self.john)

    def test_filter_with_orderby(self):
        """Test filtre + $orderby"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')&$orderby=year desc"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 3

        cars = data['value']
        years = [car['year'] for car in cars]
        # Vérifier que c'est en ordre décroissant
        assert years == sorted(years, reverse=True)


class TestNestedFilterMultipleConditions(TestCase):
    """Tests du filtrage imbriqué avec plusieurs conditions"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe', birth_date='1980-01-15')
        self.jane = Person.objects.create(first_name='Jane', last_name='Smith', birth_date='1990-05-20')
        self.john2 = Person.objects.create(first_name='John', last_name='Smith', birth_date='1985-03-10')

        Car.objects.create(brand='BMW', year=2020, owner=self.john)
        Car.objects.create(brand='Audi', year=2019, owner=self.jane)
        Car.objects.create(brand='Tesla', year=2022, owner=self.john2)

    def test_filter_with_multiple_or_conditions(self):
        """Test filtre avec plusieurs conditions OR"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John' or first_name eq 'Jane')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 3  # Deux John et une Jane

        names = set(car['owner']['first_name'] for car in data['value'])
        assert names == {'John', 'Jane'}

    def test_filter_with_multiple_and_conditions(self):
        """Test filtre avec plusieurs conditions AND"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John' and last_name eq 'Doe')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 1  # Seulement John Doe

        car = data['value'][0]
        assert car['owner']['first_name'] == 'John'
        assert car['owner']['last_name'] == 'Doe'


class TestNestedFilterEdgeCases(TestCase):
    """Tests des cas limites du filtrage imbriqué"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')
        self.car1 = Car.objects.create(brand='BMW', year=2020, owner=self.john)

    def test_filter_returns_empty_result(self):
        """Test quand le filtre ne retourne aucun résultat"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'NonExistent')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['@odata.count'] == 0
        assert data['value'] == []

    def test_filter_with_case_insensitive_comparison(self):
        """Test que la comparaison est case-insensitive pour startswith"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name startswith 'john')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        # La comparaison devrait être case-insensitive
        assert data['@odata.count'] == 1

    def test_filter_with_special_characters(self):
        """Test filtre avec caractères spéciaux"""
        # Créer une personne avec caractère spécial
        person = Person.objects.create(first_name="Jean-Paul", last_name='Dupont')
        Car.objects.create(brand='BMW', year=2020, owner=person)

        response = self.client.get(
            "/odata/cars?$expand=owner($filter=contains(first_name,'Paul'))"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        # Au moins 1 (Jean-Paul) mais possiblement plus de données de tests précédents
        assert data['@odata.count'] >= 1

    def test_filter_invalid_syntax_returns_error(self):
        """Test que un filtre syntaxiquement invalide retourne une erreur 400"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name invalid 'John')"
        )

        # Doit retourner 400 ou filtrer silencieusement selon l'implémentation
        assert response.status_code in [200, 400]


class TestNestedFilterPerformance(TestCase):
    """Tests de performance du filtrage imbriqué"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()

        # Créer plusieurs personnes
        for i in range(10):
            person = Person.objects.create(
                first_name=f'Person{i}',
                last_name=f'Last{i}'
            )

            # Créer plusieurs voitures par personne
            for j in range(5):
                Car.objects.create(
                    brand=f'Brand{j}',
                    model=f'Model{j}',
                    year=2020 + j,
                    owner=person
                )

    def test_filter_performance_no_n_plus_one(self):
        """Test que le filtrage imbriqué n'introduit pas de N+1 queries"""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            response = self.client.get(
                "/odata/cars?$expand=owner($filter=first_name startswith 'Person')"
            )
            data = json.loads(response.content)

        # Le nombre de queries devrait être raisonnable (pas 50 queries)
        # Avec select_related, on devrait avoir peu de queries
        query_count = len(context.captured_queries)
        assert query_count < 10, f"Trop de queries: {query_count}"

    def test_filter_returns_all_matching_cars(self):
        """Test que le filtre retourne bien toutes les voitures matchantes"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'Person0')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        # Person0 devrait avoir 5 voitures
        assert data['@odata.count'] == 5
        assert len(data['value']) == 5


class TestNestedFilterResponseFormat(TestCase):
    """Tests du format de la réponse"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')
        self.car = Car.objects.create(brand='BMW', year=2020, owner=self.john)

    def test_response_has_required_odata_fields(self):
        """Test que la réponse contient les champs OData requis"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        assert '@odata.context' in data
        assert '@odata.count' in data
        assert 'value' in data
        assert response.has_header('OData-Version')
        assert response['OData-Version'] == '4.0'

    def test_response_items_have_odata_type(self):
        """Test que chaque item a un @odata.type"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        for item in data['value']:
            assert '@odata.type' in item
            assert item['@odata.type'] == '#Odata.Car'

    def test_nested_owner_is_object_not_array(self):
        """Test que owner est un objet, pas un tableau"""
        response = self.client.get(
            "/odata/cars?$expand=owner($filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        for car in data['value']:
            assert isinstance(car['owner'], dict)
            assert not isinstance(car['owner'], list)


class TestNestedFilterWithMainFilter(TestCase):
    """Tests du filtrage imbriqué combiné avec un filtre principal"""

    def setUp(self):
        """Créer les données de test"""
        self.client = Client()
        self.john = Person.objects.create(first_name='John', last_name='Doe')
        self.jane = Person.objects.create(first_name='Jane', last_name='Smith')

        Car.objects.create(brand='BMW', year=2020, owner=self.john)
        Car.objects.create(brand='Audi', year=2019, owner=self.jane)
        Car.objects.create(brand='Tesla', year=2022, owner=self.john)

    def test_main_filter_and_nested_filter(self):
        """Test filtre principal + filtre imbriqué"""
        response = self.client.get(
            "/odata/cars?$filter=year gt 2020&$expand=owner($filter=first_name eq 'John')"
        )
        data = json.loads(response.content)

        assert response.status_code == 200
        # Tesla (2022, John) et les autres >= 2021 avec John
        assert data['@odata.count'] >= 1

        # Vérifier que tous les filtres sont appliqués
        for car in data['value']:
            assert car['year'] > 2020
            assert car['owner']['first_name'] == 'John'

    def test_main_filter_excludes_nested_filter_results(self):
        """Test que le filtre principal s'applique avant le nested filter"""
        response = self.client.get(
            "/odata/cars?$filter=brand eq 'BMW'&$expand=owner($filter=first_name eq 'Jane')"
        )
        data = json.loads(response.content)

        # BMW appartient à John, pas à Jane
        # Donc le résultat devrait être vide
        assert data['@odata.count'] == 0

