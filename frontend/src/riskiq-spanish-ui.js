/* RiskIQ UI language normalization. Technical product terms remain in English; explanatory UI copy is Spanish. */
const replacements = new Map([
  ['RISK OPERATING SYSTEM / OVERVIEW','RISK OPERATING SYSTEM / CENTRO DE MANDO'],
  ['Specialist cockpit','Cockpit especializado'],
  ['Risk concentration','Concentración de riesgo'],
  ['Cohort intelligence','Inteligencia de cohortes'],
  ['Roll rate & velocity','Roll rate y velocidad'],
  ['Scenario lab','Laboratorio de escenarios'],
  ['Human review','Revisión humana'],
  ['Low-code policies','Políticas Low-code'],
  ['Data quality','Calidad de datos'],
  ['Evidence engine online','Motor de evidencia en línea'],
  ['Human review required','Revisión humana requerida'],
  ['Evidence available','Evidencia disponible'],
  ['No dataset selected','Sin cartera seleccionada'],
  ['Dataset loaded','Cartera cargada'],
  ['Run analysis','Ejecutar análisis'],
  ['Loading...','Cargando…'],
  ['Loading…','Cargando…'],
  ['Processing…','Procesando…'],
  ['Analyzing evidence','Analizando evidencia'],
  ['No persisted decisions available','No hay decisiones registradas'],
  ['No decisions available','No hay decisiones disponibles'],
  ['No data available','No hay datos disponibles'],
  ['Data quality','Calidad de datos'],
  ['Decision queue','Cola de decisiones'],
  ['Decision result','Resultado de la decisión'],
  ['Decision path','Ruta de decisión'],
  ['Input & facts','Entradas y hechos'],
  ['Policy match','Coincidencia de política'],
  ['Top risk drivers','Principales factores de riesgo'],
  ['Decision evidence ledger','Registro de evidencia de decisiones'],
  ['Governance','Gobierno y control'],
  ['Evidence trace','Trazabilidad de evidencia'],
  ['Triggered rules','Reglas activadas'],
  ['Reason codes','Códigos de motivo'],
  ['Base case','Escenario base'],
  ['Scenario','Escenario'],
  ['Stress','Estrés'],
  ['Result','Resultado'],
  ['Portfolio posture','Situación de la cartera'],
  ['Key indicators','Indicadores principales'],
  ['Risk signals','Señales de riesgo'],
  ['Recent movement','Movimiento reciente'],
  ['Next best analysis','Próximo análisis recomendado'],
  ['No trend available','No hay tendencia disponible'],
  ['Current snapshot','Corte actual'],
  ['Previous snapshot','Corte anterior'],
]);

function normalize(root=document.body){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];
  while(walker.nextNode()) nodes.push(walker.currentNode);
  for(const node of nodes){
    let value=node.nodeValue;
    for(const [from,to] of replacements){
      if(value.includes(from)) value=value.split(from).join(to);
    }
    if(value!==node.nodeValue) node.nodeValue=value;
  }
}

export function installRiskIQLanguage(){
  if(typeof document==='undefined') return ()=>{};
  normalize();
  const observer=new MutationObserver(mutations=>{
    for(const mutation of mutations){
      if(mutation.type==='childList') for(const node of mutation.addedNodes){
        if(node.nodeType===Node.TEXT_NODE){
          let value=node.nodeValue;
          for(const [from,to] of replacements) value=value.split(from).join(to);
          node.nodeValue=value;
        } else if(node.nodeType===Node.ELEMENT_NODE) normalize(node);
      }
    }
  });
  observer.observe(document.body,{childList:true,subtree:true});
  return ()=>observer.disconnect();
}
