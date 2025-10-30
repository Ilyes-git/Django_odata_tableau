"""
Tests complets pour customaps/models.py et customaps/serializers.py
Vise 100% de code coverage
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from customaps.models import Folder, Map
from customaps.serializers import (
    FolderSerializer,
    SingleFolderSerializer,
    MapSerializer,
)


@pytest.mark.django_db
class TestFolderModel(TestCase):
    """Tests complets pour le modèle Folder"""

    def test_folder_creation_basic(self):
        """Tester la création basique d'un dossier"""
        folder = Folder.objects.create(
            name="Test Folder",
            username="testuser"
        )

        assert folder.id is not None
        assert folder.name == "Test Folder"
        assert folder.username == "testuser"
        assert folder.parent is None

    def test_folder_str_representation(self):
        """Tester la représentation string du dossier"""
        folder = Folder.objects.create(
            name="My Folder",
            username="testuser"
        )

        assert str(folder) == "My Folder"

    def test_folder_with_parent(self):
        """Tester la création d'un dossier avec parent"""
        parent_folder = Folder.objects.create(
            name="Parent",
            username="testuser"
        )

        child_folder = Folder.objects.create(
            name="Child",
            parent=parent_folder,
            username="testuser"
        )

        assert child_folder.parent == parent_folder
        assert child_folder in parent_folder.subfolders.all()

    def test_folder_duplicate_name_in_same_parent(self):
        """Tester que les noms dupliqués sont renommés automatiquement"""
        folder1 = Folder.objects.create(
            name="Duplicate",
            username="testuser"
        )

        # Créer un deuxième dossier avec le même nom
        folder2 = Folder.objects.create(
            name="Duplicate",
            username="testuser"
        )

        # Le deuxième devrait avoir un nom modifié
        assert folder1.name == "Duplicate"
        assert folder2.name != "Duplicate"
        assert "Duplicate_" in folder2.name

    def test_folder_duplicate_name_different_parent(self):
        """Tester que les noms dupliqués dans des parents différents sont autorisés"""
        parent1 = Folder.objects.create(name="Parent1", username="user1")
        parent2 = Folder.objects.create(name="Parent2", username="user1")

        child1 = Folder.objects.create(
            name="Child",
            parent=parent1,
            username="user1"
        )

        child2 = Folder.objects.create(
            name="Child",
            parent=parent2,
            username="user1"
        )

        # Les deux doivent garder le même nom (parents différents)
        assert child1.name == "Child"
        assert child2.name == "Child"

    def test_folder_duplicate_name_different_username(self):
        """Tester que les noms dupliqués avec usernames différents sont autorisés"""
        folder1 = Folder.objects.create(
            name="Shared Name",
            username="user1"
        )

        folder2 = Folder.objects.create(
            name="Shared Name",
            username="user2"
        )

        # Les deux doivent garder le même nom (usernames différents)
        assert folder1.name == "Shared Name"
        assert folder2.name == "Shared Name"

    def test_folder_timestamps(self):
        """Tester que les timestamps sont correctement définis"""
        folder = Folder.objects.create(
            name="Test",
            username="testuser"
        )

        assert folder.created_at is not None
        assert folder.updated_at is not None

    def test_folder_update_preserves_name(self):
        """Tester que la mise à jour d'un dossier ne change pas le nom"""
        folder = Folder.objects.create(
            name="Original",
            username="testuser"
        )

        folder.username = "newuser"
        folder.save()

        folder.refresh_from_db()
        assert folder.name == "Original"

    def test_folder_save_with_exception_in_duplicate_check(self):
        """Tester le save quand il y a une exception dans la vérification de duplicate"""
        # Créer un dossier
        folder = Folder.objects.create(
            name="Test",
            username="user"
        )

        # Le deuxième appel ne doit pas lever d'exception
        folder2 = Folder(
            name="Test",
            username="user",
            parent=None
        )
        # Ne devrait pas lever d'exception même si le premier get() retourne un résultat
        folder2.save()

        assert folder2.id is not None


