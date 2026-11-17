from django.http import HttpResponseRedirect

class RedirectOldRenderDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()

        if host == "glowcart-t6bf.onrender.com":
            new_url = "https://glowcart.co.in" + request.get_full_path()
            return HttpResponseRedirect(new_url)

        return self.get_response(request)
