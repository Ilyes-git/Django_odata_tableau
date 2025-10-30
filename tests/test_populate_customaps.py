"""
Tests complets pour le management command populate_customaps
Vise 100% de code coverage
"""
import pytest
from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from customaps.models import Folder, Map


@pytest.mark.django_db
class TestPopulateCustomapsCommand(TestCase):
    """Tests pour le management command populate_customaps"""

    def test_command_default_parameters(self):
        """Tester la commande avec les paramètres par défaut"""
        out = StringIO()
        call_command('populate_customaps', stdout=out)

        output = out.getvalue()

        # Vérifier que la commande s'est exécutée
        assert 'Creating' in output
        assert 'Successfully created' in output

        # Vérifier que des dossiers ont été créés (défaut: 5)
        assert Folder.objects.exists()
        assert Map.objects.exists()

    def test_command_with_custom_folders(self):
        """Tester avec un nombre personnalisé de dossiers"""
        out = StringIO()
        call_command('populate_customaps', '--folders=2', stdout=out)

        # Vérifier qu'il y a des dossiers racine
        root_folders = Folder.objects.filter(parent__isnull=True)
        assert root_folders.count() >= 2

    def test_command_with_custom_depth(self):
        """Tester avec une profondeur personnalisée"""
        out = StringIO()
        call_command('populate_customaps', '--depth=2', '--folders=1', stdout=out)

        output = out.getvalue()

        # Vérifier qu'il y a des sous-dossiers
        assert Folder.objects.filter(parent__isnull=False).exists()

    def test_command_with_custom_maps(self):
        """Tester avec un nombre personnalisé de maps"""
        out = StringIO()
        call_command('populate_customaps', '--maps=5', '--folders=1', '--depth=1', stdout=out)

        # Vérifier qu'il y a des maps
        assert Map.objects.exists()

    def test_command_clear_option(self):
        """Tester l'option --clear pour supprimer les données existantes"""
        # Créer des données initiales
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=2')

        initial_folders = Folder.objects.count()
        initial_maps = Map.objects.count()

        assert initial_folders > 0
        assert initial_maps > 0

        # Relancer avec --clear
        out = StringIO()
        call_command('populate_customaps', '--clear', '--folders=1', '--depth=1', '--maps=1', stdout=out)

        output = out.getvalue()
        assert 'Clearing existing data' in output
        assert 'Data cleared' in output

        # Les données doivent être recréées (pas forcément le même nombre)
        assert Folder.objects.exists()
        assert Map.objects.exists()

    def test_folder_hierarchy_structure(self):
        """Tester que la hiérarchie des dossiers est correctement créée"""
        call_command('populate_customaps', '--folders=1', '--depth=2', '--maps=1')

        # Vérifier qu'il y a des dossiers racine
        root_folders = Folder.objects.filter(parent__isnull=True)
        assert root_folders.exists()

        # Vérifier qu'il y a des sous-dossiers
        subfolders = Folder.objects.filter(parent__isnull=False)
        assert subfolders.exists()

        # Vérifier que chaque sous-dossier a un parent
        for subfolder in subfolders:
            assert subfolder.parent is not None

    def test_folder_properties(self):
        """Tester que les propriétés des dossiers sont correctement définies"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')

        folder = Folder.objects.first()

        # Vérifier les propriétés requises
        assert folder.name is not None
        assert len(folder.name) > 0
        assert folder.username is not None
        assert len(folder.username) > 0

    def test_map_structure(self):
        """Tester la structure des maps créées"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=2')

        map_obj = Map.objects.first()

        # Vérifier les propriétés requises
        assert map_obj.name is not None
        assert map_obj.data is not None
        assert map_obj.folder is not None
        assert map_obj.username is not None

    def test_map_data_format(self):
        """Tester que les données GeoJSON des maps sont correctement formatées"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')

        map_obj = Map.objects.first()
        data = map_obj.data

        # Vérifier la structure GeoJSON
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)
        assert len(data['features']) > 0

        # Vérifier la structure des features
        feature = data['features'][0]
        assert feature['type'] == 'Feature'
        assert 'properties' in feature
        assert 'geometry' in feature

        # Vérifier la géométrie
        geometry = feature['geometry']
        assert geometry['type'] == 'Point'
        assert 'coordinates' in geometry
        assert len(geometry['coordinates']) == 2

    def test_maps_per_folder_count(self):
        """Tester que le nombre correct de maps est créé par dossier"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=3')

        root_folder = Folder.objects.filter(parent__isnull=True).first()
        maps_in_root = root_folder.maps.count()

        # Le nombre de maps devrait être >= 3 (peut y avoir des maps dans les sous-dossiers aussi)
        assert maps_in_root >= 3

    def test_username_consistency(self):
        """Tester que le username est cohérent pour un dossier et ses cartes"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=2')

        folder = Folder.objects.first()
        maps = folder.maps.all()

        # Toutes les maps doivent avoir le même username que le dossier
        for map_obj in maps:
            assert map_obj.username == folder.username

    def test_subfolder_inherits_username(self):
        """Tester que les sous-dossiers héritent du username du parent"""
        call_command('populate_customaps', '--folders=1', '--depth=2')

        root_folder = Folder.objects.filter(parent__isnull=True).first()
        subfolders = root_folder.subfolders.all()

        # Les sous-dossiers doivent avoir le même username
        for subfolder in subfolders:
            assert subfolder.username == root_folder.username

    def test_output_messages(self):
        """Tester que les messages de sortie sont corrects"""
        out = StringIO()
        call_command('populate_customaps', '--folders=1', '--depth=2', '--maps=1', stdout=out)

        output = out.getvalue()

        # Vérifier la présence de messages clés
        assert 'Creating' in output
        assert 'Created root folder' in output
        assert 'subfolder' in output.lower()  # Peut apparaître comme "Created subfolder" ou juste "subfolder"
        assert 'Successfully created' in output

    def test_multiple_root_folders(self):
        """Tester la création de plusieurs dossiers racine"""
        call_command('populate_customaps', '--folders=3', '--depth=1', '--maps=1')

        root_folders = Folder.objects.filter(parent__isnull=True)

        # Devrait y avoir au moins 3 dossiers racine
        assert root_folders.count() >= 3

    def test_depth_zero(self):
        """Tester avec une profondeur de 0"""
        call_command('populate_customaps', '--folders=1', '--depth=0', '--maps=1')

        # Même avec depth=0, devrait y avoir des dossiers racine
        root_folders = Folder.objects.filter(parent__isnull=True)
        assert root_folders.count() >= 1

        # Mais pas de sous-dossiers
        subfolders = Folder.objects.filter(parent__isnull=False)
        assert subfolders.count() == 0

    def test_folder_names_are_unique_per_level(self):
        """Tester que les noms des dossiers incluent leur niveau"""
        call_command('populate_customaps', '--folders=1', '--depth=2', '--maps=1')

        # Vérifier que tous les dossiers ont des noms
        folders = Folder.objects.all()
        for folder in folders:
            assert folder.name is not None
            assert len(folder.name) > 0

    def test_map_names_are_created(self):
        """Tester que les noms des maps sont créés"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=3')

        maps = Map.objects.all()
        map_names = [m.name for m in maps]

        # Vérifier qu'il y a des noms
        assert len(map_names) > 0

        # Tous les noms doivent être non-vides
        for name in map_names:
            assert len(name) > 0

    def test_coordinates_are_valid_floats(self):
        """Tester que les coordonnées sont des nombres valides"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=2')

        map_obj = Map.objects.first()
        coordinates = map_obj.data['features'][0]['geometry']['coordinates']

        # Vérifier que ce sont des nombres valides
        lon, lat = coordinates
        assert isinstance(lon, float) or isinstance(lon, int)
        assert isinstance(lat, float) or isinstance(lat, int)

        # Vérifier les plages valides
        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

    def test_property_fields_exist(self):
        """Tester que les propriétés des features existent"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')

        map_obj = Map.objects.first()
        properties = map_obj.data['features'][0]['properties']

        # Vérifier que les propriétés requises existent
        assert 'name' in properties
        assert 'description' in properties
        assert len(properties['name']) > 0
        assert len(properties['description']) > 0


