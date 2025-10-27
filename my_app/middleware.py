from django.utils.deprecation import MiddlewareMixin


class ForceJSONMiddleware(MiddlewareMixin):
    """Middleware pour forcer le format JSON pour les endpoints OData."""

    def process_response(self, request, response):
        if request.path.startswith("/odata/"):
            response["OData-Version"] = "4.0"

        return response




