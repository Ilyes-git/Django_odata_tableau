"""
Module pour générer dynamiquement les URLs OData pour tous les models enregistrés
"""
from django.urls import path, re_path
from my_app.views import (
    ODataServiceDocumentView,
    ODataMetadataEndpoint,
    ODataMetadataJsonEndpoint,
    ODataModelViewSet,
    ODATA_MODELS_REGISTRY
)


class ODataRouter:
    """Routeur dynamique qui crée les routes OData pour tous les models enregistrés"""

    @staticmethod
    def get_urlpatterns():
        """Génère les URLs OData dynamiquement"""
        urlpatterns = [
            # Service document
            path("", ODataServiceDocumentView.as_view(), name="odata_service_document"),

            # Metadata endpoints
            path("$metadata", ODataMetadataEndpoint.as_view(), name="odata_metadata_xml"),
            path("$metadata/json", ODataMetadataJsonEndpoint.as_view(), name="odata_metadata_json"),
        ]

        # Créer les routes pour chaque entity set enregistré
        for entity_set_name in ODATA_MODELS_REGISTRY.keys():
            # Créer un ViewSet dynamique pour cet entity set
            class_name = f"{entity_set_name}ViewSet"

            # Créer une classe ViewSet dynamiquement
            DynamicViewSet = type(class_name,(ODataModelViewSet,),{'entity_set_name': entity_set_name})

            # Endpoint collection: /EntitySet
            urlpatterns.append(
                path(
                    f"{entity_set_name}",
                    DynamicViewSet.as_view({'get': 'list'}),
                    name=f"odata_{entity_set_name.lower()}_list"
                )
            )

            # Endpoint entité individuelle: /EntitySet(id)
            urlpatterns.append(
                re_path(
                    rf"^{entity_set_name}\((?P<pk>\d+)\)$",
                    DynamicViewSet.as_view({'get': 'retrieve'}),
                    name=f"odata_{entity_set_name.lower()}_retrieve"
                )
            )

        return urlpatterns


# URLs pattern
urlpatterns = ODataRouter.get_urlpatterns()

