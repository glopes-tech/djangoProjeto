from django.shortcuts import get_object_or_404
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import os
import django
from django.conf import settings
from django.db.models import F

# Configura o ambiente Django para que o FastAPI possa acessar os models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poll_academia.settings')
django.setup()

from enquetefrom fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import os
import django
from django.conf import settings
from django.db.models import F

# Configura o ambiente Django para que o FastAPI possa acessar os models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poll_academia.settings')
django.setup()

from enquetes.models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta, Aluno
from django.contrib.auth.models import User
from django.utils import timezone

app = FastAPI(
    title="API de Enquetes com FastAPI",
    description="API para gerenciar enquetes e respostas de alunos de programação.",
    version="1.0.0",
)

# Configuração CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todas as origens (para desenvolvimento)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas Pydantic ---
class OpcaoRespostaSchema(BaseModel):
    id: int
    texto_opcao: str
    contador_votos: int

    class Config:
        from_attributes = True

class QuestaoSchema(BaseModel):
    id: int
    texto_questao: str
    tipo_questao: str
    ordem: int
    opcoes_resposta: List[OpcaoRespostaSchema] = []

    class Config:
        from_attributes = True

class EnqueteSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data_inicio: str
    data_fim: str
    criador_username: str
    esta_aberta: bool
    questoes: List[QuestaoSchema] = []

    class Config:
        from_attributes = True
        json_encoders = {
            timezone.datetime: lambda dt: dt.isoformat(),
        }

class RespostaItemSchema(BaseModel):
    questao_id: int
    texto_resposta: Optional[str] = None
    opcoes_selecionadas: Optional[List[int]] = [] # Para múltipla escolha
    opcao_selecionada: Optional[int] = None # Para única escolha

class RespostaCreateSchema(BaseModel):
    aluno_id: Optional[int] = None
    identificador_anonimo: Optional[str] = None
    itens_resposta: List[RespostaItemSchema]

# --- Rotas FastAPI ---

@app.get("/fastapi/enquetes/", response_model=List[EnqueteSchema])
async def get_all_enquetes():
    enquetes = Enquete.objects.all().prefetch_related('questao_set__opcaoresposta_set')
    return [EnqueteSchema.from_orm(enquete) for enquete in enquetes]

@app.get("/fastapi/enquetes/{enquete_id}", response_model=EnqueteSchema)
async def get_enquete_by_id(enquete_id: int):
    try:
        enquete = Enquete.objects.prefetch_related('questao_set__opcaoresposta_set').get(id=enquete_id)
        return EnqueteSchema.from_orm(enquete)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada")

