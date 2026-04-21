# 在views.py中添加
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def test_cors(request):
    return JsonResponse({"message": "CORS test successful", "status": "ok"})

