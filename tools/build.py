#!/usr/bin/env python3
"""Assemble the O'Leary Holiday Lighting static site.

The client's consistency audit asked for a byte-identical header and footer on
every page, with the active nav item as the only difference. Keeping fourteen
hand-copied headers in sync is how that promise gets broken, so the shell lives
here once and each page contributes only its <main>.

    python3 tools/build.py

Output is plain static HTML in site/ — no runtime dependency on this script.
Each page fragment lives in tools/pages/<slug>.html and opens with a JSON
front-matter block delimited by <!--meta ... -->:

    <!--meta
    {"slug": "wreaths", "title": "...", "description": "...",
     "nav": "services", "service": "wreaths"}
    -->

`nav` marks the top-level nav item to highlight (home, services, about,
reviews, areas, faq, contact, or "" for none). `service` marks the dropdown
child to highlight.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "tools" / "pages"
OUT = ROOT / "site"

NAV_ITEMS = [
    ("home", "index.html", "Home"),
    ("services", "services.html", "Services"),
    ("about", "about-us.html", "About Us"),
    ("reviews", "reviews.html", "Reviews"),
    ("areas", "service-areas.html", "Service Areas"),
    ("faq", "faq.html", "FAQ"),
    ("contact", "contact.html", "Contact"),
]

SERVICES = [
    ("roofline", "roofline-lighting.html", "Roofline Lighting"),
    ("wreaths", "wreaths.html", "Wreaths"),
    ("tree-bush", "tree-bush-lighting.html", "Tree &amp; Bush Lighting"),
    ("ground", "ground-lighting.html", "Ground Lighting"),
    ("maintenance", "maintenance-storage.html", "Maintenance &amp; Storage"),
]

META_RE = re.compile(r"^<!--meta\s*(\{.*?\})\s*-->\s*", re.S)

# Repeated blocks. A fragment calls one with {{name|arg|arg}} on its own line.
PARTIAL_RE = re.compile(r"^([ \t]*)\{\{([a-z-]+)((?:\|[^}\n]*)*)\}\}[ \t]*$", re.M)
INLINE_RE = re.compile(r"\{\{([a-z-]+)((?:\|[^}\n]*)*)\}\}")

TRUST_BAR = """<div class="trust-bar">
  <div class="container trust-bar__inner">
    <p class="trust-bar__item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
      <span>Firefighter Owned</span>
    </p>
    <span class="trust-bar__rule"></span>
    <p class="trust-bar__item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" aria-hidden="true"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/><path d="M9 12l2 2 4-4"/></svg>
      <span>Award-Winning</span>
    </p>
    <span class="trust-bar__rule"></span>
    <p class="trust-bar__item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>
      <span>Christmas Lights Only</span>
    </p>
    <span class="trust-bar__rule"></span>
    <p class="trust-bar__item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" aria-hidden="true"><path d="M12 21s-7-4.5-9.5-9C.9 8.5 2 5 5.5 5c2 0 3.5 1.3 4.5 2.8C11 6.3 12.5 5 14.5 5 18 5 19.1 8.5 21.5 12c-2.5 4.5-9.5 9-9.5 9z"/></svg>
      <span>Serving Johnson County</span>
    </p>
  </div>
</div>"""

CHECK_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C8102E" '
    'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 6L9 17l-5-5"/></svg>'
)

GOOGLE_SVG = (
    '<svg width="{size}" height="{size}" viewBox="0 0 48 48" aria-hidden="true">'
    '<path fill="#4285F4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z"/>'
    '<path fill="#34A853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z"/>'
    '<path fill="#FBBC05" d="M11.69 28.18c-.44-1.32-.69-2.73-.69-4.18s.25-2.86.69-4.18v-5.7H4.34C2.85 17.09 2 20.45 2 24s.85 6.91 2.34 9.88l7.35-5.7z"/>'
    '<path fill="#EA4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z"/></svg>'
)

GOOGLE_LISTING = (
    "https://www.google.com/search?sca_esv=d777865217e22ae8&amp;"
    "sxsrf=APpeQnthfQNH0PeRcALQ8O2CAj6hvy6D5Q:1788441450674&amp;kgmid=/g/11zjq86n1s&amp;"
    "q=O%27Leary+Holiday+Lighting,+LLC&amp;shem=dlvs1,epsd1,ltae,rimspwouoe&amp;shndl=30&amp;"
    "source=sh/x/loc/uni/m1/3&amp;kgs=c6fabfb8bf140b2b&amp;"
    "utm_source=dlvs1,epsd1,ltae,rimspwouoe,sh/x/loc/uni/m1/3"
)

CITY_COLS = (
    ["Overland Park", "Olathe", "Leawood", "Stilwell", "Louisburg", "Paola"],
    ["Lenexa", "Prairie Village", "Shawnee", "Spring Hill", "Blue Springs", "Lee's Summit"],
)


def p_trust_bar():
    return TRUST_BAR


def p_check(text=""):
    return f"<li>{CHECK_SVG}<span>{text}</span></li>"


def p_google(size="16"):
    return GOOGLE_SVG.format(size=size)


def p_cities(heading="Where we install", image="", badge="", note="", bg="white"):
    """The city pill grid with a photo between the two columns."""
    def col(names):
        return "\n".join(
            f'          <a class="city-pill" href="service-areas.html">{n}</a>'
            for n in names
        )

    return f"""<section class="section section--{bg} section--tall has-badge">
  <div class="container">
    <h2 class="h2" style="text-align:center;margin-bottom:40px">{heading}</h2>
    <div class="cities">
      <div class="cities__col">
{col(CITY_COLS[0])}
      </div>
      <div class="tile cities__photo">
        <div class="tile__media" style="background-image:url('images/{image}')"></div>
        <span class="badge">{badge}</span>
      </div>
      <div class="cities__col">
{col(CITY_COLS[1])}
      </div>
    </div>
    <p class="note">{note}</p>
  </div>
