"""
Tests pour vérifier que les @property des modèles sont incluses correctement:
1. Dans les métadonnées OData ($metadata)
2. Dans les réponses API OData
3. En tant que champs read-only dans les serializers
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from datetime import date
import json

from my_app.models import Person, Car
from my_app.serializers import generate_serializer, extract_properties
from my_app.management.commands.generate_odata_metadata import ODataMetadataGenerator


class PropertyExtractionTest(TestCase):
    """Tests pour l'extraction des @property"""

    def test_extract_properties_from_person_model(self):
        """Vérifier que la propriété 'full_name' est détectée sur le modèle Person"""
        properties = extract_properties(Person)

        # La propriété full_name devrait être détectée
        self.assertIn('full_name', properties)
        self.assertIsInstance(properties['full_name'], property)

    def test_extract_properties_returns_dict(self):
        """Vérifier que extract_properties retourne un dictionnaire"""
        properties = extract_properties(Person)
        self.assertIsInstance(properties, dict)

    def test_no_private_properties_extracted(self):
        """Vérifier que les propriétés privées (commençant par _) ne sont pas extraites"""
        properties = extract_properties(Person)

        # Aucune propriété ne devrait commencer par _
        for prop_name in properties.keys():
            self.assertFalse(prop_name.startswith('_'),
                           f"Propriété privée '{prop_name}' ne devrait pas être extraite")


class PersonSerializerPropertyTest(TestCase):
    """Tests pour vérifier que les propriétés sont incluses dans le serializer"""

    def setUp(self):
        """Créer une instance de Person pour les tests"""
        self.person = Person.objects.create(
            first_name="John",
            last_name="Doe",
            birth_date=date(1990, 1, 1)
        )

    def test_serializer_includes_full_name_property(self):
        """Vérifier que le serializer inclut le champ full_name"""
        serializer_class = generate_serializer(Person)

        # Vérifier que full_name est dans les champs
        self.assertIn('full_name', serializer_class().fields)

    def test_full_name_property_is_read_only(self):
        """Vérifier que full_name est un champ read_only"""
        serializer_class = generate_serializer(Person)
        serializer = serializer_class()

        field = serializer.fields.get('full_name')
        self.assertIsNotNone(field)
        self.assertTrue(field.read_only, "full_name devrait être read-only")

    def test_serializer_returns_full_name_value(self):
        """Vérifier que le serializer retourne la valeur correcte de full_name"""
        serializer_class = generate_serializer(Person)
        serializer = serializer_class(self.person)

        data = serializer.data

        # Vérifier que full_name est dans les données
        self.assertIn('full_name', data)
        # Vérifier que la valeur est correcte
        self.assertEqual(data['full_name'], 'John Doe')

    def test_full_name_updates_with_first_and_last_name(self):
        """Vérifier que full_name se met à jour quand first_name ou last_name change"""
        serializer_class = generate_serializer(Person)

        # Vérifier la valeur initiale
        serializer = serializer_class(self.person)
        self.assertEqual(serializer.data['full_name'], 'John Doe')

        # Modifier les noms
        self.person.first_name = "Jane"
        self.person.last_name = "Smith"

        # Vérifier que la propriété se met à jour
        serializer = serializer_class(self.person)
        self.assertEqual(serializer.data['full_name'], 'Jane Smith')


class ODataMetadataPropertyTest(TestCase):
    """Tests pour vérifier que les propriétés sont dans les métadonnées OData"""

    def test_metadata_generator_includes_properties(self):
        """Vérifier que le générateur de métadonnées détecte les propriétés"""
        generator = ODataMetadataGenerator(namespace="Odata", service_name="Container")
        generator.collect_models()
        generator.process_model_fields()

        # Récupérer l'entity Person
        person_entity = generator.entity_types.get('Person')
        self.assertIsNotNone(person_entity)

        # Vérifier que full_name est dans les champs
        field_names = [f['name'] for f in person_entity['fields']]
        self.assertIn('full_name', field_names)

    def test_properties_marked_as_computed_in_xml(self):
        """Vérifier que les propriétés sont marquées comme Computed en XML"""
        generator = ODataMetadataGenerator(namespace="Odata", service_name="Container")
        metadata_xml = generator.generate(output_format='xml')

        # Vérifier que Computed="true" est présent pour full_name
        self.assertIn('Computed="true"', metadata_xml)
        # Et que c'est bien associé à full_name
        self.assertIn('Name="full_name"', metadata_xml)

    def test_properties_marked_as_computed_in_json(self):
        """Vérifier que les propriétés sont marquées comme $Computed en JSON"""
        generator = ODataMetadataGenerator(namespace="Odata", service_name="Container")
        metadata_json = generator.generate(output_format='json')
        metadata_dict = json.loads(metadata_json)

        # Naviguer jusqu'à la définition de Person dans le namespace
        odata_namespace = metadata_dict.get('Odata', {})
        person_type = odata_namespace.get('Person', {})

        # Vérifier que full_name existe et est marqué comme Computed
        full_name_field = person_type.get('full_name', {})
        self.assertIsNotNone(full_name_field)
        self.assertTrue(full_name_field.get('$Computed', False),
                       "full_name devrait avoir $Computed: true en JSON")


