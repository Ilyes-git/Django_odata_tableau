from django.http import HttpResponse, JsonResponse
from django.views import View
from django.db.models import Q, Model
from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from typing import Dict, Type
import importlib
import re
import operator
import json

from .models import Person, Car, Product
from .management.commands.generate_odata_metadata import ODataMetadataGenerator
from second_app.models import Author, Book
from vessel.models import (
    ShipClass,
    Port,
    Organisation,
    Role,
    Purpose,
    Task,
    Vessel,
    VesselQualification,
    VesselPurpose,
    OperationalParameter,
    VesselStakeholder,
    VesselFlagMmsiHistory,
    Project,
    VesselProjectHistory,
)

def _build_odata_registry() -> Dict[str, Type[Model]]:
    """
    Construire le registry OData en chargeant les modèles dynamiquement.

    Registry : Dictionnaire mappant les noms des entity sets OData aux classes modèles Django.
    Format : {
        'EntitySetName' : ModelClass,
        'Persons' : Person,
        'Cars' : Car…,

        }

    Returns :

        Dict[str, Type[Model]] : Dictionnaire des entity sets OData avec leurs modèles associés
    """


    return {
        'Persons': Person,
        'Cars': Car,
        'Products': Product,
        'Authors': Author,
        'Books': Book,
        'ShipClasses': ShipClass,
        'Ports': Port,
        'Organisations': Organisation,
        'Roles': Role,
        'Purposes': Purpose,
        'Tasks': Task,
        'Vessels': Vessel,
        'VesselQualifications': VesselQualification,
        'VesselPurposes': VesselPurpose,
        'OperationalParameters': OperationalParameter,
        'VesselStakeholders': VesselStakeholder,
        'VesselFlagMmsiHistories': VesselFlagMmsiHistory,
        'Projects': Project,
        'VesselProjectHistories': VesselProjectHistory,
    }


ODATA_MODELS_REGISTRY = _build_odata_registry()



class ODataFilterParser:
    """Parser les filtres OData et les convertit en requêtes Django Q."""

    # Opérateurs de comparaison OData
    OPERATORS = {
        'eq': operator.eq,
        'ne': operator.ne,
        'lt': operator.lt,
        'le': operator.le,
        'gt': operator.gt,
        'ge': operator.ge,
    }

    @staticmethod
    def parse_filter(filter_str, model):
        """
        Parse un filtre OData et retourne un objet Q Django.
        Exemples:
            - first_name eq 'John'
            - age gt 25 and birth_date lt 2000-01-01
            - brand eq 'BMW' or brand eq 'Audi'
        """
        if not filter_str:
            return Q()

        try:
            conditions = ODataFilterParser._tokenize_filter(filter_str)
            return ODataFilterParser._build_q_object(conditions, model)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du filtre: {str(e)}")

    @staticmethod
    def _tokenize_filter(filter_str):
        """Tokenize le filtre en conditions simples."""
        pattern = r"(\w+)\s+(eq|ne|lt|le|gt|ge|startswith|endswith|contains)\s+(?:'([^']*)'|(\d+(?:\.\d+)?)|(\d{4}-\d{2}-\d{2}))"

        tokens = []
        last_end = 0

        for match in re.finditer(pattern, filter_str):
            between_text = filter_str[last_end:match.start()].strip()
            if between_text and between_text.lower() in ['and', 'or']:
                tokens.append(between_text.lower())

            field = match.group(1)
            op = match.group(2)

            if match.group(3) is not None:
                value = match.group(3)
            elif match.group(4) is not None:
                value = float(match.group(4)) if '.' in match.group(4) else int(match.group(4))
            elif match.group(5) is not None:
                value = match.group(5)
            else:
                continue

            tokens.append({
                'field': field,
                'op': op,
                'value': value
            })

            last_end = match.end()

        return tokens

    @staticmethod
    def _build_q_object(tokens, model):
        """Construit un objet Q à partir des tokens."""
        q_objects = []
        current_op = 'and'

        for token in tokens:
            if isinstance(token, str):
                current_op = token
            elif isinstance(token, dict):
                field = token['field']
                op = token['op']
                value = token['value']

                if op in ODataFilterParser.OPERATORS:
                    q = Q(**{f"{field}__{ODataFilterParser._map_operator(op)}": value})
                elif op == 'startswith':
                    q = Q(**{f"{field}__istartswith": value})
                elif op == 'endswith':
                    q = Q(**{f"{field}__iendswith": value})
                elif op == 'contains':
                    q = Q(**{f"{field}__icontains": value})
                else:
                    q = Q()

                if current_op == 'or':
                    q_objects.append(('or', q))
                else:
                    q_objects.append(('and', q))

        if not q_objects:
            return Q()

        result = q_objects[0][1]
        for op, q in q_objects[1:]:
            if op == 'or':
                result = result | q
            else:
                result = result & q

        return result

    @staticmethod
    def _map_operator(op):
        """Mappe les opérateurs OData aux lookups Django."""
        mapping = {
            'eq': 'exact',
            'ne': 'ne',
            'lt': 'lt',
            'le': 'lte',
            'gt': 'gt',
            'ge': 'gte',
        }
        return mapping.get(op, 'exact')


