from django.apps import apps
import inflection


def model_to_endpoint(model_name: str) -> str:
    """
    Convert model name to a PascalCase pluralized endpoint.
    Example: Person -> People, Car -> Cars, VesselQualification -> VesselQualifications
    """
    # Pluraliser le nom du modèle directement (garde le PascalCase)
    return inflection.pluralize(model_name)


def get_dynamic_odata_registry(
        include_apps=None,
        exclude_apps=None,
        exclude_models=(),
        custom_viewsets=None,
):
    """
    Build a dynamic OData registry mapping API endpoints to Django model classes.

    Rules:
    - Convert model names to PascalCase plural.
    - Exclude Django internal apps by default.
    """

    include_apps = set(include_apps or [])
    exclude_apps = set(exclude_apps or {"admin", "auth", "sessions", "contenttypes"})
    exclude_models = exclude_models
    custom_viewsets = custom_viewsets or {}

    registry = {}
    apps_map = {}

    for model in apps.get_models():
        opts = model._meta

        # Skip excluded apps
        if opts.app_label in exclude_apps:
            continue

        # Skip if include_apps is defined and the app is not in it
        if include_apps and opts.app_label not in include_apps:
            continue

        # Skip excluded models by name
        if opts.model_name in exclude_models or model.__name__ in exclude_models:
            continue

        # Generate endpoint
        endpoint = model_to_endpoint(model.__name__)

        # Vérifier si un custom viewset est défini pour ce modèle
        if model.__name__ in custom_viewsets:
            registry[endpoint] = {
                'model': model,
                'viewset': custom_viewsets[model.__name__]
            }
        else:
            registry[endpoint] = model

        # --- Build apps grouping
        apps_map.setdefault(opts.app_label, []).append(model)

    return registry, apps_map
