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

SITE_URL = "https://www.olearyholidaylighting.com"
# Transactional / non-content pages that shouldn't be indexed or crawled.
SITEMAP_EXCLUDE = {"thank-you", "404"}


def page_url(slug):
    return SITE_URL + "/" if slug == "index" else f"{SITE_URL}/{slug}.html"


# --------------------------------------------------------------------------
# SEO: canonical / Open Graph / Twitter tags and JSON-LD structured data.
# Real, on-page data only — see seo-audit.md for what could and couldn't be
# verified, and for the one FAQ answer deliberately left out of FAQPage
# schema because its visible text still carries a "[CLIENT TO CONFIRM]"
# placeholder.
# --------------------------------------------------------------------------

ORG_ID = SITE_URL + "/#organization"
WEBSITE_ID = SITE_URL + "/#website"
BIZ_ID = SITE_URL + "/#localbusiness"

PHONE_E164 = "+19134268386"
FACEBOOK_URL = "https://www.facebook.com/share/1JNp1tX1uM/"
GBP_URL = "https://share.google/d3Q3Bb9cU76evWhM8"

# The Service Areas page is the authoritative city list — it's the one page
# whose sole job is naming the towns served. The homepage and About Us also
# list "Blue Springs" and "Lee's Summit" (Missouri cities absent here); that
# mismatch is flagged in seo-audit.md rather than silently resolved, since
# only the client knows which list is actually correct.
SERVICE_AREA_CITIES = [
    "Overland Park", "Olathe", "Leawood", "Lenexa", "Prairie Village",
    "Shawnee", "Gardner", "Spring Hill", "Stilwell", "De Soto",
    "Paola", "Louisburg", "Osawatomie", "Fontana", "Linn Valley",
]

OG_IMAGE_OVERRIDES = {
    "roofline-lighting": "roofline-hero.webp",
    "wreaths": "wreaths-hero.webp",
    "tree-bush-lighting": "tree-bush-hero.webp",
    "ground-lighting": "ground-hero.webp",
    "maintenance-storage": "maintenance-hero.webp",
    "services": "services-hero.webp",
    "about-us": "tommy-oleary.webp",
}


def og_image_url(slug):
    return f"{SITE_URL}/images/{OG_IMAGE_OVERRIDES.get(slug, 'hero-house.webp')}"


# slug -> (breadcrumb label, parent slug or None). A page absent from this
# map (index, thank-you, 404) gets no breadcrumb — it's either the root or
# not meant for organic entry.
BREADCRUMB_LABELS = {
    "about-us": ("About Us", None),
    "contact": ("Contact", None),
    "faq": ("FAQ", None),
    "reviews": ("Reviews", None),
    "service-areas": ("Service Areas", None),
    "request-a-quote": ("Request a Quote", None),
    "privacy-policy": ("Privacy Policy", None),
    "services": ("Services", None),
    "roofline-lighting": ("Roofline Lighting", "services"),
    "wreaths": ("Wreaths", "services"),
    "tree-bush-lighting": ("Tree & Bush Lighting", "services"),
    "ground-lighting": ("Ground Lighting", "services"),
    "maintenance-storage": ("Maintenance & Storage", "services"),
}


def breadcrumb_trail(slug):
    """List of (label, slug) from Home down to the current page, or None."""
    if slug not in BREADCRUMB_LABELS:
        return None
    label, parent = BREADCRUMB_LABELS[slug]
    trail = [("Home", "index")]
    if parent:
        trail.append((BREADCRUMB_LABELS[parent][0], parent))
    trail.append((label, slug))
    return trail


def breadcrumb_html(slug):
    trail = breadcrumb_trail(slug)
    if not trail:
        return ""
    items = []
    for i, (label, crumb_slug) in enumerate(trail):
        if i == len(trail) - 1:
            items.append(f'      <li aria-current="page">{label}</li>')
        else:
            # Relative filename, matching every other internal link on the site.
            href = "index.html" if crumb_slug == "index" else f"{crumb_slug}.html"
            items.append(f'      <li><a href="{href}">{label}</a></li>')
    return (
        '\n<nav class="breadcrumb" aria-label="Breadcrumb">\n'
        '  <div class="container">\n    <ol>\n'
        + "\n".join(items)
        + "\n    </ol>\n  </div>\n</nav>\n"
    )


