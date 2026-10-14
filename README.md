# Three Principles

Starting indicators for diagnosing the state of small areas. Site for the Three Principles Initiative: https://three-principles.org

The site is built around the **Open Problem Brief** (draft v0.5), a request for critique, not for funding.

## Pages
- `index.html` Home
- `brief.html` / `brief.pdf` Full text of the brief, with references
- `evidence.html` Field accounts (SFOCSG, Nairobi, in the organisation's approved words)
- `prototype.html` Country-level prototype map (hand-entered approximate values; not the intended unit)
- `framework.html` Redirects to `brief.html` (old links)

## Notes
- Static HTML, no build step. Deployed on Cloudflare Pages from this repository.
- `d3.min.js` (ISC, d3 7.8.5), `topojson-client.min.js` (ISC, 3.1.0) and `world-110m.json` (world-atlas 2.0.2, from Natural Earth, public domain) are bundled so the map has no third-party runtime dependency.
- `og-image.html` is the source of `og-image.png` (1200x630).
- The brief text is licensed CC BY 4.0. The SFOCSG account is SFOCSG's and is used with their permission and attribution.
- Contact: [LinkedIn](https://www.linkedin.com/company/109664349/) · [X](https://x.com/3principles_org). Critique via GitHub Issues will open once there is enough traffic to need it.
