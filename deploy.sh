#!/bin/bash

# اسم المشروع والملف
ZIP_FILE="$HOME/Downloads/nasdaq-watchdog.zip"
PROJECT_NAME="nasdaq-watchdog"
REPO_URL="https://github.com/6ayoob/nasdaq-watchdog.git"

# تحقق من وجود الملف
if [ ! -f "$ZIP_FILE" ]; then
  echo "❌ لم يتم العثور على الملف: $ZIP_FILE"
  exit 1
fi

# حذف المجلد القديم إن وجد
rm -rf "$HOME/Downloads/$PROJECT_NAME"

# فك الضغط
unzip "$ZIP_FILE" -d "$HOME/Downloads/" || { echo "❌ فشل في فك الضغط"; exit 1; }

# الدخول إلى المجلد
cd "$HOME/Downloads/$PROJECT_NAME" || { echo "❌ تعذر الدخول إلى المجلد"; exit 1; }

# تهيئة git
git init

# إزالة remote قديم إن وجد
git remote remove origin 2>/dev/null

# ربط بالمستودع
git remote add origin "$REPO_URL"

# إضافة الملفات
git add .

# عمل commit
git commit -m "Initial working bot"

# تعيين الفرع main
git branch -M main

# رفع الملفات
git push -u origin main || { echo "❌ فشل في رفع الملفات إلى GitHub"; exit 1; }

echo "✅ تم رفع المشروع بنجاح إلى $REPO_URL"
