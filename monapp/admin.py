from django.contrib import admin

from .models import ArticleCommande, Categorie, Commande, Produit, ProfilClient


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'prix', 'stock', 'en_promo', 'actif')
    list_filter = ('categorie', 'actif', 'en_promo')
    search_fields = ('nom', 'description')


class ArticleCommandeInline(admin.TabularInline):
    model = ArticleCommande
    extra = 0


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero', 'client_nom', 'total', 'statut', 'mode_paiement', 'date_creation')
    list_filter = ('statut', 'mode_paiement', 'mode_reception')
    search_fields = ('numero', 'client_nom', 'client_telephone')
    inlines = [ArticleCommandeInline]


@admin.register(ProfilClient)
class ProfilClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'points', 'date_creation')
    list_filter = ('points',)
    search_fields = ('user__username', 'telephone')
    ordering = ('-points',)
