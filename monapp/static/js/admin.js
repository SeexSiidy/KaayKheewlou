// Kaay Kheewlou — script espace de gestion (aucune dépendance externe)
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.message').forEach(function (msg) {
    setTimeout(function () {
      msg.style.transition = 'opacity .5s ease';
      msg.style.opacity = '0';
      setTimeout(function () { msg.remove(); }, 500);
    }, 5000);
  });

  // Confirmation avant suppression
  document.querySelectorAll('[data-confirmer]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm(form.getAttribute('data-confirmer') || 'Confirmer cette action ?')) {
        e.preventDefault();
      }
    });
  });

  // Aperçu de l'image sélectionnée dans le formulaire produit
  var inputImage = document.querySelector('#id_image');
  var apercu = document.querySelector('[data-apercu-image]');
  if (inputImage && apercu) {
    inputImage.addEventListener('change', function () {
      var fichier = inputImage.files[0];
      if (fichier) {
        apercu.src = URL.createObjectURL(fichier);
        apercu.style.display = 'block';
      }
    });
  }

  // Afficher/masquer le pourcentage promo selon la case "en promo"
  var casePromo = document.querySelector('#id_en_promo');
  var champPromo = document.querySelector('[data-champ-promo]');
  function majPromo() {
    if (!champPromo) return;
    champPromo.style.display = (casePromo && casePromo.checked) ? 'block' : 'none';
  }
  if (casePromo) {
    casePromo.addEventListener('change', majPromo);
    majPromo();
  }
});
