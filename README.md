# Antigravity_MES

Django 製造執行系統（MES），含組織/設備/物料/產品/供應商/客戶/生產/文件/檔案庫九大模組、角色權限（admin / manager / operator）、SQLite 資料庫、CI 測試與 uWSGI/Nginx 佈署設定。

## 快速開始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations Customer Dashboard Documents Equipment FileLibrary Material Orgnization Product Production Supplier 
python manage.py migrate
python manage.py runserver 127.0.0.1:9090
```

- 首頁 Dashboard：http://127.0.0.1:9090/
- Admin：http://127.0.0.1:9090/admin/

## 登入帳號（重要）

系統登入**只接受員工編號（emp_no）**，不支援 username 登入。
`createsuperuser` 建立的帳號沒有對應員工資料，直接登入會失敗，需先綁定：

```bash
# 1. 建立 superuser
python manage.py createsuperuser

# 2. 將 superuser 綁定為員工（自動建立部門/職位）
python manage.py create_employee --username <你的superuser帳號> --emp-no EMP-001 --role admin
```

之後登入：
- **帳號**：`EMP-001`（員工編號）
- **密碼**：superuser 的密碼

### create_employee 參數

| 參數 | 預設 | 說明 |
|------|------|------|
| `--username` | 必填 | createsuperuser 建立的帳號 |
| `--emp-no` | `EMP-001` | 登入用的員工編號（需唯一） |
| `--role` | `admin` | `admin` / `manager` / `operator` |
| `--name` | username | 員工姓名 |
| `--dept` / `--dept-name` | `D001` / `管理部` | 部門代碼/名稱（不存在自動建立） |
| `--position` / `--position-name` | `P001` / `管理職` | 職位代碼/名稱（不存在自動建立） |

> 角色權限：`admin` 完整權限；`manager` 可新增/編輯；`operator` 僅瀏覽。模板層以 `is_manager` / `is_admin` context 控制按鈕顯示，後端視圖亦用 `RoleRequiredMixin` / `@role_required` 雙重防護。

## Tech Stack

| 工具 | 版本/備註 |
|---|---|
| Python / Django | 3.12 / 5.2 |
| 資料庫 | SQLite（開發用），可往 PostgreSQL 遷移 |
| CSS / Forms | Bootstrap 5（Linear Light Design）+ django-crispy-forms + crispy-bootstrap5 |
| 圖片 / 影片 | Pillow 12.2.0 / ffmpeg（H.264 轉檔） |
| QR-Code | qrcode 8.2（Pillow 產生 PNG） |
| WSGI | uWSGI（见 `uwsgi.ini`） |
| Proxy | Nginx（见 `Nginx.md`） |
| CI | GitHub Actions（`.github/workflows/django.yml`） |

## App 架構

```
miniMES/
├── settings.py / urls.py / wsgi.py
│
├── Dashboard/            # 首頁 + 儀表板
├── Orgnization/          # 組織：部門 / 職位 / 員工（含角色權限）
├── Equipment/            # 設備：分類 / 設備 / 維護紀錄
├── Material/             # 物料：分類 / 物料 / 庫存交易
├── Product/              # 產品：分類 / 產品
├── Supplier/             # 供應商：分類 / 供應商
├── Customer/             # 客戶：客戶資料（編號/聯絡人/統一編號等）
├── Production/           # 生產：工單（含製程步驟）/ BOM
├── Documents/            # 文件：分類 / 文件 / 多圖 / 審核紀錄（簽核流程）
├── FileLibrary/          # 檔案庫：分類 / 檔案（分片上傳 / 影片轉檔）
│
├── templates/            # 全站共用基底樣板
│   └── registration/
│       └── login.html    # Django auth 登入頁
│
└── statics/              # 靜態檔（CSS / JS）
```

## 模組設計總覽

### 1. Dashboard
- `LandingPageView`（未登入首頁）、`DashboardView`（登入後儀表板）
- **儀表板模板可切換**：原版（Linear Light）與工業風（Data-Dense，`ui-ux-pro-max` 設計系統：藍 `#1E40AF` / 琥珀 `#F59E0B`、KPI 卡片、資料表、Fira 字型降級 Inter）— 右上角按鈕切換，偏好存於 session；亦可 `?template=classic|industrial` 指定

### 2. Orgnization（組織管理）
| Model | 職責 |
|---|---|
| `Department` | 部門編號 code（唯一）、名稱、描述 |
| `Position` | 職位編號 code（唯一）、名稱、描述 |
| `Employee` | 員工編號 emp_no（唯一）、姓名、部門 FK、職位 FK、角色（admin/manager/operator）、照片等 |

- 登入綁定 `Employee.user`（OneToOne），自訂 `EmployeeNoBackend` 認證後端
- 照片上傳時 `post_delete` / `pre_save` 自動清除舊檔
- `create_employee` 管理命令：superuser 快速綁定員工

