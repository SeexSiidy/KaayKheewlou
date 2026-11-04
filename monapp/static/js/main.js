// Kaay Kheewlou — script client (aucune dépendance externe)
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.navbar-toggle');
  var links = document.querySelector('.navbar-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('ouvert');
    });
  }

  // Fermer les messages flash automatiquement
  document.querySelectorAll('.message').forEach(function (msg) {
    setTimeout(function () {
      msg.style.transition = 'opacity .5s ease';
      msg.style.opacity = '0';
      setTimeout(function () { msg.remove(); }, 500);
    }, 5000);
  });

  // Boutons +/- de quantité
  document.querySelectorAll('[data-qte-moins]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.querySelector(btn.getAttribute('data-qte-moins'));
      if (input) input.value = Math.max(1, (parseInt(input.value, 10) || 1) - 1);
    });
  });
  document.querySelectorAll('[data-qte-plus]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.querySelector(btn.getAttribute('data-qte-plus'));
      if (input) input.value = (parseInt(input.value, 10) || 1) + 1;
    });
  });

  // Auto-submit des formulaires de mise à jour de quantité du panier
  document.querySelectorAll('.qte-form input[type="number"]').forEach(function (input) {
    input.addEventListener('change', function () {
      input.closest('form').submit();
    });
  });

  // Afficher/masquer le champ adresse selon le mode de réception choisi
  var radiosReception = document.querySelectorAll('input[name="mode_reception"]');
  var blocAdresse = document.querySelector('[data-bloc-adresse]');
  function majAdresse() {
    if (!blocAdresse) return;
    var val = document.querySelector('input[name="mode_reception"]:checked');
    blocAdresse.style.display = (val && val.value === 'livraison') ? 'block' : 'none';
  }
  radiosReception.forEach(function (r) { r.addEventListener('change', majAdresse); });
  majAdresse();

  // Confirmation avant action sensible (ex : annuler une commande)
  document.querySelectorAll('[data-confirmer]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm(form.getAttribute('data-confirmer') || 'Confirmer cette action ?')) {
        e.preventDefault();
      }
    });
  });

  // Ajout au panier sans rechargement de page (le panier s'incrémente
  // immédiatement) — dégradation gracieuse : si fetch n'est pas
  // disponible, le formulaire est soumis normalement.
  if (window.fetch) {
    document.querySelectorAll('form.ajout-panier').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (form.dataset.fallback === '1') { return; }
        e.preventDefault();
        var bouton = form.querySelector('button[type="submit"]');
        var texteInitial = bouton ? bouton.innerHTML : null;
        if (bouton) { bouton.disabled = true; bouton.innerHTML = 'Ajout...'; }

        fetch(form.action, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body: new FormData(form),
          credentials: 'same-origin',
        })
          .then(function (reponse) { return reponse.json(); })
          .then(function (donnees) {
            if (donnees.ok) {
              document.querySelectorAll('[data-panier-badge]').forEach(function (badge) {
                badge.textContent = donnees.panier_nb_articles;
              });
              afficherToast('« ' + donnees.produit + ' » ajouté au panier (' + donnees.panier_nb_articles + ' article(s))');
            }
          })
          .catch(function () {
            form.dataset.fallback = '1';
            form.submit();
          })
          .finally(function () {
            if (bouton) { bouton.disabled = false; bouton.innerHTML = texteInitial; }
          });
      });
    });
  }

  function afficherToast(message) {
    var toast = document.getElementById('toast-panier');
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    requestAnimationFrame(function () { toast.classList.add('visible'); });
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.classList.remove('visible');
      setTimeout(function () { toast.hidden = true; }, 300);
    }, 3000);
  }
});
