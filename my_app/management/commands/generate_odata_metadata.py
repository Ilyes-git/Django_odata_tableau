#!/usr/bin/env python
"""
Script de management Django pour générer le schéma metadata EDMX OData v4.

Usage:
    python manage.py generate_odata_metadata [options]

Options:
    --output, -o: Chemin du fichier de sortie (défaut: odata_metadata.xml)
    --namespace: Espace de noms pour les entités (défaut: Odata)
    --service-name: Nom du conteneur de service (défaut: Container)
    --include-auth: Inclure les modèles d'authentification (défaut: True)
    --format: Format de sortie: 'xml' ou 'json' (défaut: xml)
"""

import json
from typing import Dict, List, Set, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models as django_models
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, OneToOneRel, ManyToOneRel, ManyToManyRel
)



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
        namespace: str = "Odata",
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
        self.relationships: List[Tuple] = []  # (model, fk_field, related_model)
        self.processed_relationships: Set[str] = set()  # Pour éviter les doublons

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

    def extract_properties(self, model) -> List[Dict]:
        """
        Extraire les @property d'une classe Django.

        Args:
            model: La classe Django

        Returns:
            Liste des propriétés avec leur nom et type déduit
        """
        properties = []

        # Parcourir les attributs de la classe
        for attr_name in dir(model):
            # Ignorer les attributs privés et magiques
            if attr_name.startswith('_'):
                continue

            try:
                attr = getattr(model, attr_name)

                # Vérifier si c'est une propriété (property object)
                if isinstance(attr, property):
                    # Déduire le type OData (par défaut Edm.String)
                    odata_type = 'Edm.String'

                    properties.append({
                        'name': attr_name,
                        'type': odata_type,
                        'nullable': True,
                        'is_key': False,
                        'max_length': None,
                        'is_property': True  # Marqueur pour les propriétés
                    })
            except (AttributeError, TypeError):
                # Ignorer les erreurs d'accès
                continue

        return properties

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
                    'app_label': model._meta.app_label,
                    'navigation_properties': []
                }

    def process_model_fields(self):
        """Traiter les champs de chaque modèle."""
        for model_name, model in self.models.items():
            entity = self.entity_types[model_name]

            for field in model._meta.get_fields():
                # Ignorer les champs Many-to-Many
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

                # Traiter les ForeignKey et OneToOneField
                elif isinstance(field, (ForeignKey, OneToOneField)):
                    related_model = field.related_model.__name__
                    if related_model in self.models:
                        fk_field = f"{field.name}"
                        entity['fields'].append({
                            'name': fk_field,
                            'type': 'Edm.Int32',
                            'nullable': getattr(field, 'null', True),
                            'is_key': False,
                            'max_length': None
                        })

                        # Créer une entrée de relationship
                        rel_info = {
                            'name': field.name,
                            'type': related_model,
                            'fk_field': fk_field,
                            'is_one_to_one': isinstance(field, OneToOneField),
                            'is_collection': False
                        }
                        entity['navigation_properties'].append(rel_info)
                        self.relationships.append((model_name, field.name, related_model))

                # Traiter les relations inverses (OneToOneRel, ManyToOneRel)
                elif isinstance(field, (OneToOneRel, ManyToOneRel)):
                    related_model = field.related_model.__name__
                    if related_model in self.models:
                        # Créer une navigation property pour la relation inverse
                        # IMPORTANT: Vérifier OneToOneRel en premier car il hérite de ManyToOneRel
                        is_one_to_one_rel = isinstance(field, OneToOneRel)

                        rel_info = {
                            'name': field.name,  # ex: 'header', 'loads'
                            'type': related_model,
                            'fk_field': None,  # Pas de FK sur ce modèle
                            'is_one_to_one': is_one_to_one_rel,
                            'is_collection': not is_one_to_one_rel  # False pour OneToOneRel, True pour ManyToOneRel
                        }
                        entity['navigation_properties'].append(rel_info)

                # Traiter les champs normaux
                elif not field.many_to_one and not field.one_to_many and not isinstance(field, (ManyToManyRel, ForeignObjectRel)):
                    if hasattr(field, 'name') and field.name not in ['id']:
                        max_length = getattr(field, 'max_length', None)
                        entity['fields'].append({
                            'name': field.name,
                            'type': self.get_odata_type(field),
                            'nullable': getattr(field, 'null', True),
                            'is_key': False,
                            'max_length': max_length
                        })

            # Ajouter les @property du modèle
            properties = self.extract_properties(model)
            entity['fields'].extend(properties)

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
        Générer un schéma JSON OData v4.0 conforme à la spécification officielle CSDL JSON.

        Référence: https://docs.oasis-open.org/odata/odata-csdl-json/v4.01/odata-csdl-json-v4.01.html

        Returns:
            Le schéma en format JSON OData v4.0
        """
        from my_app.views import ODATA_MODELS_REGISTRY

        # Créer un mapping modèle -> entity_set_name depuis le registry
        model_to_entity_set = {}
        for entity_set_name, entry in ODATA_MODELS_REGISTRY.items():
            model_name = entry.__name__
            model_to_entity_set[model_name] = entity_set_name

        # Structure racine conforme OData v4.0 CSDL JSON
        schema = {
            "$Version": "4.0",
            "$EntityContainer": f"{self.namespace}.{self.service_name}",
            f"{self.namespace}": {
                "$Alias": "self"
            }
        }

        # Ajouter les EntityTypes
        namespace_def = schema[self.namespace]

        for model_name in sorted(self.entity_types.keys()):
            entity = self.entity_types[model_name]

            entity_type_def = {
                "$Kind": "EntityType"
            }

            # Ajouter la clé primaire
            if entity['key']:
                entity_type_def["$Key"] = [entity['key']]

            # Ajouter les propriétés normales (non-navigation)
            for field in entity['fields']:
                property_def = {
                    "$Type": field['type']
                }

                # Nullable
                if not field['nullable']:
                    property_def["$Nullable"] = False

                # MaxLength pour les chaînes
                if field['max_length'] and field['type'] == 'Edm.String':
                    property_def["$MaxLength"] = field['max_length']

                # Marquer comme Computed si c'est une @property
                if field.get('is_property', False):
                    property_def["$Computed"] = True

                entity_type_def[field['name']] = property_def

            # Ajouter les NavigationProperties
            for nav_prop in entity['navigation_properties']:
                nav_def = {
                    "$Kind": "NavigationProperty",
                }

                # Si c'est une collection (relation one-to-many inverse)
                if nav_prop.get('is_collection', False):
                    nav_def["$Collection"] = True
                    nav_def["$Type"] = f"self.{nav_prop['type']}"
                else:
                    nav_def["$Type"] = f"self.{nav_prop['type']}"

                # Ajouter Partner si trouvé
                partner_name = self._find_partner_name(model_name, nav_prop['type'], nav_prop['name'])
                if partner_name:
                    nav_def["$Partner"] = partner_name

                # Ajouter ReferentialConstraint seulement si cette entité possède la FK
                if nav_prop.get('fk_field'):
                    related_key = self._get_related_model_key(nav_prop['type'])
                    nav_def["$ReferentialConstraint"] = {
                        nav_prop['fk_field']: related_key
                    }

                entity_type_def[nav_prop['name']] = nav_def

            namespace_def[model_name] = entity_type_def

        # Ajouter l'EntityContainer
        container_def = {
            "$Kind": "EntityContainer"
        }

        for model_name in sorted(self.models.keys()):
            # Utiliser le registry pour obtenir le nom d'entity set correct
            if model_name in model_to_entity_set:
                entity_set_name = model_to_entity_set[model_name]
            else:
                # Fallback: pluralisation simple
                entity_set_name = f"{model_name}s"

            entity_set_def = {
                "$Collection": True,
                "$Type": f"self.{model_name}"
            }

            # Ajouter les NavigationPropertyBindings
            entity = self.entity_types.get(model_name)
            if entity and entity['navigation_properties']:
                bindings = {}
                for nav_prop in entity['navigation_properties']:
                    related_model = nav_prop['type']
                    prop_name = nav_prop['name']

                    # Obtenir le nom du related entity set
                    related_entity_set = model_to_entity_set.get(related_model)
                    if not related_entity_set:
                        related_entity_set = f"{related_model}s"

                    bindings[prop_name] = related_entity_set

                if bindings:
                    entity_set_def["$NavigationPropertyBinding"] = bindings

            container_def[entity_set_name] = entity_set_def

        namespace_def[self.service_name] = container_def

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

            # Ajouter l'attribut Computed pour les @property
            if field.get('is_property', False):
                attrs['Computed'] = 'true'

            ET.SubElement(entity_type, 'Property', attrs)

        # ...existing code...

        # Ajouter les NavigationProperty OData V4
        for nav_prop in entity['navigation_properties']:
            nav_attrs = {
                'Name': nav_prop['name'],
                'Type': f"{self.namespace}.{nav_prop['type']}"
            }

            # Ajouter Collection attribute si c'est une collection
            if nav_prop.get('is_collection', False):
                nav_attrs['Type'] = f"Collection({self.namespace}.{nav_prop['type']})"

            # Créer la reference Partner inverse
            related_model_name = nav_prop['type']
            fk_field = nav_prop['fk_field']

            # Essayer de trouver le partenaire inverse (reverse relationship)
            partner_name = self._find_partner_name(model_name, related_model_name, nav_prop['name'])
            if partner_name:
                nav_attrs['Partner'] = partner_name

            nav_prop_elem = ET.SubElement(entity_type, 'NavigationProperty', nav_attrs)

            # Ajouter ReferentialConstraint SEULEMENT si ce modèle possède la FK
            if fk_field:
                ref_constraint = ET.SubElement(nav_prop_elem, 'ReferentialConstraint')
                ref_constraint.set('Property', fk_field)
                ref_constraint.set('ReferencedProperty', self._get_related_model_key(related_model_name))



    def _add_entity_container(self, parent_element):
        """Ajouter le conteneur de service."""
        from my_app.views import ODATA_MODELS_REGISTRY

        container = ET.SubElement(
            parent_element,
            'EntityContainer',
            {'Name': self.service_name}
        )

        # Créer un mapping modèle -> entity_set_name depuis le registry
        model_to_entity_set = {}
        for entity_set_name, entry in ODATA_MODELS_REGISTRY.items():
            model_name = entry.__name__
            model_to_entity_set[model_name] = entity_set_name

        # Ajouter les jeux d'entités
        for model_name in sorted(self.models.keys()):
            # Utiliser le registry pour obtenir le nom d'entity set correct
            if model_name in model_to_entity_set:
                entity_set_name = model_to_entity_set[model_name]
            else:
                # Fallback: pluralisation simple
                entity_set_name = f"{model_name}s"

            entity_set = ET.SubElement(
                container,
                'EntitySet',
                {
                    'Name': entity_set_name,
                    'EntityType': f"{self.namespace}.{model_name}"
                }
            )

            # Ajouter les NavigationPropertyBinding
            entity = self.entity_types.get(model_name)
            if entity:
                for nav_prop in entity['navigation_properties']:
                    related_model = nav_prop['type']
                    prop_name = nav_prop['name']

                    # Obtenir le nom du related entity set
                    related_entity_set = model_to_entity_set.get(related_model)
                    if not related_entity_set:
                        related_entity_set = f"{related_model}s"

                    # Ajouter le binding
                    ET.SubElement(
                        entity_set,
                        'NavigationPropertyBinding',
                        {
                            'Path': prop_name,
                            'Target': related_entity_set
                        }
                    )


    def _prettify_xml(self, elem) -> str:
        """Formater le XML pour le rendre lisible."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _find_partner_name(self, model_name: str, related_model_name: str, fk_field_name: str):
        """
        Trouver le nom du partenaire inverse (reverse relationship).

        Ex: Si DprIndex a une FK vers Header, on cherche la relationship
        inverse de Header vers DprIndex
        """
        related_entity = self.entity_types.get(related_model_name)
        if not related_entity:
            return None

        # Chercher dans les navigation properties du modèle lié
        for nav_prop in related_entity['navigation_properties']:
            # Le partenaire devrait référencer le modèle courant
            if nav_prop['type'] == model_name:
                return nav_prop['name']

        return None

    def _get_related_model_key(self, model_name: str) -> str:
        """Retourner la clé primaire d'un modèle."""
        entity = self.entity_types.get(model_name)
        if entity and entity['key']:
            return entity['key']
        return 'id'

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
            'relationships_count': len(self.relationships),
            'models': {
                model_name: {
                    'properties': len(entity['fields']),
                    'navigation_properties': len(entity['navigation_properties']),
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
            default='Odata',
            help='Espace de noms pour les entités (défaut: Odata)'
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
            self.style.SUCCESS('[*] Generation du schema metadata OData...')
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
                self.style.SUCCESS(f'[OK] Metadata sauvegarde dans: {output_file}')
            )

            # Afficher le résumé
            summary = generator.get_summary()
            self.stdout.write(self.style.WARNING('\n[RESUME]:'))
            self.stdout.write(f"   - Modeles trouves: {summary['models_count']}")
            self.stdout.write(f"   - Types d'entites: {summary['entity_types_count']}")
            self.stdout.write(f"   - Relationships: {summary['relationships_count']}")

            self.stdout.write(self.style.WARNING('\n   Modeles:'))
            for model_name, info in summary['models'].items():
                self.stdout.write(
                    f"   - {model_name} ({info['app']}): "
                    f"{info['properties']} proprietes, {info['navigation_properties']} nav properties"
                )

            # Afficher le contenu si demandé
            if should_print:
                self.stdout.write(
                    self.style.WARNING('\n[SCHEMA]:\n')
                )
                self.stdout.write(metadata_content)

        except Exception as e:
            raise CommandError(
                self.style.ERROR(f'[ERREUR] Erreur lors de la generation: {str(e)}')
            )