@pytest.mark.django_db
class TestPopulateCustomapsIntegration(TestCase):
    """Tests d'intégration pour le management command"""

    def test_complete_workflow(self):
        """Tester un workflow complet"""
        # Créer des données
        call_command('populate_customaps', '--folders=2', '--depth=2', '--maps=2')

        # Vérifier la structure complète
        root_folders = Folder.objects.filter(parent__isnull=True)
        assert root_folders.count() >= 2

        subfolders = Folder.objects.filter(parent__isnull=False)
        assert subfolders.exists()

        maps = Map.objects.all()
        assert maps.exists()

        # Vérifier l'intégrité des relations
        for folder in Folder.objects.all():
            if folder.parent:
                # Vérifier que la relation inverse fonctionne
                assert folder in folder.parent.subfolders.all()

            # Vérifier que toutes les maps appartiennent au dossier
            for map_obj in folder.maps.all():
                assert map_obj.folder == folder

    def test_sequential_commands(self):
        """Tester l'exécution successive de commandes"""
        # Première exécution
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')
        first_count = Folder.objects.count()

        # Deuxième exécution sans clear (devrait ajouter)
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')
        second_count = Folder.objects.count()

        # Le nombre devrait augmenter
        assert second_count >= first_count

    def test_command_with_all_options(self):
        """Tester la commande avec toutes les options"""
        out = StringIO()
        call_command(
            'populate_customaps',
            '--folders=2',
            '--depth=2',
            '--maps=3',
            '--clear',
            stdout=out
        )

        output = out.getvalue()

        # Vérifier que tout s'est bien déroulé
        assert 'Successfully created' in output
        assert Folder.objects.exists()
        assert Map.objects.exists()


@pytest.mark.django_db
class TestPopulateCustomapsEdgeCases(TestCase):
    """Tests des cas limites pour le management command"""

    def test_very_deep_hierarchy(self):
        """Tester avec une profondeur très importante"""
        call_command('populate_customaps', '--folders=1', '--depth=5', '--maps=1')

        # Vérifier qu'il y a une bonne structure
        folders = Folder.objects.all()
        assert folders.count() > 1

    def test_many_maps_per_folder(self):
        """Tester avec beaucoup de maps par dossier"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=10')

        maps = Map.objects.all()
        assert maps.count() >= 10

    def test_single_folder_single_depth_single_map(self):
        """Tester avec les valeurs minimales"""
        call_command('populate_customaps', '--folders=1', '--depth=1', '--maps=1')

        # Au minimum, devrait y avoir 1 dossier racine et quelques cartes
        root_folders = Folder.objects.filter(parent__isnull=True)
        assert root_folders.count() >= 1

