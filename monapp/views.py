from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .cart import Panier
from .forms import (
    CategorieForm, ChangerMotDePasseForm, ConnexionAdminForm, InfosCommandeForm,
    InscriptionForm, NouveauMotDePasseForm, ProduitForm, ProfilForm,
    RecuperationIdentiteForm, RechercheCommandeForm,
)
from .models import ArticleCommande, Categorie, Commande, Produit, ProfilClient

SESSION_INFOS_COMMANDE = 'infos_commande'
SESSION_MES_COMMANDES = 'mes_commandes'
SESSION_RESET_USER_ID = 'reset_user_id'


def est_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


# ---------------------------------------------------------------------------
# Espace client (visiteur)
# ---------------------------------------------------------------------------

def accueil(request):
    produits = Produit.objects.filter(actif=True).select_related('categorie')

    q = request.GET.get('q', '').strip()
    if q:
        produits = produits.filter(Q(nom__icontains=q) | Q(description__icontains=q))

    categorie_slug = request.GET.get('categorie', '').strip()
    if categorie_slug:
        produits = produits.filter(categorie__slug=categorie_slug)

    contexte = {
        'produits': produits,
        'categories': Categorie.objects.all(),
        'q': q,
        'categorie_slug': categorie_slug,
        'produits_promo': Produit.objects.filter(actif=True, en_promo=True)[:6],
    }
    return render(request, 'src/accueil.html', contexte)


def produit_detail(request, slug):
    produit = get_object_or_404(Produit, slug=slug, actif=True)
    suggestions = Produit.objects.filter(actif=True, categorie=produit.categorie).exclude(pk=produit.pk)[:4]
    return render(request, 'src/produit_detail.html', {'produit': produit, 'suggestions': suggestions})


def panier_ajouter(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id, actif=True)
    panier = Panier(request)
    try:
        quantite = int(request.POST.get('quantite', 1))
    except (TypeError, ValueError):
        quantite = 1
    quantite = max(1, quantite)
    panier.ajouter(produit=produit, quantite=quantite)

    if est_ajax(request):
        return JsonResponse({
            'ok': True,
            'produit': produit.nom,
            'panier_nb_articles': len(panier),
            'panier_total': str(panier.get_total()),
        })

    messages.success(request, f"« {produit.nom} » a été ajouté à votre panier.")
    suivant = request.POST.get('suivant') or request.META.get('HTTP_REFERER') or reverse('monapp:accueil')
    return redirect(suivant)


