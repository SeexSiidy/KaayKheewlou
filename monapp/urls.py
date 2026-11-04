from django.urls import path

from . import views

app_name = 'monapp'

urlpatterns = [
    # Client
    path('', views.accueil, name='accueil'),
    path('produit/<slug:slug>/', views.produit_detail, name='produit_detail'),

    path('panier/', views.panier_vue, name='panier'),
    path('panier/ajouter/<int:produit_id>/', views.panier_ajouter, name='panier_ajouter'),
    path('panier/maj/<int:produit_id>/', views.panier_maj, name='panier_maj'),
    path('panier/retirer/<int:produit_id>/', views.panier_retirer, name='panier_retirer'),

    path('compte/connexion/', views.compte_connexion_vue, name='compte_connexion'),
    path('compte/inscription/', views.compte_inscription_vue, name='compte_inscription'),
    path('compte/', views.compte_vue, name='compte'),
    path('compte/deconnexion/', views.compte_deconnexion_vue, name='compte_deconnexion'),
    path('compte/mot-de-passe-oublie/', views.compte_mdp_oublie_vue, name='compte_mdp_oublie'),
    path('compte/mot-de-passe-oublie/nouveau/', views.compte_mdp_nouveau_vue, name='compte_mdp_nouveau'),

    path('commande/', views.commande_vue, name='commande'),
    path('commande/valider/', views.valider_commande_vue, name='valider_commande'),
    path('commande/<str:numero>/annuler/', views.commande_annuler_vue, name='commande_annuler'),
    path('suivi/<str:numero>/', views.suivi_commande_vue, name='suivi_commande'),
    path('suivre-commande/', views.suivre_commande_vue, name='suivre_commande'),

    # Gestion (administrateur)
    path('gestion/connexion/', views.admin_login_vue, name='admin_login'),
    path('gestion/deconnexion/', views.admin_logout_vue, name='admin_logout'),
    path('gestion/', views.admin_dashboard_vue, name='admin_dashboard'),

    path('gestion/produits/', views.admin_produits_vue, name='admin_produits'),
    path('gestion/produits/ajouter/', views.admin_produit_form_vue, name='admin_produit_ajouter'),
    path('gestion/produits/<int:pk>/modifier/', views.admin_produit_form_vue, name='admin_produit_modifier'),
    path('gestion/produits/<int:pk>/supprimer/', views.admin_produit_supprimer_vue, name='admin_produit_supprimer'),

    path('gestion/categories/', views.admin_categories_vue, name='admin_categories'),
    path('gestion/categories/<int:pk>/supprimer/', views.admin_categorie_supprimer_vue, name='admin_categorie_supprimer'),

    path('gestion/commandes/', views.admin_commandes_vue, name='admin_commandes'),
    path('gestion/commandes/<int:pk>/', views.admin_commande_detail_vue, name='admin_commande_detail'),
]
