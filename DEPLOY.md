# نشر THE QS HUB (React + FastAPI) — دليل سريع

> المعمارية الجديدة: واجهة React (Vite) + خلفية FastAPI. الواجهة تُبنى وتُخدَّم من
> FastAPI على نفس الـorigin، فكل روابط الـAPI نسبية (`/api`, `/cache`) ولا تحتاج عنواناً ثابتاً.

## 1) التطوير المحلي (خدمتان)

```powershell
# الخلفية (FastAPI) على المنفذ 8000
uvicorn api.main:app --reload --port 8000

# الواجهة (Vite) على 5173 — تُمرِّر /api و /cache تلقائياً للخلفية (انظر vite.config.js)
cd frontend
npm install
npm run dev
```

افتح http://localhost:5173

## 2) بناء واختبار محلي بنمط الإنتاج

```powershell
cd frontend; npm run build; cd ..      # ينتج frontend/dist
uvicorn api.main:app --port 8000        # يخدّم الواجهة المبنية على /
```
افتح http://localhost:8000 (الواجهة) و http://localhost:8000/api/health (فحص الخلفية).

## 3) Docker (حاوية واحدة: واجهة + خلفية)

```powershell
docker build -f Dockerfile.web -t qshub-web .
docker run -p 8000:8000 --env-file .env qshub-web
```

## 4) النشر على Render

استخدم `render.web.yaml` كـ Blueprint (أو أعد تسميته إلى `render.yaml`).
عبّئ المتغيّرات السرّية في لوحة Render (`sync:false`).

## متغيّرات البيئة المطلوبة (الحدّ الأدنى للإطلاق)

| المتغيّر | الوصف |
|---|---|
| `JWT_SECRET` | سلسلة عشوائية طويلة — **إلزامي، بلا قيمة افتراضية في الإنتاج** |
| `APP_BASE_URL` | عنوان الخدمة العام (لروابط الدفع/العودة) |
| `TIDB_*` | اتصال قاعدة البيانات الإنتاجية |
| `DODO_*` | مفاتيح الدفع ومنتجات الخطط |
| `AI_API_KEY_1` | مفتاح Gemini |
| `SENTRY_DSN` | (اختياري) للمراقبة |

## ما تبقّى لإغلاق الإطلاق (خارج هذه الملفات)

- [ ] تقييد CORS في `api/main.py` على نطاق الواجهة بدل `["*"]`.
- [ ] حذف القيمة الاحتياطية لـ `JWT_SECRET` من `api/auth.py` (إلزام البيئة).
- [ ] وقف إرجاع توكن إعادة التعيين في `/api/auth/forgot-password` وربط SMTP.
- [ ] توصيل Dodo webhook (مسار داخل FastAPI أو خدمة `payment_webhook_app` منفصلة).
- [ ] تدوير كل الأسرار القديمة (خاصة توكن GitHub المكشوف في `.git/config`).
