from django import forms

from .models import PulaarDomain


class ProposalForm(forms.Form):
    term_lemma = forms.CharField(label="Mot en pulaar", max_length=200)
    definition_ff = forms.CharField(label="Définition en pulaar", required=False, widget=forms.Textarea)
    definition_fr = forms.CharField(label="Définition en français", required=False, widget=forms.Textarea)
    domain = forms.ModelChoiceField(label="Domaine", queryset=PulaarDomain.objects.all(), required=False,
                                    empty_label="— Aucun —")
    justification = forms.CharField(label="D'où vient ce mot ?", required=False, widget=forms.Textarea)
    contributor_name = forms.CharField(label="Ton nom (facultatif)", required=False, max_length=120)
    contributor_contact = forms.CharField(label="Contact (facultatif, jamais publié)", required=False, max_length=200)
    # Piège à robots : un humain ne voit pas ce champ, un robot le remplit.
    site_web = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean(self):
        data = super().clean()
        ff = (data.get("definition_ff") or "").strip()
        fr = (data.get("definition_fr") or "").strip()
        # Au moins UNE des deux définitions suffit : exiger le français
        # empêcherait un locuteur de contribuer en pulaar seul.
        if len(ff) < 5 and len(fr) < 5:
            raise forms.ValidationError(
                "Indique au moins une définition, en pulaar ou en français (5 caractères minimum)."
            )
        return data
