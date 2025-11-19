from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import ALL_FIELDS, SerializerMethodField
from django.db.models import ForeignKey, OneToOneField, ManyToManyField, ForeignObjectRel, Model

# Cache pour stocker les serializers générés et éviter les multiples créations
_serializer_cache = {}


def extract_properties(model: Model):
    """
    Extrait les @property d'une classe Django définie dans le modèle lui-même.
    Exclut les propriétés système/héritées de Django (pk, etc.)

    Returns:
        Dict avec les propriétés détectées: {nom_propriété: property_object}
    """
    properties = {}

    # Propriétés système Django à exclure
    django_system_properties = {'pk', '_state', '_meta'}

    # Récupérer le module du modèle pour vérifier que la propriété est définie dans ce modèle
    model_module = model.__module__
    model_dict = vars(model)  # Les attributs définis directement dans la classe

    for attr_name in model_dict.keys():
        # Ignorer les attributs privés et magiques
        if attr_name.startswith('_'):
            continue

        # Ignorer les propriétés système Django
        if attr_name in django_system_properties:
            continue

        try:
            attr = model_dict[attr_name]

            # Vérifier si c'est une propriété (property object)
            if isinstance(attr, property):
                properties[attr_name] = attr
        except (AttributeError, TypeError):
            # Ignorer les erreurs d'accès
            continue

    return properties


def generate_expandable_fields(model : Model):
    """
    Génère automatiquement les expandable_fields en analysant les relations du modèle.

    Parcourt tous les champs du modèle et identifie:
    - Les ForeignKey et OneToOneField (relations many-to-one et one-to-one)
    - Les ManyToManyField
    - Les relations inverses (reverse relations)

    Retourne un dictionnaire avec:
    - Clé: nom du champ
    - Valeur: tuple (serializer, config)

    Les serializers sont générés à la demande et mis en cache pour éviter la récursion.
    """
    expandable_fields = {}

    for field in model._meta.get_fields():
        field_name = field.name

        # Gérer les ForeignKey et OneToOneField
        if isinstance(field, (ForeignKey, OneToOneField)):
            related_model = field.remote_field.model
            # Générer le serializer du modèle relié
            serializer = generate_serializer(related_model)
            expandable_fields[field_name] = (serializer, {})

        # Gérer les ManyToManyField
        elif isinstance(field, ManyToManyField):
            related_model = field.remote_field.model
            # Générer le serializer du modèle relié
            serializer = generate_serializer(related_model)
            expandable_fields[field_name] = (serializer, {'many': True})

        # Gérer les relations inverses (reverse ForeignKey, OneToOne, ManyToMany)
        elif isinstance(field, ForeignObjectRel):
            related_model = field.related_model
            # Générer le serializer du modèle relié
            serializer = generate_serializer(related_model)

            # Pour les reverse ForeignKey et ManyToMany, on utilise 'many': True
            if field.one_to_one:
                expandable_fields[field_name] = (serializer, {})
            else:
                expandable_fields[field_name] = (serializer, {'many': True})

    return expandable_fields



def generate_serializer(model: Model):
    """
    Génère dynamiquement une classe de serializer pour un modèle donné.
    Inclut automatiquement:
    - Les expandable_fields détectés
    - Les @property du modèle comme champs read-only
    Utilise un cache pour éviter de créer plusieurs fois le même serializer
    et pour éviter les récursions infinies.
    """
    model_key = f"{model.__module__}.{model.__name__}"

    # Si le serializer existe en cache, le retourner directement
    if model_key in _serializer_cache:
        return _serializer_cache[model_key]

    serializer_name = f"{model.__name__}Serializer"

    # Extraire les @property du modèle
    properties = extract_properties(model)

    # Créer dynamiquement les SerializerMethodField pour chaque propriété
    serializer_fields = {}

    for prop_name in properties.keys():
        # Créer une fonction getter pour chaque propriété
        def make_getter(prop):
            def get_property(self, obj):
                return getattr(obj, prop, None)
            return get_property

        serializer_fields[f'get_{prop_name}'] = make_getter(prop_name)
        serializer_fields[prop_name] = SerializerMethodField(read_only=True)

    # Créer la classe Meta avec les champs
    meta_attrs = {
        'model': model,
        'fields': ALL_FIELDS,
        'expandable_fields': {}  # Vide pour l'instant
    }


    # Créer un serializer avec les champs de propriétés
    serializer = type(serializer_name, (FlexFieldsModelSerializer,), {
        'Meta': type('Meta', (), meta_attrs),
        **serializer_fields
    })

    # Mettre en cache IMMÉDIATEMENT
    _serializer_cache[model_key] = serializer

    # Maintenant générer les expandable_fields (qui peuvent appeler d'autres generate_serializer)
    expandable_fields = generate_expandable_fields(model)

    # Mettre à jour la Meta du serializer avec les expandable_fields
    serializer.Meta.expandable_fields = expandable_fields

    return serializer

