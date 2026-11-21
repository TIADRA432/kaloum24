"""Wagtail routes with a database-free liveness endpoint."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from kaloum24_v2.home import views as home_views
from kaloum24_v2.news import views_presse as presse_views

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from kaloum24_v2.news.feeds import LatestArticlesFeed
from kaloum24_v2.public.views import health, robots
from kaloum24_v2.pulaar.sitemaps import PulaarSitemap
from wagtail.contrib.sitemaps import Sitemap as WagtailSitemap
from kaloum24_v2.search import views as search_views

urlpatterns = [
    path("healthz", health, name="kaloum24_health"),
    path("healthz/", health),
    path("robots.txt", robots),
    path("sitemap.xml", sitemap, {"sitemaps": {"pages": WagtailSitemap, "pulaar": PulaarSitemap}}),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("pulaar/", include("kaloum24_v2.pulaar.urls")),
    path("credits-images/", home_views.credits_images, name="credits_images"),
    path("meteo/", home_views.meteo_page, name="meteo"),
    path("prix/", include("kaloum24_v2.prix.urls")),
    path("revue-de-presse/", presse_views.revue, name="revue_de_presse"),
    path("search/", search_views.search, name="search"),
    path("news/feed/", LatestArticlesFeed(), name="news_feed"),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [path("", include(wagtail_urls))]
