(function(){
const items=[
 ['Proyecto','proyecto.html'],['9 pilares','pilares.html'],['Arquitectura','arquitectura.html'],['Pila','pila.html'],['Buddy','buddy.html'],['LOTB','lotb.html'],['Ubuntu / RHEL','os.html'],['Scripts','scripts.html'],['Prospección','prospeccion.html'],['Aplicación','app.html'],['Resultados','resultados.html'],['manada_leones','manada.html'],['Contacto','contacto.html']
];
const mains=[['Inicio','index.html'],['Conocer LEONES','pilares.html'],['Arquitectura','arquitectura.html'],['Operar','operacion.html'],['Aplicación','app.html'],['Comunidad','manada.html']];
const path=location.pathname.split('/').pop()||'index.html';
const current=items.find(x=>x[1]===path);
const el=document.currentScript;
function render(){
 const old=document.querySelector('nav.site-nav'); if(old) old.remove();
 const nav=document.createElement('nav'); nav.className='site-nav'; nav.setAttribute('aria-label','Navegación principal');
 nav.innerHTML='<div class="site-top"><div class="site-top-inner">'+mains.map(x=>'<a href="'+x[1]+'">'+x[0]+'</a>').join('')+'</div></div>'+
 '<div class="site-crumb"><div class="site-crumb-inner"><a href="index.html">LEONES</a><span>›</span><strong>'+(current?current[0]:'Inicio')+'</strong></div></div>'+
 '<aside class="site-side"><div class="side-title">SECCIONES</div>'+items.map(x=>'<a class="'+(x[1]===path?'active':'')+'" href="'+x[1]+'">'+x[0]+'</a>').join('')+'</aside>';
 document.body.insertBefore(nav,document.body.firstChild);
 document.documentElement.style.setProperty('--leones-side-space','190px');
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',render); else render();
})();
