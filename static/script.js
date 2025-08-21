(function(){
  const table = document.getElementById('kontroll-tabell');
  if(!table) return;

  table.addEventListener('click', function(e){
    const span = e.target.closest('.editable');
    if(span){
      const current = span.textContent;
      const input = document.createElement('input');
      input.value = current;
      span.replaceWith(input);
      input.focus();
      input.addEventListener('blur', () => {
        const newSpan = document.createElement('span');
        newSpan.className = 'editable';
        newSpan.textContent = input.value;
        input.replaceWith(newSpan);
      });
    }
    const delBtn = e.target.closest('button.danger');
    if(delBtn){
      const tr = delBtn.closest('tr');
      if(tr && !tr.classList.contains('locked')){
        tr.remove();
      }
    }
  });

  const addCategory = document.getElementById('add-category');
  if(addCategory){
    addCategory.addEventListener('click', () => {
      const tr = document.createElement('tr');
      tr.className = 'category';
      tr.innerHTML = '<td><span class="editable">Ny rubrik</span></td><td></td><td></td><td></td><td></td><td></td><td><button type="button" class="danger">Ta bort</button></td>';
      table.querySelector('tbody').appendChild(tr);
    });
  }

  const addRow = document.getElementById('add-row');
  if(addRow){
    addRow.addEventListener('click', () => {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td><span class="editable">Ny kontrollpunkt</span></td><td><span class="editable">BH</span></td><td><span class="editable">Egenkontroll</span></td><td><span class="editable">Ritningar</span></td><td><span class="editable">Under arbetet</span></td><td><span class="editable"></span></td><td><button type="button" class="danger">Ta bort</button></td>';
      table.querySelector('tbody').appendChild(tr);
    });
  }

  const form = document.getElementById('pdf-form');
  if(form){
    form.addEventListener('submit', () => {
      const hidden = document.getElementById('hidden-rows');
      hidden.innerHTML = '';
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(tr => {
        const tds = tr.querySelectorAll('td');
        const isCat = tr.classList.contains('category') ? '1' : '0';
        const add = (name, value) => {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = name;
          input.value = value;
          hidden.appendChild(input);
        };
        add('is_category[]', isCat);
        if(isCat === '1'){
          const title = tds[0].innerText.trim();
          add('kategori[]', title);
        } else {
          add('kp[]', tds[0].innerText.trim());
          add('vem[]', tds[1].innerText.trim());
          add('hur[]', tds[2].innerText.trim());
          add('mot[]', tds[3].innerText.trim());
          add('nar[]', tds[4].innerText.trim());
          add('signatur[]', tds[5].innerText.trim());
        }
      });
    });
  }
})();