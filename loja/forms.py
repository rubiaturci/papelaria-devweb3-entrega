from django import forms

from .models import Contato, Integrante, Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "descricao", "preco", "estoque", "categoria", "imagem", "ativo"]


class ContatoForm(forms.ModelForm):
    # No formulário o telefone é obrigatório, como na demonstração.
    telefone = forms.CharField(max_length=20)

    class Meta:
        model = Contato
        fields = ["nome", "telefone", "email", "mensagem"]


class IntegranteForm(forms.ModelForm):
    foto_url = forms.URLField(label="URL da foto", required=False, assume_scheme="https")

    class Meta:
        model = Integrante
        fields = ["nome", "cargo", "biografia", "foto_url"]
        widgets = {"biografia": forms.Textarea}