def breadcrumb_jsonld(slug):
    trail = breadcrumb_trail(slug)
    if not trail:
        return None
    return {
        "@type": "BreadcrumbList",
        "@id": page_url(slug) + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": label, "item": page_url(crumb_slug)}
            for i, (label, crumb_slug) in enumerate(trail)
        ],
    }


# Each (question, answer) is transcribed verbatim from the page it maps to —
# nothing here that isn't visibly rendered there. That's what keeps FAQPage
# schema safe rather than a manual-action risk.
SERVICE_FAQS = {
    "roofline-lighting": [
        ("Do I need to buy the lights?", "No. Everything is ours and stays ours. That's what makes the maintenance and storage work."),
        ("What if something goes out in December?", "Call us. We come fix it, usually next day, at no extra cost."),
        ("Will the clips damage my roof or gutters?", "No. They're sized to your shingles and gutters and come off clean in January. Nothing gets stapled or nailed."),
        ("When should I book?", "ASAP. We fill up fast, and as spots on the schedule run out, price tends to increase."),
        ("Do you do commercial?", "Yes — we've done a number of commercial properties, including businesses and stores, HOAs, and a few city lighting projects."),
    ],
    "wreaths": [
        ("Can I get wreaths without a full light install?", "Yes, that's something we can do — it's just a little pricier on its own."),
        ("Are they real or artificial?", "Artificial. That's what lets us reuse them without any extra charge, and it keeps them from rotting away on the house."),
        ("How many can I get?", "As many as the house will hold. That's the point of the pricing."),
    ],
    "tree-bush-lighting": [
        ("How big a tree can you do?", "The tallest trees we've done are around 45 ft. Anything much taller than that needs a lift, which increases the price."),
        ("Will wrapping hurt the tree?", "No. Strands come off in January and nothing is fastened into the bark."),
        ("Can I add trees to a roofline quote?", "Yes. Most people do it at the on-site visit once they see the layout."),
        ("Do you light trees without a roofline install?", "Yes — same as with wreaths. It costs a bit more than it would as an add-on to a roofline install."),
    ],
    "ground-lighting": [
        ("Will it survive snow removal?", "Stakes sit clear of the walk and drive surface, but tell us where you plow or shovel and we'll route around it."),
        ("Can I add this to an existing quote?", "Yes. Easiest to decide at the on-site visit."),
        ("Do you do ground lighting on its own?", "Yes. It costs a bit more than it would as an add-on to a roofline install already in progress."),
        ("What about the backyard or patio?", "Yes."),
    ],
    "maintenance-storage": [
        ("Is there an extra charge for repairs?", "No."),
        ("How fast do you come out?", "Within 24 to 48 hours, though it's usually closer to 24."),
        ("When does takedown happen?", "We generally start takedowns January 2nd. We're at the weather's mercy in January, but we try to have everything down by mid-February."),
        ("Do I need to be home?", "No, for either takedown or repairs on the exterior."),
    ],
}

