"""Formulaires d'administration (séparés de models.py pour éviter un import circulaire)."""
from wagtail.admin.forms.models import WagtailAdminModelForm


class EntryAdminForm(WagtailAdminModelForm):
    """Refuse « validé » sans définition en pulaar (règle D1) avec un message clair
    plutôt qu'une erreur : les sens ne sont pas encore enregistrés à ce stade, il
    faut donc lire le formulaire des sens."""

    def is_valid(self):
        ok = super().is_valid()
        if ok and self.cleaned_data.get("status") == "validated":
            formset = self.formsets.get("senses")
            if formset is not None and not any(
                f.cleaned_data and not f.cleaned_data.get("DELETE") and (f.cleaned_data.get("text") or "").strip()
                for f in formset.forms
            ):
                self.add_error("status", "Une entrée ne peut être validée sans définition en pulaar.")
                return False
        return ok
