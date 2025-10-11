
const $=(s,r=document)=>r.querySelector(s);
const api=(p,o={})=>fetch('/admin'+p,{headers:{'Content-Type':'application/json'},...o}).then(async r=>{ if(!r.ok) throw await r.json().catch(()=>({ok:false})); return r.json(); });

function toggleTheme(){ const isLight=document.documentElement.classList.toggle('light'); localStorage.setItem('theme', isLight?'light':'dark') }
function applyTheme(){ const t=localStorage.getItem('theme')||'dark'; document.documentElement.classList.toggle('light', t==='light') }
function setLangBtn(){ const l=localStorage.getItem('lang')||'ar'; $('#btnLang').textContent = l==='ar'?'EN':'AR'; document.documentElement.dir = l==='ar'?'rtl':'ltr' }

// Settings bottom sheet (points + users)
function openSettingsSheet(){
  const wrap=document.createElement('div'); wrap.className='modal-wrap';
  wrap.innerHTML = `<div class="sheet">
    <h3>الإعدادات</h3>
    <div class="stack" id="settingsBox">
      <label>نقاط لكل زيارة</label>
      <input id="ppv" type="number" class="input" min="1">
      <label>حد الاستبدال</label>
      <input id="rt" type="number" class="input" min="1">
      <button id="btnSaveSettings" class="btn">حفظ</button>
    </div>
    <div class="stack" style="margin-top:14px">
      <h3>المستخدمون</h3>
      <div class="stack">
        <input id="newUser" class="input" placeholder="اسم المستخدم">
        <input id="newPass" class="input" type="password" placeholder="كلمة المرور">
        <select id="newRole" class="input"><option value="ACCOUNTANT">ACCOUNTANT</option><option value="ADMIN">ADMIN</option></select>
        <button id="btnAddUser" class="btn">إضافة مستخدم</button>
      </div>
      <div id="users" class="list"></div>
    </div>
    <div class="row" style="justify-content:flex-end;margin-top:8px"><button class="btn ghost sm" id="closeSheet">إغلاق</button></div>
  </div>`;
  document.body.appendChild(wrap);
  $('#closeSheet', wrap).onclick=()=>wrap.remove();
  // Load settings + users
  api('/api/settings').then(r=>{ $('#ppv').value=r.settings.pointsPerVisit; $('#rt').value=r.settings.redeemThreshold });
  api('/api/users').then(r=> renderUsers(r.users, wrap));
  $('#btnSaveSettings', wrap).onclick = async()=>{ await api('/api/settings',{method:'PATCH', body: JSON.stringify({ pointsPerVisit:+$('#ppv').value||10, redeemThreshold:+$('#rt').value||50 })}); alert('تم الحفظ') };
  $('#btnAddUser', wrap).onclick = async()=>{
    const email=$('#newUser').value.trim(); const password=$('#newPass').value; const role=$('#newRole').value;
    if(!email || !password) return alert('ادخل اسم المستخدم وكلمة المرور');
    await api('/api/users',{method:'POST', body: JSON.stringify({ email, password, role })});
    $('#newUser').value=''; $('#newPass').value=''; const users=(await api('/api/users')).users; renderUsers(users, wrap);
  };
}
function renderUsers(arr, root=document){ const box=$('#users',root); box.innerHTML=''; arr.forEach(u=>{ const it=document.createElement('div'); it.className='item'; it.innerHTML=`<span>${u.email} <span class="badge">${u.role}</span></span>`; const actions=document.createElement('div'); actions.className='row'; const b1=document.createElement('button'); b1.className='btn ghost sm'; b1.textContent='تعديل'; b1.onclick=async()=>{ const email=prompt('اسم المستخدم', u.email)||u.email; const role=prompt('الدور (ADMIN/ACCOUNTANT)', u.role)||u.role; const p=prompt('كلمة المرور (اتركها كما هي إن لم ترغب بالتعديل)',''); const body={}; if(email&&email!==u.email) body.email=email; if(role) body.role=role; if(p) body.password=p; await api('/api/users/'+u.id,{method:'PATCH', body: JSON.stringify(body)}); const users=(await api('/api/users')).users; renderUsers(users, root); }; const b2=document.createElement('button'); b2.className='btn danger sm'; b2.textContent='حذف'; b2.onclick=async()=>{ if(!confirm('تأكيد حذف المستخدم؟')) return; await api('/api/users/'+u.id,{method:'DELETE'}); const users=(await api('/api/users')).users; renderUsers(users, root); }; actions.append(b1,b2); it.appendChild(actions); box.appendChild(it) }) }

