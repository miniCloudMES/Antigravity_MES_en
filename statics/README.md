# Static Files

App-level static files go here. Django collectstatic will gather them into STATIC_ROOT.

## Vendor 前端資源（`vendor/`）

所有第三方前端資源已**本地化（self-hosted）**，不再依賴外部 CDN，
可在工廠內網 / 離線環境正常運作。來源與版本如下：

| 資源 | 版本 | 路徑 | 來源 |
|---|---|---|---|
| Bootstrap | 5.3.2 | `vendor/bootstrap/` | npm `bootstrap` |
| Bootstrap Icons | 1.11.1 | `vendor/bootstrap-icons/` | npm `bootstrap-icons`（含 woff/woff2 字型） |
| jQuery | 3.6.0 | `vendor/jquery/jquery.min.js` | npm `jquery` |
| jQuery UI | 1.13.2 | `vendor/jquery-ui/` | code.jquery.com 官方發行（含 base theme 圖片） |
| Chart.js | 4.4.6 | `vendor/chart.js/chart.umd.js` | npm `chart.js`（UMD build） |
| Cropper.js | 1.6.2 | `vendor/cropperjs/` | npm `cropperjs` |
| Quill | 2.0.3 | `vendor/quill/` | npm `quill`（`quill.js` + `quill.snow.css`） |
| Inter 字型 | 4 weights (300/400/600/800) | `vendor/inter/` | Google Fonts（CSS 已改寫為本地相對路徑） |

### 升級方式

1. 下載新版本 npm tarball 或官方發行檔，覆蓋 `vendor/` 對應檔案。
2. 若新版本的 CSS 內含相對路徑資源（字型、圖片），**必須一併複製**（如
   `bootstrap-icons/font/fonts/`、`jquery-ui/themes/base/images/`）。
3. 更新模板中對應的 `{% static 'vendor/...' %}` 路徑（若檔名改變）。
4. 執行 `python manage.py collectstatic` 驗證。

> 注意：模板一律透過 `{% static %}` 引用 `vendor/`，不要直接寫死路徑或改回 CDN。