class ODataModelViewSet(ModelViewSet):
    """ViewSet générique dynamique pour OData - s'adapte au registry"""

    # Seront définis dynamiquement
    queryset = None
    serializer_class = None
    entity_set_name = None
    _expand_fields = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expand_fields = {}

    def get_registry_entry(self):
        """Récupère l'entry du registry pour cet entity set"""
        return ODATA_MODELS_REGISTRY.get(self.entity_set_name)

    def get_queryset(self):
        """Retourner le queryset avec les paramètres OData appliqués"""
        entry = self.get_registry_entry()
        if not entry:
            return entry.objects.none()

        queryset = entry.objects.all()

        # Appliquer les paramètres OData
        try:
            queryset = self.apply_odata_params(queryset)
        except ValueError:
            pass

        return queryset

    def get_serializer_context(self):
        """Ajouter les paramètres OData au contexte du serializer pour drf-flex-fields"""
        context = super().get_serializer_context()

        # Traduire les paramètres OData en paramètres drf-flex-fields
        # drf-flex-fields lit automatiquement 'expand' et 'fields' depuis les query_params
        # Donc on va créer une vue spéciale de la request avec les params traduits

        # Créer une wrapper autour de la request pour traduire les paramètres à la volée
        class ODataQueryParamsWrapper:
            """Wrapper qui traduit les paramètres OData en paramètres drf-flex-fields"""
            def __init__(self, request):
                self.request = request
                self.translated_params = self._translate_odata_params()

            def _translate_odata_params(self):
                """Translate OData params ($expand) to drf-flex-fields params (expand)"""
                translated = {}
                for key, value in self.request.GET.items():
                    if key == '$expand':
                        translated['expand'] = value
                    elif key == '$select':
                        translated['select'] = value
                    else:
                        translated[key] = value
                return translated

            def __getattr__(self, name):
                """Déléguer à la request originale"""
                return getattr(self.request, name)

            @property
            def query_params(self):
                """Retourner les params traduits comme drf-flex-fields les attend"""
                # Créer un QueryDict-like object
                class QueryParamsProxy:
                    def __init__(self, params):
                        self.params = params

                    def get(self, key, default=None):
                        return self.params.get(key, default)

                    def getlist(self, key):
                        value = self.params.get(key, '')
                        if value:
                            return value.split(',') if isinstance(value, str) else [value]
                        return []

                return QueryParamsProxy(self.translated_params)

        # Remplacer la request dans le contexte par notre wrapper
        context['request'] = ODataQueryParamsWrapper(context['request'])

        return context

    def get_serializer_class(self):
        """Récupère le serializer depuis le registry en utilisant la convention de nommage"""
        entry = self.get_registry_entry()
        if entry:
            serializer_name = f"{entry.__name__}Serializer"
            serializer_modules = []
            for app in settings.INSTALLED_APPS:
                try:
                    module = importlib.import_module(f"{app}.serializers")
                    serializer_modules.append(module)
                except ImportError:
                    continue
            for module in serializer_modules:
                if hasattr(module, serializer_name):
                    return getattr(module, serializer_name)
            raise ValueError(f"Serializer '{serializer_name}' non trouvé pour le modèle '{entry.__name__}'")
        return self.serializer_class

    def apply_odata_params(self, queryset):
        """Applique les paramètres OData ($filter, $orderby, $skip, $top)"""
        entry = self.get_registry_entry()
        if not entry:
            raise ValueError(f"Entity set '{self.entity_set_name}' non enregistré")

        model = entry

        # $filter
        filter_param = self.request.GET.get("$filter", "")
        if filter_param:
            try:
                filter_q = ODataFilterParser.parse_filter(filter_param, model)
                queryset = queryset.filter(filter_q)
            except Exception as e:
                raise ValueError(f"Filtre invalide: {str(e)}")

        # $orderby
        orderby_param = self.request.GET.get("$orderby", "")
        if orderby_param:
            order_fields = []
            for field_spec in orderby_param.split(','):
                parts = field_spec.strip().split()
                field = parts[0]
                direction = parts[1].lower() if len(parts) > 1 else 'asc'
                if direction == 'desc':
                    order_fields.append(f"-{field}")
                else:
                    order_fields.append(field)
            if order_fields:
                queryset = queryset.order_by(*order_fields)

        return queryset

    def paginate_queryset(self, queryset):
        """Gère la pagination avec $skip et $top"""
        skip = int(self.request.GET.get("$skip", 0))
        top = int(self.request.GET.get("$top", 50))

        if skip > 0:
            queryset = queryset[skip:]
        if top > 0:
            queryset = queryset[:top]

        return queryset

    def apply_select(self, data):
        """Applique le paramètre $select pour filtrer les colonnes"""
        select_param = self.request.GET.get("$select", "")
        if not select_param or not isinstance(data, list):
            return data

        fields = [f.strip() for f in select_param.split(',')]
        selected_data = []
        for item in data:
            selected_item = {k: v for k, v in item.items() if k in fields or k.startswith('@')}
            selected_data.append(selected_item)
        return selected_data

    def list(self, request, *args, **kwargs):
        """GET /EntitySet - Liste avec support OData ($filter, $orderby, $skip, $top, $select, $expand)"""
        try:
            queryset = self.get_queryset()
            total_count = queryset.count()

            # Appliquer la pagination
            queryset = self.paginate_queryset(queryset)

            # Créer le serializer avec le contexte contenant expand et select
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            # Appliquer $select pour filtrer les colonnes (si pas géré par le serializer)
            data = self.apply_select(data)

            # Ajouter métadonnées OData
            entry = self.get_registry_entry()
            odata_type = f"#Odata.{entry.__name__}" if entry else None
            for item in data:
                if isinstance(item, dict) and odata_type:
                    item["@odata.type"] = odata_type

            # Formater réponse OData
            base_url = request.build_absolute_uri("/odata")
            response_data = {
                "value": data,
                "@odata.context": f"{base_url}/$metadata#{self.entity_set_name}",
                "@odata.count": total_count
            }

            return Response(response_data)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=400)
        except Exception as e:
            return Response({"error": f"Erreur lors de la lecture: {str(e)}"}, status=500)

    def retrieve(self, request, *args, **kwargs):
        """GET /EntitySet(id) - Entité spécifique avec support $expand et $select"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data


            # Ajouter métadonnées OData
            entry = self.get_registry_entry()
            if isinstance(data, dict):
                data["@odata.type"] = f"#Odata.{entry.__name__}" if entry else None
                base_url = request.build_absolute_uri("/odata")
                data["@odata.context"] = f"{base_url}/$metadata#{self.entity_set_name}('{kwargs.get('pk')}')"

            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.path.startswith("/odata/"):
            response["OData-Version"] = "4.0"
        return response


class ODataServiceDocumentView(View):
    """Service document générique qui expose tous les entity sets enregistrés"""

    def get(self, request, *args, **kwargs):
        """Retourner le service document OData"""
        try:
            base_url = request.build_absolute_uri("/odata/").rstrip("/")

            entity_sets = []
            for entity_set_name, entry in ODATA_MODELS_REGISTRY.items():
                entity_sets.append({
                    "name": entity_set_name,
                    "kind": "EntitySet",
                    "url": entity_set_name
                })

            response_data = {
                "@odata.context": f"{base_url}/$metadata",
                "value": entity_sets
            }

            response = JsonResponse(
                response_data,
                json_dumps_params={"ensure_ascii": False},
            )
            response["Content-Type"] = (
                "application/json;odata.metadata=minimal;"
                "odata.streaming=true;IEEE754Compatible=false;charset=utf-8"
            )
            response["OData-Version"] = "4.0"
            return response
        except Exception as e:
            response = JsonResponse(
                {"error": str(e)},
                status=500
            )
            response["OData-Version"] = "4.0"
            return response


class ODataMetadataEndpoint(View):
    """Endpoint pour exposer le schéma metadata OData."""

    def get(self, request, *args, **kwargs):
        """Générer et retourner le schéma metadata EDMX OData v4."""
        try:
            output_format = request.GET.get('format', 'xml').lower()

            if output_format not in ['xml', 'json']:
                output_format = 'xml'

            generator = ODataMetadataGenerator(
                namespace="Odata",
                service_name="Container",
                include_auth=False
            )

            metadata_content = generator.generate(output_format=output_format)

            if output_format == 'json':
                response = JsonResponse(
                    generator.entity_types,
                    status=200,
                    safe=False
                )
                response['Content-Type'] = 'application/json;charset=utf-8'
                response["OData-Version"] = "4.0"
            else:
                response = HttpResponse(metadata_content, content_type='application/xml')
                response["OData-Version"] = "4.0"

            return response

        except Exception as e:
            response = JsonResponse(
                {
                    'error': 'Erreur lors de la génération du metadata',
                    'detail': str(e)
                },
                status=500
            )
            response["OData-Version"] = "4.0"
            return response


class ODataMetadataJsonEndpoint(View):
    """Endpoint pour exposer le schéma metadata en format JSON."""

    def get(self, request, *args, **kwargs):
        """Retourner le schéma metadata au format JSON."""
        try:
            generator = ODataMetadataGenerator(
                namespace="Odata",
                service_name="Container",
                include_auth=False
            )

            metadata_content = generator.generate(output_format='json')
            metadata_dict = json.loads(metadata_content)

            response = JsonResponse(metadata_dict, status=200)
            response['Content-Type'] = 'application/json;charset=utf-8'
            response["OData-Version"] = "4.0"

            return response

        except Exception as e:
            response = JsonResponse(
                {
                    'error': 'Erreur lors de la génération du metadata',
                    'detail': str(e)
                },
                status=500
            )
            response["OData-Version"] = "4.0"
            return response
