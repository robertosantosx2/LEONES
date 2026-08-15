(function(){
const items=[
 ['Inicio','index.html','top'],['Proyectos','proyecto.html','top'],['Atlas','atlas.html','project'],['Pilares','pilares.html','project'],['Arquitectura','arquitectura.html','project'],['Diagramas','diagramas.html','project'],['Pila','pila.html','project'],['Operación','operacion.html','project'],['Aplicación','app.html','top'],['Scripts','scripts.html','application'],['Resultados','resultados.html','application'],['Evaluación','evaluacion.html','application'],['Recomendaciones','recommendations.html','application'],['Manada','manada.html','top'],['Prospección','prospeccion.html','top'],['Horizonte','horizon.html','top'],['Contacto','contacto.html','top']
];
const path=location.pathname.split('/').pop()||'index.html';const current=items.find(x=>x[1]===path);
function addActivityLogos(){if(!document.querySelector('link[data-leones-activity-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='assets/css/activity-logos.css';l.dataset.leonesActivityCss='1';document.head.appendChild(l)}}
function link(x,level){return '<a class="level-'+level+(x[1]===path?' active':'')+(x[1]==='atlas.html'?' atlas-link':'')+' href="'+x[1]+'">'+x[0]+'</a>'}
function render(){
 const old=document.querySelector('nav.site-nav');if(old)old.remove();
 const style=document.createElement('style');style.id='leones-navigation-force';style.textContent=`
:root{--leones-side-space:230px!important}
body{padding-left:var(--leones-side-space)!important}
.skip-link{position:fixed;left:10px;top:-60px;z-index:10000;background:#102f49;color:#fff;padding:10px 14px;border-radius:8px;font-weight:800;text-decoration:none}.skip-link:focus{top:10px}
.leones-nav-toggle{display:none}
.site-side{width:230px!important;padding:14px 12px 18px!important;background:#fff!important;box-shadow:2px 0 14px rgba(16,47,73,.06)!important}
.site-brand{display:flex!important;justify-content:center!important;align-items:center!important;padding:4px 10px 14px!important}.site-brand img{display:block!important;width:100%!important;max-width:178px!important;height:auto!important;max-height:88px!important;object-fit:contain!important}
.side-title{padding:0 11px 7px!important;font-size:.68rem!important;letter-spacing:.12em!important;color:#91a2ad!important;font-weight:900!important}
.site-side a{display:block!important}.site-side .level-top{margin-top:3px!important;font-size:.84rem!important;color:#315d7d!important;padding:9px 11px!important;background:transparent!important;border-radius:8px!important}.site-side .level-top:hover{background:#f4f7fa!important;color:#16486a!important}.site-side .level-top.active{color:#c62828!important;background:#fff0f0!important;box-shadow:inset 4px 0 #c62828!important;font-weight:950!important}
.site-side .level-project,.site-side .level-application{margin-left:18px!important;padding:6px 10px!important;font-size:.77rem!important;color:#7f98a5!important;border-left:1px solid #d8e0e7!important;border-radius:0 7px 7px 0!important}.site-side .level-project:hover,.site-side .level-application:hover{color:#16486a!important;background:#f4f7fa!important}.site-side .level-project.active,.site-side .level-application.active{color:#c62828!important;border-left:3px solid #c62828!important;background:#fff0f0!important;font-weight:950!important}.site-side .atlas-link{font-weight:950!important;color:#1769aa!important}
.site-crumb{position:sticky!important;top:0!important;z-index:50!important}.site-crumb-inner{max-width:none!important}
@media(max-width:800px){:root{--leones-side-space:0px!important}body{padding-left:0!important}.leones-nav-toggle{display:flex;position:fixed;left:10px;top:10px;z-index:1001;border:1px solid #d8e0e7;background:#fff;color:#102f49;border-radius:10px;padding:9px 12px;font-weight:900;box-shadow:0 3px 12px rgba(16,47,73,.12);cursor:pointer}.site-side{position:fixed!important;left:0!important;top:0!important;bottom:0!important;width:min(290px,88vw)!important;z-index:1000!important;overflow-y:auto!important;transform:translateX(-105%)!important;transition:transform .2s ease!important;padding-top:58px!important}.site-side.is-open{transform:translateX(0)!important}.site-side-backdrop{display:none;position:fixed;inset:0;background:rgba(16,47,73,.35);z-index:999}.site-side-backdrop.is-open{display:block}.site-brand img{max-width:150px!important}.site-crumb{padding-left:62px!important}}
@media(prefers-reduced-motion:reduce){.site-side{transition:none!important}}
`;
 document.head.appendChild(style);
 const skip=document.createElement('a');skip.className='skip-link';skip.href='#main';skip.textContent='Saltar al contenido';document.body.insertBefore(skip,document.body.firstChild);
 const nav=document.createElement('nav');nav.className='site-nav';nav.setAttribute('aria-label','Navegación principal');
 const group=current?current[2]:null;const groupHref=group==='project'?'proyecto.html':group==='application'?'app.html':'index.html';
 nav.innerHTML='<div class="site-top" aria-hidden="true"></div><div class="site-crumb"><div class="site-crumb-inner"><a href="index.html">Inicio</a><span>›</span>'+(group&&group!=='top'?'<a href="'+groupHref+'">'+(group==='project'?'Proyectos':'Aplicación')+'</a><span>›</span>':'')+'<strong>'+(current?current[0]:'Inicio')+'</strong></div></div><button class="leones-nav-toggle" type="button" aria-controls="leones-side" aria-expanded="false">☰ Menú</button><div class="site-side-backdrop" aria-hidden="true"></div><aside id="leones-side" class="site-side"><div class="site-brand"><a href="index.html" aria-label="LEONES · Inicio"><img src="assets/graphics/leones-logo-principal.jpg" alt="LEONES"></a></div><div class="side-title">NAVEGACIÓN</div>'+items.map(x=>link(x,x[2])).join('')+'</aside>';
 document.body.insertBefore(nav,document.body.firstChild);
 const toggle=nav.querySelector('.leones-nav-toggle'),side=nav.querySelector('.site-side'),backdrop=nav.querySelector('.site-side-backdrop');
 function close(){side.classList.remove('is-open');backdrop.classList.remove('is-open');toggle.setAttribute('aria-expanded','false')}
 toggle.addEventListener('click',function(){const open=!side.classList.contains('is-open');side.classList.toggle('is-open',open);backdrop.classList.toggle('is-open',open);toggle.setAttribute('aria-expanded',String(open))});backdrop.addEventListener('click',close);side.addEventListener('click',function(e){if(e.target.closest('a'))close()});document.addEventListener('keydown',function(e){if(e.key==='Escape')close()});
 const main=document.querySelector('main');if(main&&!main.id)main.id='main';
 addActivityLogos()
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',render);else render();
})();