def panier_maj(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    panier = Panier(request)
    try:
        quantite = int(request.POST.get('quantite', 1))
    except (TypeError, ValueError):
        quantite = 1
    panier.ajouter(produit=produit, quantite=quantite, remplacer=True)
    return redirect('monapp:panier')


def panier_retirer(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    panier = Panier(request)
    panier.retirer(produit)
    messages.info(request, f"« {produit.nom} » a été retiré de votre panier.")
    return redirect('monapp:panier')


def panier_vue(request):
    panier = Panier(request)
    autres_produits = Produit.objects.filter(actif=True).exclude(
        id__in=[item['produit'].id for item in panier]
    )[:8]
    return render(request, 'src/panier.html', {'panier': panier, 'autres_produits': autres_produits})


def commande_vue(request):
    panier = Panier(request)
    if panier.est_vide():
        messages.warning(request, "Votre panier est vide. Ajoutez des produits avant de commander.")
        return redirect('monapp:accueil')

    if request.method == 'POST':
        form = InfosCommandeForm(request.POST)
        if form.is_valid():
            request.session[SESSION_INFOS_COMMANDE] = form.cleaned_data
            return redirect('monapp:valider_commande')
    else:
        initial = {}
        if request.user.is_authenticated and not request.user.is_staff:
            profil = getattr(request.user, 'profil_client', None)
            initial = {
                'client_nom': request.user.first_name or request.user.username,
                'client_telephone': profil.telephone if profil else '',
                'client_email': request.user.email,
            }
        initial.update(request.session.get(SESSION_INFOS_COMMANDE, {}))
        form = InfosCommandeForm(initial=initial)

    produits_dispo = Produit.objects.filter(actif=True).exclude(
        id__in=[item['produit'].id for item in panier]
    )[:6]

    return render(request, 'src/commande.html', {
        'panier': panier,
        'form': form,
        'produits_dispo': produits_dispo,
    })


def valider_commande_vue(request):
    panier = Panier(request)
    infos = request.session.get(SESSION_INFOS_COMMANDE)
    if panier.est_vide() or not infos:
        messages.warning(request, "Merci de renseigner vos informations de commande avant de valider.")
        return redirect('monapp:commande')

    mode_reception = infos.get('mode_reception', Commande.MODE_RETRAIT)
    frais_livraison = Decimal(settings.FRAIS_LIVRAISON) if mode_reception == Commande.MODE_LIVRAISON else Decimal('0')
    sous_total = panier.get_total()

    client_connecte = request.user.is_authenticated and not request.user.is_staff
    profil = getattr(request.user, 'profil_client', None) if client_connecte else None
    points_disponibles = profil.points if profil else 0
    reduction_max = min(profil.valeur_points_fcfa, sous_total) if profil else Decimal('0')

    if request.method == 'POST':
        utiliser_points = request.POST.get('utiliser_points') == 'on'
    else:
        utiliser_points = request.GET.get('utiliser_points') == 'on'
    reduction_points = Decimal(reduction_max) if utiliser_points else Decimal('0')
    total = sous_total + frais_livraison - reduction_points

    if request.method == 'POST':
        mode_paiement = request.POST.get('mode_paiement', Commande.PAIEMENT_LIQUIDE)
        points_utilises = 0
        if utiliser_points and reduction_points > 0 and profil:
            points_utilises = int(reduction_points // settings.POINT_VALEUR_REDUCTION)
            profil.points -= points_utilises
            profil.save(update_fields=['points'])

        commande = Commande.objects.create(
            utilisateur=request.user if client_connecte else None,
            client_nom=infos.get('client_nom', ''),
            client_telephone=infos.get('client_telephone', ''),
            client_email=infos.get('client_email', ''),
            client_adresse=infos.get('client_adresse', ''),
            mode_reception=mode_reception,
            mode_paiement=mode_paiement,
            note=infos.get('note', ''),
            sous_total=sous_total,
            frais_livraison=frais_livraison,
            points_utilises=points_utilises,
            reduction_points=reduction_points,
            total=total,
        )
        for item in panier:
            ArticleCommande.objects.create(
                commande=commande,
                produit=item['produit'],
                nom_produit=item['produit'].nom,
                prix_unitaire=item['prix_unitaire'],
                quantite=item['quantite'],
            )
            produit = item['produit']
            if produit.stock >= item['quantite']:
                produit.stock = F('stock') - item['quantite']
                produit.save(update_fields=['stock'])

        mes_commandes = request.session.get(SESSION_MES_COMMANDES, [])
        mes_commandes.insert(0, commande.numero)
        request.session[SESSION_MES_COMMANDES] = mes_commandes[:20]

        panier.vider()
        request.session.pop(SESSION_INFOS_COMMANDE, None)

        messages.success(request, f"Votre commande {commande.numero} a bien été validée. Merci pour votre confiance !")
        return redirect('monapp:suivi_commande', numero=commande.numero)

    return render(request, 'src/valider_commande.html', {
        'panier': panier,
        'infos': infos,
        'frais_livraison': frais_livraison,
        'sous_total': sous_total,
        'reduction_points': reduction_points,
        'total': total,
        'points_disponibles': points_disponibles,
        'reduction_max': reduction_max,
        'utiliser_points': utiliser_points,
        'paiement_choices': Commande.PAIEMENT_CHOICES,
    })


def suivi_commande_vue(request, numero):
    commande = get_object_or_404(Commande, numero=numero)
    etapes = [c for c in Commande.STATUT_CHOICES if c[0] != Commande.STATUT_ANNULEE]
    return render(request, 'src/suivi_commande.html', {'commande': commande, 'etapes': etapes})


def suivre_commande_vue(request):
    """Page unique de suivi : un client connecté retrouve directement son
    historique (plus besoin de ressaisir numéro/téléphone) ; un visiteur non
    connecté doit indiquer le numéro de commande et son téléphone."""
    if request.user.is_authenticated and not request.user.is_staff:
        numeros = request.session.get(SESSION_MES_COMMANDES, [])
        commandes_qs = Commande.objects.filter(numero__in=numeros) | Commande.objects.filter(utilisateur=request.user)
        commandes = list(commandes_qs.distinct())
        commandes.sort(key=lambda c: c.date_creation, reverse=True)
        return render(request, 'src/suivre_commande.html', {'connecte': True, 'commandes': commandes})

    commande = None
    form = RechercheCommandeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            commande = Commande.objects.get(
                numero__iexact=form.cleaned_data['numero'].strip(),
                client_telephone=form.cleaned_data['client_telephone'].strip(),
            )
        except Commande.DoesNotExist:
            messages.error(request, "Aucune commande ne correspond à ces informations.")
    return render(request, 'src/suivre_commande.html', {'connecte': False, 'form': form, 'commande': commande})


@login_required(login_url='monapp:compte_connexion')
def commande_annuler_vue(request, numero):
    commande = get_object_or_404(Commande, numero=numero, utilisateur=request.user)
    if request.method == 'POST':
        if commande.est_annulable:
            for article in commande.articles.all():
                if article.produit:
                    article.produit.stock = F('stock') + article.quantite
                    article.produit.save(update_fields=['stock'])
            commande.statut = Commande.STATUT_ANNULEE
            commande.save(update_fields=['statut', 'date_maj'])
            messages.success(request, f"Votre commande {commande.numero} a été annulée.")
        else:
            messages.error(request, "Cette commande ne peut plus être annulée (déjà en livraison ou terminée).")
    return redirect('monapp:suivre_commande')


# ---------------------------------------------------------------------------
# Mon compte (client) — connexion, inscription et tableau de bord séparés
# ---------------------------------------------------------------------------

def compte_connexion_vue(request):
    """Page de connexion dédiée aux clients. Un compte administrateur qui
    s'y connecterait par erreur est simplement redirigé vers sa propre
    page de connexion (l'espace de gestion a la sienne, dans /gestion/)."""
    if request.user.is_authenticated:
        return redirect('monapp:admin_dashboard' if request.user.is_staff else 'monapp:compte')

    form = ConnexionAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            if user.is_staff:
                messages.success(request, "Connexion administrateur réussie.")
                return redirect('monapp:admin_dashboard')
            messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
            return redirect('monapp:compte')
        form.add_error(None, "Identifiant ou mot de passe incorrect.")
    return render(request, 'src/compte_connexion.html', {'form': form})


def compte_inscription_vue(request):
    if request.user.is_authenticated:
        return redirect('monapp:compte')

    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        donnees = form.cleaned_data
        user = User.objects.create_user(
            username=donnees['username'],
            email=donnees['email'],
            password=donnees['password1'],
            first_name=donnees['nom'],
        )
        ProfilClient.objects.create(user=user, telephone=donnees['telephone'])
        login(request, user)
        messages.success(request, f"Votre compte a été créé, bienvenue {user.first_name} !")
        return redirect('monapp:compte')
    return render(request, 'src/compte_inscription.html', {'form': form})


@login_required(login_url='monapp:compte_connexion')
def compte_vue(request):
    if request.user.is_staff:
        return redirect('monapp:admin_dashboard')

    profil = getattr(request.user, 'profil_client', None)
    profil_form = ProfilForm(user=request.user, initial={
        'nom': request.user.first_name,
        'telephone': profil.telephone if profil else '',
        'email': request.user.email,
    })
    mdp_form = ChangerMotDePasseForm(user=request.user)

    if request.method == 'POST' and request.POST.get('action') == 'profil':
        profil_form = ProfilForm(request.POST, user=request.user)
        if profil_form.is_valid():
            donnees = profil_form.cleaned_data
            request.user.first_name = donnees['nom']
            request.user.email = donnees['email']
            request.user.save(update_fields=['first_name', 'email'])
            if profil:
                profil.telephone = donnees['telephone']
                profil.save(update_fields=['telephone'])
            else:
                profil = ProfilClient.objects.create(user=request.user, telephone=donnees['telephone'])
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect('monapp:compte')

    elif request.method == 'POST' and request.POST.get('action') == 'mot_de_passe':
        mdp_form = ChangerMotDePasseForm(request.POST, user=request.user)
        if mdp_form.is_valid():
            request.user.set_password(mdp_form.cleaned_data['password1'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Votre mot de passe a été changé avec succès.")
            return redirect('monapp:compte')

    commandes_qs = Commande.objects.filter(utilisateur=request.user)
    nb_commandes = commandes_qs.count()
    total_depense = commandes_qs.exclude(statut=Commande.STATUT_ANNULEE).aggregate(total=Sum('total'))['total'] or 0
    dernieres_commandes = commandes_qs.order_by('-date_creation')[:5]

    return render(request, 'src/compte.html', {
        'profil': profil,
        'profil_form': profil_form,
        'mdp_form': mdp_form,
        'nb_commandes': nb_commandes,
        'total_depense': total_depense,
        'dernieres_commandes': dernieres_commandes,
    })


def compte_deconnexion_vue(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('monapp:accueil')


def compte_mdp_oublie_vue(request):
    form = RecuperationIdentiteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            profil = ProfilClient.objects.get(
                telephone=form.cleaned_data['telephone'].strip(),
                user__username__iexact=form.cleaned_data['username'].strip(),
            )
        except ProfilClient.DoesNotExist:
            messages.error(request, "Aucun compte ne correspond à cet identifiant et ce téléphone.")
        else:
            request.session[SESSION_RESET_USER_ID] = profil.user_id
            return redirect('monapp:compte_mdp_nouveau')
    return render(request, 'src/compte_mdp_oublie.html', {'form': form})


def compte_mdp_nouveau_vue(request):
    user_id = request.session.get(SESSION_RESET_USER_ID)
    if not user_id:
        messages.warning(request, "Merci de vérifier d'abord votre identité.")
        return redirect('monapp:compte_mdp_oublie')

    utilisateur = get_object_or_404(User, pk=user_id)
    form = NouveauMotDePasseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        utilisateur.set_password(form.cleaned_data['password1'])
        utilisateur.save()
        request.session.pop(SESSION_RESET_USER_ID, None)
        messages.success(request, "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.")
        return redirect('monapp:compte')
    return render(request, 'src/compte_mdp_nouveau.html', {'form': form, 'utilisateur': utilisateur})


# ---------------------------------------------------------------------------
# Espace administrateur (gestion)
# ---------------------------------------------------------------------------

def admin_login_vue(request):
    if request.user.is_authenticated:
        return redirect('monapp:admin_dashboard')

    form = ConnexionAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('monapp:admin_dashboard')
        messages.error(request, "Identifiant ou mot de passe incorrect.")
    return render(request, 'src/admin_login.html', {'form': form})


def admin_logout_vue(request):
    logout(request)
    return redirect('monapp:admin_login')


def est_staff(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_dashboard_vue(request):
    commandes = Commande.objects.all()
    commandes_valides = commandes.exclude(statut=Commande.STATUT_ANNULEE)
    commandes_payees = commandes.filter(statut__in=[Commande.STATUT_LIVRAISON, Commande.STATUT_TERMINEE])

    chiffre_affaires = commandes_payees.aggregate(total=Sum('total'))['total'] or 0
    nb_commandes_valides = commandes_valides.count()
    panier_moyen = (chiffre_affaires / commandes_payees.count()) if commandes_payees.count() else 0

    aujourd_hui = timezone.now().date()
    commandes_du_jour = commandes.filter(date_creation__date=aujourd_hui).count()
    ca_du_jour = commandes.filter(date_creation__date=aujourd_hui).exclude(
        statut=Commande.STATUT_ANNULEE
    ).aggregate(total=Sum('total'))['total'] or 0

    top_produits = (
        ArticleCommande.objects.exclude(commande__statut=Commande.STATUT_ANNULEE)
        .values('nom_produit')
        .annotate(quantite_totale=Sum('quantite'))
        .order_by('-quantite_totale')[:5]
    )

    commandes_par_statut = commandes.values('statut').annotate(total=Count('id'))
    compteurs = {s: 0 for s, _ in Commande.STATUT_CHOICES}
    for entree in commandes_par_statut:
        compteurs[entree['statut']] = entree['total']
    stats_statuts = [
        {'cle': cle, 'libelle': libelle, 'total': compteurs.get(cle, 0)}
        for cle, libelle in Commande.STATUT_CHOICES
    ]

    # Chiffre d'affaires des 7 derniers jours (pour un mini graphique en barres CSS)
    ventes_semaine = []
    max_jour = 1
    for i in range(6, -1, -1):
        jour = aujourd_hui - timedelta(days=i)
        total_jour = commandes.filter(date_creation__date=jour).exclude(
            statut=Commande.STATUT_ANNULEE
        ).aggregate(total=Sum('total'))['total'] or 0
        ventes_semaine.append({'jour': jour, 'total': total_jour})
        max_jour = max(max_jour, total_jour)
    for entree in ventes_semaine:
        entree['pourcentage'] = int((entree['total'] / max_jour) * 100) if max_jour else 0

    produits_stock_faible = Produit.objects.filter(stock__gt=0, stock__lte=5)
    produits_rupture = Produit.objects.filter(stock=0)
    valeur_stock = Produit.objects.aggregate(
        total=Sum(F('prix') * F('stock'))
    )['total'] or 0

    meilleurs_clients = (
        ProfilClient.objects.select_related('user').filter(points__gt=0).order_by('-points')[:5]
    )

    contexte = {
        'nb_commandes': commandes.count(),
        'nb_commandes_valides': nb_commandes_valides,
        'nb_commandes_en_cours': commandes.filter(
            statut__in=[Commande.STATUT_VALIDEE, Commande.STATUT_PREPARATION, Commande.STATUT_LIVRAISON]
        ).count(),
        'nb_commandes_annulees': commandes.filter(statut=Commande.STATUT_ANNULEE).count(),
        'chiffre_affaires': chiffre_affaires,
        'panier_moyen': round(panier_moyen),
        'commandes_du_jour': commandes_du_jour,
        'ca_du_jour': ca_du_jour,
        'top_produits': top_produits,
        'stats_statuts': stats_statuts,
        'ventes_semaine': ventes_semaine,
        'produits_stock_faible': produits_stock_faible,
        'produits_rupture': produits_rupture,
        'nb_stock_faible': produits_stock_faible.count(),
        'nb_rupture': produits_rupture.count(),
        'valeur_stock': valeur_stock,
        'nb_produits': Produit.objects.count(),
        'nb_clients': ProfilClient.objects.count(),
        'meilleurs_clients': meilleurs_clients,
        'dernieres_commandes': commandes[:6],
    }
    return render(request, 'src/admin_dashboard.html', contexte)


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_produits_vue(request):
    produits = Produit.objects.select_related('categorie').all()
    q = request.GET.get('q', '').strip()
    if q:
        produits = produits.filter(nom__icontains=q)
    return render(request, 'src/admin_produits.html', {'produits': produits, 'q': q})


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_produit_form_vue(request, pk=None):
    produit = get_object_or_404(Produit, pk=pk) if pk else None
    form = ProduitForm(request.POST or None, request.FILES or None, instance=produit)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Produit enregistré avec succès.")
        return redirect('monapp:admin_produits')
    return render(request, 'src/admin_produit_form.html', {'form': form, 'produit': produit})


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_produit_supprimer_vue(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        produit.delete()
        messages.success(request, "Produit supprimé.")
        return redirect('monapp:admin_produits')
    return render(request, 'src/admin_confirmer_suppression.html', {'objet': produit, 'type_objet': 'produit'})


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_categories_vue(request):
    categories = Categorie.objects.annotate(nb_produits=Count('produits'))
    form = CategorieForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Catégorie ajoutée.")
        return redirect('monapp:admin_categories')
    return render(request, 'src/admin_categories.html', {'categories': categories, 'form': form})


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_categorie_supprimer_vue(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        categorie.delete()
        messages.success(request, "Catégorie supprimée.")
        return redirect('monapp:admin_categories')
    return render(request, 'src/admin_confirmer_suppression.html', {'objet': categorie, 'type_objet': 'catégorie'})


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_commandes_vue(request):
    commandes = Commande.objects.all()
    statut = request.GET.get('statut', '').strip()
    if statut:
        commandes = commandes.filter(statut=statut)
    return render(request, 'src/admin_commandes.html', {
        'commandes': commandes,
        'statut_choices': Commande.STATUT_CHOICES,
        'statut': statut,
    })


@user_passes_test(est_staff, login_url='monapp:admin_login')
def admin_commande_detail_vue(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        ancien_statut = commande.statut
        if nouveau_statut in dict(Commande.STATUT_CHOICES) and nouveau_statut != ancien_statut:
            if nouveau_statut == Commande.STATUT_ANNULEE and ancien_statut != Commande.STATUT_ANNULEE:
                for article in commande.articles.all():
                    if article.produit:
                        article.produit.stock = F('stock') + article.quantite
                        article.produit.save(update_fields=['stock'])
            commande.statut = nouveau_statut
            commande.save(update_fields=['statut', 'date_maj'])
            if nouveau_statut == Commande.STATUT_TERMINEE:
                commande.crediter_points_fidelite()
            messages.success(request, f"Statut de la commande {commande.numero} mis à jour.")
        return redirect('monapp:admin_commande_detail', pk=pk)
    return render(request, 'src/admin_commande_detail.html', {
        'commande': commande,
        'statut_choices': Commande.STATUT_CHOICES,
    })
