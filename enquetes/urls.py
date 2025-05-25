# ~/workspace/djangoProjeto/enquetes/urls.py
from django.urls import path
from . import views
# from django.contrib.auth import views as auth_views # Removido, pois as URLs de autenticação estão no projeto principal

from .views import (
    EnqueteListView, EnqueteDetailView, EnqueteCreateView, EnqueteUpdateView, EnqueteDeleteView
)

urlpatterns = [
    # URLs para Enquetes (agora sem o prefixo 'enquetes/' porque ele já é tratado no urls.py principal)
    path('', EnqueteListView.as_view(), name='enquete_list'), # Agora /enquetes/ para listar enquetes
    path('criar/', EnqueteCreateView.as_view(), name='enquete_create'), # Agora /enquetes/criar/
    path('<int:pk>/', EnqueteDetailView.as_view(), name='enquete_detail'), # Agora /enquetes/<id>/
    path('<int:pk>/editar/', EnqueteUpdateView.as_view(), name='enquete_update'), # Agora /enquetes/<id>/editar/
    path('<int:pk>/deletar/', EnqueteDeleteView.as_view(), name='enquete_delete'), # Agora /enquetes/<id>/deletar/

    # URLs para Responder Enquetes (Baseado em Função)
    path('<int:pk>/responder/', views.responder_enquete, name='responder_enquete'), # Agora /enquetes/<id>/responder/

    # URLs para Questões (Baseadas em Função)
    path('<int:enquete_id>/questoes/criar/', views.questao_create, name='questao_create'), # Agora /enquetes/<id>/questoes/criar/
    path('<int:enquete_id>/questoes/<int:questao_id>/editar/', views.questao_update, name='questao_update'), # Agora /enquetes/<id>/questoes/<id>/editar/
    path('<int:enquete_id>/questoes/<int:questao_id>/deletar/', views.questao_delete, name='questao_delete'), # Agora /enquetes/<id>/questoes/<id>/deletar/

    # URLs para Respostas (Baseadas em Função)
    path('respostas/<int:pk>/detalhes/', views.resposta_detail, name='resposta_detail'),
    path('<int:enquete_id>/respostas/', views.resposta_list, name='resposta_list'), # Assumindo que você tem uma resposta_list no views.py
]