# The full FAQ page, minus "What areas do you serve?" — its visible answer
# currently contains a live "[CLIENT TO CONFIRM — final city list]"
# placeholder (see seo-audit.md), and baking that into FAQPage schema risks
# Google surfacing the placeholder text itself as a search result snippet.
FAQ_PAGE_QA = [
    ("How much does it cost?", "Every house is different — roofline length, height, pitch, and how much of the yard you want lit. That's why the quote is free and done on-site. New installs typically run around $750; rehangs of an existing setup are generally around $500."),
    ("What's included in the price?", "Design, all lights and clips and cords and timers, install, maintenance all season, takedown in January, and storage until next year. One price, no per-visit charges, no storage fee."),
    ("Do I pay up front?", "We collect a 50% deposit up front on new installs. The rest is due once the lights are put up."),
    ("When should I book?", "ASAP. We fill up fast, and as spots on the schedule run out, price tends to increase."),
    ("Do you offer a discount for booking early or rebooking?", "Yes — $25 off when your install is booked before November."),
    ("Do I buy the lights or do you?", "They're ours. You're not buying strands you have to store, replace, and re-hang — that's what makes the maintenance and storage work."),
    ("What kind of bulbs do you use?", "Commercial-grade C9 bulbs on rooflines, in warm white, cool white, or color. Mini lights on trees and bushes. We'll bring samples to the quote so you can see them against your brick or siding."),
    ("Can I pick the colors?", "Yes. We'll also show you what a color looks like on your house before you commit — it reads differently on red brick than on gray siding."),
    ("Can I keep the lights up past the season?", "We'll ask everyone at the start of the year who wants their lights down early and who doesn't mind if they stay up a little longer — that helps us coordinate takedowns. Everything we put up does come down by the end of the season, though."),
    ("How long does install take?", "An average-size roofline job takes about an hour for a first-time install. Reinstalls at a house we've already done usually take about half that."),
    ("Do I need to be home?", "No. We work on the exterior. If we need access to an outlet or a GFCI, we'll arrange that when we quote."),
    ("Will the clips damage my roof or gutters?", "No. Clips are sized to your shingles and gutters and come off clean in January. Nothing is stapled, nailed, or screwed into the house."),
    ("How high will you go?", "Second and third stories, steep pitches, and the spots other crews pass on. Firefighter owned — ladder work is the part we're least worried about."),
    ("Will you use my outdoor outlet, and what does it do to my electric bill?", "Yes, we run off your exterior outlets on a timer. We only use LED bulbs, which draw a lot less power than old glass incandescent bulbs — about 20 cents a day to run."),
    ("Something went out. What do I do?", "Call us. We come fix it, usually next day, at no extra charge."),
    ("What if a storm knocks something down?", "Same answer — call us and we'll come reset it. Wind and ice are the two things that move lights in Kansas, and we plan for both."),
    ("Is there a charge for repairs?", "No."),
    ("When do you take the lights down?", "We generally start takedowns January 2nd. We're at the weather's mercy in January, but we try to have everything down by mid-February."),
    ("Do I need to be home for takedown?", "No."),
    ("Where do the lights go afterward?", "Back to our warehouse. Everything gets checked and labeled to your house, so next season it goes up exactly the same way. Nothing takes up space in your garage."),
    ("Do you do anything besides Christmas lights?", "No. That's the point. Most companies in Kansas City hang lights to get through the winter and are back on landscaping by January. This is our whole season."),
    ("Are you insured?", "Yes — we're insured up to $1 million per occurrence, with a $2 million aggregate policy."),
    ("Do you do commercial properties?", "Yes — we've done a number of commercial properties, including businesses and stores, HOAs, and a few city lighting projects."),
]

# name, quote — exactly the reviews rendered on that specific page, all
# 5-star per their visible aria-labels. Deliberately not repeated on every
# page: aggregateRating/review schema is scoped to where the rating badge
# and review text are actually visible.
REVIEWS_ON_PAGE = {
    "index": [
        ("David Nawrocki", "Tommy has done a great job with our holiday lights for two years now. Our roof has high peaks and likely isn't an easy job, but he makes it look easy. He's a good communicator and very professional."),
        ("Hope Campbell", "We used O'Leary Holiday Lighting last season and are using them again this season. They gave us options on lighting schemes so we got exactly what we wanted. The prices were reasonable and did not vary from the quote. They returned to take the lights down and stored them for us."),
        ("Keagan Sinclair", "The team at O'Leary Holiday Lighting did such a great job on my lights in Leawood. I cannot recommend them enough. Super happy with how they turned out, and they handled everything, which made it super easy."),
    ],
    "reviews": [
        ("Maria Collins", "I can't recommend Tommy at O'Leary Holiday Lighting enough! We use him for our business and personal lighting. He's absolutely amazing—super responsive, professional, and does incredible work. Our Christmas lights look perfect every year, and he makes the whole process so easy and stress-free. 10/10 service!"),
        ("John Forkner", "Tommy did a fantastic job of getting our home in the Holiday spirit last year. We are already on his schedule to get them up early this year. I would highly recommend O'Leary Holiday Lighting for your holiday outdoor lighting project."),
        ("Alexis Kelford", "I can't say enough good things about this company! They make the whole process of putting up Christmas lights completely stress-free. Communication is always fast and easy, they get everything done quickly, and the results are absolutely beautiful every year. I love that they handle the storage, too."),
        ("Lauren Greve", "Tommy has installed our Christmas lights for 3 years and does a fantastic job every Christmas! He operates his business professionally, provides consistent communication & is always timely in both the install and take down, plus the prices are very reasonable."),
        ("Todd Crescio", "Tommy did a great job installing our Christmas lights on the outside of our home, as well as decorating our trees. He was prompt, professional, and made sure we were satisfied with the installation before he left. We would highly recommend O'Leary to anyone looking for holiday lighting."),
        ("Elizabeth Duroche", "We absolutely love O'Leary Holiday Lighting! They help bring the holidays to life around our house. They are professional, friendly & do a wonderful job! Thank you for being a part of our holiday tradition!"),
    ],
}

