from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.shortcuts import get_object_or_404

from enquetes.models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta
from .serializers import (
    EnqueteSerializer,
    QuestaoSerializer,
    OpcaoRespostaSerializer,
    RespostaSerializer,
    ItemRespostaSerializer,
    EnqueteRespostaSerializer
)

class EnqueteViewSet(viewsets.ModelViewSet):
    queryset = Enquete.objects.all().order_by('-data_inicio')
    serializer_class = EnqueteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] # Permite leitura para não autenticados

    def perform_create(self, serializer):
        serializer.save(criador=self.request.user)

    @action(detail=True, methods=['post'], serializer_class=EnqueteRespostaSerializer, permission_classes=[])
    def responder(self, request, pk=None):
        enquete = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'enquete': enquete})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Resposta registrada com sucesso!'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], serializer_class=RespostaSerializer, permission_classes=[IsAuthenticated])
    def respostas(self, request, pk=None):
        enquete = self.get_object()
        # Apenas criador da enquete ou admin pode ver todas as respostas
        if request.user == enquete.criador or request.user.is_staff:
            respostas = enquete.resposta_set.all().order_by('-data_resposta')
            serializer = RespostaSerializer(respostas, many=True)
            return Response(serializer.data)
        return Response({'detail': 'Você não tem permissão para ver as respostas desta enquete.'}, status=status.HTTP_403_FORBIDDEN)

class QuestaoViewSet(viewsets.ModelViewSet):
    queryset = Questao.objects.all().order_by('ordem')
    serializer_class = QuestaoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Garante que a questão está sendo criada para uma enquete existente
        enquete_id = self.request.data.get('enquete')
        enquete = get_object_or_404(Enquete, pk=enquete_id)
        serializer.save(enquete=enquete)

class OpcaoRespostaViewSet(viewsets.ModelViewSet):
    queryset = OpcaoResposta.objects.all()
    serializer_class = OpcaoRespostaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Garante que a opção está sendo criada para uma questão existente
        questao_id = self.request.data.get('questao')
        questao = get_object_or_404(Questao, pk=questao_id)
        serializer.save(questao=questao)

class RespostaViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly para respostas (criação via action na Enquete)
    queryset = Resposta.objects.all().order_by('-data_resposta')
    serializer_class = RespostaSerializer
    permission_classes = [IsAuthenticated] # Apenas autenticados podem ver respostas individuais

class ItemRespostaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ItemResposta.objects.all()
    serializer_class = ItemRespostaSerializer
    permission_classes = [IsAuthenticated]