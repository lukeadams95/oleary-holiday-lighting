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

  /* ---------------------------------------------------------------- form --- */
  /* TODO(deploy): point every <form data-quote-form> at a real handler —
     set its `action` to your Formspree/Netlify/CRM endpoint and delete this
     block. Until then, submitting shows a confirmation instead of posting to
     the placeholder endpoint. */
  var PLACEHOLDER_ACTION = 'https://example.invalid/oleary-quote-endpoint';
  var forms = document.querySelectorAll('form[data-quote-form]');

  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('submit', function (event) {
      if (form.getAttribute('action') !== PLACEHOLDER_ACTION) return; // real endpoint wired up
      event.preventDefault();

      if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;

      var notice = form.querySelector('.form__status');
      if (!notice) {
        notice = document.createElement('p');
        notice.className = 'form__footnote form__status';
        notice.setAttribute('role', 'status');
        form.appendChild(notice);
      }
      notice.textContent =
        'Form not connected yet — add your form endpoint before launch. ' +
        'Call (913) 437-1221 in the meantime.';
    });
  });
})();
