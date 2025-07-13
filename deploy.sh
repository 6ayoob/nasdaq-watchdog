#!/bin/bash

# اسم مجلد المشروع (عدّله إذا كان مختلف)
PROJECT_DIR="nasdaq-watchdog-fixed"

# تحقق من وجود المجلد
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ المجلد '$PROJECT_DIR' غير موجود!"
  exit 1
fi

cd "$PROJECT_DIR"

# بدء مشروع git جديد
git init

# تعيين الفرع الرئيسي إلى main
git branch -M main

# ربط المستودع البعيد
git remote add origin https://github.com/6ayoob/nasdaq-watchdog.git

# إضافة جميع الملفات
git add .

# أول commit
git commit -m "Initial working commit"

# دفع التغييرات إلى GitHub
git push -f origin main

echo "✅ تم رفع المشروع بنجاح إلى GitHub!"
