from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    if request.user.is_authenticated:
        # User is logged in
        user = request.user
        return render(request, "user_dashboard.html", {"user": user})
    else:
        return HttpResponse("Dashboard index.")

