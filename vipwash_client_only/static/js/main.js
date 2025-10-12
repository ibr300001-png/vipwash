
function normalizeDigits(s){
  if(!s) return s;
  const map = {'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9',
               '۰':'0','۱':'1','۲':'2','۳':'3','۴':'4','۵':'5','۶':'6','۷':'7','۸':'8','۹':'9'};
  return String(s).replace(/[٠-٩۰-۹]/g, d => map[d] || d);
}
document.addEventListener('DOMContentLoaded', () => {

  function showModal(title, msg, qrBase64, pointsText){
    const modal = document.getElementById('modal');
    if(!modal) return;
    modal.classList.remove('hidden');
    const t = document.getElementById('modalTitle');
    const m = document.getElementById('modalMsg');
    const img = document.getElementById('modalQR');
    const pts = document.getElementById('modalPoints');
    if(t) t.innerText = title || 'تم';
    if(m) m.innerText = msg || '';
    if(img) img.src = qrBase64 ? ('data:image/png;base64,' + qrBase64) : '';
    if(pts) pts.innerText = pointsText || '';
  }
  function closeModal(){ const modal = document.getElementById('modal'); if(modal) modal.classList.add('hidden'); }

  // NEW CUSTOMER
  const newForm = document.getElementById('newForm');
  if(newForm){
    newForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(newForm);
      form.set('phone', normalizeDigits(form.get('phone')));
      form.set('plate_numbers', normalizeDigits(form.get('plate_numbers')));
      try{
        const res = await fetch('/api/new', { method:'POST', body: form });
        const data = await res.json();
        if(!res.ok){ alert(data.message || 'حدث خطأ'); return; }
        // لا نعرض "تمت إضافة نقاط" هنا – فقط رسالة التوجيه للمحاسب
        showModal('وجّه الباركود للمحاسب للإعتماد', '', data.qr || '' , '');
      }catch(err){ alert('خطأ في الاتصال'); console.error(err); }
    });
  }

  // LOYAL CUSTOMER (existing)
  const loyalForm = document.getElementById('loyalForm');
  if(loyalForm){
    loyalForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(loyalForm);
      form.set('phone', normalizeDigits(form.get('phone')));
      form.set('plate_numbers', normalizeDigits(form.get('plate_numbers')));
      try{
        const res = await fetch('/api/loyal', { method:'POST', body: form });
        const data = await res.json();
        if(res.status === 404 && data && data.new){
          if(confirm('يبدو أنك عميل جديد. الانتقال للتسجيل الآن؟')){ window.location.href = '/new'; }
          return;
        }
        if(!res.ok){ alert(data.message || 'حدث خطأ'); return; }
        showModal('وجّه الباركود للمحاسب للإعتماد', '', data.qr || '', '');
      }catch(err){ alert('خطأ في الاتصال'); console.error(err); }
    });
  }

  const closeBtn = document.getElementById('modalClose');
  if(closeBtn) closeBtn.addEventListener('click', closeModal);
});