@app.post("/fastapi/enquetes/{enquete_id}/responder/", status_code=status.HTTP_201_CREATED)
async def submit_enquete_response(enquete_id: int, response_data: RespostaCreateSchema):
    try:
        enquete = Enquete.objects.get(id=enquete_id)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada.")

    if not enquete.esta_aberta:
        raise HTTPException(status_code=400, detail="Esta enquete não está aberta para respostas.")

    aluno_instance = None
    if response_data.aluno_id:
        try:
            aluno_instance = Aluno.objects.get(id=response_data.aluno_id)
        except Aluno.DoesNotExist:
            raise HTTPException(status_code=400, detail="Aluno não encontrado.")
    elif not response_data.identificador_anonimo:
        raise HTTPException(status_code=400, detail="Para respostas anônimas, 'identificador_anonimo' é obrigatório.")

    try:
        with transaction.atomic():
            resposta = Resposta.objects.create(
                enquete=enquete,
                aluno=aluno_instance,
                identificador_anonimo=response_data.identificador_anonimo,
                finalizada=True # Marcar como finalizada ao submeter via API
            )

            for item_data in response_data.itens_resposta:
                questao = get_object_or_404(Questao, pk=item_data.questao_id, enquete=enquete)

                if questao.tipo_questao == 'texto':
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        texto_resposta=item_data.texto_resposta
                    )
                elif questao.tipo_questao == 'multipla_escolha':
                    if not item_data.opcoes_selecionadas:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de opções.")
                    for opcao_id in item_data.opcoes_selecionadas:
                        opcao = get_object_or_404(OpcaoResposta, pk=opcao_id, questao=questao)
                        ItemResposta.objects.create(
                            resposta=resposta,
                            questao=questao,
                            opcao_selecionada=opcao
                        )
                        opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                        opcao.save(update_fields=['contador_votos'])
                elif questao.tipo_questao == 'unica_escolha':
                    if not item_data.opcao_selecionada:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de uma opção.")
                    opcao = get_object_or_404(OpcaoResposta, pk=item_data.opcao_selecionada, questao=questao)
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        opcao_selecionada=opcao
                    )
                    opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                    opcao.save(update_fields=['contador_votos'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar resposta: {e}")

    return {"message": "Resposta da enquete submetida com sucesso!", "resposta_id": resposta.id}from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import os
import django
from django.conf import settings
from django.db.models import F

# Configura o ambiente Django para que o FastAPI possa acessar os models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poll_academia.settings')
django.setup()

from enquetes.models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta, Aluno
from django.contrib.auth.models import User
from django.utils import timezone

app = FastAPI(
    title="API de Enquetes com FastAPI",
    description="API para gerenciar enquetes e respostas de alunos de programação.",
    version="1.0.0",
)

# Configuração CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todas as origens (para desenvolvimento)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas Pydantic ---
class OpcaoRespostaSchema(BaseModel):
    id: int
    texto_opcao: str
    contador_votos: int

    class Config:
        from_attributes = True

class QuestaoSchema(BaseModel):
    id: int
    texto_questao: str
    tipo_questao: str
    ordem: int
    opcoes_resposta: List[OpcaoRespostaSchema] = []

    class Config:
        from_attributes = True

class EnqueteSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data_inicio: str
    data_fim: str
    criador_username: str
    esta_aberta: bool
    questoes: List[QuestaoSchema] = []

    class Config:
        from_attributes = True
        json_encoders = {
            timezone.datetime: lambda dt: dt.isoformat(),
        }

class RespostaItemSchema(BaseModel):
    questao_id: int
    texto_resposta: Optional[str] = None
    opcoes_selecionadas: Optional[List[int]] = [] # Para múltipla escolha
    opcao_selecionada: Optional[int] = None # Para única escolha

class RespostaCreateSchema(BaseModel):
    aluno_id: Optional[int] = None
    identificador_anonimo: Optional[str] = None
    itens_resposta: List[RespostaItemSchema]

# --- Rotas FastAPI ---

@app.get("/fastapi/enquetes/", response_model=List[EnqueteSchema])
async def get_all_enquetes():
    enquetes = Enquete.objects.all().prefetch_related('questao_set__opcaoresposta_set')
    return [EnqueteSchema.from_orm(enquete) for enquete in enquetes]

@app.get("/fastapi/enquetes/{enquete_id}", response_model=EnqueteSchema)
async def get_enquete_by_id(enquete_id: int):
    try:
        enquete = Enquete.objects.prefetch_related('questao_set__opcaoresposta_set').get(id=enquete_id)
        return EnqueteSchema.from_orm(enquete)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada")

@app.post("/fastapi/enquetes/{enquete_id}/responder/", status_code=status.HTTP_201_CREATED)
async def submit_enquete_response(enquete_id: int, response_data: RespostaCreateSchema):
    try:
        enquete = Enquete.objects.get(id=enquete_id)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada.")

    if not enquete.esta_aberta:
        raise HTTPException(status_code=400, detail="Esta enquete não está aberta para respostas.")

    aluno_instance = None
    if response_data.aluno_id:
        try:
            aluno_instance = Aluno.objects.get(id=response_data.aluno_id)
        except Aluno.DoesNotExist:
            raise HTTPException(status_code=400, detail="Aluno não encontrado.")
    elif not response_data.identificador_anonimo:
        raise HTTPException(status_code=400, detail="Para respostas anônimas, 'identificador_anonimo' é obrigatório.")

    try:
        with transaction.atomic():
            resposta = Resposta.objects.create(
                enquete=enquete,
                aluno=aluno_instance,
                identificador_anonimo=response_data.identificador_anonimo,
                finalizada=True # Marcar como finalizada ao submeter via API
            )

            for item_data in response_data.itens_resposta:
                questao = get_object_or_404(Questao, pk=item_data.questao_id, enquete=enquete)

                if questao.tipo_questao == 'texto':
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        texto_resposta=item_data.texto_resposta
                    )
                elif questao.tipo_questao == 'multipla_escolha':
                    if not item_data.opcoes_selecionadas:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de opções.")
                    for opcao_id in item_data.opcoes_selecionadas:
                        opcao = get_object_or_404(OpcaoResposta, pk=opcao_id, questao=questao)
                        ItemResposta.objects.create(
                            resposta=resposta,
                            questao=questao,
                            opcao_selecionada=opcao
                        )
                        opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                        opcao.save(update_fields=['contador_votos'])
                elif questao.tipo_questao == 'unica_escolha':
                    if not item_data.opcao_selecionada:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de uma opção.")
                    opcao = get_object_or_404(OpcaoResposta, pk=item_data.opcao_selecionada, questao=questao)
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        opcao_selecionada=opcao
                    )
                    opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                    opcao.save(update_fields=['contador_votos'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar resposta: {e}")

    return {"message": "Resposta da enquete submetida com sucesso!", "resposta_id": resposta.id}.models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta, Aluno
from django.contrib.auth.models import User
from django.utils import timezone

app = FastAPI(
    title="API de Enquetes com FastAPI",
    description="API para gerenciar enquetes e respostas de alunos de programação.",
    version="1.0.0",
)

# Configuração CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todas as origens (para desenvolvimento)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas Pydantic ---
class OpcaoRespostaSchema(BaseModel):
    id: int
    texto_opcao: str
    contador_votos: int

    class Config:
        from_attributes = True

class QuestaoSchema(BaseModel):
    id: int
    texto_questao: str
    tipo_questao: str
    ordem: int
    opcoes_resposta: List[OpcaoRespostaSchema] = []

    class Config:
        from_attributes = True

class EnqueteSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data_inicio: str
    data_fim: str
    criador_username: str
    esta_aberta: bool
    questoes: List[QuestaoSchema] = []

    class Config:
        from_attributes = True
        json_encoders = {
            timezone.datetime: lambda dt: dt.isoformat(),
        }

class RespostaItemSchema(BaseModel):
    questao_id: int
    texto_resposta: Optional[str] = None
    opcoes_selecionadas: Optional[List[int]] = [] # Para múltipla escolha
    opcao_selecionada: Optional[int] = None # Para única escolha

class RespostaCreateSchema(BaseModel):
    aluno_id: Optional[int] = None
    identificador_anonimo: Optional[str] = None
    itens_resposta: List[RespostaItemSchema]

# --- Rotas FastAPI ---

@app.get("/fastapi/enquetes/", response_model=List[EnqueteSchema])
async def get_all_enquetes():
    enquetes = Enquete.objects.all().prefetch_related('questao_set__opcaoresposta_set')
    return [EnqueteSchema.from_orm(enquete) for enquete in enquetes]

@app.get("/fastapi/enquetes/{enquete_id}", response_model=EnqueteSchema)
async def get_enquete_by_id(enquete_id: int):
    try:
        enquete = Enquete.objects.prefetch_related('questao_set__opcaoresposta_set').get(id=enquete_id)
        return EnqueteSchema.from_orm(enquete)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada")

@app.post("/fastapi/enquetes/{enquete_id}/responder/", status_code=status.HTTP_201_CREATED)
async def submit_enquete_response(enquete_id: int, response_data: RespostaCreateSchema):
    try:
        enquete = Enquete.objects.get(id=enquete_id)
    except Enquete.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enquete não encontrada.")

    if not enquete.esta_aberta:
        raise HTTPException(status_code=400, detail="Esta enquete não está aberta para respostas.")

    aluno_instance = None
    if response_data.aluno_id:
        try:
            aluno_instance = Aluno.objects.get(id=response_data.aluno_id)
        except Aluno.DoesNotExist:
            raise HTTPException(status_code=400, detail="Aluno não encontrado.")
    elif not response_data.identificador_anonimo:
        raise HTTPException(status_code=400, detail="Para respostas anônimas, 'identificador_anonimo' é obrigatório.")

    try:
        with transaction.atomic():
            resposta = Resposta.objects.create(
                enquete=enquete,
                aluno=aluno_instance,
                identificador_anonimo=response_data.identificador_anonimo,
                finalizada=True # Marcar como finalizada ao submeter via API
            )

            for item_data in response_data.itens_resposta:
                questao = get_object_or_404(Questao, pk=item_data.questao_id, enquete=enquete)

                if questao.tipo_questao == 'texto':
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        texto_resposta=item_data.texto_resposta
                    )
                elif questao.tipo_questao == 'multipla_escolha':
                    if not item_data.opcoes_selecionadas:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de opções.")
                    for opcao_id in item_data.opcoes_selecionadas:
                        opcao = get_object_or_404(OpcaoResposta, pk=opcao_id, questao=questao)
                        ItemResposta.objects.create(
                            resposta=resposta,
                            questao=questao,
                            opcao_selecionada=opcao
                        )
                        opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                        opcao.save(update_fields=['contador_votos'])
                elif questao.tipo_questao == 'unica_escolha':
                    if not item_data.opcao_selecionada:
                        raise HTTPException(status_code=400, detail=f"Questão '{questao.texto_questao}' requer seleção de uma opção.")
                    opcao = get_object_or_404(OpcaoResposta, pk=item_data.opcao_selecionada, questao=questao)
                    ItemResposta.objects.create(
                        resposta=resposta,
                        questao=questao,
                        opcao_selecionada=opcao
                    )
                    opcao.contador_votos = F('contador_votos') + 1 # Incrementa atomicamente
                    opcao.save(update_fields=['contador_votos'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar resposta: {e}")

    return {"message": "Resposta da enquete submetida com sucesso!", "resposta_id": resposta.id}