</section>"""


def p_cta(heading="Ready to see your house lit up?",
          line="Free on-site quote. Booking now for the 2026 season.",
          foot=""):
    foot_html = f'\n    <p class="cta-banner__foot">{foot}</p>' if foot else ""
    return f"""<section class="cta-banner">
  <div class="cta-banner__bg" style="background-image:url('images/cta-house-lit.webp')"></div>
  <div class="cta-banner__scrim"></div>
  <div class="cta-banner__inner">
    <h2 class="h2">{heading}</h2>
    <p class="cta-banner__line">{line}</p>
    <div class="btn-row btn-row--cta">
      <a class="btn btn--primary" href="request-a-quote.html">Request a Free Quote</a>
      <a class="btn btn--outline-light" href="tel:9134268387">Call (913) 426-8387</a>
    </div>{foot_html}
  </div>
</section>"""


PARTIALS = {
    "trust-bar": p_trust_bar,
    "cities": p_cities,
    "cta": p_cta,
    "check": p_check,
    "google": p_google,
    "google-url": lambda: GOOGLE_LISTING,
}


def expand_partials(text, source):
    def sub(match):
        indent, name, rawargs = match.group(1), match.group(2), match.group(3)
        if name not in PARTIALS:
            raise SystemExit(f"{source}: unknown partial {{{{{name}}}}}")
        args = [a for a in rawargs.split("|")[1:]] if rawargs else []
        block = PARTIALS[name](*args)
        return "\n".join(indent + ln if ln else ln for ln in block.split("\n"))

    text = PARTIAL_RE.sub(sub, text)
    # Second pass for partials used inline (inside an attribute or list item).
    return INLINE_RE.sub(
        lambda m: PARTIALS[m.group(1)](*[a for a in m.group(2).split("|")[1:]])
        if m.group(1) in PARTIALS
        else m.group(0),
        text,
    )


def desktop_nav(active_nav, active_service):
    out = ['    <nav class="nav" aria-label="Main">']
    for key, href, label in NAV_ITEMS:
        active = key == active_nav
        cls = "nav__link is-active" if active else "nav__link"
        current = ' aria-current="page"' if active and key != "services" else ""
        if key == "services":
            out.append('      <div class="nav__item">')
            out.append(
                f'        <a class="{cls}" href="{href}" aria-haspopup="true">{label}</a>'
            )
            out.append('        <div class="dropdown">')
            for skey, shref, slabel in SERVICES:
                scls = ' class="is-active"' if skey == active_service else ""
                scur = ' aria-current="page"' if skey == active_service else ""
                out.append(f'          <a{scls} href="{shref}"{scur}>{slabel}</a>')
            out.append("        </div>")
            out.append("      </div>")
        else:
            out.append(f'      <a class="{cls}" href="{href}"{current}>{label}</a>')
    out.append("    </nav>")
    return "\n".join(out)


def mobile_nav(active_nav, active_service):
    out = ['  <nav class="mobile-menu" aria-label="Mobile">']
    for key, href, label in NAV_ITEMS:
        active = key == active_nav
        cls = ' class="is-active"' if active else ""
        cur = ' aria-current="page"' if active and key != "services" else ""
        out.append(f"    <a{cls} href=\"{href}\"{cur}>{label}</a>")
        if key == "services":
            for skey, shref, slabel in SERVICES:
                scls = "is-sub is-active" if skey == active_service else "is-sub"
                scur = ' aria-current="page"' if skey == active_service else ""
                out.append(f'    <a class="{scls}" href="{shref}"{scur}>{slabel}</a>')
    out.append('    <a href="request-a-quote.html">Request a Quote</a>')
    out.append("  </nav>")
    return "\n".join(out)


# Feedbucket review widget. Gated to the Cloudflare Pages preview host so the
# client can leave feedback there and it never loads on the live site. Remove
# this block (and the {feedbucket} slot below) once review is finished.
FEEDBUCKET = """<script>
  /* Feedbucket review widget — preview host only, never the live site. */
  if (location.hostname === "oleary-holiday-lighting.pages.dev") {
    (function (k) {
      var s = document.createElement("script");
      s.defer = true;
      s.src = "https://cdn.feedbucket.app/assets/feedbucket.js";
      s.dataset.feedbucket = k;
      document.head.appendChild(s);
    })("kRWOaFJvMYHvpk1CEI79");
  }
