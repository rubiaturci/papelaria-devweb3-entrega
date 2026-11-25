from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CadastroForm(UserCreationForm):
    email = forms.EmailField(label="E-mail")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nome de usuário"
        self.fields["username"].help_text = "Escolha um nome único, sem espaços. Você usará esse nome para entrar, não o e-mail."
        self.fields["password1"].label = "Senha"
        self.fields["password2"].label = "Confirme sua senha"

    class Meta:
        model = User
        fields = ("username", "email")


class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
