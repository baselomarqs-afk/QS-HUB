# خارطة الطريق التفصيلية للوصول إلى 100/100

هذا الملف يوضح ما تم إنجازه وما يجب فعله خارج الكود للوصول إلى إطلاق Production كامل.

## الوضع الحالي بعد التعديلات

الكود أصبح جاهزا بقوة لمرحلة Staging / Private Beta:

- إعدادات آمنة عبر environment/secrets.
- Migration كامل للجداول الأساسية.
- Dodo Payments integration.
- FastAPI app (API + React frontend).
- Worker service منفصل.
- Storage abstraction.
- Usage limits.
- Audit logs.
- Billing page.
- Legal/Compliance pages.
- QTO Quality Report.
- Docker وDocker Compose.
- CI pipeline.
- Production readiness script.
- 31 اختبار ناجح.

## للوصول إلى 100/100 من ناحية Dev/SaaS

1. تدوير كل الأسرار القديمة من Google وTiDB وأي مزود آخر.
2. إنشاء قاعدة بيانات Production منفصلة عن Staging.
3. تشغيل `python migrate_db.py` على Production.
4. نشر FastAPI app خلف HTTPS.
5. إعداد Webhooks وتوصيله في Dodo Payments.
6. تشغيل Worker process دائما.
7. إعداد S3/R2/Azure Blob كـ private storage.
8. إعداد Sentry ومراجعة أول error event.
9. إعداد SMTP حقيقي لايميلات password reset.
10. تشغيل CI على GitHub أو منصة Git.
11. تشغيل `production_readiness.py` في CI قبل أي release.
12. اختبار backup/restore لقاعدة البيانات.
13. اختبار تحميل ملفات كبيرة حسب حدود الخطط.
14. اختبار concurrent users.
15. اختبار خطة rollback عند فشل deploy.

## للوصول إلى 100/100 من ناحية QTO

1. تجهيز 20-50 مشروع فيلا حقيقي كـ validation set.
2. مقارنة BOQ الناتج مع BOQ يدوي معتمد.
3. حساب دقة لكل بند وليس فقط إجمالي المشروع.
4. تحديد tolerance لكل نوع بند:
   - Concrete.
   - Blockwork.
   - Finishes.
   - Openings.
   - External works.
5. اعتماد قائمة assumptions رسمية.
6. إضافة قواعد تنبيه عند الكميات غير المنطقية.
7. توثيق كل معادلة مستخدمة في النظام.
8. إضافة review screen للبنود التي فيها confidence منخفض.
9. منع export النهائي إذا توجد critical missing inputs إلا بموافقة صريحة.
10. اعتماد التقرير من QS محترف قبل بيعه كأداة مدفوعة.

## للوصول إلى 100/100 من ناحية Product/SaaS

1. اختبار checkout كامل في Dodo Payments sandbox.
2. اختبار cancel/resume/past_due/payment_failed.
3. إعداد Dodo Payments customer portal.
4. إعداد pricing page نهائية.
5. إعداد onboarding لأول مشروع.
6. إعداد support email رسمي.
7. إعداد صفحة status أو طريقة إبلاغ عن الأعطال.
8. مراجعة نصوص Legal مع محام.
9. مراجعة Privacy مع متطلبات البلد المستهدف.
10. إعداد refund policy النهائية في Dodo Payments والموقع.
11. اختبار تجربة مستخدم من التسجيل حتى تحميل BOQ.
12. جمع feedback من 5 مستخدمين QS فعليين.
13. إصلاح كل blocker قبل public launch.

## أمر التشغيل المقترح للإنتاج

```powershell
docker compose up --build
```

أو تشغيل الخدمات منفصلة:

```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000
python worker.py
```

## أوامر الفحص قبل أي إطلاق

```powershell
pytest
python -m compileall worker.py production_readiness.py utils workflow tests api
python production_readiness.py
```

للفحص الصارم مع env:

```powershell
$env:QTO_STRICT_READINESS="1"
python production_readiness.py
```

## التقييم الواقعي عند اكتمال الخطوات الخارجية

إذا تم تنفيذ كل ما سبق واختبار مشاريع حقيقية:

- Dev/SaaS: 95-100
- QTO: 90-100 حسب نتائج المقارنة مع BOQ يدوي
- Product/SaaS: 90-100 حسب نجاح الدفع والدعم وتجربة المستخدم

