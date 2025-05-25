from django.shortcuts import get_object_or_404
from rest_framework import serializers
from enquetes.models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta

class OpcaoRespostaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcaoResposta
        fields = ['id', 'texto_opcao', 'contador_votos']
        read_only_fields = ['contador_votos'] # Não permitir que a API modifique votos diretamente

class QuestaoSerializer(serializers.ModelSerializer):
    opcoes_resposta = OpcaoRespostaSerializer(source='opcaoresposta_set', many=True, read_only=True)

    class Meta:
        model = Questao
        fields = ['id', 'enquete', 'texto_questao', 'tipo_questao', 'ordem', 'ativa', 'opcoes_resposta']
        read_only_fields = ['enquete'] # A enquete é definida ao criar a questão

class EnqueteSerializer(serializers.ModelSerializer):
    questoes = QuestaoSerializer(source='questao_set', many=True, read_only=True)
    criador_username = serializers.CharField(source='criador.username', read_only=True)

    class Meta:
        model = Enquete
        fields = ['id', 'titulo', 'descricao', 'data_inicio', 'data_fim', 'criador_username', 'esta_aberta', 'questoes']
        read_only_fields = ['esta_aberta'] # Propriedade não pode ser editada via API

# Serializers para respostas
class RespostaSerializer(serializers.ModelSerializer):
    aluno_username = serializers.CharField(source='aluno.user.username', read_only=True)

    class Meta:
        model = Resposta
        fields = ['id', 'enquete', 'aluno_username', 'identificador_anonimo', 'data_resposta', 'finalizada']
        read_only_fields = ['data_resposta', 'finalizada']

class ItemRespostaSerializer(serializers.ModelSerializer):
    questao_texto = serializers.CharField(source='questao.texto_questao', read_only=True)
    opcao_selecionada_texto = serializers.CharField(source='opcao_selecionada.texto_opcao', read_only=True)

    class Meta:
        model = ItemResposta
        fields = ['id', 'resposta', 'questao', 'questao_texto', 'texto_resposta', 'opcao_selecionada', 'opcao_selecionada_texto']
        read_only_fields = ['resposta', 'questao'] # Estes campos são definidos ao criar a resposta

class EnqueteRespostaSerializer(serializers.Serializer):
    # Serializer para receber respostas de uma enquete via API
    # Esta é uma abordagem mais complexa para lidar com a submissão de respostas
    # Via API, pode-se enviar um JSON com a estrutura da resposta
    # Exemplo:
    # {
    #   "aluno": 1, (ou "identificador_anonimo": "fulano")
    #   "respostas_questoes": [
    #     {
    #       "questao_id": 1,
    #       "texto_resposta": "Minha opinião sobre a questão 1"
    #     },
    #     {
    #       "questao_id": 2,
    #       "opcoes_selecionadas": [3, 4]
    #     },
    #     {
    #       "questao_id": 3,
    #       "opcao_selecionada": 5
    #     }
    #   ]
    # }
    aluno = serializers.PrimaryKeyRelatedField(queryset=Resposta.objects.all(), required=False, allow_null=True)
    identificador_anonimo = serializers.CharField(max_length=100, required=False, allow_blank=True)
    respostas_questoes = serializers.ListField(child=serializers.DictField())

    def validate(self, data):
        # Validações complexas aqui, como verificar se a enquete está aberta,
        # se as questões e opções existem e pertencem à enquete.
        return data

    def create(self, validated_data):
        enquete = self.context['enquete']
        aluno = validated_data.get('aluno')
        identificador_anonimo = validated_data.get('identificador_anonimo')
        respostas_questoes_data = validated_data.get('respostas_questoes')

        if not enquete.esta_aberta:
            raise serializers.ValidationError("Esta enquete não está aberta para respostas.")

        with transaction.atomic():
            resposta = Resposta.objects.create(
                enquete=enquete,
                aluno=aluno,
                identificador_anonimo=identificador_anonimo,
                finalizada=True
            )

            for item_data in respostas_questoes_data:
                questao_id = item_data.get('questao_id')
                questao = get_object_or_404(Questao, pk=questao_id, enquete=enquete)

                if questao.tipo_questao == 'texto':
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        texto_resposta=item_data.get('texto_resposta')
                    )
                elif questao.tipo_questao == 'multipla_escolha':
                    opcoes_selecionadas_ids = item_data.get('opcoes_selecionadas', [])
                    for opcao_id in opcoes_selecionadas_ids:
                        opcao = get_object_or_404(OpcaoResposta, pk=opcao_id, questao=questao)
                        ItemResposta.objects.create(
                            resposta=resposta,
                            questao=questao,
                            opcao_selecionada=opcao
                        )
                        opcao.contador_votos += 1
                        opcao.save()
                elif questao.tipo_questao == 'unica_escolha':
                    opcao_selecionada_id = item_data.get('opcao_selecionada')
                    if opcao_selecionada_id:
                        opcao = get_object_or_404(OpcaoResposta, pk=opcao_selecionada_id, questao=questao)
                        ItemResposta.objects.create(
                            resposta=resposta,
                            questao=questao,
                            opcao_selecionada=opcao
                        )
                        opcao.contador_votos += 1
                        opcao.save()
        return resposta