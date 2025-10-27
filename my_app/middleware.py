from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse


class ForceJSONMiddleware(MiddlewareMixin):
    """Middleware pour forcer le format JSON pour les endpoints OData."""



    def process_response(self, request, response):
        """Ajouter les en-têtes CORS et OData appropriés."""
        if request.path.startswith("/odata/"):
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS, HEAD"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response["Access-Control-Max-Age"] = "3600"
            response["OData-Version"] = "4.0"

        return response
