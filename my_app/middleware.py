from django.utils.deprecation import MiddlewareMixin


class OdataVersionMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.path.startswith("/odata/"):
            response["OData-Version"] = "4.0"
        return response
