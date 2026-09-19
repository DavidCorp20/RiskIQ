(()=>{
 const style=document.createElement('style');
 style.textContent='.sim-impact{margin-top:18px}.sim-impact-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:10px}.sim-impact-card{border:1px solid rgba(15,23,42,.09);border-radius:14px;padding:16px;background:rgba(255,255,255,.72)}.sim-impact-card .label{display:block;font-size:10px;font-weight:800;letter-spacing:.12em;color:#64748b;margin-bottom:8px}.sim-impact-card strong{font-size:20px}.sim-impact-card p{margin:7px 0 0;line-height:1.45}.sim-impact-card.warn{border-left:4px solid #f59e0b}.sim-impact-card.good{border-left:4px solid #10b981}.sim-impact-card.bad{border-left:4px solid #ef4444}.sim-governance{margin-top:12px;padding:12px 14px;border-radius:12px;background:#f8fafc;color:#64748b;font-size:12px}@media(max-width:800px){.sim-impact-grid{grid-template-columns:1fr}}';document.head.appendChild(style);
 let last=null;
 const esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
 const money=v=>Number(v||0).toLocaleString(undefined,{maximumFractionDigits:0});
 const pp=v=>`${Number(v||0).toFixed(2)} pp`;
 const render=()=>{
  if(!last)return;
  const cards=document.querySelectorAll('.metric');
  if(!cards.length)return;
  let anchor=cards[cards.length-1].closest('.card')||cards[cards.length-1];
  let host=document.querySelector('.sim-impact');
  if(!host){host=document.createElement('div');host.className='sim-impact';anchor.parentNode.insertBefore(host,anchor.nextSibling)}
  const d=last.delta||{},i=last.impact||{},g=last.governance||{};
  const direction=String(i.direction||'remains stable');
  const tone=direction==='improves'?'good':direction==='deteriorates'?'bad':'warn';
  host.innerHTML=`<div class="sim-impact-grid"><div class="sim-impact-card ${tone}"><span class="label">DIRECCIÓN</span><strong>${esc(direction)}</strong><p>Escenario ${esc(last.name||'personalizado')} sobre el snapshot persistido.</p></div><div class="sim-impact-card ${Number(d.at_risk_30||0)>0?'warn':'good'}"><span class="label">IMPACTO PAR30</span><strong>${pp(i.par30_delta_pp)}</strong><p>Exposición PAR30: ${money(d.at_risk_30)} vs baseline.</p></div><div class="sim-impact-card ${Number(d.at_risk_90||0)>0?'warn':'good'}"><span class="label">IMPACTO PAR90</span><strong>${pp(i.par90_delta_pp)}</strong><p>Exposición PAR90: ${money(d.at_risk_90)} vs baseline.</p></div></div><div class="sim-governance"><strong>Revisión humana requerida.</strong> No se infiere causalidad y RiskIQ no ejecuta acciones sobre clientes automáticamente.</div>`;
 };
 const original=window.fetch;
 window.fetch=async(...args)=>{const res=await original(...args);try{const url=typeof args[0]==='string'?args[0]:args[0]?.url||'';if(url.includes('/api/v1/simulator/run')){const clone=res.clone();const data=await clone.json();if(data?.scenario)last=data;setTimeout(render,0)}}catch{}return res};
 new MutationObserver(render).observe(document.documentElement,{childList:true,subtree:true});
})();
