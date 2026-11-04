from decimal import Decimal

from .models import Produit

CART_SESSION_ID = 'panier'


class Panier:
    """Panier basé sur la session — aucune base de données ni compte client requis."""

    def __init__(self, request):
        self.session = request.session
        panier = self.session.get(CART_SESSION_ID)
        if panier is None:
            panier = self.session[CART_SESSION_ID] = {}
        self.panier = panier

    def ajouter(self, produit, quantite=1, remplacer=False):
        cle = str(produit.id)
        if cle not in self.panier:
            self.panier[cle] = {'quantite': 0}
        if remplacer:
            self.panier[cle]['quantite'] = quantite
        else:
            self.panier[cle]['quantite'] += quantite
        if self.panier[cle]['quantite'] <= 0:
            self.retirer(produit)
        else:
            self.sauvegarder()

    def retirer(self, produit):
        cle = str(produit.id)
        if cle in self.panier:
            del self.panier[cle]
            self.sauvegarder()

    def vider(self):
        self.session[CART_SESSION_ID] = {}
        self.sauvegarder()

    def sauvegarder(self):
        self.session.modified = True

    def __iter__(self):
        ids = self.panier.keys()
        produits = Produit.objects.filter(id__in=ids)
        produits_par_id = {str(p.id): p for p in produits}
        for cle, donnee in self.panier.items():
            produit = produits_par_id.get(cle)
            if not produit:
                continue
            quantite = donnee['quantite']
            prix = produit.prix_promo
            yield {
                'produit': produit,
                'quantite': quantite,
                'prix_unitaire': prix,
                'sous_total': prix * quantite,
            }

    def __len__(self):
        return sum(item['quantite'] for item in self.panier.values())

    def get_total(self):
        return sum((item['sous_total'] for item in self), Decimal('0'))

    def est_vide(self):
        return len(self.panier) == 0
