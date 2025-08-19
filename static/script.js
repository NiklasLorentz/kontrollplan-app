
function makeEditableCell(value=''){
  const s=document.createElement('span');
  s.contentEditable='true';
  s.className='editable';
  s.textContent=value||'';
  return s;
}
function buttonDanger(label='Ta bort'){
  const b=document.createElement('button');
  b.type='button'; b.textContent=label; b.className='danger';
  return b;
}
let lastRemoved=null;
function attachRemoveHandler(tr){
  const btn = tr.querySelector('button.danger');
  if(!btn) return;
  btn.onclick = () => {
    const tbody = document.querySelector('#kontroll-tabell tbody');
    const index = Array.from(tbody.children).indexOf(tr);
    lastRemoved = { html: tr.outerHTML, index };
    tr.remove();
    document.getElementById('undo-remove').disabled = false;
    rebuildHidden();
  };
}
function addCategoryRow(title='Ny rubrik'){
  const tbody = document.querySelector('#kontroll-tabell tbody');
  const tr = document.createElement('tr');
  tr.classList.add('category');
  const tdTitle = document.createElement('td');
  const span = document.createElement('span'); span.className='editable'; span.contentEditable='true'; span.textContent=title;
  tdTitle.appendChild(span);
  tr.appendChild(tdTitle);
  for (let i=0;i<5;i++){ tr.appendChild(document.createElement('td')); }
  const tdRemove = document.createElement('td');
  const btn = buttonDanger();
  tdRemove.appendChild(btn);
  tr.appendChild(tdRemove);
  tbody.appendChild(tr);
  attachRemoveHandler(tr);
  rebuildHidden();
}
function addDataRow(data={}){
  const tbody = document.querySelector('#kontroll-tabell tbody');
  const tr = document.createElement('tr');
  if (data.obligatorisk) tr.classList.add('locked');
  ['kontrollpunkt','vem','hur','mot','nar','signatur'].forEach(k=>{
    const td=document.createElement('td'); 
    const val=(data[k]||'');
    const span=document.createElement('span'); span.contentEditable='true'; span.className='editable'; span.textContent=val;
    td.appendChild(span); tr.appendChild(td);
  });
  const tdRemove=document.createElement('td');
  if (data.obligatorisk){ tdRemove.textContent='Låst'; tdRemove.title='Obligatorisk rad – kan inte tas bort'; }
  else { const btn=buttonDanger(); tdRemove.appendChild(btn); }
  tr.appendChild(tdRemove); tbody.appendChild(tr);
  if (!data.obligatorisk) attachRemoveHandler(tr);
  rebuildHidden();
}
function rebuildHidden(){
  const cont=document.getElementById('hidden-rows'); cont.innerHTML='';
  const rows=Array.from(document.querySelectorAll('#kontroll-tabell tbody tr'));
  rows.forEach(tr=>{
    const isCat=tr.classList.contains('category')?'1':'0';
    const cells=tr.querySelectorAll('td .editable'); const vals=Array.from(cells).map(c=>c.textContent.trim());
    function hidden(n,v){ const i=document.createElement('input'); i.type='hidden'; i.name=n; i.value=v; cont.appendChild(i); }
    if(isCat==='1'){ hidden('is_category[]','1'); hidden('kategori[]', vals[0]||''); }
    else{
      hidden('is_category[]','0'); hidden('kategori[]','');
      const [kp,vem,hur,mot,nar,sign]=vals;
      hidden('kp[]',kp||''); hidden('vem[]',vem||''); hidden('hur[]',hur||'');
      hidden('mot[]',mot||''); hidden('nar[]',nar||''); hidden('signatur[]',sign||'');
    }
  });
}
function undoLastRemove(){
  if(!lastRemoved) return;
  const tbody=document.querySelector('#kontroll-tabell tbody');
  const tmp=document.createElement('tbody'); tmp.innerHTML=(lastRemoved.html||'').trim();
  const restored=tmp.firstElementChild; const rows=Array.from(tbody.children);
  if(lastRemoved.index>=0&&lastRemoved.index<=rows.length){ if(lastRemoved.index===rows.length) tbody.appendChild(restored); else tbody.insertBefore(restored, rows[lastRemoved.index]); }
  else tbody.appendChild(restored);
  attachRemoveHandler(restored); lastRemoved=null; document.getElementById('undo-remove').disabled=true; rebuildHidden();
}
function init(){
  document.querySelectorAll('#kontroll-tabell tbody tr').forEach(tr=>attachRemoveHandler(tr));
  document.getElementById('add-category').onclick=()=>addCategoryRow('Ny rubrik');
  document.getElementById('add-row').onclick=()=>addDataRow({vem:'BH', hur:'Egenkontroll', mot:'Ritningar', nar:'Under arbetet'});
  document.getElementById('clear-all').onclick=()=>{ document.querySelector('#kontroll-tabell tbody').innerHTML=''; lastRemoved=null; document.getElementById('undo-remove').disabled=true; rebuildHidden(); };
  document.getElementById('undo-remove').onclick=undoLastRemove;
  document.querySelector('#kontroll-tabell').addEventListener('input', e=>{ if(e.target.matches('.editable')) rebuildHidden(); });
  document.getElementById('pdf-form').addEventListener('submit', rebuildHidden);
  rebuildHidden();
}
document.addEventListener('DOMContentLoaded', init);