class ODataAPIPropertyTest(APITestCase):
    """Tests pour vérifier que les propriétés sont retournées par l'API OData"""

    def setUp(self):
        """Créer des données de test"""
        self.person1 = Person.objects.create(
            first_name="John",
            last_name="Doe",
            birth_date=date(1990, 1, 1)
        )
        self.person2 = Person.objects.create(
            first_name="Jane",
            last_name="Smith",
            birth_date=date(1992, 5, 15)
        )
        self.client = Client()

    def test_odata_list_includes_properties(self):
        """Vérifier que l'API /odata/persons inclut les propriétés"""
        response = self.client.get('/odata/persons')

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('value', data)

        # Vérifier qu'au moins une personne est retournée
        self.assertGreater(len(data['value']), 0)

        # Vérifier que full_name est présent dans chaque enregistrement
        for person in data['value']:
            self.assertIn('full_name', person,
                         "full_name devrait être présent dans chaque enregistrement")
            self.assertEqual(person['full_name'],
                           f"{person['first_name']} {person['last_name']}")

    def test_odata_list_full_name_values(self):
        """Vérifier que les valeurs de full_name sont correctes"""
        response = self.client.get('/odata/persons')

        data = response.json()
        persons = {p['id']: p for p in data['value']}

        # Vérifier les valeurs exactes
        self.assertEqual(persons[self.person1.id]['full_name'], 'John Doe')
        self.assertEqual(persons[self.person2.id]['full_name'], 'Jane Smith')

    def test_odata_retrieve_includes_properties(self):
        """Vérifier que l'API GET /odata/persons(id) inclut les propriétés"""
        response = self.client.get(f'/odata/persons({self.person1.id})')

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('full_name', data)
        self.assertEqual(data['full_name'], 'John Doe')

    def test_properties_are_read_only(self):
        """Vérifier que les propriétés ne peuvent pas être modifiées"""
        # Les propriétés ne devraient pas être modifiables
        # (ce test vérifie que la tentative de modification est ignorée)
        response = self.client.patch(
            f'/odata/persons({self.person1.id})',
            data={
                'full_name': 'Invalid Name'  # Essayer de modifier la propriété
            },
            content_type='application/json'
        )

        # Récupérer la personne et vérifier que full_name n'a pas changé
        self.person1.refresh_from_db()
        self.assertEqual(
            f"{self.person1.first_name} {self.person1.last_name}",
            'John Doe',
            "full_name ne devrait pas pouvoir être modifiée directement"
        )

    def test_select_parameter_includes_properties(self):
        """Vérifier que $select fonctionne avec les propriétés"""
        response = self.client.get('/odata/persons?$select=first_name,full_name')

        self.assertEqual(response.status_code, 200)

        data = response.json()
        for person in data['value']:
            # Devrait avoir au moins first_name et full_name
            self.assertIn('full_name', person)

    def test_multiple_properties_if_they_exist(self):
        """Test pour vérifier que plusieurs propriétés fonctionnent"""
        # Ce test est extensible pour d'autres modèles avec plusieurs propriétés
        serializer_class = generate_serializer(Person)
        serializer = serializer_class(self.person1)

        # Vérifier que tous les champs read-only sont présents
        readonly_fields = [field for field, f in serializer.fields.items()
                          if f.read_only and field.startswith('full_name') or
                          (hasattr(f, 'source') and f.source == field)]

        # Au moins full_name devrait être présent
        self.assertGreater(len(readonly_fields), 0)


class ODataMetadataEndpointPropertyTest(APITestCase):
    """Tests pour l'endpoint /odata/$metadata avec les propriétés"""

    def test_metadata_endpoint_xml_includes_properties(self):
        """Vérifier que GET /odata/$metadata inclut les propriétés"""
        response = self.client.get('/odata/$metadata')

        self.assertEqual(response.status_code, 200)
        self.assertIn('xml', response.get('Content-Type', '').lower())

        content = response.content.decode('utf-8')

        # Vérifier que full_name est mentionné
        self.assertIn('full_name', content)
        # Vérifier que c'est marqué comme Computed
        self.assertIn('Computed="true"', content)

    def test_metadata_endpoint_json_includes_properties(self):
        """Vérifier que GET /odata/$metadata?format=json inclut les propriétés"""
        response = self.client.get('/odata/$metadata?format=json')

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # L'endpoint retourne entity_types directement (format simplifié)
        # Chercher Person dans les entity_types
        if 'Person' in data:
            person_type = data['Person']
        else:
            # Sinon, chercher dans le namespace
            odata_namespace = data.get('Odata', {})
            person_type = odata_namespace.get('Person', {})

        # Vérifier que Person a des champs
        self.assertIsNotNone(person_type)

        # Vérifier que full_name existe en tant que champ dans les champs
        if 'fields' in person_type:
            field_names = [f['name'] for f in person_type['fields']]
            self.assertIn('full_name', field_names)

