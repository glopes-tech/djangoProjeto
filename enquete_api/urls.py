from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnqueteViewSet, QuestaoViewSet, OpcaoRespostaViewSet, RespostaViewSet, ItemRespostaViewSet

router = DefaultRouter()
router.register(r'enquetes', EnqueteViewSet)
router.register(r'questoes', QuestaoViewSet)
router.register(r'opcoes', OpcaoRespostaViewSet)
router.register(r'respostas', RespostaViewSet)
router.register(r'itens-respostas', ItemRespostaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]