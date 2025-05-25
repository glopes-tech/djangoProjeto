from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.urls import reverse_lazy
from django.forms import formset_factory # Não usaremos inlineformset_factory diretamente aqui, mas é útil
from django.db import transaction # Para garantir atomicidade nas respostas
from django.utils import timezone # Importar timezone para usar timezone.now()

from .models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta, Aluno # Importar Aluno
from .forms import (
    EnqueteForm,
    QuestaoForm,
    OpcaoRespostaForm,
    RespostaForm,
    ItemRespostaTextoForm, # Formulários específicos para tipos de questão
    ItemRespostaMultiplaEscolhaForm,
    ItemRespostaUnicaEscolhaForm
)

def home(request):
    """View para renderizar a página inicial (home.html)."""
    context = {
        'now': timezone.now(), # Passa a data/hora atual para o template
    }
    return render(request, 'enquetes/home.html', context)

# --- Classes Base para Enquete (CRUD) ---

class EnqueteListView(ListView): # Classe Listar
    model = Enquete
    template_name = 'enquetes/enquete_list.html'
    context_object_name = 'enquetes'
    ordering = ['-data_inicio']

class EnqueteDetailView(DetailView): # Classe Detalhar
    model = Enquete
    template_name = 'enquetes/enquete_detail.html'
    context_object_name = 'enquete'

class EnqueteCreateView(LoginRequiredMixin, CreateView): # Classe Criar
    model = Enquete
    form_class = EnqueteForm
    template_name = 'enquetes/enquete_form.html'
    success_url = reverse_lazy('enquete_list')

    def form_valid(self, form):
        form.instance.criador = self.request.user
        return super().form_valid(form)

class EnqueteUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView): # Classe Editar
    model = Enquete
    form_class = EnqueteForm
    template_name = 'enquetes/enquete_form.html'
    context_object_name = 'enquete'
    success_url = reverse_lazy('enquete_list')

    def test_func(self):
        enquete = self.get_object()
        return enquete.criador == self.request.user

    def handle_no_permission(self):
        return redirect('enquete_list') # Redireciona se o utilizador não tiver permissão

class EnqueteDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView): # Classe Deletar
    model = Enquete
    template_name = 'enquetes/enquete_confirm_delete.html'
    success_url = reverse_lazy('enquete_list')
    context_object_name = 'enquete'

    def test_func(self):
        enquete = self.get_object()
        return enquete.criador == self.request.user

    def handle_no_permission(self):
        return redirect('enquete_list')

# --- Métodos Base para Resposta da Enquete ---

