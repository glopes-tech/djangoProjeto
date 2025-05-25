from django import forms
from .models import Enquete, Questao, OpcaoResposta, Resposta, ItemResposta

class EnqueteForm(forms.ModelForm):
    class Meta:
        model = Enquete
        fields = ['titulo', 'descricao', 'data_inicio', 'data_fim']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class QuestaoForm(forms.ModelForm):
    class Meta:
        model = Questao
        fields = ['enquete', 'texto_questao', 'tipo_questao', 'ordem']

class OpcaoRespostaForm(forms.ModelForm):
    class Meta:
        model = OpcaoResposta
        fields = ['questao', 'texto_opcao']

class RespostaForm(forms.ModelForm):
    class Meta:
        model = Resposta
        fields = ['aluno', 'identificador_anonimo']
        # aluno pode ser None se a resposta for anônima
        # No template, tratar a exibição do campo aluno se o usuário estiver logado.

class ItemRespostaTextoForm(forms.ModelForm):
    class Meta:
        model = ItemResposta
        fields = ['texto_resposta']

class ItemRespostaMultiplaEscolhaForm(forms.Form):
    # Este formulário será dinâmico, as opções serão geradas na view/template
    opcoes_selecionadas = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class ItemRespostaUnicaEscolhaForm(forms.Form):
    # Este formulário será dinâmico, as opções serão geradas na view/template
    opcao_selecionada = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=False
    )