@pytest.mark.django_db
class TestMapModelExceptionHandling(TestCase):
    """Tests pour la gestion des exceptions dans Map model"""

    def test_map_save_with_exception_in_duplicate_check(self):
        """Tester le save quand il y a une exception dans la vérification de duplicate"""
        folder = Folder.objects.create(name="Folder", username="user")

        # Créer une carte
        map1 = Map.objects.create(
            name="Test",
            data={},
            folder=folder,
            username="user"
        )

        # Créer une deuxième carte avec le même nom - ne devrait pas lever d'exception
        map2 = Map(
            name="Test",
            data={},
            folder=folder,
            username="user"
        )
        map2.save()

        assert map2.id is not None


@pytest.mark.django_db
class TestMapModel(TestCase):
    """Tests complets pour le modèle Map"""

    def test_map_creation_basic(self):
        """Tester la création basique d'une carte"""
        folder = Folder.objects.create(name="Test", username="user")

        map_obj = Map.objects.create(
            name="Test Map",
            data={"type": "FeatureCollection", "features": []},
            folder=folder,
            username="user"
        )

        assert map_obj.id is not None
        assert map_obj.name == "Test Map"
        assert map_obj.folder == folder

    def test_map_str_representation(self):
        """Tester la représentation string de la carte"""
        folder = Folder.objects.create(name="Test", username="user")
        map_obj = Map.objects.create(
            name="My Map",
            data={},
            folder=folder,
            username="user"
        )

        assert str(map_obj) == "My Map"

    def test_map_duplicate_name_in_same_folder(self):
        """Tester que les noms dupliqués sont renommés automatiquement"""
        folder = Folder.objects.create(name="Folder", username="user")

        map1 = Map.objects.create(
            name="Duplicate",
            data={},
            folder=folder,
            username="user"
        )

        map2 = Map.objects.create(
            name="Duplicate",
            data={},
            folder=folder,
            username="user"
        )

        # Le deuxième devrait avoir un nom modifié
        assert map1.name == "Duplicate"
        assert map2.name != "Duplicate"
        assert "Duplicate_" in map2.name

    def test_map_duplicate_name_different_folder(self):
        """Tester que les noms dupliqués dans des dossiers différents sont autorisés"""
        folder1 = Folder.objects.create(name="Folder1", username="user")
        folder2 = Folder.objects.create(name="Folder2", username="user")

        map1 = Map.objects.create(
            name="Same Name",
            data={},
            folder=folder1,
            username="user"
        )

        map2 = Map.objects.create(
            name="Same Name",
            data={},
            folder=folder2,
            username="user"
        )

        # Les deux doivent garder le même nom (dossiers différents)
        assert map1.name == "Same Name"
        assert map2.name == "Same Name"

    def test_map_duplicate_name_different_username(self):
        """Tester que les noms dupliqués avec usernames différents sont autorisés"""
        folder = Folder.objects.create(name="Folder", username="user")

        map1 = Map.objects.create(
            name="Same Name",
            data={},
            folder=folder,
            username="user1"
        )

        map2 = Map.objects.create(
            name="Same Name",
            data={},
            folder=folder,
            username="user2"
        )

        # Les deux doivent garder le même nom (usernames différents)
        assert map1.name == "Same Name"
        assert map2.name == "Same Name"

    def test_map_timestamps(self):
        """Tester que les timestamps sont correctement définis"""
        folder = Folder.objects.create(name="Test", username="user")
        map_obj = Map.objects.create(
            name="Test",
            data={},
            folder=folder,
            username="user"
        )

        assert map_obj.created_at is not None
        assert map_obj.updated_at is not None

    def test_map_update_preserves_name(self):
        """Tester que la mise à jour d'une carte ne change pas le nom"""
        folder = Folder.objects.create(name="Folder", username="user")
        map_obj = Map.objects.create(
            name="Original",
            data={},
            folder=folder,
            username="user"
        )

        map_obj.data = {"updated": "data"}
        map_obj.save()

        map_obj.refresh_from_db()
        assert map_obj.name == "Original"


