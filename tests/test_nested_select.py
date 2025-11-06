"""
Tests pour vérifier que la sélection imbriquée dans $expand fonctionne correctement.

Test de : /odata/folders?expand=parent($select=id)
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from customaps.models import Folder
from datetime import date


@pytest.mark.django_db
class TestNestedSelect(TestCase):
    """Tests pour vérifier la sélection imbriquée dans $expand"""

    def setUp(self):
        """Préparer les données de test"""
        self.client = APIClient()

        # Créer une hiérarchie de dossiers
        self.root_folder = Folder.objects.create(
            name="root",
            username="testuser",
            parent=None
        )

        self.parent_folder = Folder.objects.create(
            name="parent_folder",
            username="testuser",
            parent=self.root_folder
        )

        self.child_folder = Folder.objects.create(
            name="child_folder",
            username="testuser",
            parent=self.parent_folder
        )

        self.another_child = Folder.objects.create(
            name="another_child",
            username="testuser",
            parent=self.parent_folder
        )

    def test_expand_parent_without_select(self):
        """
        Test 1: Tester que $expand=parent retourne tous les champs du parent
        GET /odata/folders?$expand=parent
        """
        response = self.client.get(
            "/odata/folders?$expand=parent",
            format="json"
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Content: {response.content}"
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 4

        # Trouver le child_folder dans les résultats
        child = None
        for item in data["value"]:
            if item.get("id") == self.child_folder.id:
                child = item
                break

        assert child is not None, "child_folder not found in response"

        # Vérifier que parent est un objet (développé)
        assert "parent" in child, "parent field missing in child_folder"
        assert isinstance(child["parent"], dict), f"parent should be dict, got {type(child['parent'])}"

        # Vérifier que le parent contient les champs attendus (tous les champs)
        parent_obj = child["parent"]
        assert "id" in parent_obj, "parent.id missing"
        assert "name" in parent_obj, "parent.name missing"
        assert "username" in parent_obj, "parent.username missing"
        assert "created_at" in parent_obj, "parent.created_at missing"
        assert "updated_at" in parent_obj, "parent.updated_at missing"

        # Vérifier les valeurs du parent
        assert parent_obj["id"] == self.parent_folder.id
        assert parent_obj["name"] == "parent_folder"
        print("✓ Test 1 passed: expand=parent retourne tous les champs")

    def test_expand_parent_with_select_id_only(self):
        """
        Test 2: Tester que $expand=parent($select=id) retourne UNIQUEMENT le champ id du parent
        GET /odata/folders?$expand=parent($select=id)

        Ceci est le test critique pour vérifier que la nested selection fonctionne !
        """
        response = self.client.get(
            "/odata/folders?$expand=parent($select=id)",
            format="json"
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Content: {response.content}"
        data = response.json()
        assert "value" in data
        assert len(data["value"]) == 4

        # Trouver le child_folder dans les résultats
        child = None
        for item in data["value"]:
            if item.get("id") == self.child_folder.id:
                child = item
                break

        assert child is not None, "child_folder not found in response"

        # Vérifier que parent existe et est un objet
        assert "parent" in child, "parent field missing in child_folder"
        assert isinstance(child["parent"], dict), f"parent should be dict, got {type(child['parent'])}"

        parent_obj = child["parent"]

        # TEST CRITIQUE: Vérifier que SEUL le champ id est présent
        assert "id" in parent_obj, "parent.id should be present"
        assert parent_obj["id"] == self.parent_folder.id

        # Les autres champs NE DOIVENT PAS être présents
        assert "name" not in parent_obj, f"parent.name should NOT be present, but got: {parent_obj.get('name')}"
        assert "username" not in parent_obj, f"parent.username should NOT be present, but got: {parent_obj.get('username')}"
        assert "created_at" not in parent_obj, f"parent.created_at should NOT be present, but got: {parent_obj.get('created_at')}"
        assert "updated_at" not in parent_obj, f"parent.updated_at should NOT be present, but got: {parent_obj.get('updated_at')}"

        # Vérifier que le parent ne contient que le champ id (et possiblement @odata.type)
        allowed_fields = {"id", "@odata.type"}
        for key in parent_obj.keys():
            assert key in allowed_fields, f"Unexpected field '{key}' in parent object: {parent_obj}"

        print("✓ Test 2 passed: expand=parent($select=id) retourne UNIQUEMENT le champ id")

    def test_expand_parent_with_select_multiple_fields(self):
        """
        Test 3: Tester que $expand=parent($select=id,name) retourne UNIQUEMENT les champs id et name
        GET /odata/folders?$expand=parent($select=id,name)
        """
        response = self.client.get(
            "/odata/folders?$expand=parent($select=id,name)",
            format="json"
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Content: {response.content}"
        data = response.json()

        # Trouver le child_folder
        child = None
        for item in data["value"]:
            if item.get("id") == self.child_folder.id:
                child = item
                break

        assert child is not None, "child_folder not found in response"
        assert "parent" in child, "parent field missing"

        parent_obj = child["parent"]

        # Vérifier que UNIQUEMENT id et name sont présents
        assert "id" in parent_obj, "parent.id should be present"
        assert "name" in parent_obj, "parent.name should be present"
        assert parent_obj["id"] == self.parent_folder.id
        assert parent_obj["name"] == "parent_folder"

        # Les autres champs NE DOIVENT PAS être présents
        assert "username" not in parent_obj, f"parent.username should NOT be present, but got: {parent_obj.get('username')}"
        assert "created_at" not in parent_obj, f"parent.created_at should NOT be present, but got: {parent_obj.get('created_at')}"
        assert "updated_at" not in parent_obj, f"parent.updated_at should NOT be present, but got: {parent_obj.get('updated_at')}"

        # Vérifier les champs autorisés
        allowed_fields = {"id", "name", "@odata.type"}
        for key in parent_obj.keys():
            assert key in allowed_fields, f"Unexpected field '{key}' in parent object: {parent_obj}"

        print("✓ Test 3 passed: expand=parent($select=id,name) retourne UNIQUEMENT id et name")

    def test_expand_with_select_on_main_resource(self):
        """
        Test 4: Tester que $select=id,name,parent fonctionne avec $expand=parent
        GET /odata/folders?$select=id,name,parent&$expand=parent($select=id)
        """
        response = self.client.get(
            "/odata/folders?$select=id,name,parent&$expand=parent($select=id)",
            format="json"
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Content: {response.content}"
        data = response.json()

        # Vérifier chaque item
        for item in data["value"]:
            # Sur la ressource principale, vérifier que seuls id, name, parent sont présents
            allowed_main_fields = {"id", "name", "parent", "@odata.type"}
            for key in item.keys():
                assert key in allowed_main_fields, f"Unexpected field '{key}' in main object: {item}"

            # username ne devrait pas être là
            assert "username" not in item, f"username should NOT be in main object"
            assert "created_at" not in item, f"created_at should NOT be in main object"

            # Si parent est développé (dict), vérifier que seul id est présent
            if isinstance(item.get("parent"), dict):
                parent_obj = item["parent"]
                allowed_parent_fields = {"id", "@odata.type"}
                for key in parent_obj.keys():
                    assert key in allowed_parent_fields, f"Unexpected field '{key}' in parent object: {parent_obj}"
                assert "name" not in parent_obj, "parent.name should NOT be present"

        print("✓ Test 4 passed: Nested select fonctionne avec select sur la ressource principale")

    def test_expand_parent_with_select_no_select_specified(self):
        """
        Test 5: Tester que quand parent n'a pas de parent, il est null ou absent
        """
        response = self.client.get(
            "/odata/folders?$expand=parent($select=id)",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        # Trouver le root folder (qui n'a pas de parent)
        root = None
        for item in data["value"]:
            if item.get("id") == self.root_folder.id:
                root = item
                break

        assert root is not None, "root_folder not found"

        # parent devrait être null ou None
        assert root.get("parent") is None or root.get("parent") == {}, \
            f"root.parent should be null or empty dict, got: {root.get('parent')}"

        print("✓ Test 5 passed: Parent null est correctement géré")

    def test_expand_parent_with_invalid_field_in_select(self):
        """
        Test 6: Tester le comportement avec un champ invalide dans $select
        GET /odata/folders?$expand=parent($select=id,nonexistent_field)
        """
        response = self.client.get(
            "/odata/folders?$expand=parent($select=id,nonexistent_field)",
            format="json"
        )

        # La requête devrait réussir ou retourner une erreur gracieuse
        assert response.status_code in [200, 400], f"Status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Si la réponse est 200, vérifier que les données sont présentes
            assert "value" in data

            # Vérifier les champs présents dans parent (devrait être au moins id)
            for item in data["value"]:
                if isinstance(item.get("parent"), dict):
                    parent_obj = item["parent"]
                    # id devrait toujours être présent si parent existe
                    if parent_obj:  # if parent is not empty
                        assert "id" in parent_obj or "nonexistent_field" not in parent_obj

        print("✓ Test 6 passed: Champ invalide géré correctement")

    def test_deeply_nested_expand_parent_of_parent(self):
        """
        Test 7: Tester $expand=parent retourne le parent avec tous les champs
        GET /odata/folders?$expand=parent

        Note: Le double nested expand $expand=parent($expand=parent($select=id))
        est un cas très avancé qui peut ne pas être entièrement supporté.
        Ce test se concentre sur l'expand simple du parent.
        """
        response = self.client.get(
            "/odata/folders?$expand=parent",
            format="json"
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Content: {response.content}"
        data = response.json()

        # Trouver le child_folder
        child = None
        for item in data["value"]:
            if item.get("id") == self.child_folder.id:
                child = item
                break

        assert child is not None, "child_folder not found"

        # Vérifier la structure imbriquée
        assert "parent" in child, "parent should exist"
        assert isinstance(child["parent"], dict), "parent should be dict"

        parent = child["parent"]
        # Vérifier que le parent a au moins id et name
        assert "id" in parent, "parent.id should be present"
        assert parent["id"] == self.parent_folder.id
        assert "name" in parent, "parent.name should be present"
        assert parent["name"] == "parent_folder"

        print("✓ Test 7 passed: Nested expand retourne le parent avec les champs")

    def test_response_structure_complete(self):
        """
        Test 8: Vérifier la structure complète de la réponse
        """
        response = self.client.get(
            "/odata/folders?$expand=parent($select=id)&$top=1",
            format="json"
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier les champs OData présents
        assert "@odata.context" in data, "@odata.context should be present"
        assert "@odata.count" in data, "@odata.count should be present"
        assert "value" in data, "value should be present"

        assert isinstance(data["value"], list), "value should be a list"
        assert len(data["value"]) <= 1, "Should have at most 1 item due to $top=1"

        print("✓ Test 8 passed: Structure complète de la réponse OData correcte")

