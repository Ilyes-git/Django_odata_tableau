from django.http import HttpResponse, JsonResponse
from django.views import View
from django.db.models import Q
from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
import importlib
import re
import operator
import json

from customaps.models import Folder, Map
from .models import Person, Car, Product
from .serializers import generate_serializer
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

ODATA_MODELS_REGISTRY = {
        'persons': Person,
        'cars': Car,
        'products': Product,
        'authors': Author,
        'books': Book,
        'ship_classes': ShipClass,
        'ports': Port,
        'organisations': Organisation,
        'roles': Role,
        'purposes': Purpose,
        'tasks': Task,
        'vessels': Vessel,
        'vessel_qualifications': VesselQualification,
        'vessel_purposes': VesselPurpose,
        'operational_parameters': OperationalParameter,
        'vessel_stake_holders': VesselStakeholder,
        'vessel_flag_mmsi_histories': VesselFlagMmsiHistory,
        'projects': Project,
        'vessel_project_histories': VesselProjectHistory,
        'maps': Map,
        'folders': Folder
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
        """Tokenize le filtre en conditions simples.
        Supporte deux syntaxes:
        1. Syntaxe fonctionnelle OData: startswith(field,'value'), endswith(field,'value'), contains(field,'value')
        2. Syntaxe infix: field eq 'value', field gt 25, etc.
        """
        tokens = []
        last_end = 0

        # Pattern pour les fonctions OData: startswith(field,'value'), endswith(...), contains(...)
        # Group 1: function name, Group 2: field name, Group 3: value
        function_pattern = r"(startswith|endswith|contains)\s*\(\s*(\w+)\s*,\s*'([^']*)'\s*\)"

        # Pattern pour les opérateurs infix: field op value
        # Group 4: field, Group 5: operator, Group 6-8: value (string/float/date)
        infix_pattern = r"(\w+)\s+(eq|ne|lt|le|gt|ge)\s+(?:'([^']*)'|(\d+(?:\.\d+)?)|(\d{4}-\d{2}-\d{2}))"

        # Combiner les deux patterns avec | pour alterner
        combined_pattern = f"{function_pattern}|{infix_pattern}"

        for match in re.finditer(combined_pattern, filter_str):
            # Obtenir le texte entre le dernier match et celui-ci
            between_text = filter_str[last_end:match.start()].strip()
            if between_text and between_text.lower() in ['and', 'or']:
                tokens.append(between_text.lower())

            # Vérifier quel pattern a matché
            if match.group(1):  # function_pattern matched (groups 1-3)
                op = match.group(1)  # startswith, endswith, contains
                field = match.group(2)
                value = match.group(3)
                tokens.append({
                    'field': field,
                    'op': op,
                    'value': value
                })
            else:  # infix_pattern matched (groups 4-8)
                field = match.group(4)
                op = match.group(5)

                # Déterminer la valeur
                if match.group(6) is not None:
                    value = match.group(6)  # string value
                elif match.group(7) is not None:
                    value = float(match.group(7)) if '.' in match.group(7) else int(match.group(7))  # numeric
                elif match.group(8) is not None:
                    value = match.group(8)  # date
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

                # Gérer le cas spécial de 'ne' (non-égal)
                if op == 'ne':
                    q = ~Q(**{f"{field}__exact": value})
                elif op in ODataFilterParser.OPERATORS:
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

        # Créer le wrapper OData pour parser les paramètres imbriqués
        # (important pour apply_nested_expand_filters qui en a besoin)
        if not hasattr(self.request, '_odata_wrapper'):
            self._create_odata_wrapper()

        # Appliquer l'optimisation des requêtes (select_related / prefetch_related)
        queryset = self.apply_query_optimization(queryset)

        # Appliquer les paramètres OData
        try:
            queryset = self.apply_odata_params(queryset)
        except ValueError:
            pass

        return queryset

    def _create_odata_wrapper(self):
        """Crée le wrapper OData pour parser les paramètres imbriqués"""
        # Import de la classe depuis get_serializer_context
        class ODataQueryParamsWrapper:
            """Wrapper qui traduit les paramètres OData en paramètres drf-flex-fields"""
            def __init__(self, request):
                self.request = request
                self.translated_params = self._translate_odata_params()

            def _parse_nested_expand(self, expand_str):
                """
                Parse la syntaxe OData nested: author($select=name,bio) ou author($filter=startswith(first_name,'A'))
                Retourne: 'author' avec les params imbriqués stockés
                Gère les parenthèses imbriquées
                """
                import re

                result = {}
                i = 0
                while i < len(expand_str):
                    # Find the next field name (starts with letter/underscore, contains word chars)
                    match = re.match(r'(\w+)', expand_str[i:])
                    if not match:
                        i += 1
                        continue

                    field_name = match.group(1)
                    i += len(field_name)

                    # Skip to next opening parenthesis
                    if i >= len(expand_str) or expand_str[i] != '(':
                        result[field_name] = {}
                        # Skip until comma or end
                        while i < len(expand_str) and expand_str[i] != ',':
                            i += 1
                        if i < len(expand_str):
                            i += 1  # Skip comma
                        continue

                    # We have an opening paren, now find matching closing paren
                    i += 1  # Skip opening paren
                    paren_count = 1
                    params_start = i

                    while i < len(expand_str) and paren_count > 0:
                        if expand_str[i] == '(':
                            paren_count += 1
                        elif expand_str[i] == ')':
                            paren_count -= 1
                        i += 1

                    params_str = expand_str[params_start:i-1]  # Exclude closing paren

                    # Now parse the params
                    nested_params = {}

                    # Extract $filter parameter (might contain functions with parens)
                    filter_match = re.search(r'\$filter=([^$]*?)(?=,\$|$)', params_str)
                    if filter_match:
                        filter_value = filter_match.group(1).strip()
                        filter_value = filter_value.rstrip(',').strip()
                        nested_params['filter'] = filter_value

                    # Extract $select parameter - can have multiple fields separated by comma
                    select_match = re.search(r'\$select=([^$]+?)(?=,\$|$)', params_str)
                    if select_match:
                        select_value = select_match.group(1).strip()
                        select_value = select_value.rstrip(',').strip()
                        nested_params['select'] = select_value

                    # Extract $expand parameter - need to handle nested parentheses
                    expand_match = re.search(r'\$expand=', params_str)
                    if expand_match:
                        expand_start = expand_match.end()
                        # Find the value for expand (handle nested parentheses)
                        j = expand_start
                        paren_depth = 0
                        while j < len(params_str):
                            if params_str[j] == '(':
                                paren_depth += 1
                            elif params_str[j] == ')':
                                paren_depth -= 1
                            elif params_str[j] == ',' and paren_depth == 0:
                                break
                            elif params_str[j] == '$' and paren_depth == 0:
                                break
                            j += 1
                        expand_value = params_str[expand_start:j].strip()
                        nested_params['expand'] = expand_value

                    result[field_name] = nested_params

                    # Skip comma if present
                    if i < len(expand_str) and expand_str[i] == ',':
                        i += 1

                return result

            def _translate_odata_params(self):
                """Translate OData params ($expand, $select) to drf-flex-fields params (expand, fields)"""
                translated = {}
                nested_expand_config = {}

                for key, value in self.request.GET.items():
                    if key == '$expand':
                        nested_config = self._parse_nested_expand(value)
                        nested_expand_config = nested_config
                        expand_fields = ','.join(nested_config.keys())
                        translated['expand'] = expand_fields

                    elif key == '$select':
                        translated['select'] = value
                    else:
                        translated[key] = value

                self.nested_expand_config = nested_expand_config
                return translated

            def __getattr__(self, name):
                """Déléguer à la request originale"""
                return getattr(self.request, name)

            @property
            def query_params(self):
                """Retourner les params traduits"""
                class QueryParamsProxy:
                    def __init__(self, params, nested_config=None):
                        self.params = params
                        self.nested_config = nested_config or {}

                    def get(self, key, default=None):
                        return self.params.get(key, default)

                    def getlist(self, key):
                        value = self.params.get(key, '')
                        if value:
                            return value.split(',') if isinstance(value, str) else [value]
                        return []

                    def get_nested_config(self, field):
                        return self.nested_config.get(field, {})

                return QueryParamsProxy(self.translated_params, self.nested_expand_config)

        wrapper = ODataQueryParamsWrapper(self.request)
        self.request._odata_wrapper = wrapper


    def apply_query_optimization(self, queryset):
        """
        Optimise automatiquement les requêtes en utilisant select_related et prefetch_related
        basé sur le paramètre $expand pour éviter le problème N+1
        """
        expand_param = self.request.GET.get("$expand", "")
        if not expand_param:
            return queryset

        # Parser les champs à expand (même format que dans get_serializer_context)
        import re

        # Pattern: fieldname($param1=value1,$param2=value2)
        pattern = r'(\w+)\(([^)]+)\)'
        expand_fields = set()

        # Extraire les champs entre parenthèses
        for match in re.finditer(pattern, expand_param):
            expand_fields.add(match.group(1))

        # Extraire aussi les champs simples sans parenthèses
        simple_expand = re.sub(pattern, '', expand_param)
        for field in simple_expand.split(','):
            field = field.strip()
            if field:
                expand_fields.add(field)

        # Analyser le modèle pour déterminer quels champs sont des ForeignKey/OneToOne (select_related)
        # et quels sont des reverse relations (prefetch_related)
        model = self.get_registry_entry()
        if not model:
            return queryset

        select_related_fields = []
        prefetch_related_fields = []

        for field_name in expand_fields:
            try:
                field = model._meta.get_field(field_name)

                # ForeignKey et OneToOneField: utiliser select_related
                if hasattr(field, 'many_to_one') and field.many_to_one:
                    select_related_fields.append(field_name)
                elif hasattr(field, 'one_to_one') and field.one_to_one:
                    select_related_fields.append(field_name)
                # ManyToMany et autres: utiliser prefetch_related
                else:
                    prefetch_related_fields.append(field_name)
            except Exception:
                # Si get_field échoue, essayer comme reverse relation
                # mais seulement si c'est un nom de related_name valide
                try:
                    # Vérifions si c'est une reverse relation en accédant au related object
                    rel = getattr(model, field_name, None)
                    if rel and hasattr(rel, 'field'):
                        # C'est probablement une relation valide
                        prefetch_related_fields.append(field_name)
                    # Sinon on ignore silencieusement
                except Exception:
                    # Ignorer les champs invalides
                    pass

        # Appliquer les optimisations
        try:
            if select_related_fields:
                queryset = queryset.select_related(*select_related_fields)

            if prefetch_related_fields:
                queryset = queryset.prefetch_related(*prefetch_related_fields)
        except Exception:
            # Si l'optimisation échoue (champ invalide), retourner le queryset non optimisé
            pass

        return queryset

    def get_serializer_context(self):
        """Ajouter les paramètres OData au contexte du serializer pour drf-flex-fields"""
        context = super().get_serializer_context()

        # Utiliser le wrapper OData déjà créé dans get_queryset()
        if hasattr(self.request, '_odata_wrapper'):
            context['request'] = self.request._odata_wrapper
            return context

        # Fallback: créer le wrapper si ce n'est pas fait
        self._create_odata_wrapper()
        context['request'] = self.request._odata_wrapper
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
            # Si le serializer n'est pas trouvé, le créer dynamiquement
            # avec les expandable_fields générés automatiquement
            serializer_class = generate_serializer(entry)
            return serializer_class
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

        # Appliquer les filtres imbriqués de $expand
        queryset = self.apply_nested_expand_filters(queryset)

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

    def apply_nested_expand_filters(self, queryset):
        """
        Applique les filtres imbriqués de $expand au niveau du queryset.
        Par exemple: $expand=owner($filter=first_name eq 'John')
        va filtrer le queryset pour retourner seulement les items dont le owner match le filtre.
        """
        expand_param = self.request.GET.get("$expand", "")
        if not expand_param:
            return queryset

        # Parser les paramètres imbriqués depuis le wrapper OData
        nested_config = {}
        if hasattr(self.request, '_odata_wrapper') and hasattr(self.request._odata_wrapper, 'nested_expand_config'):
            nested_config = self.request._odata_wrapper.nested_expand_config

        if not nested_config:
            return queryset

        # Pour chaque champ avec un filtre imbriqué
        for field_name, nested_params in nested_config.items():
            if 'filter' not in nested_params:
                continue

            filter_str = nested_params['filter']

            # Récupérer le modèle actuel et le modèle de la relation
            model = self.get_registry_entry()
            if not model:
                continue

            try:
                # Récupérer le modèle de la relation
                try:
                    field = model._meta.get_field(field_name)
                    related_model = field.related_model
                except Exception as e:
                    # Si on ne trouve pas le champ, on ignore
                    continue

                # Parser le filtre OData sur le modèle de la relation
                filter_q = ODataFilterParser.parse_filter(filter_str, related_model)

                # Construire les conditions préfixées avec le nom du champ
                # Transformer la Q object pour ajouter le préfixe
                prefixed_q = self._prefix_q_object(filter_q, field_name)

                # Appliquer le filtre sur la relation imbriquée
                queryset = queryset.filter(prefixed_q)
            except Exception as e:
                # Si le filtre imbriqué échoue, continuer sans le filtrer
                pass

        return queryset

    def _prefix_q_object(self, q_obj, prefix):
        """
        Ajoute un préfixe à tous les lookups dans une Q object.
        Par exemple: Q(first_name='John') devient Q(owner__first_name='John')
        """
        if not q_obj:
            return q_obj

        # Créer une nouvelle Q object avec les lookups préfixés
        new_children = []
        for child in q_obj.children:
            if isinstance(child, tuple):
                # C'est un tuple (key, value)
                key, value = child
                new_key = f"{prefix}__{key}"
                new_children.append((new_key, value))
            elif isinstance(child, Q):
                # C'est une Q object imbriquée - appeler récursivement
                new_children.append(self._prefix_q_object(child, prefix))
            else:
                # Autrement, le garder tel quel
                new_children.append(child)

        # Créer une nouvelle Q object avec les enfants modifiés
        new_q = Q()
        new_q.children = new_children
        new_q.connector = q_obj.connector
        new_q.negated = q_obj.negated
        return new_q


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

    def apply_nested_select(self, data, nested_expand_config):
        """
        Applique les paramètres $select imbriqués pour les champs expandés.
        Par exemple: $expand=parent($select=id) affectera le parent développé.

        nested_expand_config est un dictionnaire de format:
        {
            'parent': {'select': 'id'},
            'subfolders': {'select': 'id,name'}
        }
        """
        if not nested_expand_config or not isinstance(data, list):
            return data

        result = []
        for item in data:
            if not isinstance(item, dict):
                result.append(item)
                continue

            # Copier l'item
            processed_item = dict(item)

            # Pour chaque champ qui a une configuration imbriquée
            for field_name, nested_config in nested_expand_config.items():
                if field_name not in processed_item:
                    continue

                field_value = processed_item[field_name]

                # Si le champ contient un select imbriqué
                if 'select' in nested_config and nested_config['select']:
                    select_fields = [f.strip() for f in nested_config['select'].split(',')]

                    # Cas 1: La valeur est un objet (relation one-to-one)
                    if isinstance(field_value, dict):
                        filtered_obj = {
                            k: v for k, v in field_value.items()
                            if k in select_fields or k.startswith('@')
                        }
                        processed_item[field_name] = filtered_obj

                    # Cas 2: La valeur est une liste (relation many-to-many ou one-to-many)
                    elif isinstance(field_value, list):
                        filtered_list = []
                        for obj in field_value:
                            if isinstance(obj, dict):
                                filtered_obj = {
                                    k: v for k, v in obj.items()
                                    if k in select_fields or k.startswith('@')
                                }
                                filtered_list.append(filtered_obj)
                            else:
                                filtered_list.append(obj)
                        processed_item[field_name] = filtered_list

            result.append(processed_item)

        return result


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

            # Appliquer les $select imbriqués (nested select dans $expand)
            # Récupérer la configuration imbriquée depuis le wrapper OData
            nested_config = {}
            if hasattr(self.request, '_odata_wrapper') and hasattr(self.request._odata_wrapper, 'nested_expand_config'):
                nested_config = self.request._odata_wrapper.nested_expand_config
            data = self.apply_nested_select(data, nested_config)

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
