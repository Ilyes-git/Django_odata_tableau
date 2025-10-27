from django.http import HttpResponse, JsonResponse
from django.views import View
from django.db.models import Q
from .models import Person, Car, Product
from .serializers import PersonSerializer, CarSerializer, ProductSerializer
from .management.commands.generate_odata_metadata import ODataMetadataGenerator
import re
import operator


ODATA_MODELS_REGISTRY = {
    'Persons': {
        'model': Person,
        'serializer': PersonSerializer,
        'display_name': 'Persons',
    },
    'Cars': {
        'model': Car,
        'serializer': CarSerializer,
        'display_name': 'Cars',
    },
    'Products': {
        'model': Product,
        'serializer': ProductSerializer,
        'display_name': 'Products',
    }
}

def register_odata_model(entity_set_name, model, serializer, display_name=None):
    """Enregistre un model pour OData"""
    ODATA_MODELS_REGISTRY[entity_set_name] = {
        'model': model,
        'serializer': serializer,
        'display_name': display_name or entity_set_name,
    }


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

    # Fonctions de chaîne OData
    STRING_FUNCTIONS = ['startswith', 'endswith', 'contains', 'toupper', 'tolower', 'length']

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
            # Séparer les conditions par 'and' et 'or'
            conditions = ODataFilterParser._tokenize_filter(filter_str)
            return ODataFilterParser._build_q_object(conditions, model)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du filtre: {str(e)}")

    @staticmethod
    def _tokenize_filter(filter_str):
        """Tokenize le filtre en conditions simples."""
        # Améliorer le pattern pour capturer tous les cas
        # Pattern unique: field operator value
        pattern = r"(\w+)\s+(eq|ne|lt|le|gt|ge|startswith|endswith|contains)\s+(?:'([^']*)'|(\d+(?:\.\d+)?)|(\d{4}-\d{2}-\d{2}))"

        tokens = []
        last_end = 0

        for match in re.finditer(pattern, filter_str):
            # Ajouter les opérateurs logiques avant cette condition
            between_text = filter_str[last_end:match.start()].strip()
            if between_text and between_text.lower() in ['and', 'or']:
                tokens.append(between_text.lower())

            # Extraire la condition
            field = match.group(1)
            op = match.group(2)

            # La valeur peut être une chaîne (groupe 3), un nombre (groupe 4), ou une date (groupe 5)
            if match.group(3) is not None:  # String value
                value = match.group(3)
            elif match.group(4) is not None:  # Number value
                value = float(match.group(4)) if '.' in match.group(4) else int(match.group(4))
            elif match.group(5) is not None:  # Date value
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
            if isinstance(token, str):  # Opérateur logique
                current_op = token
            elif isinstance(token, dict):  # Condition
                field = token['field']
                op = token['op']
                value = token['value']

                # Construire la requête Django
                if op in ODataFilterParser.OPERATORS:
                    # Opérateurs de comparaison simples
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

        # Fusionner les conditions
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
            'ne': 'ne',  # Géré avec ~Q
            'lt': 'lt',
            'le': 'lte',
            'gt': 'gt',
            'ge': 'gte',
        }
        return mapping.get(op, 'exact')


class GenericODataView(View):
    """Vue générique pour OData — supporte n'importe quel model"""

    def get_registry_entry(self, entity_set_name):
        """Récupère l'entry du registry pour un entity set"""
        return ODATA_MODELS_REGISTRY.get(entity_set_name)

    def get_odata_json_response(self, data, entity_set_name, context_url=None, count=None):
        """Formater une réponse au format OData JSON avec métadonnées complètes."""
        # Obtenir le type OData depuis le registry
        entry = self.get_registry_entry(entity_set_name)
        odata_type = f"#DjangoOData.{entry['model'].__name__}" if entry else None

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and odata_type:
                    item["@odata.type"] = odata_type
        else:
            if isinstance(data, dict) and odata_type:
                data["@odata.type"] = odata_type

        if isinstance(data, list):
            response_data = {"value": data}
        else:
            response_data = data

        if context_url:
            response_data["@odata.context"] = context_url

        if count is not None:
            response_data["@odata.count"] = count

        return response_data

    def apply_odata_params(self, queryset, entity_set_name):
        """Applique les paramètres OData ($filter, $orderby, $skip, $top, $select)."""
        entry = self.get_registry_entry(entity_set_name)
        if not entry:
            raise ValueError(f"Entity set '{entity_set_name}' non enregistré")

        model = entry['model']

        # $filter
        filter_param = self.request.GET.get("$filter", "")
        if filter_param:
            try:
                filter_q = ODataFilterParser.parse_filter(filter_param, model)
                queryset = queryset.filter(filter_q)
            except Exception as e:
                raise ValueError(f"Filtre invalide: {str(e)}")

        # $orderby (comma-separated: field asc, field2 desc)
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

        # Total count avant pagination
        total_count = queryset.count()

        # $skip et $top
        skip = int(self.request.GET.get("$skip", 0))
        top = int(self.request.GET.get("$top", 50))

        if skip > 0:
            queryset = queryset[skip:]
        if top > 0:
            queryset = queryset[:top]

        return queryset, total_count

    def apply_select(self, data, select_param):
        """Applique le paramètre $select pour filtrer les colonnes."""
        if not select_param or not isinstance(data, list):
            return data

        fields = [f.strip() for f in select_param.split(',')]
        selected_data = []
        for item in data:
            selected_item = {k: v for k, v in item.items() if k in fields or k.startswith('@')}
            selected_data.append(selected_item)
        return selected_data