SERVICE_PAGE_NAMES = {
    "roofline-lighting": "Roofline Lighting",
    "wreaths": "Wreaths",
    "tree-bush-lighting": "Tree & Bush Lighting",
    "ground-lighting": "Ground Lighting",
    "maintenance-storage": "Maintenance, Takedown & Storage",
}


def organization_node():
    return {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": "O'Leary Holiday Lighting",
        "legalName": "O'Leary Holiday Lighting, LLC",
        "url": SITE_URL + "/",
        "logo": SITE_URL + "/images/logo.webp",
        "sameAs": [FACEBOOK_URL, GBP_URL],
    }


def website_node():
    return {
        "@type": "WebSite",
        "@id": WEBSITE_ID,
        "name": "O'Leary Holiday Lighting",
        "url": SITE_URL + "/",
        "publisher": {"@id": ORG_ID},
    }


def local_business_node(slug):
    node = {
        "@type": "HomeAndConstructionBusiness",
        "@id": BIZ_ID,
        "name": "O'Leary Holiday Lighting",
        "url": SITE_URL + "/",
        "telephone": PHONE_E164,
        "image": SITE_URL + "/images/logo.webp",
        "areaServed": [{"@type": "City", "name": c} for c in SERVICE_AREA_CITIES],
        "openingHoursSpecification": {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ],
            "opens": "08:00",
            "closes": "20:00",
        },
        "foundingDate": "2022",
        "parentOrganization": {"@id": ORG_ID},
    }
    if slug in REVIEWS_ON_PAGE:
        node["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": "5.0",
            "reviewCount": "44",
        }
        node["review"] = [
            {
                "@type": "Review",
                "author": {"@type": "Person", "name": name},
                "reviewRating": {"@type": "Rating", "ratingValue": "5", "bestRating": "5"},
                "reviewBody": quote,
            }
            for name, quote in REVIEWS_ON_PAGE[slug]
        ]
    return node


def faq_node(slug):
    qa = FAQ_PAGE_QA if slug == "faq" else SERVICE_FAQS.get(slug)
    if not qa:
        return None
    return {
        "@type": "FAQPage",
        "@id": page_url(slug) + "#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in qa
        ],
    }


def service_node(slug):
    name = SERVICE_PAGE_NAMES.get(slug)
    if not name:
        return None
    return {
        "@type": "Service",
        "@id": page_url(slug) + "#service",
        "name": name,
        "serviceType": name,
        "provider": {"@id": BIZ_ID},
        "areaServed": [{"@type": "City", "name": c} for c in SERVICE_AREA_CITIES],
        "url": page_url(slug),
    }


def jsonld_for(slug):
    graph = [organization_node(), website_node(), local_business_node(slug)]
    for node in (breadcrumb_jsonld(slug), faq_node(slug), service_node(slug)):
        if node:
            graph.append(node)
    data = {"@context": "https://schema.org", "@graph": graph}
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n</script>"
    )


