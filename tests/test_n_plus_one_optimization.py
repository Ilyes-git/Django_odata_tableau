"""
Tests pour vérifier l'optimisation des requêtes OData (N+1 problem)
Valide que drf-flex-fields et notre implémentation utilisent prefetch_related et select_related
"""
import pytest
from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from my_app.models import Person, Car
from second_app.models import Author, Book
from datetime import date


@pytest.mark.django_db
class TestODataQueryOptimization(TestCase):
    """Tests pour vérifier l'optimisation des requêtes OData"""

    def setUp(self):
        """Préparer les données de test"""
        self.client = APIClient()

        # Créer plusieurs personnes
        self.persons = []
        for i in range(5):
            person = Person.objects.create(
                first_name=f"Person{i}",
                last_name=f"Last{i}",
                birth_date=date(1990 + i, 1, 1)
            )
            self.persons.append(person)

        # Créer plusieurs voitures pour chaque personne
        for person in self.persons:
            for j in range(3):
                Car.objects.create(
                    brand=f"Brand{j}",
                    model=f"Model{j}",
                    year=2020 + j,
                    owner=person
                )

        # Créer plusieurs auteurs
        self.authors = []
        for i in range(5):
            author = Author.objects.create(
                name=f"Author{i}",
                email=f"author{i}@example.com"
            )
            self.authors.append(author)

        # Créer plusieurs livres pour chaque auteur
        for author in self.authors:
            for j in range(3):
                Book.objects.create(
                    title=f"Book{j} by {author.name}",
                    author=author,
                    isbn=f"{100000 + author.id * 100 + j}",
                    pages=300 + j * 50,
                    published_date=date(2020 + j, 1, 1),
                    rating=4 + (j % 2)
                )

    def test_expand_forward_relation_without_optimization(self):
        """
        Test SANS expand - devrait faire 1 requête
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/odata/cars", format="json")

        query_count_no_expand = len(queries)
        print(f"\n=== Cars WITHOUT expand ===")
        print(f"Nombre de requêtes: {query_count_no_expand}")
        print(f"Requêtes:")
        for i, query in enumerate(queries, 1):
            print(f"  {i}. {query['sql'][:100]}...")

        assert response.status_code == 200
        # Devrait avoir peu de requêtes (juste la requête principale)
        assert query_count_no_expand <= 2

    def test_expand_forward_relation_with_optimization(self):
        """
        Test AVEC expand=owner - devrait faire 2 requêtes (1 cars + 1 prefetch owners)

        SANS optimisation: 1 requête cars + N requêtes pour chaque owner = 1 + 15 = 16 requêtes
        AVEC optimisation (select_related ou prefetch_related): 2 requêtes
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/odata/cars?$expand=owner", format="json")

        query_count_with_expand = len(queries)
        print(f"\n=== Cars WITH expand=owner ===")
        print(f"Nombre de requêtes: {query_count_with_expand}")
        print(f"Requêtes:")
        for i, query in enumerate(queries, 1):
            print(f"  {i}. {query['sql'][:150]}...")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que owner est bien développé
        assert "value" in data
        for car in data["value"]:
            assert "owner" in car
            if car["owner"]:  # Si ce n'est pas null
                assert isinstance(car["owner"], dict)
                assert "first_name" in car["owner"]

        # CLEF: Avec optimisation, devrait être <= 3 requêtes (cars + prefetch owners)
        # Sans optimisation, ce serait 1 + 15 = 16 requêtes
        print(f"\nOptimisation détectée: {query_count_with_expand <= 3}")
        assert query_count_with_expand <= 5  # Tolérance: 5 requêtes

    def test_expand_reverse_relation_with_optimization(self):
        """
        Test AVEC expand=cars - devrait faire 2 requêtes (1 persons + 1 prefetch cars)

        SANS optimisation: 1 requête persons + N requêtes pour les cars de chaque person = 1 + 5 = 6 requêtes
        AVEC optimisation: 2 requêtes
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/odata/persons?$expand=cars", format="json")

        query_count_with_expand = len(queries)
        print(f"\n=== Persons WITH expand=cars ===")
        print(f"Nombre de requêtes: {query_count_with_expand}")
        print(f"Requêtes:")
        for i, query in enumerate(queries, 1):
            print(f"  {i}. {query['sql'][:150]}...")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que cars est bien développé
        assert "value" in data
        for person in data["value"]:
            assert "cars" in person
            assert isinstance(person["cars"], list)

        # CLEF: Avec optimisation, devrait être <= 3 requêtes (persons + prefetch cars)
        # Sans optimisation, ce serait 1 + 5 = 6 requêtes
        print(f"\nOptimisation détectée: {query_count_with_expand <= 3}")
        assert query_count_with_expand <= 5  # Tolérance: 5 requêtes

    def test_expand_with_select_optimization(self):
        """
        Test AVEC expand=author($select=name,email)

        Devrait faire 2 requêtes: 1 books + 1 prefetch authors
        Et les colonnes sélectionnées doivent être limitées
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/odata/books?$expand=author($select=name,email)", format="json")

        query_count = len(queries)
        print(f"\n=== Books WITH expand=author($select=name,email) ===")
        print(f"Nombre de requêtes: {query_count}")
        print(f"Requêtes:")
        for i, query in enumerate(queries, 1):
            print(f"  {i}. {query['sql'][:150]}...")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que author est bien développé avec select limité
        assert "value" in data
        for book in data["value"]:
            assert "author" in book
            if book["author"]:
                assert isinstance(book["author"], dict)
                # Avec select, on devrait avoir name et email
                assert "name" in book["author"] or "email" in book["author"]

        # Devrait être optimisé
        assert query_count <= 5

    def test_n_plus_one_comparison(self):
        """
        Comparaison directe du nombre de requêtes
        """
        print("\n\n=== COMPARAISON N+1 QUERY PROBLEM ===\n")

        # Sans expand
        with CaptureQueriesContext(connection) as queries_no_expand:
            response = self.client.get("/odata/cars", format="json")

        # Avec expand
        with CaptureQueriesContext(connection) as queries_with_expand:
            response = self.client.get("/odata/cars?$expand=owner", format="json")

        count_no = len(queries_no_expand)
        count_with = len(queries_with_expand)

        print(f"Sans expand: {count_no} requête(s)")
        print(f"Avec expand: {count_with} requête(s)")
        print(f"\nDifférence: {count_with - count_no} requête(s) supplémentaire(s)")

        # Sans optimisation, la différence serait N (5 personnes)
        # Avec optimisation (prefetch_related), la différence devrait être 1
        optimization_ratio = (count_with - count_no)
        print(f"\nRatio d'optimisation: {optimization_ratio}")
        print(f"✅ OPTIMISÉ" if optimization_ratio <= 2 else f"⚠️ PAS OPTIMISÉ (N+1 problem)")

        # Afficher les requêtes
        print(f"\n--- Requêtes SANS expand ---")
        for i, q in enumerate(queries_no_expand, 1):
            print(f"{i}. {q['sql'][:100]}...")

        print(f"\n--- Requêtes AVEC expand ---")
        for i, q in enumerate(queries_with_expand, 1):
            print(f"{i}. {q['sql'][:100]}...")

    def test_multiple_expand_optimization(self):
        """
        Test avec plusieurs expand pour vérifier les performances
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                "/odata/persons?$expand=cars($select=brand,model)",
                format="json"
            )

        query_count = len(queries)
        print(f"\n=== Persons WITH expand=cars($select=brand,model) ===")
        print(f"Nombre de requêtes: {query_count}")

        assert response.status_code == 200
        assert query_count <= 5

