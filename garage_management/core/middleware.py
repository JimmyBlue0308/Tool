class ContentTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Setze Content-Type für statische Dateien
        if request.path.endswith('.css'):
            response['Content-Type'] = 'text/css; charset=utf-8'
        elif request.path.endswith('.js'):
            response['Content-Type'] = 'text/javascript; charset=utf-8'
            
        return response