def meta_tags_for(slug, meta):
    title = meta["title"]
    description = meta["description"]
    url = page_url(slug)
    image = og_image_url(slug)
    return f"""<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="O'Leary Holiday Lighting">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">
{jsonld_for(slug)}"""

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
      <a class="btn btn--outline-light" href="tel:9134268386">Call (913) 426-8386</a>
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

SHELL_HEAD_TOP = """<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RD7LE5J4YS"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-RD7LE5J4YS');
</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
"""

SHELL_HEAD_BOTTOM = """
<link rel="icon" type="image/x-icon" href="favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<meta name="theme-color" content="#C8102E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@700&amp;family=Archivo:wght@400;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/site.css">
{feedbucket}
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>

<!-- ===================================================== HEADER ========= -->
<header class="site-header">
  <div class="site-header__bar">
    <a class="site-header__logo" href="index.html">
      <img src="images/logo.webp" alt="O'Leary Holiday Lighting" width="123" height="81">
    </a>

{desktop_nav}

    <div class="site-header__cta">
      <a class="site-header__phone" href="tel:9134268386">(913) 426-8386</a>
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
        <img src="images/logo.webp" alt="O'Leary Holiday Lighting" width="161" height="110" loading="lazy">
        <p class="site-footer__blurb">Custom Christmas light installation for Johnson County, Kansas.</p>
        <div class="site-footer__contact">
          <a href="tel:9134268386">(913) 426-8386</a>
        </div>
        <div class="social">
          <a class="social__fb" href="https://www.facebook.com/share/1JNp1tX1uM/" aria-label="Facebook">f</a>
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

    slugs = []
    for frag in fragments:
        raw = frag.read_text()
        match = META_RE.match(raw)
        if not match:
            raise SystemExit(f"{frag.name}: missing <!--meta {{...}} --> front matter")
        meta = json.loads(match.group(1))
        body = expand_partials(raw[match.end():].rstrip(), frag.name) + "\n"
        slug = meta["slug"]

        page = (
            SHELL_HEAD_TOP.format(title=meta["title"], description=meta["description"])
            + meta_tags_for(slug, meta)
            + "\n"
            + SHELL_HEAD_BOTTOM.format(
                feedbucket=FEEDBUCKET,
                desktop_nav=desktop_nav(meta.get("nav", ""), meta.get("service", "")),
                mobile_nav=mobile_nav(meta.get("nav", ""), meta.get("service", "")),
            )
            + breadcrumb_html(slug)
            + body
            + SHELL_FOOT
        )
        target = OUT / f"{slug}.html"
        target.write_text(page)
        print(f"  wrote {target.relative_to(ROOT)}")
        slugs.append(slug)

    write_sitemap(slugs)
    write_robots()


def write_sitemap(slugs):
    urls = [
        SITE_URL + "/" if slug == "index" else f"{SITE_URL}/{slug}.html"
        for slug in slugs
        if slug not in SITEMAP_EXCLUDE
    ]
    body = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
    target = OUT / "sitemap.xml"
    target.write_text(xml)
    print(f"  wrote {target.relative_to(ROOT)}")


def write_robots():
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    target = OUT / "robots.txt"
    target.write_text(text)
    print(f"  wrote {target.relative_to(ROOT)}")


# Cloudflare Pages reads a plain-text `_redirects` file from the publish
# root. Every real page lives at an explicit `/slug.html` URL (see the
# module docstring), so any extensionless path 404s unless it's listed
# here.
#
# - "/contact" -> "/contact.html": Search Console reported this exact path
#   404ing, presumably from an old external link or a stale indexed URL
#   that never carried the extension. 301 it to the real page.
# - "/hibu-video-splash" -> "/": leftover URL from the site's previous
#   provider (Hibu), from before this static rebuild. It has no equivalent
#   page here, so send it to the homepage instead of leaving it a dead
#   link Google keeps re-checking.
REDIRECTS = [
    ("/contact", "/contact.html", 301),
    ("/hibu-video-splash", "/", 301),
]


def write_redirects():
    text = "".join(f"{src}  {dest}  {code}\n" for src, dest, code in REDIRECTS)
    target = OUT / "_redirects"
    target.write_text(text)
    print(f"  wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build()
    write_redirects()
