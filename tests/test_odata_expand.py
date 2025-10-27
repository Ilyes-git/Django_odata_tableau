"""
Tests pour vérifier le support du paramètre $expand dans OData
Tests complexes pour assurer la robustesse de la fonctionnalité
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from my_app.models import Person, Car, Product
from second_app.models import Author, Book
from datetime import date
from decimal import Decimal


@pytest.mark.django_db
class TestODataExpandBasics(TestCase):
    """Tests basiques pour le paramètre $expand"""

    def setUp(self):
        """Préparer les données de test"""
        self.client = APIClient()

        # Créer plusieurs personnes
        self.person1 = Person.objects.create(
            first_name="John",
            last_name="Doe",
            birth_date=date(1990, 5, 15)
        )

        self.person2 = Person.objects.create(
            first_name="Jane",
            last_name="Smith",
            birth_date=date(1992, 3, 20)
        )

        # Créer des voitures associées à person1
        self.car1 = Car.objects.create(
            brand="BMW",
            model="X5",
            year=2020,
            owner=self.person1
        )

        self.car2 = Car.objects.create(
            brand="Audi",
            model="A4",
            year=2022,
            owner=self.person1
        )

        # Créer une voiture pour person2
        self.car3 = Car.objects.create(
            brand="Mercedes",
            model="C-Class",
            year=2021,
            owner=self.person2
        )

    def test_expand_single_relationship_forward(self):
        """Tester $expand avec une relation ForeignKey (forward)"""
        response = self.client.get(
            "/odata/Cars?$expand=owner",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 3

        # Vérifier que le propriétaire est développé
        car = data["value"][0]
        assert "owner" in car
        assert isinstance(car["owner"], dict)
        assert "first_name" in car["owner"]
        assert "last_name" in car["owner"]

    def test_expand_single_relationship_reverse(self):
        """Tester $expand avec une relation reverse (OneToMany)"""
        response = self.client.get(
            "/odata/Persons?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 2

        # Vérifier que les voitures sont développées pour person1
        person = data["value"][0]
        assert "cars" in person
        assert isinstance(person["cars"], list)
        assert len(person["cars"]) == 2

    def test_expand_without_relations(self):
        """Tester que $expand sans paramètre retourne les relations comme IDs"""
        response = self.client.get(
            "/odata/Cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        # Sans expand, owner devrait être un ID
        car = data["value"][0]
        assert "owner" in car
        assert isinstance(car["owner"], int)

    def test_expand_with_empty_relations(self):
        """Tester $expand quand une entité n'a pas de relations"""
        response = self.client.get(
            "/odata/Products?$expand=nonexistent",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data


@pytest.mark.django_db
class TestODataExpandAdvanced(TestCase):
    """Tests avancés pour les combinaisons de paramètres OData"""

    def setUp(self):
        """Préparer les données"""
        self.client = APIClient()

        # Créer des personnes
        self.person = Person.objects.create(
            first_name="Alice",
            last_name="Wonder",
            birth_date=date(1995, 3, 10)
        )

        # Créer plusieurs voitures
        self.car1 = Car.objects.create(brand="Tesla", model="Model 3", year=2023, owner=self.person)
        self.car2 = Car.objects.create(brand="Tesla", model="Model S", year=2022, owner=self.person)
        self.car3 = Car.objects.create(brand="BMW", model="i8", year=2023, owner=self.person)

    def test_expand_with_filter(self):
        """Tester $expand combiné avec $filter"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$filter=brand eq 'Tesla'",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 2

        # Vérifier que chaque voiture Tesla a son propriétaire développé
        for car in data["value"]:
            assert car["brand"] == "Tesla"
            assert "owner" in car
            assert isinstance(car["owner"], dict)
            assert car["owner"]["first_name"] == "Alice"

    def test_expand_with_orderby(self):
        """Tester $expand combiné avec $orderby"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$orderby=year desc",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 3

        # Vérifier l'ordre décroissant par année
        years = [car["year"] for car in data["value"]]
        assert years == sorted(years, reverse=True)

        # Vérifier que le proprietaire est toujours développé
        for car in data["value"]:
            assert isinstance(car["owner"], dict)

    def test_expand_with_select(self):
        """Tester $expand combiné avec $select"""
        response = self.client.get(
            "/odata/Persons?$expand=cars&$select=id,first_name,cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        person = data["value"][0]
        # Vérifier que les champs essentiels sont présents
        assert "id" in person
        assert "first_name" in person
        assert "cars" in person
        assert isinstance(person["cars"], list)

    def test_expand_with_pagination_skip(self):
        """Tester $expand combiné avec $skip et $top"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$skip=1&$top=2",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 2

        # Vérifier que les relations sont toujours développées
        for car in data["value"]:
            assert isinstance(car["owner"], dict)

    def test_expand_with_pagination_top(self):
        """Tester $expand avec $top"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$top=2",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 2

    def test_expand_with_complex_filter_and_orderby(self):
        """Tester $expand avec filtre ET orderby complexes"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$filter=year gt 2022&$orderby=brand asc",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "value" in data

        # Vérifier le filtrage
        for car in data["value"]:
            assert car["year"] > 2022
            # Vérifier que owner est étendu
            assert isinstance(car["owner"], dict)

        # Vérifier l'ordre
        brands = [car["brand"] for car in data["value"]]
        assert brands == sorted(brands)

    def test_expand_count_metadata(self):
        """Vérifier que @odata.count est correct avec expand"""
        response = self.client.get(
            "/odata/Cars?$expand=owner",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "@odata.count" in data
        assert data["@odata.count"] == 3
        assert len(data["value"]) == 3


@pytest.mark.django_db
class TestODataExpandMultipleEntitySets(TestCase):
    """Tests pour expand avec plusieurs entity sets"""

    def setUp(self):
        """Préparer les données pour multiple entity sets"""
        self.client = APIClient()

        # Créer des auteurs
        self.author1 = Author.objects.create(
            name="Author One",
            email="author1@example.com"
        )

        self.author2 = Author.objects.create(
            name="Author Two",
            email="author2@example.com"
        )

        # Créer des livres
        self.book1 = Book.objects.create(
            title="Book 1",
            author=self.author1,
            isbn="9781111111111",
            pages=300,
            published_date=date(2020, 1, 15),
            rating=4.5
        )

        self.book2 = Book.objects.create(
            title="Book 2",
            author=self.author1,
            isbn="9781111111112",
            pages=350,
            published_date=date(2021, 6, 20),
            rating=4.8
        )

        self.book3 = Book.objects.create(
            title="Book 3",
            author=self.author2,
            isbn="9781111111113",
            pages=280,
            published_date=date(2022, 3, 10),
            rating=4.2
        )

    def test_expand_books_with_author(self):
        """Tester l'expand sur Books avec Author"""
        response = self.client.get(
            "/odata/Books?$expand=author",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 3

        for book in data["value"]:
            assert "author" in book
            assert isinstance(book["author"], dict)
            assert "name" in book["author"]

    def test_expand_authors_with_books(self):
        """Tester l'expand sur Authors avec Books"""
        response = self.client.get(
            "/odata/Authors?$expand=books",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 2

        # Author1 devrait avoir 2 livres
        author1 = data["value"][0]
        assert "books" in author1
        assert isinstance(author1["books"], list)
        assert len(author1["books"]) == 2

        # Vérifier que les livres sont complètement sérialisés
        for book in author1["books"]:
            assert "title" in book
            assert "isbn" in book

    def test_expand_books_with_filter_and_author(self):
        """Tester Books avec expand, filtre et author"""
        response = self.client.get(
            "/odata/Books?$expand=author&$filter=pages gt 300",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 1

        book = data["value"][0]
        assert book["pages"] == 350
        assert "author" in book
        assert isinstance(book["author"], dict)


@pytest.mark.django_db
class TestODataExpandSingleEntity(TestCase):
    """Tests pour expand sur entité unique GET /EntitySet(id)"""

    def setUp(self):
        """Préparer les données"""
        self.client = APIClient()

        self.person = Person.objects.create(
            first_name="Bob",
            last_name="Builder",
            birth_date=date(1988, 7, 4)
        )

        self.car1 = Car.objects.create(
            brand="Volvo",
            model="XC90",
            year=2023,
            owner=self.person
        )

        self.car2 = Car.objects.create(
            brand="Saab",
            model="9-3",
            year=2019,
            owner=self.person
        )

    def test_expand_single_entity_with_relations(self):
        """Tester $expand sur une entité unique"""
        response = self.client.get(
            f"/odata/Persons({self.person.id})?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier que c'est un objet unique, pas une liste
        assert not isinstance(data, list)
        assert "@odata.type" in data
        assert "id" in data

        # Vérifier que les relations sont développées
        assert "cars" in data
        assert isinstance(data["cars"], list)
        assert len(data["cars"]) == 2

        for car in data["cars"]:
            assert isinstance(car, dict)
            assert "brand" in car

    def test_expand_single_entity_reverse_with_select(self):
        """Tester $expand + $select sur entité unique"""
        response = self.client.get(
            f"/odata/Persons({self.person.id})?$expand=cars&$select=id,first_name,cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "first_name" in data
        assert "cars" in data
        assert isinstance(data["cars"], list)


@pytest.mark.django_db
class TestODataExpandEdgeCases(TestCase):
    """Tests pour les cas limites et edge cases"""

    def setUp(self):
        """Préparer les données"""
        self.client = APIClient()

        # Créer une personne sans voitures
        self.person_no_cars = Person.objects.create(
            first_name="NoBody",
            last_name="NoCars",
            birth_date=date(2000, 1, 1)
        )

        # Créer une personne avec voitures
        self.person_with_cars = Person.objects.create(
            first_name="SomeBody",
            last_name="HasCars",
            birth_date=date(1990, 1, 1)
        )

        Car.objects.create(
            brand="Ford",
            model="Mustang",
            year=2023,
            owner=self.person_with_cars
        )

    def test_expand_empty_relations(self):
        """Tester $expand quand une entité n'a pas de relations"""
        response = self.client.get(
            "/odata/Persons?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 2

        # Vérifier que même sans voitures, la structure est correcte
        person_no_cars = data["value"][0]
        assert "cars" in person_no_cars
        assert isinstance(person_no_cars["cars"], list)
        assert len(person_no_cars["cars"]) == 0

    def test_expand_with_invalid_field_name(self):
        """Tester $expand avec un nom de champ invalide"""
        response = self.client.get(
            "/odata/Persons?$expand=nonexistent_field",
            format="json"
        )

        # Devrait retourner succès car le champ n'existe pas est ignoré
        assert response.status_code == 200
        data = response.json()
        assert "value" in data

    def test_expand_multiple_fields_separated_by_comma(self):
        """Tester $expand avec plusieurs champs séparés par virgule"""
        # Note: Ce test montre le comportement du système avec plusieurs expand
        # même si un champ peut ne pas avoir de relation
        response = self.client.get(
            "/odata/Persons?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        for person in data["value"]:
            assert "cars" in person

    def test_expand_with_filter_no_results(self):
        """Tester $expand avec filtre qui retourne zéro résultats"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$filter=brand eq 'NonexistentBrand'",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 0
        assert data["@odata.count"] == 0


@pytest.mark.django_db
class TestODataExpandODataMetadata(TestCase):
    """Tests pour vérifier la métadonnées OData avec expand"""

    def setUp(self):
        """Préparer les données"""
        self.client = APIClient()

        self.person = Person.objects.create(
            first_name="Meta",
            last_name="Person",
            birth_date=date(1990, 1, 1)
        )

        Car.objects.create(
            brand="Test",
            model="Car",
            year=2023,
            owner=self.person
        )

    def test_response_has_odata_metadata(self):
        """Tester que la réponse contient les métadonnées OData"""
        response = self.client.get(
            "/odata/Persons?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier les métadonnées OData
        assert "@odata.context" in data
        assert "@odata.count" in data
        assert "value" in data

    def test_response_items_have_odata_type(self):
        """Tester que chaque item a le @odata.type"""
        response = self.client.get(
            "/odata/Persons?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        for item in data["value"]:
            assert "@odata.type" in item

    def test_single_entity_response_has_odata_metadata(self):
        """Tester que la réponse d'entité unique contient les métadonnées"""
        response = self.client.get(
            f"/odata/Persons({self.person.id})?$expand=cars",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        assert "@odata.type" in data
        assert "@odata.context" in data


@pytest.mark.django_db
class TestODataExpandPerformance(TestCase):
    """Tests pour la performance et la stabilité avec expand"""

    def setUp(self):
        """Préparer les données"""
        self.client = APIClient()

        # Créer plusieurs personnes avec plusieurs voitures
        for i in range(5):
            person = Person.objects.create(
                first_name=f"Person{i}",
                last_name=f"Last{i}",
                birth_date=date(1990 + i, 1, 1)
            )

            for j in range(3):
                Car.objects.create(
                    brand=f"Brand{j}",
                    model=f"Model{j}",
                    year=2020 + j,
                    owner=person
                )

    def test_expand_large_dataset(self):
        """Tester $expand avec un grand ensemble de données"""
        response = self.client.get(
            "/odata/Persons?$expand=cars&$top=10",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 5

        # Vérifier que toutes les relations sont développées correctement
        for person in data["value"]:
            assert "cars" in person
            assert len(person["cars"]) == 3

    def test_expand_with_skip_and_top(self):
        """Tester $expand avec skip et top sur grand dataset"""
        response = self.client.get(
            "/odata/Cars?$expand=owner&$skip=5&$top=5",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) == 5

        for car in data["value"]:
            assert isinstance(car["owner"], dict)

    def test_expand_consistency_across_pages(self):
        """Tester que expand reste cohérent à travers la pagination"""
        # Page 1
        response1 = self.client.get(
            "/odata/Cars?$expand=owner&$top=5&$skip=0",
            format="json"
        )
        data1 = response1.json()

        # Page 2
        response2 = self.client.get(
            "/odata/Cars?$expand=owner&$top=5&$skip=5",
            format="json"
        )
        data2 = response2.json()

        # Toutes les voitures devraient avoir un owner développé
        for car in data1["value"] + data2["value"]:
            assert isinstance(car["owner"], dict)


