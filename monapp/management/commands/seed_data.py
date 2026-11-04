from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from monapp.models import Categorie, Produit


class Command(BaseCommand):
    help = "Crée le compte administrateur et des données de démonstration pour Kaay Kheewlou."

    def handle(self, *args, **options):
        User = get_user_model()
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'is_staff': True, 'is_superuser': True},
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Compte administrateur créé : {username} / {password}"))
        else:
            self.stdout.write(self.style.WARNING(f"Compte administrateur mis à jour : {username} / {password}"))

        categories_data = [
            ("Plats", "Plats traditionnels transformés, prêts à consommer"),
            ("Céréales & Farines", "Céréales locales transformées et farines"),
            ("Jus & Boissons", "Jus naturels et boissons artisanales"),
            ("Épices & Condiments", "Épices, sauces et condiments locaux"),
            ("Snacks", "Produits de grignotage sains"),
        ]
        categories = {}
        for nom, description in categories_data:
            cat, _ = Categorie.objects.get_or_create(nom=nom, defaults={'description': description})
            categories[nom] = cat

        produits_data = [
            ("Thiéré complet 1kg", "Céréales & Farines", 2500, "Couscous de mil 100% naturel, sans additifs.", "Mil local, sans gluten ajouté."),
            ("Farine de mil bio 1kg", "Céréales & Farines", 1800, "Farine de mil finement moulue.", "Mil bio 100%."),
            ("Jus de bissap 1L", "Jus & Boissons", 1500, "Jus de bissap artisanal, naturellement sucré.", "Fleurs d'hibiscus, sucre, eau."),
            ("Jus de bouye 1L", "Jus & Boissons", 1800, "Jus de pain de singe (baobab), riche en vitamine C.", "Pulpe de bouye, sucre, eau."),
            ("Sauce yassa prête 500g", "Plats", 2000, "Sauce yassa prête à réchauffer.", "Oignons, moutarde, citron, huile."),
            ("Thiébou dieune surgelé", "Plats", 3500, "Riz au poisson traditionnel, portion familiale.", "Riz, poisson, légumes, épices."),
            ("Mélange épices Yassa", "Épices & Condiments", 1200, "Mélange d'épices prêt à l'emploi pour yassa.", "Poivre, moutarde, ail, oignon séché."),
            ("Piment séché 200g", "Épices & Condiments", 900, "Piment local séché et broyé.", "Piment 100% naturel."),
            ("Biscuits de mil 250g", "Snacks", 1000, "Biscuits croustillants à base de mil.", "Mil, sucre, huile végétale."),
            ("Arachides grillées 500g", "Snacks", 1200, "Arachides locales grillées et salées.", "Arachides, sel."),
        ]

        for nom, cat_nom, prix, description, composition in produits_data:
            Produit.objects.get_or_create(
                nom=nom,
                defaults={
                    'categorie': categories.get(cat_nom),
                    'prix': prix,
                    'description': description,
                    'composition': composition,
                    'stock': 25,
                    'actif': True,
                },
            )

        # Une petite promo de démonstration
        promo = Produit.objects.filter(nom="Jus de bissap 1L").first()
        if promo:
            promo.en_promo = True
            promo.promo_pourcentage = 15
            promo.save(update_fields=['en_promo', 'promo_pourcentage'])

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées avec succès."))
