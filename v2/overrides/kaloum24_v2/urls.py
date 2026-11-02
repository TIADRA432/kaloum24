"""Wagtail routes with a database-free liveness endpoint."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from kaloum24_v2.news.feeds import LatestArticlesFeed
from kaloum24_v2.public.views import health
from kaloum24_v2.search import views as search_views

urlpatterns = [
    path("healthz", health, name="kaloum24_health"),
    path("healthz/", health),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("news/feed/", LatestArticlesFeed(), name="news_feed"),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [path("", include(wagtail_urls))]
