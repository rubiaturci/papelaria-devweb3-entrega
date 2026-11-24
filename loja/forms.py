from django import forms

from .models import Contato, Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "descricao", "preco", "estoque", "categoria", "imagem", "ativo"]


class ContatoForm(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ["nome", "email", "telefone", "mensagem"]


class IntegranteForm(forms.Form):
    nome = forms.CharField(max_length=100)
    cargo = forms.CharField(max_length=100)
    biografia = forms.CharField(widget=forms.Textarea, required=False)
    foto_url = forms.URLField(label="URL da foto", required=False, assume_scheme="https")
