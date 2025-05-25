from django.db import models
from django.contrib.auth.models import User

class Curso(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['nome'] # Meta Classe: ordering

    def __str__(self):
        return self.nome

    @property
    def total_turmas(self): # Property 1
        return self.turma_set.count()

class Turma(models.Model):
    nome = models.CharField(max_length=100)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE) # Relação 1: ForeignKey
    ano_letivo = models.IntegerField()
    semestre = models.IntegerField()
    data_inicio = models.DateField()
    data_fim = models.DateField()
    professor_responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # Relação 2: ForeignKey

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"
        unique_together = ['curso', 'ano_letivo', 'semestre'] # Meta Classe: unique_together

    def __str__(self):
        return f"{self.nome} - {self.curso.nome} ({self.ano_letivo}/{self.semestre})"

    @property
    def esta_ativa(self): # Property 2
        from datetime import date
        return self.data_inicio <= date.today() <= self.data_fim

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE) # Relação 3: OneToOneField
    matricula = models.CharField(max_length=20, unique=True)
    data_nascimento = models.DateField()
    endereco = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    turmas = models.ManyToManyField(Turma) # Relação 4: ManyToManyField

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        db_table = 'aluno' # Meta Classe: db_table

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Enquete(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    criador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enquetes_criadas')

    class Meta:
        verbose_name = "Enquete"
        verbose_name_plural = "Enquetes"
        get_latest_by = 'data_criacao' # Meta Classe: get_latest_by

    def __str__(self):
        return self.titulo

    @property
    def esta_aberta(self):
        from django.utils import timezone
        return self.data_inicio <= timezone.now() <= self.data_fim

class Questao(models.Model):
    enquete = models.ForeignKey(Enquete, on_delete=models.CASCADE)
    texto_questao = models.CharField(max_length=255)
    tipo_questao = models.CharField(max_length=50, choices=[('texto', 'Texto'), ('multipla_escolha', 'Múltipla Escolha'), ('unica_escolha', 'Única Escolha')])
    ordem = models.IntegerField(default=0)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Questão"
        verbose_name_plural = "Questões"
        unique_together = ['enquete', 'ordem'] # Meta Classe: unique_together

    def __str__(self):
        return f"Q{self.ordem}: {self.texto_questao}"

class OpcaoResposta(models.Model):
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    texto_opcao = models.CharField(max_length=200)
    contador_votos = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Opção de Resposta"
        verbose_name_plural = "Opções de Resposta"
        ordering = ['texto_opcao'] # Meta Classe: ordering

    def __str__(self):
        return self.texto_opcao

class Resposta(models.Model):
    enquete = models.ForeignKey(Enquete, on_delete=models.CASCADE)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, null=True, blank=True) # Resposta pode ser anônima
    data_resposta = models.DateTimeField(auto_now_add=True)
    identificador_anonimo = models.CharField(max_length=100, blank=True, null=True) # Para respostas anônimas
    finalizada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Resposta"
        verbose_name_plural = "Respostas"
        constraints = [
            models.UniqueConstraint(fields=['enquete', 'aluno'], name='unique_enquete_aluno_resposta')
        ] # Meta Classe: constraints

    def __str__(self):
        return f"Resposta de {self.aluno.user.username if self.aluno else 'Anônimo'} para {self.enquete.titulo}"

class ItemResposta(models.Model):
    resposta = models.ForeignKey(Resposta, on_delete=models.CASCADE)
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    texto_resposta = models.TextField(blank=True, null=True) # Para questões de texto
    opcao_selecionada = models.ForeignKey(OpcaoResposta, on_delete=models.SET_NULL, null=True, blank=True) # Para questões de múltipla/única escolha
    data_resposta_item = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('resposta', 'questao')
        indexes = [
            models.Index(fields=['resposta', 'questao'], name='resp_quest_idx'),
        ]
        verbose_name = "Item de Resposta"
        verbose_name_plural = "Itens de Resposta"

    def __str__(self):
        return f"Item para Q{self.questao.ordem} da Resposta {self.resposta.id}"