# enquetes/admin.py
from django.contrib import admin
from .models import Curso, Turma, Aluno, Enquete, Questao, OpcaoResposta, Resposta, ItemResposta

admin.site.register(Curso)
admin.site.register(Turma)
admin.site.register(Aluno)
admin.site.register(Enquete)
admin.site.register(Questao)
admin.site.register(OpcaoResposta)
admin.site.register(Resposta)
admin.site.register(ItemResposta)