
const $=(s,r=document)=>r.querySelector(s);
const T={
  lang: localStorage.getItem('lang')||'ar',
  set(l){ this.lang=l; localStorage.setItem('lang',l); applyLang() }
};
const L={
  ar:{ title:'تسجيل الدخول', u:'اسم المستخدم', p:'كلمة المرور', r:'الدور', si:'تسجيل الدخول', meta:'سيتم توجيهك تلقائيًا بعد تسجيل الدخول.' },
  en:{ title:'Sign in', u:'Username', p:'Password', r:'Role', si:'Sign in', meta:'You will be redirected automatically.' }
};
function applyLang(){
  const l=L[T.lang];
  document.documentElement.dir = T.lang==='ar'?'rtl':'ltr';
  document.documentElement.lang = T.lang;
  $('#title').textContent=l.title; $('#lblUser').textContent=l.u; $('#lblPass').textContent=l.p; $('#lblRole').textContent=l.r;
  $('#btnLoginTxt').textContent=l.si; $('#meta').textContent=l.meta;
}
function apiLogin(email,password,role){
  return fetch('/admin/api/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email, password, role }) })
    .then(async r=>{ if(!r.ok){ let msg=''; try{const j=await r.json(); msg=j.error||''}catch{}; throw new Error(msg||'Failed to login') } return r.json() })
}
document.addEventListener('DOMContentLoaded', ()=>{
  applyLang();
  const f=$('#loginForm'), err=$('#err');
  f.addEventListener('submit', async (e)=>{
    e.preventDefault(); err.style.display='none';
    const email=$('#email').value.trim(); const password=$('#password').value; const role=$('#role').value;
    try{
      const res = await apiLogin(email,password,role);
      sessionStorage.setItem('vip_user', JSON.stringify(res.user));
      location.href = res.user.role==='ADMIN'? '/admin/assets/admin.html' : '/admin/assets/cashier.html';
    }catch(ex){ err.textContent = ex.message || 'Failed to fetch'; err.style.display='block' }
  });
});