### 3. Equipment（設備管理）
| Model | 職責 |
|---|---|
| `EquipmentCategory` | 設備分類（唯一）、描述 |
| `Equipment` | 設備編號（唯一）、名稱、分類 FK、狀態（active/maintenance/broken/retired） |
| `MaintenanceRecord` | 維護/保養紀錄 |

### 4. Material（物料管理）
| Model | 職責 |
|---|---|
| `MaterialCategory` | 物料分類（唯一）、描述 |
| `Material` | 物料編號（唯一）、名稱、分類 FK、單位、庫存、安全庫存、供應商、位置 |
| `StockTransaction` | 庫存交易（INBOUND/OUTBOUND/ADJUST），記錄 `balance_after` |

- `is_low_stock`：`stock_quantity <= min_stock` 時低庫存警示

### 5. Product（產品管理）
| Model | 職責 |
|---|---|
| `ProductCategory` | 產品分類 |
| `Product` | 產品編號（唯一）、名稱、分類 FK、規格 |

### 6. Supplier（供應商管理）
| Model | 職責 |
|---|---|
| `SupplierCategory` | 供應商分類 |
| `Supplier` | 供應商編號（唯一）、名稱、分類 FK、聯絡資訊 |

### 7. Customer（客戶管理）
| Model | 職責 |
|---|---|
| `Customer` | 客戶編號（唯一）、名稱、聯絡人、電話、Email、地址、統一編號、啟用狀態 |

- 客戶編號格式驗證（英數字/底線/連字號）與即時唯一性檢查（`check_customer_id` AJAX 端點）

### 8. Production（生產管理）
| Model | 職責 |
|---|---|
| `WorkOrder` | 工單號碼（唯一）、產品 FK、數量、狀態、計畫/實際起迄時間 |
| `BOM` / `BOMItem` | 成品物料組成與用量（`unique_together = (bom, component)`） |
| `ProcessStep` | 製程步驟定義（工序、順序、負責職位） |
| `WorkOrderStep` | 工單製程步驟實例（狀態由製程步驟自動推導；含 Track In/Out 追蹤：進站/出站人員、實際設備、時間、備註；`is_picking_step` 標記領料站） |
| `MaterialPickingItem` | 領料站物料確認明細（依 BOM 應領數量、確認數量/人員/時間、備註） |

- 工單狀態：`PENDING` / `IN_PROGRESS` / `COMPLETED` / `CANCELLED` / `ABNORMAL`（異常）
- **領料站（第一站）**：建立工單且產品有啟用 BOM 時，自動建立「領料」工序（step 0）並依 BOM × 工單數量產生**物料確認清單**；員工逐項核對應領/庫存數量並填報確認數量與備註，**確認完成即直接扣減庫存**（OUTBOUND 交易，防重複扣料），領料站才算完成，**未確認前無法進站下一工序**（嚴格串行）；完工時不重複扣料
- **Track In / Track Out**：工序以「進站 / 出站」執行 — 進站填寫**進站數量與進站備註/狀況**（驗證嚴格串行、人員職位、設備狀態與 BOM 齊套，記錄進站人員、實際設備與時間）；出站強制填報良品/不良品/遺失數量且須平衡，填寫**出站備註/狀況**，記錄出站人員與時間；流程卡顯示各站數量變化與進出站狀況，並將良品/不良品數量**自動流轉到下一站**（進站數量 = 良品 + 不良品，遺失不流轉；跳過已取消工序）
- **完工扣料**：完成工單時檢查 BOM 子件庫存，不足即擋下；足夠則 atomic 扣料並寫入 StockTransaction（OUTBOUND）
- **工單 QR-Code**：明細頁頂部顯示編碼工單編號的 QR-Code PNG（`qrcode` 動態產生），可下載列印貼於現場

### 9. Documents（文件管理）
| Model | 職責 |
|---|---|
| `DocumentCategory` | 文件分類 |
| `Document` | 標題、編碼（唯一）、分類 FK、內容、版本、簽核狀態、送審/審核者 |
| `DocumentImage` | 文件多圖 |
| `DocumentAuditLog` | 審核操作歷程（建立/送審/核准/退回/撤回/啟用切換） |

- 簽核流程：`draft → pending → approved / rejected`；退回重送自動升版
- 權限：送審者本人可撤回；草稿/退回可編輯刪除；核准後僅 manager/admin 可編輯

### 10. FileLibrary（檔案庫）
| Model | 職責 |
|---|---|
| `FileCategory` | 檔案分類 |
| `LibraryFile` | 檔案、分類 FK、說明、上傳者、`video_status` / `video_standard` / `video_error`（影片轉檔） |

- **分片上傳**：>5MB 自動切 5MB 塊、進度條、斷點續傳、單檔上限 100MB
- **影片轉檔**：上傳影片背景轉為 720p / **H.264** / MP4（全瀏覽器相容），提供線上播放
- 權限：admin 上傳/編輯/刪除/分類管理；manager 可上傳；operator 僅瀏覽下載

## 角色權限矩陣

