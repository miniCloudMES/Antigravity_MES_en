# Static Files

App-level static files go here. Django collectstatic will gather them into STATIC_ROOT.

## Vendor Frontend Assets (`vendor/`)

All third-party frontend assets are **self-hosted**; no external CDN is required, so they
keep working on a factory intranet or in an offline environment. Sources and versions:

| Asset | Version | Path | Source |
|---|---|---|---|
| Bootstrap | 5.3.2 | `vendor/bootstrap/` | npm `bootstrap` |
| Bootstrap Icons | 1.11.1 | `vendor/bootstrap-icons/` | npm `bootstrap-icons` (includes woff/woff2 fonts) |
| jQuery | 3.6.0 | `vendor/jquery/jquery.min.js` | npm `jquery` |
| jQuery UI | 1.13.2 | `vendor/jquery-ui/` | official code.jquery.com release (includes base theme images) |
| Chart.js | 4.4.6 | `vendor/chart.js/chart.umd.js` | npm `chart.js` (UMD build) |
| Cropper.js | 1.6.2 | `vendor/cropperjs/` | npm `cropperjs` |
| Quill | 2.0.3 | `vendor/quill/` | npm `quill` (`quill.js` + `quill.snow.css`) |
| Inter font | 4 weights (300/400/600/800) | `vendor/inter/` | Google Fonts (CSS rewritten to local relative paths) |

### Upgrading

1. Download the new npm tarball or official release and overwrite the matching files under `vendor/`.
2. If the new CSS references relative assets (fonts, images), you **must copy those too** (e.g.
   `bootstrap-icons/font/fonts/`, `jquery-ui/themes/base/images/`).
3. Update the matching `{% static 'vendor/...' %}` paths in templates if filenames changed.
4. Run `python manage.py collectstatic` to verify.

> Note: templates must always reference `vendor/` through `{% static %}` — never hard-code
> paths or switch back to a CDN.
