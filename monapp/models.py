import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Categorie(models.Model):
    nom = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom) or "categorie"
        super().save(*args, **kwargs)


class Produit(models.Model):
    nom = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, related_name='produits')
    description = models.TextField(blank=True, help_text="Description courte du produit")
    composition = models.TextField(
        blank=True,
        help_text="Composition / ingrédients / allergènes du produit"
    )
    prix = models.DecimalField(max_digits=10, decimal_places=0, help_text="Prix en FCFA")
    image = models.ImageField(upload_to='produits/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True, help_text="Visible côté client")

    en_promo = models.BooleanField(default=False)
    promo_pourcentage = models.PositiveIntegerField(
        default=0, help_text="Pourcentage de réduction appliqué (0-90)"
    )

    date_ajout = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-date_ajout']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nom) or "produit"
            i = 1
            candidate = base
            while Produit.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}-{i}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('monapp:produit_detail', args=[self.slug])

    @property
    def prix_promo(self):
        if self.en_promo and self.promo_pourcentage > 0:
            reduction = (self.prix * Decimal(self.promo_pourcentage)) / Decimal(100)
            return (self.prix - reduction).quantize(Decimal('1'))
        return self.prix

    @property
    def en_rupture(self):
        return self.stock <= 0

    @property
    def stock_faible(self):
        return 0 < self.stock <= 5


def generer_numero_commande():
    while True:
        suffixe = "".join(random.choices(string.digits, k=6))
        numero = f"KK-{suffixe}"
        if not Commande.objects.filter(numero=numero).exists():
            return numero


class Commande(models.Model):
    STATUT_VALIDEE = 'validee'
    STATUT_PREPARATION = 'preparation'
    STATUT_LIVRAISON = 'livraison'
    STATUT_TERMINEE = 'terminee'
    STATUT_ANNULEE = 'annulee'

    STATUT_CHOICES = [
        (STATUT_VALIDEE, 'Commande validée'),
        (STATUT_PREPARATION, 'En préparation'),
        (STATUT_LIVRAISON, 'En livraison'),
        (STATUT_TERMINEE, 'Terminée'),
        (STATUT_ANNULEE, 'Annulée'),
    ]

    # Statuts que l'on peut choisir manuellement en gestion (l'annulation se
    # fait normalement côté client, mais reste possible en gestion aussi)
    STATUT_POURCENTAGE = {
        STATUT_VALIDEE: 25,
        STATUT_PREPARATION: 50,
        STATUT_LIVRAISON: 75,
        STATUT_TERMINEE: 100,
        STATUT_ANNULEE: 0,
    }

    # Statuts à partir desquels le client peut encore annuler sa commande
    STATUTS_ANNULABLES = (STATUT_VALIDEE, STATUT_PREPARATION)

    MODE_RETRAIT = 'retrait'
    MODE_LIVRAISON = 'livraison'
    MODE_RECEPTION_CHOICES = [
        (MODE_RETRAIT, 'Retrait sur place'),
        (MODE_LIVRAISON, 'Livraison à domicile'),
    ]

    PAIEMENT_WAVE = 'wave'
    PAIEMENT_OM = 'orange_money'
    PAIEMENT_CARTE = 'carte'
    PAIEMENT_LIQUIDE = 'liquide'
    PAIEMENT_CHOICES = [
        (PAIEMENT_WAVE, 'Wave'),
        (PAIEMENT_OM, 'Orange Money'),
        (PAIEMENT_CARTE, 'Carte bancaire'),
        (PAIEMENT_LIQUIDE, 'Liquide (paiement à la livraison)'),
    ]

    numero = models.CharField(max_length=20, unique=True, default=generer_numero_commande, editable=False)

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes'
    )

    client_nom = models.CharField(max_length=120)
    client_telephone = models.CharField(max_length=30)
    client_email = models.EmailField(blank=True)
    client_adresse = models.CharField(max_length=255, blank=True)

    mode_reception = models.CharField(max_length=15, choices=MODE_RECEPTION_CHOICES, default=MODE_RETRAIT)
    mode_paiement = models.CharField(max_length=15, choices=PAIEMENT_CHOICES, default=PAIEMENT_LIQUIDE)

    sous_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    frais_livraison = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    points_utilises = models.PositiveIntegerField(default=0)
    reduction_points = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    points_credites = models.BooleanField(default=False, help_text="Les points de fidélité ont déjà été crédités pour cette commande")

    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default=STATUT_VALIDEE)

    note = models.TextField(blank=True, help_text="Précisions du client sur la commande")

    date_creation = models.DateTimeField(default=timezone.now)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-date_creation']

    def __str__(self):
        return self.numero

    @property
    def pourcentage(self):
        return self.STATUT_POURCENTAGE.get(self.statut, 0)

    @property
    def est_annulable(self):
        return self.statut in self.STATUTS_ANNULABLES

    @property
    def est_annulee(self):
        return self.statut == self.STATUT_ANNULEE

    def recalculer_total(self):
        self.sous_total = sum((a.sous_total for a in self.articles.all()), Decimal('0'))
        self.total = self.sous_total + self.frais_livraison - self.reduction_points
        return self.total

    @property
    def points_gagnes(self):
        return int(self.sous_total // settings.POINTS_SEUIL_FCFA)

    def crediter_points_fidelite(self):
        """Crédite les points de fidélité sur le profil du client une seule
        fois, lorsque la commande passe au statut 'terminée'."""
        if self.points_credites or not self.utilisateur:
            return
        profil = getattr(self.utilisateur, 'profil_client', None)
        if not profil:
            return
        points = self.points_gagnes
        if points > 0:
            profil.points += points
            profil.save(update_fields=['points'])
        self.points_credites = True
        self.save(update_fields=['points_credites'])


class ArticleCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='articles')
    produit = models.ForeignKey(Produit, on_delete=models.SET_NULL, null=True, related_name='articles_commandes')
    nom_produit = models.CharField(max_length=120)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=0)
    quantite = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"

    def __str__(self):
        return f"{self.quantite} x {self.nom_produit}"

    @property
    def sous_total(self):
        return self.prix_unitaire * self.quantite


class ProfilClient(models.Model):
    """Informations complémentaires pour un compte client (utilisées notamment
    pour la récupération de mot de passe, sans email ni SMS)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profil_client')
    telephone = models.CharField(max_length=30, unique=True)
    adresse = models.CharField(max_length=255, blank=True)
    points = models.PositiveIntegerField(default=0, help_text="Points de fidélité cumulés")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil client"
        verbose_name_plural = "Profils clients"

    def __str__(self):
        return f"Profil de {self.user.username}"

    @property
    def valeur_points_fcfa(self):
        return self.points * settings.POINT_VALEUR_REDUCTION
