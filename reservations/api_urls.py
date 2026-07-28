from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register('lignes', api_views.RouteViewSet, basename='api-routes')
router.register('bateaux', api_views.BateauViewSet, basename='api-bateaux')
router.register('traversees', api_views.TraverseeViewSet, basename='api-traversees')
router.register('reservations', api_views.ReservationViewSet, basename='api-reservations')

urlpatterns = router.urls
