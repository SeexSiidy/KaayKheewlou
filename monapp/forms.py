from django import forms
from django.contrib.auth.models import User

from .models import Categorie, Commande, Produit


class InfosCommandeForm(forms.Form):
    client_nom = forms.CharField(label="Nom complet", max_length=120)
    client_telephone = forms.CharField(label="Téléphone", max_length=30)
    client_email = forms.EmailField(label="Email (facultatif)", required=False)
    mode_reception = forms.ChoiceField(label="Réception", choices=Commande.MODE_RECEPTION_CHOICES, widget=forms.RadioSelect)
    client_adresse = forms.CharField(label="Adresse de livraison", max_length=255, required=False, widget=forms.Textarea(attrs={'rows': 2}))
    note = forms.CharField(label="Note pour votre commande", max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('mode_reception') == Commande.MODE_LIVRAISON and not cleaned.get('client_adresse'):
            self.add_error('client_adresse', "L'adresse est requise pour une livraison.")
        return cleaned


class PaiementForm(forms.Form):
    mode_paiement = forms.ChoiceField(choices=Commande.PAIEMENT_CHOICES, widget=forms.RadioSelect)


class RechercheCommandeForm(forms.Form):
    numero = forms.CharField(label="Numéro de commande", max_length=20)
    client_telephone = forms.CharField(label="Téléphone utilisé", max_length=30)


class ConnexionAdminForm(forms.Form):
    """Formulaire de connexion générique (utilisé par l'espace de gestion
    ET par la page « Mon compte » — un compte administrateur comme
    admin123 se connecte avec exactement le même formulaire)."""
    username = forms.CharField(label="Identifiant")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)


class InscriptionForm(forms.Form):
    username = forms.CharField(label="Identifiant (nom d'utilisateur)", max_length=150)
    nom = forms.CharField(label="Nom complet", max_length=120)
    telephone = forms.CharField(label="Téléphone", max_length=30)
    email = forms.EmailField(label="Email (facultatif)", required=False)
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean_telephone(self):
        from .models import ProfilClient
        telephone = self.cleaned_data['telephone'].strip()
        if ProfilClient.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà associé à un compte.")
        return telephone

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        elif p1 and len(p1) < 6:
            self.add_error('password1', "Le mot de passe doit contenir au moins 6 caractères.")
        return cleaned


class RecuperationIdentiteForm(forms.Form):
    """Étape 1 de la récupération de mot de passe : pas d'email/SMS
    disponible (contrainte hors-ligne), la vérification se fait donc via
    l'identifiant + le téléphone enregistré sur le compte."""
    username = forms.CharField(label="Identifiant")
    telephone = forms.CharField(label="Téléphone associé au compte", max_length=30)


class NouveauMotDePasseForm(forms.Form):
    password1 = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        elif p1 and len(p1) < 6:
            self.add_error('password1', "Le mot de passe doit contenir au moins 6 caractères.")
        return cleaned


class ProfilForm(forms.Form):
    nom = forms.CharField(label="Nom complet", max_length=120)
    telephone = forms.CharField(label="Téléphone", max_length=30)
    email = forms.EmailField(label="Email (facultatif)", required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_telephone(self):
        from .models import ProfilClient
        telephone = self.cleaned_data['telephone'].strip()
        conflit = ProfilClient.objects.filter(telephone=telephone)
        if self.user is not None:
            conflit = conflit.exclude(user=self.user)
        if conflit.exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà associé à un autre compte.")
        return telephone


class ChangerMotDePasseForm(forms.Form):
    ancien_mot_de_passe = forms.CharField(label="Mot de passe actuel", widget=forms.PasswordInput)
    password1 = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_ancien_mot_de_passe(self):
        ancien = self.cleaned_data['ancien_mot_de_passe']
        if self.user is not None and not self.user.check_password(ancien):
            raise forms.ValidationError("Le mot de passe actuel est incorrect.")
        return ancien

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        elif p1 and len(p1) < 6:
            self.add_error('password1', "Le mot de passe doit contenir au moins 6 caractères.")
        return cleaned


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'categorie', 'description', 'composition', 'prix',
            'image', 'stock', 'actif', 'en_promo', 'promo_pourcentage',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'composition': forms.Textarea(attrs={'rows': 3}),
        }


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description']