| 功能 | admin | manager | operator |
|------|:---:|:---:|:---:|
| 瀏覽 / 下載 | ✅ | ✅ | ✅ |
| 新增（各模組） | ✅ | ✅ | ❌ |
| 編輯 / 刪除 | ✅ | 部分 | ❌ |
| 文件送審 / 撤回 | ✅ | ✅ | ✅（本人） |
| 文件審核 | ✅ | ✅ | ❌ |
| 檔案庫上傳 | ✅ | ✅ | ❌ |
| 檔案庫刪除 / 分類管理 | ✅ | ❌ | ❌ |

## 資料庫關係圖（文字版）

```
Department 1 ────< Employee >──── 1 Position
MaterialCategory 1 ────< Material
Material 1 ────< StockTransaction
ProductCategory 1 ────< Product
Product 1 ────< WorkOrder >──── Customer
Product 1 ────< BOM 1 ────< BOMItem >──── Material (子件)
ProcessStep 1 ────< WorkOrderStep >──── WorkOrder
DocumentCategory 1 ────< Document >───── auth.User
Document 1 ────< DocumentImage / DocumentAuditLog
FileCategory 1 ────< LibraryFile >───── auth.User
```

## URL 架構（`miniMES/urls.py`）

| 前綴 | App | 說明 |
|---|---|---|
| `/admin/` | Django Admin | 超級使用者後台 |
| `/accounts/` | django.contrib.auth | 登入/登出/密碼重設 |
| `/` | Dashboard | 首頁/儀表板 |
| `/org/` | Orgnization | 部門/職位/員工管理 |
| `/equipment/` | Equipment | 設備管理 |
| `/material/` | Material | 物料管理 |
| `/product/` | Product | 產品管理 |
| `/supplier/` | Supplier | 供應商管理 |
| `/customer/` | Customer | 客戶管理 |
| `/production/` | Production | 工單/BOM/製程 |
| `/documents/` | Documents | 文件管理 |
| `/files/` | FileLibrary | 檔案庫 |

## CI（GitHub Actions）

- 檔案：`.github/workflows/django.yml`
- 觸發：push / PR 至 `main`
- 動作：checkout → Python 3.12 setup → `pip install -r requirements.txt` → `python manage.py test`

## 佈署

### uWSGI + Nginx

關鍵檔案：
- `uwsgi.ini`：uWSGI 啟動設定（含 `post-buffering=8192` 大檔上傳緩衝）
- `nginx.conf`：Nginx 設定
- `uwsgi_params`：Nginx→uWSGI 參數傳遞
- `Nginx.md`：操作指令與疑難排解

建議步驟：
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py collectstatic`（有靜態檔時）
5. 修改 `nginx.conf` 內 `/static`、`/media` 的 `alias` 路徑
6. 修改 `uwsgi.ini` 內 `chdir`、`wsgi-file`、`virtualenv` 路徑
7. `uwsgi --ini uwsgi.ini`
8. `sudo nginx -c /path/to/nginx.conf`

### 部署注意事項

- 部署時**只同步程式碼**，不覆蓋生產環境的 `db.sqlite3`、`media/`、`uwsgi.ini`、`nginx.conf`、`nginx.pid`
- `uwsgi.ini` 的 `virtualenv` 路徑需指向實際 venv
- 影片轉檔需伺服器安裝 ffmpeg（含 libx264）
- 新功能若改 model，需在伺服器執行 `python manage.py makemigrations <app> && python manage.py migrate`（migration 不進 git，依部署環境產生）

### 環境變數（安全設定）

`miniMES/settings.py` 支援以環境變數覆寫安全設定（未設定時退回開發用預設值，不影響本機開發）：

| 變數 | 預設 | 說明 |
|---|---|---|
| `DJANGO_SECRET_KEY` | 開發用金鑰（不建議生產使用） | 生產務必設定，可用 `openssl rand -hex 32` 產生 |
| `DJANGO_DEBUG` | `true` | 生產請設 `false` |
| `DJANGO_ALLOWED_HOSTS` | `*` | 逗號分隔的主機清單，例如 `example.com,www.example.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | 關閉 | 設 `true` 強制 HTTPS 跳轉（需在 Nginx 後方） |
| `DJANGO_SECURE_COOKIES` | 關閉 | 設 `true` 使 Session/CSRF cookie 僅經 HTTPS 傳送 |

範例：

```bash
export DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
export DJANGO_DEBUG=false
export DJANGO_ALLOWED_HOSTS=mes.example.com
uwsgi --ini uwsgi.ini
```

### 常見問題

- Nginx 上傳權限：`sudo chmod -R 775 /run/nginx/client_body_temp`
- 影片只有聲音沒畫面：確認轉檔 codec 為 H.264（`libx264`），H.265 在桌面 Chrome 不支援
- 大檔案上傳記憶體不足：確認 `uwsgi.ini` 有 `post-buffering = 8192`

## 開發者

- GitHub：[miniCloudMES/Antigravity_MES](https://github.com/miniCloudMES/Antigravity_MES)
# Antigravity_MES_en
# Antigravity_MES_en