class ODataEntitySetView(GenericODataView):
    """Vue générique pour un entity set spécifique (collections et détails)"""

    def get(self, request, entity_set_name, pk=None, *args, **kwargs):
        """GET /EntitySet ou GET /EntitySet(id)"""
        try:
            self.request = request
            entry = self.get_registry_entry(entity_set_name)

            if not entry:
                return JsonResponse(
                    {"error": f"Entity set '{entity_set_name}' non trouvé"},
                    status=404
                )

            model = entry['model']
            serializer_class = entry['serializer']

            # GET d'une entité spécifique
            if pk is not None:
                try:
                    obj = model.objects.get(pk=pk)
                    serializer = serializer_class(obj)
                    data = serializer.data

                    base_url = request.build_absolute_uri("/odata")
                    response_data = self.get_odata_json_response(
                        data,
                        entity_set_name,
                        context_url=f"{base_url}/$metadata#{entity_set_name}('{pk}')"
                    )
                except model.DoesNotExist:
                    return JsonResponse(
                        {"error": f"{model.__name__} avec ID {pk} non trouvée"},
                        status=404
                    )
            else:
                # GET de la liste
                queryset, total_count = self.apply_odata_params(model.objects.all(), entity_set_name)
                serializer = serializer_class(queryset, many=True)
                data = serializer.data

                # Appliquer $select
                select_param = request.GET.get("$select", "")
                if select_param:
                    data = self.apply_select(data, select_param)

                base_url = request.build_absolute_uri("/odata")
                response_data = self.get_odata_json_response(
                    data,
                    entity_set_name,
                    context_url=f"{base_url}/$metadata#{entity_set_name}",
                    count=total_count
                )

            response = JsonResponse(response_data)
            response["Content-Type"] = "application/json;odata.metadata=minimal;charset=utf-8"
            return response

        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse(
                {"error": f"Erreur lors de la lecture: {str(e)}"},
                status=500
            )


class ODataMetadataEndpoint(View):
    """
    Endpoint pour exposer le schéma metadata OData.
    Accessible via GET /odata/$metadata
    """

    def get(self, request, *args, **kwargs):
        """
        Générer et retourner le schéma metadata EDMX OData v4.

        Paramètres query optionnels:
            format: 'xml' (défaut) ou 'json'
        """
        try:
            output_format = request.GET.get('format', 'xml').lower()

            # Valider le format
            if output_format not in ['xml', 'json']:
                output_format = 'xml'

            # Créer le générateur
            generator = ODataMetadataGenerator(
                namespace="DjangoOData",
                service_name="Container",
                include_auth=False
            )

            # Générer le metadata
            metadata_content = generator.generate(output_format=output_format)

            # Retourner la réponse avec le bon Content-Type
            if output_format == 'json':
                response = JsonResponse(
                    generator.entity_types,  # Retourner aussi un résumé JSON
                    status=200,
                    safe=False
                )
                response['Content-Type'] = 'application/json;charset=utf-8'
            else:
                response = HttpResponse(metadata_content, content_type='application/xml')

            return response

        except Exception as e:
            return JsonResponse(
                {
                    'error': 'Erreur lors de la génération du metadata',
                    'detail': str(e)
                },
                status=500
            )


class ODataMetadataJsonEndpoint(View):
    """
    Endpoint pour exposer le schéma metadata en format JSON.
    Accessible via GET /odata/$metadata/json
    """

    def get(self, request, *args, **kwargs):
        """Retourner le schéma metadata au format JSON."""
        try:
            # Créer le générateur
            generator = ODataMetadataGenerator(
                namespace="DjangoOData",
                service_name="Container",
                include_auth=False
            )

            # Générer le metadata
            metadata_content = generator.generate(output_format='json')

            # Parser le JSON et le retourner
            import json
            metadata_dict = json.loads(metadata_content)

            response = JsonResponse(metadata_dict, status=200)
            response['Content-Type'] = 'application/json;charset=utf-8'

            return response

        except Exception as e:
            return JsonResponse(
                {
                    'error': 'Erreur lors de la génération du metadata',
                    'detail': str(e)
                },
                status=500
            )


class ODataServiceDocumentView(View):
    """Service document générique qui expose tous les entity sets enregistrés"""

    def get(self, request, *args, **kwargs):
        """Retourner le service document OData"""
        try:
            base_url = request.build_absolute_uri("/odata/").rstrip("/")

            # Générer la liste des entity sets depuis le registry
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
            return response
        except Exception as e:
            return JsonResponse(
                {"error": str(e)},
                status=500
            )