@login_required # Adicione este decorador se quiser que apenas utilizadores logados respondam
def responder_enquete(request, pk): # Método Criar (para Resposta)
    enquete = get_object_or_404(Enquete, pk=pk)

    if not enquete.esta_aberta: # Verifica a propriedade 'esta_aberta' do modelo Enquete
        return render(request, 'enquetes/enquete_fechada.html', {'enquete': enquete})

    questoes = enquete.questao_set.all().order_by('ordem') # Correção: usar questao_set

    # Forms dinâmicos para as questões
    questoes_forms = []
    for questao in questoes:
        if questao.tipo_questao == 'texto':
            item_form = ItemRespostaTextoForm(prefix=f'q_{questao.id}')
        elif questao.tipo_questao == 'multipla_escolha':
            opcoes = [(str(op.id), op.texto_opcao) for op in questao.opcaoresposta_set.all()]
            item_form = ItemRespostaMultiplaEscolhaForm(prefix=f'q_{questao.id}')
            item_form.fields['opcoes_selecionadas'].choices = opcoes
        elif questao.tipo_questao == 'unica_escolha':
            opcoes = [(str(op.id), op.texto_opcao) for op in questao.opcaoresposta_set.all()]
            item_form = ItemRespostaUnicaEscolhaForm(prefix=f'q_{questao.id}')
            item_form.fields['opcao_selecionada'].choices = opcoes
        questoes_forms.append({'instance': questao, 'item_form': item_form})

    if request.method == 'POST':
        resposta_form = RespostaForm(request.POST)

        # Associa o aluno logado ou permite resposta anónima
        if request.user.is_authenticated:
            try:
                aluno = Aluno.objects.get(user=request.user) # Correção: Aluno.user
                resposta_form.instance.aluno = aluno
            except Aluno.DoesNotExist:
                # Se o utilizador está logado mas não tem um perfil de Aluno,
                # pode-se redirecionar ou tratar como anónimo se permitido
                resposta_form.instance.aluno = None
                resposta_form.instance.identificador_anonimo = request.POST.get('identificador_anonimo', 'Anónimo')
        else:
            resposta_form.instance.aluno = None # Para respostas anónimas
            resposta_form.instance.identificador_anonimo = request.POST.get('identificador_anonimo')

        resposta_form.instance.enquete = enquete

        if resposta_form.is_valid():
            with transaction.atomic(): # Garante que tudo seja salvo ou nada seja salvo
                resposta = resposta_form.save(commit=False)
                resposta.save() # Salva a resposta principal

                # Processa os itens de resposta
                for questao_data in questoes_forms:
                    questao = questao_data['instance']
                    if questao.tipo_questao == 'texto':
                        item_form = ItemRespostaTextoForm(request.POST, prefix=f'q_{questao.id}')
                        if item_form.is_valid():
                            item_resposta = item_form.save(commit=False)
                            item_resposta.resposta = resposta
                            item_resposta.questao = questao
                            item_resposta.save()
                    elif questao.tipo_questao == 'multipla_escolha':
                        opcoes_selecionadas_ids = request.POST.getlist(f'q_{questao.id}-opcoes_selecionadas')
                        for opcao_id in opcoes_selecionadas_ids:
                            opcao = get_object_or_404(OpcaoResposta, id=opcao_id, questao=questao)
                            ItemResposta.objects.create(
                                resposta=resposta,
                                questao=questao,
                                opcao_selecionada=opcao
                            )
                            # Incrementa o contador de votos na opção
                            opcao.contador_votos += 1
                            opcao.save()
                    elif questao.tipo_questao == 'unica_escolha':
                        opcao_selecionada_id = request.POST.get(f'q_{questao.id}-opcao_selecionada')
                        if opcao_selecionada_id:
                            opcao = get_object_or_404(OpcaoResposta, id=opcao_selecionada_id, questao=questao)
                            ItemResposta.objects.create(
                                resposta=resposta,
                                questao=questao,
                                opcao_selecionada=opcao
                            )
                            # Incrementa o contador de votos na opção
                            opcao.contador_votos += 1
                            opcao.save()

                # Marca a resposta como finalizada
                resposta.finalizada = True
                resposta.save()

                return redirect('enquete_list') # Ou para uma página de sucesso
        else:
            # Se o formulário de resposta principal não for válido, re-renderiza com erros
            pass # Os erros serão exibidos no template automaticamente

    else: # GET request
        resposta_form = RespostaForm()
        if request.user.is_authenticated and hasattr(request.user, 'aluno'):
            # Pré-preenche o campo aluno se o utilizador estiver logado e tiver um perfil de aluno
            resposta_form.fields['aluno'].initial = request.user.aluno.id
        elif not request.user.is_authenticated:
            # Não exibe o campo aluno para utilizadores anónimos
            resposta_form.fields.pop('aluno', None)


    context = {
        'enquete': enquete,
        'resposta_form': resposta_form,
        'questoes_forms': questoes_forms,
    }
    return render(request, 'enquetes/enquete_responder.html', context)


@login_required
def resposta_list(request): # Método Listar (para Respostas)
    respostas = Resposta.objects.all().order_by('-data_resposta')
    return render(request, 'enquetes/respostas_list.html', {'respostas': respostas})

@login_required
def resposta_detail(request, pk): # Método Detalhar (para Resposta)
    resposta = get_object_or_404(Resposta, pk=pk)
    itens_resposta = resposta.itemresposta_set.all() # Correção: usar itemresposta_set
    return render(request, 'enquetes/resposta_detail.html', {'resposta': resposta, 'itens_resposta': itens_resposta})


# ====================================================================
# Views para Questões (ainda como funções para maior flexibilidade)
# ====================================================================

@login_required
def questao_create(request, enquete_id): # Método Criar (para Questão)
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    if request.method == 'POST':
        form = QuestaoForm(request.POST)
        if form.is_valid():
            questao = form.save(commit=False)
            questao.enquete = enquete
            questao.save()
            return redirect('enquete_detail', pk=enquete.id)
    else:
        form = QuestaoForm(initial={'enquete': enquete}) # Pré-preenche a enquete
    return render(request, 'enquetes/questao_form.html', {'form': form, 'enquete': enquete})

@login_required
def questao_update(request, enquete_id, questao_id): # Método Editar (para Questão)
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    questao = get_object_or_404(Questao, pk=questao_id, enquete=enquete)
    if request.method == 'POST':
        form = QuestaoForm(request.POST, instance=questao)
        if form.is_valid():
            form.save()
            return redirect('enquete_detail', pk=enquete.id)
    else:
        form = QuestaoForm(instance=questao)
    return render(request, 'enquetes/questao_form.html', {'form': form, 'enquete': enquete})

@login_required
def questao_delete(request, enquete_id, questao_id): # Método Deletar (para Questão)
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    questao = get_object_or_404(Questao, pk=questao_id, enquete=enquete)
    if request.method == 'POST':
        questao.delete()
        return redirect('enquete_detail', pk=enquete.id)
    return render(request, 'enquetes/questao_confirm_delete.html', {'questao': questao, 'enquete': enquete})