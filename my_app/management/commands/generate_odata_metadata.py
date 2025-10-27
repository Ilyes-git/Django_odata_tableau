#!/usr/bin/env python
"""
Script de management Django pour générer le schéma metadata EDMX OData v4.

Usage:
    python manage.py generate_odata_metadata [options]

Options:
    --output, -o: Chemin du fichier de sortie (défaut: odata_metadata.xml)
    --namespace: Espace de noms pour les entités (défaut: DjangoOData)
    --service-name: Nom du conteneur de service (défaut: Container)
    --include-auth: Inclure les modèles d'authentification (défaut: True)
    --format: Format de sortie: 'xml' ou 'json' (défaut: xml)
"""

import os
import json
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models as django_models
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField


class ODataMetadataGenerator:
    """Génère le schéma metadata EDMX pour une application Django."""

    # Mapping entre les types Django et les types OData
    FIELD_TYPE_MAPPING = {
        'AutoField': 'Edm.Int32',
        'BigAutoField': 'Edm.Int64',
        'BigIntegerField': 'Edm.Int64',
        'IntegerField': 'Edm.Int32',
        'SmallIntegerField': 'Edm.Int16',
        'PositiveIntegerField': 'Edm.Int32',
        'PositiveSmallIntegerField': 'Edm.Int16',
        'FloatField': 'Edm.Double',
        'DecimalField': 'Edm.Decimal',
        'BooleanField': 'Edm.Boolean',
        'CharField': 'Edm.String',
        'TextField': 'Edm.String',
        'EmailField': 'Edm.String',
        'URLField': 'Edm.String',
        'SlugField': 'Edm.String',
        'DateField': 'Edm.Date',
        'DateTimeField': 'Edm.DateTimeOffset',
        'TimeField': 'Edm.TimeOfDay',
        'DurationField': 'Edm.Duration',
        'JSONField': 'Edm.String',
        'FileField': 'Edm.String',
        'ImageField': 'Edm.String',
        'UUIDField': 'Edm.Guid',
    }

    # Modèles à exclure par défaut
    EXCLUDED_MODELS = {
        'LogEntry', 'Permission', 'Group', 'User', 'ContentType', 'Session'
    }

    def __init__(
        self,
        namespace: str = "DjangoOData",
        service_name: str = "Container",
        include_auth: bool = True
    ):
        """
        Initialiser le générateur.

        Args:
            namespace: L'espace de noms XML pour les entités
            service_name: Le nom du conteneur de service
            include_auth: Inclure les modèles d'authentification Django
        """
        self.namespace = namespace
        self.service_name = service_name
        self.include_auth = include_auth
        self.models: Dict = {}
        self.entity_types: Dict = {}
        self.associations: List[Tuple] = []

    def get_odata_type(self, field) -> str:
        """
        Récupérer le type OData correspondant à un champ Django.

        Args:
            field: Le champ Django

        Returns:
            Le type OData correspondant
        """
        field_class_name = field.__class__.__name__
        return self.FIELD_TYPE_MAPPING.get(field_class_name, 'Edm.String')

    def should_include_model(self, model) -> bool:
        """Déterminer si un modèle doit être inclus."""
        model_name = model.__name__

        # Exclure les modèles d'authentification si demandé
        if not self.include_auth and model_name in self.EXCLUDED_MODELS:
            return False

        # Exclure les modèles du système Django
        if model._meta.app_label in ['contenttypes', 'auth']:
            return not self.include_auth

        return True

    def collect_models(self):
        """Collecter tous les modèles de l'application."""
        for model in apps.get_models():
            if self.should_include_model(model):
                self.models[model.__name__] = model
                self.entity_types[model.__name__] = {
                    'fields': [],
                    'key': None,
                    'relationships': [],
                    'app_label': model._meta.app_label
                }

    def process_model_fields(self):
        """Traiter les champs de chaque modèle."""
        for model_name, model in self.models.items():
            entity = self.entity_types[model_name]

            for field in model._meta.get_fields():
                # Ignorer les champs Many-to-Many (pour simplifier)
                if isinstance(field, ManyToManyField):
                    continue

                # Traiter les clés primaires
                if isinstance(field, django_models.AutoField) or (
                    hasattr(field, 'primary_key') and field.primary_key
                ):
                    entity['key'] = field.name
                    entity['fields'].append({
                        'name': field.name,
                        'type': self.get_odata_type(field),
                        'nullable': False,
                        'is_key': True,
                        'max_length': None
                    })

                # Traiter les ForeignKey
                elif isinstance(field, ForeignKey):
                    related_model = field.related_model.__name__
                    if related_model in self.models:
                        entity['relationships'].append({
                            'name': field.name,
                            'type': related_model,
                            'multiplicity': 'ZeroOrOne'
                        })
                        # Ajouter aussi la propriété de la clé étrangère
                        entity['fields'].append({
                            'name': f"{field.name}_id",
                            'type': 'Edm.Int32',
                            'nullable': True,
                            'is_key': False,
                            'max_length': None
                        })
                        self.associations.append((model_name, related_model, field.name))

                # Traiter les champs normaux
                elif not field.many_to_one and not field.one_to_many:
                    if hasattr(field, 'name') and field.name not in ['id']:
                        max_length = getattr(field, 'max_length', None)
                        entity['fields'].append({
                            'name': field.name,
                            'type': self.get_odata_type(field),
                            'nullable': getattr(field, 'null', True),
                            'is_key': False,
                            'max_length': max_length
                        })

    def generate_edmx(self) -> str:
        """
        Générer le document EDMX complet.

        Returns:
            Le document XML EDMX en tant que chaîne
        """
        # Créer l'élément racine
        edmx = ET.Element(
            'edmx:Edmx',
            {
                'Version': '4.0',
                'xmlns:edmx': 'http://docs.oasis-open.org/odata/ns/edmx'
            }
        )

        # Ajouter DataServices
        data_services = ET.SubElement(edmx, 'edmx:DataServices')

        # Ajouter le schéma
        schema = ET.SubElement(
            data_services,
            'Schema',
            {
                'Namespace': self.namespace,
                'xmlns': 'http://docs.oasis-open.org/odata/ns/edm'
            }
        )

        # Ajouter les types d'entités
        for model_name in sorted(self.entity_types.keys()):
            entity = self.entity_types[model_name]
            self._add_entity_type(schema, model_name, entity)

        # Ajouter le conteneur de service
        self._add_entity_container(schema)

        # Formater et retourner
        return self._prettify_xml(edmx)

    def generate_json_schema(self) -> str:
        """
        Générer un schéma JSON alternatif.

        Returns:
            Le schéma en format JSON
        """
        schema = {
            'version': '4.0',
            'namespace': self.namespace,
            'service_name': self.service_name,
            'entity_types': {},
            'associations': []
        }

        for model_name in sorted(self.entity_types.keys()):
            entity = self.entity_types[model_name]
            schema['entity_types'][model_name] = {
                'key': entity['key'],
                'properties': entity['fields'],
                'relationships': entity['relationships']
            }

        schema['associations'] = [
            {
                'from_entity': from_entity,
                'to_entity': to_entity,
                'property': prop
            }
            for from_entity, to_entity, prop in self.associations
        ]

        return json.dumps(schema, indent=2, ensure_ascii=False)

    def _add_entity_type(self, parent_element, model_name: str, entity: Dict):
        """Ajouter un type d'entité au schéma."""
        entity_type = ET.SubElement(
            parent_element,
            'EntityType',
            {'Name': model_name}
        )

        # Ajouter la clé
        if entity['key']:
            key_element = ET.SubElement(entity_type, 'Key')
            ET.SubElement(
                key_element,
                'PropertyRef',
                {'Name': entity['key']}
            )

        # Ajouter les propriétés
        for field in entity['fields']:
            attrs = {
                'Name': field['name'],
                'Type': field['type'],
                'Nullable': 'false' if not field['nullable'] else 'true'
            }

            # Ajouter la longueur max si applicable
            if field['max_length']:
                attrs['MaxLength'] = str(field['max_length'])

            ET.SubElement(entity_type, 'Property', attrs)

        # Ajouter les propriétés de navigation
        for rel in entity['relationships']:
            ET.SubElement(
                entity_type,
                'NavigationProperty',
                {
                    'Name': rel['name'],
                    'Type': f"{self.namespace}.{rel['type']}",
                }
            )

    def _add_entity_container(self, parent_element):
        """Ajouter le conteneur de service."""
        container = ET.SubElement(
            parent_element,
            'EntityContainer',
            {'Name': self.service_name}
        )

        # Ajouter les jeux d'entités
        for model_name in sorted(self.models.keys()):
            # Pluralisation simple
            entity_set_name = f"{model_name}s"
            ET.SubElement(
                container,
                'EntitySet',
                {
                    'Name': entity_set_name,
                    'EntityType': f"{self.namespace}.{model_name}"
                }
            )

    def _prettify_xml(self, elem) -> str:
        """Formater le XML pour le rendre lisible."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate(self, output_format: str = 'xml') -> str:
        """
        Exécuter la génération complète du metadata.

        Args:
            output_format: 'xml' ou 'json'

        Returns:
            Le schéma au format demandé
        """
        self.collect_models()
        self.process_model_fields()

        if output_format == 'json':
            return self.generate_json_schema()
        else:
            return self.generate_edmx()

    def get_summary(self) -> Dict:
        """Retourner un résumé de la génération."""
        return {
            'models_count': len(self.models),
            'entity_types_count': len(self.entity_types),
            'associations_count': len(self.associations),
            'models': {
                model_name: {
                    'properties': len(entity['fields']),
                    'relationships': len(entity['relationships']),
                    'app': entity['app_label']
                }
                for model_name, entity in sorted(self.entity_types.items())
            }
        }


class Command(BaseCommand):
    help = 'Génère le schéma metadata EDMX OData v4 de l\'application Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output',
            type=str,
            default='odata_metadata.xml',
            help='Chemin du fichier de sortie (défaut: odata_metadata.xml)'
        )

        parser.add_argument(
            '--namespace',
            type=str,
            default='DjangoOData',
            help='Espace de noms pour les entités (défaut: DjangoOData)'
        )

        parser.add_argument(
            '--service-name',
            type=str,
            default='Container',
            help='Nom du conteneur de service (défaut: Container)'
        )

        parser.add_argument(
            '--include-auth',
            type=bool,
            default=True,
            help='Inclure les modèles d\'authentification (défaut: True)'
        )

        parser.add_argument(
            '--format',
            type=str,
            choices=['xml', 'json'],
            default='xml',
            help='Format de sortie: xml ou json (défaut: xml)'
        )

        parser.add_argument(
            '--print',
            action='store_true',
            help='Afficher le résultat dans la console'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        namespace = options['namespace']
        service_name = options['service_name']
        include_auth = options['include_auth']
        output_format = options['format']
        should_print = options['print']

        self.stdout.write(
            self.style.SUCCESS('🔍 Génération du schéma metadata OData...')
        )

        try:
            # Créer le générateur
            generator = ODataMetadataGenerator(
                namespace=namespace,
                service_name=service_name,
                include_auth=include_auth
            )

            # Générer le metadata
            metadata_content = generator.generate(output_format=output_format)

            # Sauvegarder dans un fichier
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(metadata_content)

            self.stdout.write(
                self.style.SUCCESS(f'✅ Metadata sauvegardé dans: {output_file}')
            )

            # Afficher le résumé
            summary = generator.get_summary()
            self.stdout.write(self.style.WARNING('\n📊 Résumé:'))
            self.stdout.write(f"   - Modèles trouvés: {summary['models_count']}")
            self.stdout.write(f"   - Types d'entités: {summary['entity_types_count']}")
            self.stdout.write(f"   - Associations: {summary['associations_count']}")

            self.stdout.write(self.style.WARNING('\n   Modèles:'))
            for model_name, info in summary['models'].items():
                self.stdout.write(
                    f"   - {model_name} ({info['app']}): "
                    f"{info['properties']} propriétés, {info['relationships']} relations"
                )

            # Afficher le contenu si demandé
            if should_print:
                self.stdout.write(
                    self.style.WARNING('\n📄 Contenu du schéma:\n')
                )
                self.stdout.write(metadata_content)

        except Exception as e:
            raise CommandError(
                self.style.ERROR(f'❌ Erreur lors de la génération: {str(e)}')
            )
