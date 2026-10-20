import traceback
import sys

class ForcePrintExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            print("================ EXCEPTION CAUGHT ================", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("==================================================", file=sys.stderr)
            raise e