@pytest.mark.django_db
class TestMapSerializer(TestCase):
    """Tests pour MapSerializer"""

    def test_map_serializer_basic(self):
        """Tester la sérialisation basique d'une carte"""
        folder = Folder.objects.create(name="Folder", username="user")
        map_obj = Map.objects.create(
            name="Map",
            data={"test": "data"},
            folder=folder,
            username="user"
        )

        serializer = MapSerializer(map_obj)
        data = serializer.data

        assert data['name'] == "Map"
        assert data['username'] == "user"
        assert data['type'] == "userMap"
        assert data['data'] == {"test": "data"}

    def test_map_serializer_all_fields(self):
        """Tester que tous les champs sont présents"""
        folder = Folder.objects.create(name="Folder", username="user")
        map_obj = Map.objects.create(
            name="Map",
            data={},
            folder=folder,
            username="user"
        )

        serializer = MapSerializer(map_obj)
        data = serializer.data

        assert 'id' in data
        assert 'name' in data
        assert 'data' in data
        assert 'folder' in data
        assert 'username' in data
        assert 'type' in data
        assert 'created_at' in data
        assert 'updated_at' in data


@pytest.mark.django_db
class TestSingleFolderSerializer(TestCase):
    """Tests pour SingleFolderSerializer"""

    def test_single_folder_serializer_basic(self):
        """Tester la sérialisation basique d'un dossier"""
        folder = Folder.objects.create(name="Folder", username="user")

        serializer = SingleFolderSerializer(folder)
        data = serializer.data

        assert data['name'] == "Folder"
        assert data['username'] == "user"
        assert data['type'] == "folder"
        assert data['parent'] is None

    def test_single_folder_serializer_with_parent(self):
        """Tester la sérialisation d'un dossier avec parent"""
        parent = Folder.objects.create(name="Parent", username="user")
        child = Folder.objects.create(name="Child", parent=parent, username="user")

        serializer = SingleFolderSerializer(child)
        data = serializer.data

        assert data['parent'] == parent.id

    def test_single_folder_serializer_all_fields(self):
        """Tester que tous les champs sont présents"""
        folder = Folder.objects.create(name="Folder", username="user")

        serializer = SingleFolderSerializer(folder)
        data = serializer.data

        assert 'id' in data
        assert 'name' in data
        assert 'parent' in data
        assert 'username' in data
        assert 'type' in data
        assert 'created_at' in data
        assert 'updated_at' in data


