from .cart import Panier


def panier_context(request):
    panier = Panier(request)
    return {
        'panier_nb_articles': len(panier),
        'panier_total': panier.get_total(),
    }
