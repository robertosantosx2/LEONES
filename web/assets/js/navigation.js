(function(){
const items=[
 ['Proyecto','proyecto.html','Conocer'],['9 pilares','pilares.html','Conocer'],['Arquitectura','arquitectura.html','Conocer'],
 ['Pila','pila.html','Operar'],['Buddy','buddy.html','Operar'],['LOTB','lotb.html','Operar'],['Ubuntu / RHEL','os.html','Operar'],
 ['Scripts','scripts.html','Operar'],['Prospección','prospeccion.html','Operar'],['Aplicación','app.html','Aplicación'],
 ['Resultados','resultados.html','Comunidad'],['manada_leones','manada.html','Comunidad'],['Contacto','contacto.html','Comunidad']
];
const mains=[['Inicio','index.html'],['Conocer LEONES','pilares.html'],['Arquitectura','arquitectura.html'],['Operar','operacion.html'],['Aplicación','app.html'],['Comunidad','manada.html']];
const path=location.pathname.split('/').pop()||'index.html';
const current=items.find(x=>x[1]===path);
function render(){
 const old=document.querySelector('nav.site-nav'); if(old) old.remove();
 const style=document.createElement('style');style.id='leones-navigation-force';style.textContent=`
 :root{--leones-side-space:210px!important}
 body{padding-left:var(--leones-side-space)!important;padding-right:0!important}
 .site-side{position:fixed!important;left:0!important;right:auto!important;top:0!important;bottom:auto!important;width:210px!important;height:100vh!important;box-sizing:border-box!important;background:#fff!important;border-right:1px solid #d8e0e7!important;border-left:0!important;box-shadow:5px 0 18px rgba(20,40,60,.07)!important;padding:76px 10px 18px!important;overflow-y:auto!important;z-index:10000!important}
 .site-side a{display:block!important}
 .site-side a.active{box-shadow:inset -3px 0 #1769aa!important}
 .site-top,.site-crumb{margin-left:0!important}
 @media(max-width:800px){:root{--leones-side-space:165px!important}.site-side{width:165px!important}.site-side a{font-size:.75rem!important;padding:8px 7px!important}}
 @media(max-width:560px){:root{--leones-side-space:0px!important}body{padding-left:0!important}.site-side{left:0!important;right:0!important;top:auto!important;bottom:0!important;width:100%!important;height:auto!important;max-height:46vh!important;border-right:0!important;border-top:1px solid #d8e0e7!important;padding:8px!important;display:grid!important;grid-template-columns:repeat(2,1fr)!important}}
 `;document.head.appendChild(style);
 const nav=document.createElement('nav'); nav.className='site-nav'; nav.setAttribute('aria-label','Navegación principal');
 const group=current?current[2]:null;
 nav.innerHTML='<div class="site-top"><div class="site-top-inner">'+mains.map(x=>'<a href="'+x[1]+'">'+x[0]+'</a>').join('')+'</div></div>'+
 '<div class="site-crumb"><div class="site-crumb-inner"><a href="index.html">LEONES</a><span>›</span>'+(group?'<a href="'+(group==='Conocer'?'pilares.html':group==='Operar'?'operacion.html':group==='Aplicación'?'app.html':'manada.html')+'">'+group+'</a><span>›</span>':'')+'<strong>'+(current?current[0]:'Inicio')+'</strong></div></div>'+
 '<aside class="site-side"><div class="side-title">SECCIONES</div>'+items.map(x=>'<a class="'+(x[1]===path?'active':'')+'" href="'+x[1]+'">'+x[0]+'</a>').join('')+'</aside>';
 document.body.insertBefore(nav,document.body.firstChild);
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',render); else render();
})();
