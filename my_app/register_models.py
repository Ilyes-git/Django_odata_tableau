from django.apps import apps
import inflection


def model_to_endpoint(model_name: str) -> str:
    """
    Convert CamelCase model name to a PEP8 pluralized snake_case endpoint.
    """
    snake = inflection.underscore(model_name)
    plural = inflection.pluralize(snake)
    return plural.lower()


def get_dynamic_odata_registry(
        include_apps=None,
        exclude_apps=None,
        exclude_models=None,
):
    """
    Build a dynamic OData registry mapping API endpoints to Django model classes.

    Rules:
    - Convert model names to snake_case plural.
    - Exclude Django internal apps by default.
    """

    include_apps = set(include_apps or [])
    exclude_apps = set(exclude_apps or {"admin", "auth", "sessions", "contenttypes"})
    exclude_models = set()

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
        registry[endpoint] = model

        # --- Build apps grouping
        apps_map.setdefault(opts.app_label, []).append(model)

    return registry, apps_map
