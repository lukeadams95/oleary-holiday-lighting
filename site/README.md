# O'Leary Holiday Lighting — website

Static site built from the Claude Design handoff bundle in `../project/`.
Plain HTML, one stylesheet, one small script. No framework, no build step
needed to deploy.

## Deploying

Upload the contents of this folder as-is. Any static host works (Netlify,
Vercel, Cloudflare Pages, S3, or plain shared hosting). There is nothing to
compile and no server-side code.

To preview locally:

```
cd site && python3 -m http.server 8000
```

## Layout

```
site/
  *.html          14 pages
  css/site.css    the whole design system
  js/site.js      mobile menu, Services dropdown, FAQ accordion, form guard
  images/         photography, logo and icons carried over from the design
```

| Page | File |
|---|---|
| Home | `index.html` |
| Services | `services.html` |
| Roofline Lighting | `roofline-lighting.html` |
| Wreaths | `wreaths.html` |
| Tree & Bush Lighting | `tree-bush-lighting.html` |
| Ground Lighting | `ground-lighting.html` |
| Maintenance & Storage | `maintenance-storage.html` |
| About Us | `about-us.html` |
| Reviews | `reviews.html` |
| Service Areas | `service-areas.html` |
| FAQ | `faq.html` |
| Contact | `contact.html` |
| Request a Quote | `request-a-quote.html` |
| Privacy Policy | `privacy-policy.html` |

## Before launch — three things to do

**1. Connect the forms.** All three forms (homepage hero, Contact, Request a
Quote) currently post to a placeholder:

```html
action="https://example.invalid/oleary-quote-endpoint"
```

Replace that `action` on each `<form data-quote-form>` with your real endpoint
(Formspree, Netlify Forms, a CRM webhook, whatever you use). `js/site.js`
watches for the placeholder and shows a "not connected yet" notice instead of
submitting; as soon as the `action` changes, that guard steps aside and the
form posts normally. Delete the guard block in `js/site.js` once it's wired.

Separately from that endpoint, every submission also emails a lead
notification to `olearylighting@gmail.com` via the `send-lead-notification`
Netlify function (`../netlify/functions/send-lead-notification.mts`), backed
by [Resend](https://resend.com). That requires a `RESEND_API_KEY` environment
variable set on the Netlify site — nothing to change in the form markup for
it, and it fires in parallel with whatever the form's own `action` does, so a
failed email never blocks a submission.

**2. Fill the `[CLIENT TO CONFIRM — …]` placeholders.** These are deliberate,
carried over from the design, and are visible on the page. Search the folder:

```
grep -rn "CLIENT TO CONFIRM" *.html
```

They cover the award name and year, years in business, prices and wreath
sizes, booking and takedown windows, hours, deposit policy, insurance, and the
final city list.

**3. Swap the remaining photo placeholders.** Blocks reading "Photos coming
soon" are waiting on client photography:

```
grep -rln "Photos coming soon" *.html
```

To fill one, replace

```html
<div class="tile__media"><span class="tile__placeholder">Photos coming soon</span></div>
```

with

```html
<div class="tile__media" style="background-image:url('images/your-photo.webp')"></div>
```

Also still to fill in: the Facebook and Instagram links in the footer (`href="#"`),
and the Google Business Profile / Facebook links on the Contact page.

## Feedbucket review widget

`<head>` on every page carries the Feedbucket widget, gated to the preview
host so the client can leave feedback there:

```js
if (location.hostname === "oleary-holiday-lighting.pages.dev") { ... }
```

It does not load on `olearyholidaylighting.com`, on `localhost`, or on
branch-preview subdomains — only on that exact host. Nothing to undo at
launch, but the block can be deleted from `tools/build.py` (`FEEDBUCKET`)
once review is finished.

## Design system

Set in `:root` at the top of `css/site.css`, so a change there flows through
every page.

| Token | Value | Use |
|---|---|---|
| `--red` | `#C8102E` | Buttons, headings, numerals, accents |
| `--red-deep` | `#8E0B20` | Button hover |
| `--red-band` | `#E95259` | Full-bleed red section bands |
| `--warm` | `#FAF7F4` | Alternating section background |
| `--ink` / `--ink-60` | `#1A1A1A` / `#4A4A4A` | Body text / secondary text |
| `--night` | `#0E1420` | Hero overlays, photo placeholders |
| `--border` | `#EAE6E1` | Card and input borders |

Type: **Bitter 700** for headings, **Archivo** 400/600/700 for everything else,
both from Google Fonts. Sections alternate white → cream → red band. Cards are
12px radius with a 1px `#EAE6E1` border; photo tiles are 16px radius with a
soft shadow and an optional red badge straddling the bottom edge.

## Responsive behaviour

The design prototype was a fixed 1440px canvas that scaled down proportionally,
which made text unreadable on a phone. This build is genuinely responsive
instead: the desktop layout matches the prototype at 1440px, and below that
sections stack, grids collapse, and type scales down. The nav becomes a
hamburger menu at 900px. Verified free of horizontal overflow from 360px to
1920px.

## Regenerating the pages

The header and footer are byte-identical on all 14 pages — the client's
consistency audit asked for exactly that, and hand-copying them fourteen times
is how that promise gets broken. So the shell lives once in `../tools/build.py`
and each page contributes only its `<main>`, in `../tools/pages/<slug>.html`.

```
python3 tools/build.py
```

This is optional tooling. The generated `.html` files are complete and checked
in; you can edit them directly if you prefer, but then edit `tools/pages/`
too — or delete `tools/` — so the two don't drift apart.
