/* Atlas Stack Recommender: explainable metadata-only recommendations. */
(function(){
  const $=id=>document.getElementById(id);
  function esc(s){return String(s??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]))}
  window.AtlasRecommender={
    init:function(models,eco){
      const root=$('recommendations'); if(!root)return;
      const ram=$('ram'),gpu=$('gpu'),goal=$('goal'),osi=$('osi'),btn=$('recommend');
      function run(){
        const r=ram?.value||'',g=gpu?.value||'',o=goal?.value||'general',onlyOSI=osi?.value==='osi';
        const licenses=new Set((eco.licenses||[]).filter(x=>x.osi===true).map(x=>String(x.id).toLowerCase()));
        const out=[];
        (models||[]).filter(m=>String(m.capabilities||'').toLowerCase().split(';').includes(o)).forEach(m=>{
          const rel=(eco.relations||[]).filter(x=>String(x.from||'').toLowerCase()===String(m.model_name||'').toLowerCase());
          const rt=rel.filter(x=>x.type==='runs-on').map(x=>String(x.to));
          const hw=rel.filter(x=>x.type==='target').map(x=>String(x.to));
          const skills=rel.filter(x=>x.type==='supports').map(x=>String(x.to));
          const rtObj=(eco.runtimes||[]).filter(x=>rt.includes(x.id));
          const hwObj=(eco.hardware||[]).filter(x=>hw.includes(x.id));
          const hwOk=hwObj.filter(x=>(!r||String(x.ram||'')===r)&&(!g||String(x.gpu||'').toLowerCase()===g));
          const rtOk=rtObj.filter(x=>!onlyOSI||licenses.has(String(x.license||'').toLowerCase()));
          if((r||g)&&!hwOk.length) return;
          if(onlyOSI&&!rtOk.length) return;
          let score=35+(hwOk.length?30:0)+(rtOk.length?20:0)+(skills.length?10:0)+(m.status==='candidate'?5:0);
          out.push({m,rt:rtOk.map(x=>x.id),hw:hwOk.map(x=>x.id),skills,score});
        });
        out.sort((a,b)=>b.score-a.score);
        root.innerHTML=out.slice(0,6).map((x,i)=>`<article class="rec"><div class="score">#${i+1} · ${esc(x.m.model_name)} · ${x.score}/100</div><div class="path"><span class="node">${esc(x.m.model_name)}</span><span class="arrow">→</span><span class="node">${esc(x.rt.join(', ')||'runtime no registrado')}</span><span class="arrow">→</span><span class="node">${esc(x.skills.join(', ')||'skill no registrada')}</span><span class="arrow">→</span><span class="node">${esc(x.hw.join(', ')||'hardware no registrado')}</span></div><span class="check">Objetivo: ${esc(o)}</span>${onlyOSI?'<span class="check">Filtro OSI aplicado</span>':''}<div class="why">Compatibilidad inferida únicamente de relaciones y metadatos registrados. No equivale a rendimiento medido.</div></article>`).join('')||'<article class="rec"><strong>No hay combinación suficiente en los datos actuales.</strong></article>';
      }
      btn?.addEventListener('click',run); [ram,gpu,goal,osi].forEach(x=>x?.addEventListener('change',run)); run();
    }
  };
})();