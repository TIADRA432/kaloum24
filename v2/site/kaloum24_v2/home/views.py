from django.shortcuts import render


def credits_images(request):
    return render(request, "pages/credits_images.html")
