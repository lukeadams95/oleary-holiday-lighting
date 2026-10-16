/* O'Leary Holiday Lighting — site behaviour.
   Three small things: the mobile menu, the Services dropdown on touch/keyboard,
   and the FAQ accordion. Everything else is CSS. */
(function () {
  'use strict';

  /* ---------------------------------------------------------------- nav --- */
  var burger = document.querySelector('.nav-burger');
  var mobileMenu = document.querySelector('.mobile-menu');

  if (burger && mobileMenu) {
    burger.addEventListener('click', function () {
      var open = mobileMenu.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', String(open));
    });
  }

  /* The dropdown opens on hover via CSS. Pointer devices without hover (and
     keyboard users who reach the toggle) get an explicit click target. */
  var dropdownItems = document.querySelectorAll('.nav__item');

  Array.prototype.forEach.call(dropdownItems, function (item) {
    var toggle = item.querySelector('.nav__link');
    var menu = item.querySelector('.dropdown');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', function (event) {
      // On a device that can hover, let the link navigate to /services.
      if (window.matchMedia('(hover: hover)').matches) return;
      event.preventDefault();
      menu.classList.toggle('is-open');
    });

    item.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        menu.classList.remove('is-open');
        toggle.focus();
      }
    });
  });

  document.addEventListener('click', function (event) {
    Array.prototype.forEach.call(document.querySelectorAll('.dropdown.is-open'), function (menu) {
      if (!menu.closest('.nav__item').contains(event.target)) {
        menu.classList.remove('is-open');
      }
    });
  });

  /* ----------------------------------------------------------- accordion --- */
  var triggers = document.querySelectorAll('.accordion__trigger');

  Array.prototype.forEach.call(triggers, function (trigger) {
    trigger.addEventListener('click', function () {
      var expanded = trigger.getAttribute('aria-expanded') === 'true';
      var panel = document.getElementById(trigger.getAttribute('aria-controls'));
      trigger.setAttribute('aria-expanded', String(!expanded));
      if (panel) panel.hidden = expanded;
    });
  });

  /* ------------------------------------------------------------ carousel --- */
  var carousels = document.querySelectorAll('[data-carousel]');

  Array.prototype.forEach.call(carousels, function (root) {
    var slides = root.querySelectorAll('.carousel__slide');
    var dots = root.querySelectorAll('.carousel__dot');
    var prevBtn = root.querySelector('.carousel__arrow--prev');
    var nextBtn = root.querySelector('.carousel__arrow--next');
    var AUTOPLAY_MS = 5000;
    var index = 0;
    var timer = null;

    if (slides.length < 2) return;

    function show(next) {
      index = (next + slides.length) % slides.length;
      Array.prototype.forEach.call(slides, function (slide, n) {
        slide.classList.toggle('is-active', n === index);
      });
      Array.prototype.forEach.call(dots, function (dot, n) {
        dot.classList.toggle('is-active', n === index);
      });
    }

    function startAutoplay() {
      stopAutoplay();
      timer = window.setInterval(function () { show(index + 1); }, AUTOPLAY_MS);
    }

    function stopAutoplay() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        show(index - 1);
        startAutoplay();
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        show(index + 1);
        startAutoplay();
      });
    }
    Array.prototype.forEach.call(dots, function (dot, n) {
      dot.addEventListener('click', function () {
        show(n);
        startAutoplay();
      });
    });

    // Pause while a visitor is looking at or interacting with the carousel.
    root.addEventListener('mouseenter', stopAutoplay);
    root.addEventListener('mouseleave', startAutoplay);
    root.addEventListener('focusin', stopAutoplay);
    root.addEventListener('focusout', startAutoplay);

    startAutoplay();
  });

  /* ------------------------------------------------------- motion pause --- */
  /* Snowfall and the wreath accent run a few iterations, and pause off-screen. */
  if ('IntersectionObserver' in window) {
    var motionTargets = document.querySelectorAll('.snow, .wreath-accent');
    if (motionTargets.length) {
      var motionObserver = new IntersectionObserver(function (entries) {
        Array.prototype.forEach.call(entries, function (entry) {
          entry.target.classList.toggle('is-paused', !entry.isIntersecting);
        });
      });
      Array.prototype.forEach.call(motionTargets, function (el) {
        motionObserver.observe(el);
      });
    }
  }

  /* -------------------------------------------------------------- phone --- */
  Array.prototype.forEach.call(document.querySelectorAll('a[href^="tel:"]'), function (link) {
    link.addEventListener('click', function () {
      if (typeof window.__loadGtag === 'function') window.__loadGtag();
      if (typeof gtag === 'function') gtag('event', 'phone_click');
    });
  });

  /* ---------------------------------------------------------------- form --- */
  /* Quote and contact forms post to /send-lead-notification, then go to
     /thank-you. generate_lead fires only after that call returns ok.
     A ~1.5s fallback navigates even if the call hangs; a failed call still
     navigates and skips the event. Turnstile loads on the first focus or
     input, and submit stays blocked until a token exists. */
  var PLACEHOLDER_ACTION = 'https://example.invalid/oleary-quote-endpoint';
  var LEAD_NOTIFICATION_ENDPOINT = '/send-lead-notification';
  var NAV_FALLBACK_MS = 1500;
  var forms = document.querySelectorAll('form[data-quote-form]');
  var turnstileLoading = false;
  var turnstileReady = false;

  function collectFormFields(form) {
    var data = new FormData(form);
    var fields = {};
    Array.prototype.forEach.call(Array.from(new Set(data.keys())), function (key) {
      var values = data.getAll(key);
      fields[key] = values.length > 1 ? values : values[0];
    });
    return fields;
  }

  function renderTurnstile(form) {
    if (!window.turnstile) return;
    var widgets = form
      ? form.querySelectorAll('.cf-turnstile')
      : document.querySelectorAll('.cf-turnstile');
    Array.prototype.forEach.call(widgets, function (el) {
      if (el.getAttribute('data-rendered') === 'true') return;
      var sitekey = el.getAttribute('data-sitekey');
      if (!sitekey) return;
      el.setAttribute('data-rendered', 'true');
      window.turnstile.render(el, { sitekey: sitekey });
    });
  }

  function loadTurnstile(form) {
    if (turnstileReady) {
      renderTurnstile(form);
      return;
    }
    if (turnstileLoading) return;
    if (!document.querySelector('.cf-turnstile')) return;
    turnstileLoading = true;
    window.onOlearyTurnstileLoad = function () {
      turnstileReady = true;
      renderTurnstile();
    };
    var script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onOlearyTurnstileLoad';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  }

  function goToThankYou(form, recordLead) {
    if (form.__thankYouNavigated) return;
    form.__thankYouNavigated = true;
    if (recordLead && typeof gtag === 'function') {
      if (typeof window.__loadGtag === 'function') window.__loadGtag();
      gtag('event', 'generate_lead', {
        form_name: form.dataset.formName || form.id
      });
    }
    window.location.href = '/thank-you';
  }

  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('focusin', function () { loadTurnstile(form); });
    form.addEventListener('input', function () { loadTurnstile(form); });

    form.addEventListener('submit', function (event) {
      if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;

      // Cloudflare Turnstile writes its token into a hidden input once the
      // visitor passes the check. No token yet → hold the submission.
      var token = form.querySelector('[name="cf-turnstile-response"]');
      if (form.querySelector('.cf-turnstile') && (!token || !token.value)) {
        event.preventDefault();
        loadTurnstile(form);
        window.alert('Please complete the security check before submitting.');
        return;
      }

      if (form.getAttribute('action') !== PLACEHOLDER_ACTION) {
        // A real endpoint is wired up — let the browser submit it. The lead
        // notification still fires, and generate_lead only on a successful
        // response (navigation is the browser's, so the fallback doesn't apply).
        fetch(LEAD_NOTIFICATION_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(collectFormFields(form)),
          keepalive: true
        }).then(function (res) {
          if (res.ok && typeof gtag === 'function') {
            gtag('event', 'generate_lead', {
              form_name: form.dataset.formName || form.id
            });
          }
        }).catch(function (err) {
          console.error('Lead notification failed:', err);
        });
        return;
      }

      event.preventDefault();
      var settled = false;
      var timer = window.setTimeout(function () {
        if (settled) return;
        settled = true;
        goToThankYou(form, false);
      }, NAV_FALLBACK_MS);

      fetch(LEAD_NOTIFICATION_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectFormFields(form)),
        keepalive: true
      }).then(function (res) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        goToThankYou(form, res.ok);
      }).catch(function (err) {
        console.error('Lead notification failed:', err);
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        goToThankYou(form, false);
      });
    });
  });
})();