</script>"""

SHELL_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@700&amp;family=Archivo:wght@400;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/site.css">
{feedbucket}
</head>
<body>

<!-- ===================================================== HEADER ========= -->
<header class="site-header">
  <div class="site-header__bar">
    <a class="site-header__logo" href="index.html">
      <img src="images/logo.webp" alt="O'Leary Holiday Lighting">
    </a>

{desktop_nav}

    <div class="site-header__cta">
      <a class="site-header__phone" href="tel:9134268387">(913) 426-8387</a>
      <a class="site-header__quote" href="request-a-quote.html">Request a Quote</a>
    </div>

    <button class="nav-burger" type="button" aria-label="Menu" aria-expanded="false">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
  </div>

{mobile_nav}
</header>

"""

SHELL_FOOT = """

<!-- ===================================================== FOOTER ========= -->
<footer class="site-footer">
  <div class="container">
    <div class="site-footer__grid">
      <div>
        <img src="images/logo.webp" alt="O'Leary Holiday Lighting">
        <p class="site-footer__blurb">Custom Christmas light installation for Johnson County, Kansas.</p>
        <div class="site-footer__contact">
          <a href="tel:9134268387">(913) 426-8387</a>
        </div>
        <div class="social">
          <a class="social__fb" href="#" aria-label="Facebook">f</a>
          <a class="social__ig" href="#" aria-label="Instagram"><span><span></span></span></a>
        </div>
      </div>
      <div>
        <p class="site-footer__col-title">SERVICES</p>
        <div class="site-footer__links">
          <a href="roofline-lighting.html">Roofline Lighting</a>
          <a href="wreaths.html">Wreaths</a>
          <a href="tree-bush-lighting.html">Tree &amp; Bush Lighting</a>
          <a href="ground-lighting.html">Ground Lighting</a>
          <a href="maintenance-storage.html">Maintenance &amp; Storage</a>
        </div>
      </div>
      <div>
        <p class="site-footer__col-title">COMPANY</p>
        <div class="site-footer__links">
          <a href="about-us.html">About Us</a>
          <a href="reviews.html">Reviews</a>
          <a href="faq.html">FAQ</a>
          <a href="contact.html">Contact</a>
        </div>
      </div>
      <div>
        <p class="site-footer__col-title">SERVICE AREAS</p>
        <div class="site-footer__links">
          <a href="service-areas.html">Overland Park</a>
          <a href="service-areas.html">Olathe</a>
          <a href="service-areas.html">Leawood</a>
          <a href="service-areas.html">Lenexa</a>
        </div>
      </div>
    </div>
    <div class="site-footer__bar">
      <span>&copy; 2026 O'Leary Holiday Lighting LLC &middot; Overland Park, KS</span>
      <a href="privacy-policy.html">Privacy Policy</a>
    </div>
  </div>
</footer>

<script src="js/site.js"></script>
</body>
</html>
"""


def build():
    fragments = sorted(p for p in PAGES.glob("*.html") if not p.name.startswith("_"))
    if not fragments:
        raise SystemExit("no page fragments found in tools/pages/")

    for frag in fragments:
        raw = frag.read_text()
        match = META_RE.match(raw)
        if not match:
            raise SystemExit(f"{frag.name}: missing <!--meta {{...}} --> front matter")
        meta = json.loads(match.group(1))
        body = expand_partials(raw[match.end():].rstrip(), frag.name) + "\n"

        page = (
            SHELL_HEAD.format(
                title=meta["title"],
                description=meta["description"],
                feedbucket=FEEDBUCKET,
                desktop_nav=desktop_nav(meta.get("nav", ""), meta.get("service", "")),
                mobile_nav=mobile_nav(meta.get("nav", ""), meta.get("service", "")),
            )
            + body
            + SHELL_FOOT
        )
        target = OUT / f"{meta['slug']}.html"
        target.write_text(page)
        print(f"  wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build()
