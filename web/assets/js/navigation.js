(function(){
const items=[
 ['Proyecto','proyecto.html','Conocer'],['9 pilares','pilares.html','Conocer'],['Arquitectura','arquitectura.html','Conocer'],
 ['Pila','pila.html','Operar'],['Buddy','buddy.html','Operar'],['LOTB','lotb.html','Operar'],['Ubuntu / RHEL','os.html','Operar'],
 ['Scripts','scripts.html','Operar'],['Prospección','prospeccion.html','Operar'],['Aplicación','app.html','Aplicación'],
 ['Resultados','resultados.html','Comunidad'],['manada_leones','manada.html','Comunidad'],['Contacto','contacto.html','Comunidad']
];
const path=location.pathname.split('/').pop()||'index.html';
const current=items.find(x=>x[1]===path);
function render(){
 const old=document.querySelector('nav.site-nav'); if(old) old.remove();
 if(!document.querySelector('link[data-leones-favicon]')){const icon=document.createElement('link');icon.rel='icon';icon.type='image/svg+xml';icon.href='assets/graphics/leones-mark.svg';icon.dataset.leonesFavicon='1';document.head.appendChild(icon)}
 const style=document.createElement('style');style.id='leones-navigation-force';style.textContent=`
 :root{--leones-side-space:210px!important}
 body{padding-left:var(--leones-side-space)!important;padding-right:0!important}
 body>nav:not(.site-nav){display:none!important}
 .site-top{display:none!important}
 .site-side{position:fixed!important;left:0!important;right:auto!important;top:0!important;bottom:auto!important;width:210px!important;height:100vh!important;box-sizing:border-box!important;background:linear-gradient(180deg,#07151f,#0b202c)!important;border-right:1px solid rgba(255,255,255,.08)!important;border-left:0!important;box-shadow:8px 0 30px rgba(7,21,31,.12)!important;padding:76px 12px 18px!important;overflow-y:auto!important;z-index:10000!important}
 .site-side:before{content:'🦁  LEONES';display:block;color:#fff;font-weight:950;letter-spacing:.04em;font-size:1rem;padding:0 10px 18px}
 .site-side .side-title{font-size:.65rem!important;letter-spacing:.14em!important;font-weight:900!important;color:#647f8d!important;padding:9px 10px 6px!important;text-transform:uppercase!important}
 .site-side a{display:block!important;padding:9px 11px!important;margin:3px 0!important;border-radius:9px!important;color:#93a9b4!important;text-decoration:none!important;font-size:.83rem!important;font-weight:850!important}
 .site-side a:hover{background:rgba(255,255,255,.07)!important;color:#fff!important;transform:translateX(2px)!important}
 .site-side a.active{background:rgba(25,183,122,.14)!important;color:#63e0ad!important;box-shadow:inset 3px 0 #19b77a!important}
 .site-crumb{background:#f3f6f9!important;border-bottom:1px solid #d8e0e7!important}
 .site-crumb-inner{max-width:1050px!important;margin:auto!important;padding:8px 22px!important;display:flex!important;align-items:center!important;gap:8px!important;flex-wrap:wrap!important;color:#526872!important}
 .site-crumb-inner a{color:#04547f!important;text-decoration:none!important;font-weight:900!important}
 @media(max-width:800px){:root{--leones-side-space:165px!important}.site-side{width:165px!important}.site-side a{font-size:.75rem!important;padding:8px 7px!important}}
 @media(max-width:560px){:root{--leones-side-space:0px!important}body{padding-left:0!important}.site-side{left:0!important;right:0!important;top:auto!important;bottom:0!important;width:100%!important;height:auto!important;max-height:46vh!important;border-right:0!important;border-top:1px solid rgba(255,255,255,.1)!important;padding:8px!important;display:grid!important;grid-template-columns:repeat(2,1fr)!important;gap:2px!important}.site-side:before{display:none!important}.site-side .side-title{grid-column:1/-1!important}.site-side a{margin:0!important}}
 `;document.head.appendChild(style);
 const nav=document.createElement('nav'); nav.className='site-nav'; nav.setAttribute('aria-label','Navegación principal');
 const group=current?current[2]:null;
 const groupHref=group==='Conocer'?'pilares.html':group==='Operar'?'pila.html':group==='Aplicación'?'app.html':'manada.html';
 nav.innerHTML='<div class="site-top" aria-hidden="true"></div>'+
 '<div class="site-crumb"><div class="site-crumb-inner"><a href="index.html">LEONES</a><span>›</span>'+(group?'<a href="'+groupHref+'">'+group+'</a><span>›</span>':'')+'<strong>'+(current?current[0]:'Inicio')+'</strong></div></div>'+
 '<aside class="site-side"><div class="side-title">SECCIONES</div>'+items.map(x=>'<a class="'+(x[1]===path?'active':'')+'" href="'+x[1]+'">'+x[0]+'</a>').join('')+'</aside>';
 document.body.insertBefore(nav,document.body.firstChild);
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',render); else render();
})();