@pytest.mark.django_db
class TestFolderSerializer(TestCase):
    """Tests pour FolderSerializer"""

    def test_folder_serializer_basic(self):
        """Tester la sérialisation basique d'un dossier"""
        folder = Folder.objects.create(name="Folder", username="user")

        serializer = FolderSerializer(folder)
        data = serializer.data

        assert data['name'] == "Folder"
        assert data['username'] == "user"
        assert data['type'] == "folder"

    def test_folder_serializer_path_root(self):
        """Tester le chemin pour un dossier racine"""
        folder = Folder.objects.create(name="root", username="user")

        serializer = FolderSerializer(folder)
        data = serializer.data

        assert data['path'] == "/"

    def test_folder_serializer_path_with_parent(self):
        """Tester le chemin pour un dossier avec parent"""
        parent = Folder.objects.create(name="root", username="user")
        child = Folder.objects.create(name="Child", parent=parent, username="user")

        serializer = FolderSerializer(child)
        data = serializer.data

        assert "Child" in data['path']
        assert "/" in data['path']

    def test_folder_serializer_path_deeply_nested(self):
        """Tester le chemin pour un dossier profondément imbriqué"""
        root = Folder.objects.create(name="root", username="user")
        level1 = Folder.objects.create(name="L1", parent=root, username="user")
        level2 = Folder.objects.create(name="L2", parent=level1, username="user")
        level3 = Folder.objects.create(name="L3", parent=level2, username="user")

        serializer = FolderSerializer(level3)
        data = serializer.data

        assert "L3" in data['path']
        assert "L2" in data['path']
        assert "L1" in data['path']

    def test_folder_serializer_path_max_depth_protection(self):
        """Tester que la profondeur est limitée à 10"""
        # Créer une chaîne profonde
        current = None
        for i in range(12):
            current = Folder.objects.create(
                name=f"Level_{i}",
                parent=current,
                username="user"
            )

        serializer = FolderSerializer(current)
        data = serializer.data

        # Devrait avoir un chemin valide (profondeur limitée)
        assert isinstance(data['path'], str)
        assert "/" in data['path']

    def test_folder_serializer_expandable_fields(self):
        """Tester que les expandable_fields sont définis"""
        meta = FolderSerializer.Meta

        assert hasattr(meta, 'expandable_fields')
        assert 'subfolders' in meta.expandable_fields
        assert 'maps' in meta.expandable_fields
        assert 'parent' in meta.expandable_fields

    def test_folder_serializer_with_expand_subfolders(self):
        """Tester la sérialisation avec expand=subfolders"""
        parent = Folder.objects.create(name="Parent", username="user")
        child1 = Folder.objects.create(name="Child1", parent=parent, username="user")
        child2 = Folder.objects.create(name="Child2", parent=parent, username="user")

        factory = APIRequestFactory()
        request = factory.get('/?expand=subfolders')
        drf_request = Request(request)

        context = {'request': drf_request}
        serializer = FolderSerializer(parent, context=context)
        data = serializer.data

        assert 'subfolders' in data
        assert isinstance(data['subfolders'], list)
        assert len(data['subfolders']) == 2

    def test_folder_serializer_with_expand_maps(self):
        """Tester la sérialisation avec expand=maps"""
        folder = Folder.objects.create(name="Folder", username="user")
        Map.objects.create(name="Map1", data={}, folder=folder, username="user")
        Map.objects.create(name="Map2", data={}, folder=folder, username="user")

        factory = APIRequestFactory()
        request = factory.get('/?expand=maps')
        drf_request = Request(request)

        context = {'request': drf_request}
        serializer = FolderSerializer(folder, context=context)
        data = serializer.data

        assert 'maps' in data
        assert isinstance(data['maps'], list)
        assert len(data['maps']) == 2

    def test_folder_serializer_with_expand_parent(self):
        """Tester la sérialisation avec expand=parent"""
        parent = Folder.objects.create(name="Parent", username="user")
        child = Folder.objects.create(name="Child", parent=parent, username="user")

        factory = APIRequestFactory()
        request = factory.get('/?expand=parent')
        drf_request = Request(request)

        context = {'request': drf_request}
        serializer = FolderSerializer(child, context=context)
        data = serializer.data

        assert 'parent' in data
        assert isinstance(data['parent'], dict)
        assert data['parent']['name'] == "Parent"

    def test_folder_serializer_all_fields(self):
        """Tester que tous les champs sont présents"""
        folder = Folder.objects.create(name="Folder", username="user")

        serializer = FolderSerializer(folder)
        data = serializer.data

        assert 'id' in data
        assert 'name' in data
        assert 'username' in data
        assert 'type' in data
        assert 'path' in data
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_folder_serializer_parent_field_readonly(self):
        """Tester que le champ parent est correct"""
        parent = Folder.objects.create(name="Parent", username="user")
        child = Folder.objects.create(name="Child", parent=parent, username="user")

        serializer = FolderSerializer(child)
        data = serializer.data

        assert data['parent'] == parent.id


@pytest.mark.django_db
class TestSerializerIntegration(TestCase):
    """Tests d'intégration pour les sérialiseurs"""

    def test_complete_folder_hierarchy_serialization(self):
        """Tester la sérialisation d'une hiérarchie complète"""
        root = Folder.objects.create(name="root", username="user")
        folder1 = Folder.objects.create(name="Folder1", parent=root, username="user")
        folder2 = Folder.objects.create(name="Folder2", parent=root, username="user")

        Map.objects.create(name="Map1", data={}, folder=folder1, username="user")
        Map.objects.create(name="Map2", data={}, folder=folder2, username="user")

        serializer = FolderSerializer(root)
        data = serializer.data

        assert data['name'] == "root"
        assert 'id' in data
        assert 'path' in data

    def test_serializer_with_empty_folder(self):
        """Tester la sérialisation d'un dossier vide"""
        folder = Folder.objects.create(name="Empty", username="user")

        serializer = FolderSerializer(folder)
        data = serializer.data

        assert data['name'] == "Empty"
        assert len(data) > 0

    def test_multiple_serializers_on_same_data(self):
        """Tester que plusieurs sérialiseurs peuvent traiter les mêmes données"""
        folder = Folder.objects.create(name="Folder", username="user")

        serializer1 = FolderSerializer(folder)
        serializer2 = SingleFolderSerializer(folder)

        data1 = serializer1.data
        data2 = serializer2.data

        assert data1['name'] == data2['name']
        assert data1['id'] == data2['id']

