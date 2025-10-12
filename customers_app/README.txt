تشغيل مشروع غسيل وتلميع VIP
----------------------------
1. ضع شعارك باسم logo.png داخل المجلد: static/img/logo.png
2. افتح Terminal / CMD واذهب للمجلد المشروع:
   cd Desktop\VIP_Loyalty_Final   (أو المسار الذي نقلت إليه)

3. انشئ بيئة افتراضية (اختياري):
   python -m venv venv
   venv\Scripts\activate   (Windows)
   source venv/bin/activate  (mac/linux)

4. ثبت المتطلبات:
   pip install -r requirements.txt

5. شغل السيرفر:
   python app.py

6. افتح المتصفح على:
   http://127.0.0.1:5000
   أو افتح الرابط الذي يطبع في الكونسول ليفتح من جوالك على نفس الشبكة.