// Stats
function kpi(label,value){ const d=document.createElement('div'); d.className='notice'; d.innerHTML=`<div class="row" style="justify-content:space-between"><strong>${label}</strong><span>${value}</span></div>`; return d }
function chartList(map, labelFn=(k)=>k){ const wrap=document.createElement('div'); wrap.className='stack'; Object.keys(map||{}).sort().forEach(k=>{ const v=map[k]; const row=document.createElement('div'); row.innerHTML=`<div class="row" style="justify-content:space-between"><span>${labelFn(k)}</span><span class="badge">${v}</span></div>`; wrap.appendChild(row) }); return wrap }
async function loadStats(){ const box=$('#stats'); box.innerHTML=''; try{ const r=await api('/api/stats'); const s=r.stats||{}; box.appendChild(kpi('عدد المحاسبين النشطين', (s.accountants||[]).length)); const acc=document.createElement('div'); acc.className='list'; acc.innerHTML='<h3>المحاسبين</h3>'; (s.accountants||[]).forEach(a=>{ const it=document.createElement('div'); it.className='item'; it.innerHTML=`<span>${a.user}</span><span class="badge">${a.count}</span>`; acc.appendChild(it) }); box.appendChild(acc); const rt=document.createElement('div'); rt.innerHTML='<h3>التقييمات</h3>'; rt.appendChild(chartList(s.ratings||{}, k=>k+'★')); box.appendChild(rt); const pk=document.createElement('div'); pk.innerHTML='<h3>أوقات الذروة</h3>'; pk.appendChild(chartList(s.peaks||{}, k=>k+':00')); box.appendChild(pk); }catch{ box.innerHTML='<div class="meta">تعذر تحميل الإحصائيات</div>' } }

// Alerts (clickable -> detail)
async function loadAlerts(){ try{ const r=await api('/api/alerts'); const box=$('#alerts'); box.innerHTML=''; if(!r.alerts||!r.alerts.length){ box.innerHTML='<div class="meta">لا توجد تنبيهات الآن</div>'; return } r.alerts.forEach(a=>{ const d=document.createElement('div'); d.className='notice'; d.innerHTML = `<strong>${a.message}</strong><br><span class="meta">${a.name} — ${a.phone} — ${a.plate_letters}-${a.plate_numbers}</span>`; d.style.cursor='pointer'; d.onclick=()=> openClientDetail(a.car_id); box.appendChild(d) }) }catch{ $('#alerts').innerHTML='<div class="meta">...</div>' } }
async function openClientDetail(car_id){ const r = await api('/api/clients'); const c = (r.clients||[]).find(x=>x.car_id===car_id); if(!c){ alert('لم يتم العثور على بيانات العميل'); return } const wrap=document.createElement('div'); wrap.className='modal-wrap'; wrap.innerHTML=`<div class="sheet"><h3>بيانات العميل</h3><div class="notice">الاسم: <strong>${c.name}</strong><br>الهاتف: ${c.phone}<br>اللوحة: ${c.plate}<br>الزيارات: ${c.visits} | النقاط: ${c.points}<br>آخر 5 تقييمات: ${c.ratings_last5.join('، ')} (المجموع: ${c.ratings_sum_last5})</div><div class="row" style="justify-content:flex-end;margin-top:8px"><button class="btn ghost sm" id="closeSheet">إغلاق</button></div></div>`; document.body.appendChild(wrap); $('#closeSheet',wrap).onclick=()=>wrap.remove() }

// Clients table
async function loadClients(){ const box=$('#clientsBox'); box.innerHTML=''; const r=await api('/api/clients'); const data=r.clients||[]; const q=$('#q').value.trim().toLowerCase(); const filtered=data.filter(x=>!q|| (x.name||'').toLowerCase().includes(q) || (x.phone||'').includes(q) || (x.plate||'').includes(q)); const table=document.createElement('table'); table.className='table'; table.innerHTML='<thead><tr><th>الاسم</th><th>الجوال</th><th>المركبة</th><th>اللوحة</th><th>الزيارات</th><th>النقاط</th><th>مجموع آخر 5</th></tr></thead>'; const tb=document.createElement('tbody'); filtered.forEach(c=>{ const tr=document.createElement('tr'); tr.innerHTML=`<td>${c.name}</td><td>${c.phone}</td><td>${c.car_type||'-'}</td><td>${c.plate}</td><td>${c.visits}</td><td>${c.points}</td><td>${c.ratings_sum_last5}</td>`; tb.appendChild(tr) }); table.appendChild(tb); box.appendChild(table) }
function exportStatsPDF(){ const w = window.open('', '_blank', 'width=900,height=700'); w.document.write(`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>Export</title><style>body{font-family:system-ui, -apple-system,'Tajawal',Arial;padding:16px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #bbb;padding:6px}</style></head><body>`); w.document.write($('#stats').innerHTML); w.document.write('</body></html>'); w.document.close(); w.focus(); w.print() }
function exportClientsPDF(){ const w = window.open('', '_blank', 'width=900,height=700'); const html = $('#clientsBox').innerHTML; w.document.write(`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>Clients</title><style>body{font-family:system-ui,-apple-system,'Tajawal',Arial;padding:16px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #bbb;padding:6px}</style></head><body>${html}</body></html>`); w.document.close(); w.focus(); w.print() }

