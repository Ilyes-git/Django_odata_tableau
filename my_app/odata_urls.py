"""
Module pour générer dynamiquement les URLs OData pour tous les models enregistrés
"""
from django.urls import path, re_path
from my_app.views import (
    ODataServiceDocumentView,
    ODataMetadataEndpoint,
    ODataMetadataJsonEndpoint,
    ODataEntitySetView,
    ODATA_MODELS_REGISTRY
)


def generate_odata_urls():
    """Génère les URLs OData dynamiquement pour tous les models enregistrés"""
    urlpatterns = [
        # Service document
        path("", ODataServiceDocumentView.as_view(), name="odata_service_document"),

        # Metadata endpoints
        path("$metadata", ODataMetadataEndpoint.as_view(), name="odata_metadata_xml"),
        path("$metadata/json", ODataMetadataJsonEndpoint.as_view(), name="odata_metadata_json"),
    ]

    # Générer dynamiquement les endpoints pour chaque entity set enregistré
    for entity_set_name in ODATA_MODELS_REGISTRY.keys():
        # Endpoint collection: /EntitySet
        urlpatterns.append(
            path(
                f"{entity_set_name}",
                ODataEntitySetView.as_view(),
                kwargs={'entity_set_name': entity_set_name},
                name=f"odata_{entity_set_name.lower()}_collection"
            )
        )

        # Endpoint entité individuelle: /EntitySet(id)
        urlpatterns.append(
            re_path(
                rf"^{entity_set_name}\((?P<pk>\d+)\)$",
                ODataEntitySetView.as_view(),
                kwargs={'entity_set_name': entity_set_name},
                name=f"odata_{entity_set_name.lower()}_detail"
            )
        )

    return urlpatterns


# URLs pattern
urlpatterns = generate_odata_urls()

