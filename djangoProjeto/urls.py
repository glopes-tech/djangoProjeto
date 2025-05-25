from django.contrib import admin
from django.urls import path, include
from enquetes import views as enquete_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', enquete_views.home, name= 'home'),      # Inclui as URLs do app 'enquetes' na raiz do projeto (para a homepage)
    path('enquetes/', include('enquetes.urls')), # URLs do app 'enquetes' agora estarão sob '/enquetes/'
    path('accounts/', include('django.contrib.auth.urls')), # URLs de autenticação do Django (login, logout, password_reset, etc.)
    # path('register/', seu_app.views.register, name='register'), # Se você tiver uma view de registro em algum app (ex: usuarios)
]