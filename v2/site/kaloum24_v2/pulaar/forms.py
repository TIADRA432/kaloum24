from django import forms

from .models import PulaarDialect, PulaarDomain


class ProposalForm(forms.Form):
    term_lemma = forms.CharField(label="Mot en pulaar", max_length=200)
    definition_ff = forms.CharField(label="Définition en pulaar", widget=forms.Textarea, min_length=5,
                                    help_text="Le dictionnaire est monolingue : explique le mot en pulaar.")
    translation_fr = forms.CharField(label="Traduction en français (facultatif)", required=False, max_length=300)
    dialect = forms.ModelChoiceField(label="Variété du pulaar", queryset=PulaarDialect.objects.all(),
                                     required=False, empty_label="— Je ne sais pas / pulaar de Guinée par défaut —")
    domain = forms.ModelChoiceField(label="Domaine", queryset=PulaarDomain.objects.all(), required=False,
                                    empty_label="— Aucun —")
    justification = forms.CharField(label="D'où vient ce mot ?", required=False, widget=forms.Textarea)
    contributor_name = forms.CharField(label="Ton nom (facultatif)", required=False, max_length=120)
    contributor_contact = forms.CharField(label="Contact (facultatif, jamais publié)", required=False, max_length=200)
    # Piège à robots : un humain ne voit pas ce champ, un robot le remplit.
    site_web = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))
