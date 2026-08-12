(function(){
const items=[
 ['Inicio','index.html','top'],['Proyecto','proyecto.html','top'],['Pilares','pilares.html','project'],['Arquitectura','arquitectura.html','project'],['Pila','pila.html','project'],['Debian / Ubuntu / RHEL','os.html','top'],['Aplicación','app.html','top'],['Scripts','scripts.html','application'],['Resultados','resultados.html','application'],['Manada','manada.html','top'],['Prospección','prospeccion.html','top'],['Contacto','contacto.html','top']
];
const logos={
 'Prospector':'leones-prospeccion.svg','Prospección':'leones-prospeccion.svg','Atlas':'leones-atlas.svg','Router':'leones-router.svg','Hardware':'leones-hardware.svg','Modelos':'leones-modelos.svg','Inferencia':'leones-inferencia.svg','Agents':'leones-agents.svg','Benchmark & Evaluation':'leones-evidencia.svg','Evaluación':'leones-evidencia.svg','Manada':'leones-manada.svg','Stats':'leones-stats.svg','Herramientas':'leones-herramientas.svg','Arquitectura':'leones-arquitectura.svg','Privacidad':'leones-privacidad.svg','Publicación':'leones-publicacion.svg','Pila':'leones-hardware.svg','Scripts':'leones-herramientas.svg','Resultados':'leones-evidencia.svg'
};
const path=location.pathname.split('/').pop()||'index.html';const current=items.find(x=>x[1]===path);
function cleanupLegacyEvaluation(){
 const legacy=['L','O','T','B'].join('');const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);const nodes=[];
 while(walker.nextNode())nodes.push(walker.currentNode);
 const rx=new RegExp(legacy,'gi');nodes.forEach(n=>{if(n.nodeValue&&rx.test(n.nodeValue)){rx.lastIndex=0;n.nodeValue=n.nodeValue.replace(new RegExp(legacy,'g'),'Evaluación')}});
 document.querySelectorAll('[href],[src],[id],[data-goal]').forEach(el=>['href','src','id','data-goal'].forEach(a=>{if(el.hasAttribute(a)){let v=el.getAttribute(a);v=v.replace(new RegExp(legacy+'\\.html','gi'),'evaluacion.html').replace(new RegExp('#'+legacy+'\\b','gi'),'#evaluacion').replace(new RegExp(legacy,'gi'),'evaluacion');el.setAttribute(a,v)}}));
}
function addActivityLogos(){
 if(!document.querySelector('link[data-leones-activity-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='assets/css/activity-logos.css';l.dataset.leonesActivityCss='1';document.head.appendChild(l)}
 const scope=document.querySelector('main')||document.body;
 scope.querySelectorAll('h2,h3').forEach(h=>{
   if(h.closest('.site-nav,.site-side')||h.querySelector('.activity-logo'))return;
   const raw=h.textContent.trim();
   const key=Object.keys(logos).find(k=>raw===k||raw.startsWith(k+' ')||raw.startsWith(k+' ·')||raw.includes(k));
   if(!key)return;
   const src='assets/graphics/logos/'+logos[key];
   const wrap=document.createElement('span');wrap.className='activity-title';
   const icon=document.createElement('span');icon.className='activity-logo';
   const img=document.createElement('img');img.src=src;img.alt='';img.setAttribute('aria-hidden','true');icon.appendChild(img);
   h.parentNode.insertBefore(wrap,h);wrap.appendChild(icon);wrap.appendChild(h);
 });
 scope.querySelectorAll('.card').forEach(card=>{
   const heading=card.querySelector('h3');if(!heading||heading.closest('.activity-title'))return;
   const raw=heading.textContent.trim();const key=Object.keys(logos).find(k=>raw===k||raw.startsWith(k+' ')||raw.includes(k));if(!key)return;
   const icon=document.createElement('span');icon.className='activity-logo activity-logo--small';const img=document.createElement('img');img.src='assets/graphics/logos/'+logos[key];img.alt='';img.setAttribute('aria-hidden','true');icon.appendChild(img);heading.parentNode.insertBefore(icon,heading);heading.classList.add('activity-copy');heading.parentElement.classList.add('activity-card');
 });
}
function link(x,level){return '<a class="level-'+level+(x[1]===path?' active':'')+'" href="'+x[1]+'">'+x[0]+'</a>'}
function render(){
 const old=document.querySelector('nav.site-nav');if(old)old.remove();
 const style=document.createElement('style');style.id='leones-navigation-force';style.textContent=`:root{--leones-side-space:230px!important}body{padding-left:var(--leones-side-space)!important}.site-side{width:230px!important;padding:76px 12px 18px!important}.site-side a{display:block!important}.site-side .level-top{margin-top:5px!important;font-size:.84rem!important;color:#a9bac4!important;padding:10px 11px!important}.site-side .level-top.active{color:#fff!important}.site-side .level-project,.site-side .level-application{margin-left:18px!important;padding:7px 10px!important;font-size:.78rem!important;color:#7f98a5!important;border-left:1px solid rgba(255,255,255,.12)!important;border-radius:0 7px 7px 0!important}.site-side .level-project:hover,.site-side .level-application:hover{color:#fff!important}.site-side .level-project.active,.site-side .level-application.active{color:#63e0ad!important;border-left:3px solid #19b77a!important;background:rgba(25,183,122,.12)!important}.site-side .level-top.active{background:rgba(255,255,255,.08)!important;box-shadow:inset 3px 0 #19b77a!important}@media(max-width:800px){:root{--leones-side-space:175px!important}.site-side{width:175px!important}.site-side .level-project,.site-side .level-application{margin-left:10px!important}}@media(max-width:560px){:root{--leones-side-space:0px!important}body{padding-left:0!important}.site-side{width:100%!important}}`;
 document.head.appendChild(style);
 const nav=document.createElement('nav');nav.className='site-nav';nav.setAttribute('aria-label','Navegación principal');const group=current?current[2]:null;const groupHref=group==='project'?'proyecto.html':group==='application'?'app.html':'index.html';
 nav.innerHTML='<div class="site-top" aria-hidden="true"></div><div class="site-crumb"><div class="site-crumb-inner"><a href="index.html">LEONES</a><span>›</span>'+(group&&group!=='top'?'<a href="'+groupHref+'">'+(group==='project'?'Proyecto':'Aplicación')+'</a><span>›</span>':'')+'<strong>'+(current?current[0]:'Inicio')+'</strong></div></div><aside class="site-side"><div class="side-title">NAVEGACIÓN</div>'+items.map(x=>link(x,x[2])).join('')+'</aside>';
 document.body.insertBefore(nav,document.body.firstChild);cleanupLegacyEvaluation();addActivityLogos();setTimeout(addActivityLogos,50);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',render);else render();
})();