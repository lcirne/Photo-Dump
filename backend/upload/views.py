from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    # User is logged in
    user = request.user
    return render(request, "upload.html", {"user": user})