// Scanner + modal (verify/redeem)
function showSheet(html){ const wrap=document.createElement('div'); wrap.className='modal-wrap'; wrap.innerHTML=`<div class="sheet">${html}<div class="row" style="justify-content:flex-end;margin-top:8px"><button class="btn ghost sm" id="closeSheet">إغلاق</button></div></div>`; document.body.appendChild(wrap); $('#closeSheet',wrap).onclick=()=>wrap.remove(); return wrap }
function initScanner(){ const v=$('#video'); const out=$('#scanOut'); let stream=null, raf=null, detector=('BarcodeDetector' in window)? new BarcodeDetector({formats:['qr_code']}) : null; async function start(){ try{ stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}}); v.srcObject=stream; await v.play(); loop() }catch(e){ out.style.display='block'; out.textContent='لا يمكن فتح الكاميرا' } } function stop(){ if(raf) cancelAnimationFrame(raf); if(stream){stream.getTracks().forEach(t=>t.stop())} stream=null } async function loop(){ if(!v.videoWidth){ raf=requestAnimationFrame(loop); return } try{ if(detector){ const bmp=await createImageBitmap(v); const codes=await detector.detect(bmp); if(codes && codes[0]){ handleToken(codes[0].rawValue); stop(); return } } }catch{} raf=requestAnimationFrame(loop) } async function handleToken(raw){ out.style.display='block'; out.textContent='تم القراءة: '+raw; const token = (raw||'').split('TOKEN:').pop().trim(); try{ const user = JSON.parse(sessionStorage.getItem('vip_user')||'{}'); const r = await api('/api/verify', { method:'POST', body: JSON.stringify({ token, user_id: user.id }) }); const c=r.client||{}; const canRedeem=!!r.canRedeem; const html=`<h3>بيانات العميل</h3><div class="notice">الاسم: <strong>${c.name||'-'}</strong><br>الهاتف: ${c.phone||'-'}<br>السيارة: ${c.plate||'-'}<br>الزيارات: ${c.washes||0} | النقاط: ${c.points||0}</div><div class="row"><button id="btnApprove" class="btn">اعتماد الزيارة</button><button id="btnRedeem" class="btn secondary" ${canRedeem?'':'disabled'}>استبدال النقاط</button></div>`; const sheet = showSheet(html); $('#btnApprove',sheet).onclick=async()=>{ await api('/api/verify', { method:'POST', body: JSON.stringify({ token, action:'visit', user_id: user.id }) }); alert('تم الاعتماد'); sheet.remove() }; $('#btnRedeem',sheet).onclick=async()=>{ if($('#btnRedeem',sheet).disabled) return; await api('/api/redeem', { method:'POST', body: JSON.stringify({ token, user_id: user.id }) }); alert('تم الاستبدال'); sheet.remove() }; }catch(e){ alert('فشل التحقق'); } } $('#btnScan').onclick=start; $('#btnStop').onclick=stop; $('#btnManual').onclick=()=>{ const t=$('#manualToken').value.trim(); if(t){ handleToken(t) } } }

// Raffle
async function runRaffle(){ try{ const r=await api('/api/raffle',{method:'POST'}); const w=r.winner||{}; const waText = encodeURIComponent(r.wa_message_ar || ''); const html = `<h3>الفائز</h3><div class="notice">${w.name||''} — ${w.phone||''} — ${w.plate||''}</div><div style="margin:8px 0"><img src="${r.qr}" alt="QR" style="max-width:240px;background:#fff;padding:8px;border-radius:12px"></div><div class="row"><a class="btn secondary" href="${r.qr}" download="winner_qr.png">تحميل الباركود</a><a class="btn" target="_blank" rel="noopener" href="https://wa.me/?text=${waText}">إرسال عبر واتساب أعمال</a></div><div class="meta">أرسل الرسالة من هاتفك ثم أرفق صورة الباركود المحمّلة.</div>`; showSheet(html) }catch{ alert('لا يوجد مرشحون'); } }

document.addEventListener('DOMContentLoaded', ()=>{
  applyTheme(); setLangBtn(); $('#btnTheme').onclick=toggleTheme; $('#btnLang').onclick=()=>{ const l=localStorage.getItem('lang')==='ar'?'en':'ar'; localStorage.setItem('lang',l); setLangBtn(); location.reload() };
  $('#btnSettings').onclick=openSettingsSheet;
  initScanner(); loadStats(); loadAlerts(); loadClients();
  $('#btnRefreshAlerts').onclick=loadAlerts; $('#btnExport').onclick=exportStatsPDF; $('#btnExportClients').onclick=exportClientsPDF; $('#btnReloadClients').onclick=loadClients; $('#btnRaffle').onclick=runRaffle;
});
