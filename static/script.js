(function () {
  'use strict';

  const table = document.getElementById('kontroll-tabell');
  if (!table) return;

  const tbody = table.querySelector('tbody');

  /* ── Inline-redigering ─────────────────────────────────── */
  table.addEventListener('click', function (e) {
    // Klick på .editable → gör om till input
    const span = e.target.closest('.editable');
    if (span && !span.querySelector('input')) {
      const val = span.textContent;
      const input = document.createElement('input');
      input.type = 'text';
      input.value = val;
      span.textContent = '';
      span.appendChild(input);
      input.focus();
      input.select();

      const commit = () => {
        const newVal = input.value;
        span.textContent = newVal;
      };
      input.addEventListener('blur', commit);
      input.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); input.blur(); }
        if (ev.key === 'Escape') { span.textContent = val; }
      });
    }

    // Klick på Ta bort-knapp
    const delBtn = e.target.closest('button.btn-danger');
    if (delBtn) {
      const tr = delBtn.closest('tr');
      if (tr && !tr.classList.contains('locked')) {
        tr.remove();
      }
    }
  });

  /* ── Lägg till rubrik ──────────────────────────────────── */
  const addCategoryBtn = document.getElementById('add-category');
  if (addCategoryBtn) {
    addCategoryBtn.addEventListener('click', function () {
      const tr = document.createElement('tr');
      tr.className = 'category-row';
      tr.innerHTML =
        '<td colspan="5"><span class="editable">Ny rubrik – klicka för att ändra</span></td>' +
        '<td><button type="button" class="btn btn-danger btn-sm">Ta bort</button></td>';
      tbody.appendChild(tr);
      // Trigga direkt redigering
      tr.querySelector('.editable').click();
    });
  }

  /* ── Lägg till kontrollpunkt ───────────────────────────── */
  const addRowBtn = document.getElementById('add-row');
  if (addRowBtn) {
    addRowBtn.addEventListener('click', function () {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td><span class="editable">Ny kontrollpunkt</span></td>' +
        '<td><span class="editable">BH</span></td>' +
        '<td><span class="editable">Egenkontroll</span></td>' +
        '<td><span class="editable">Ritningar</span></td>' +
        '<td><span class="editable">Under arbetet</span></td>' +
        '<td><button type="button" class="btn btn-danger btn-sm">Ta bort</button></td>';
      tbody.appendChild(tr);
      tr.querySelector('.editable').click();
    });
  }

  /* ── Rensa icke-låsta rader ────────────────────────────── */
  const clearBtn = document.getElementById('clear-all');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      if (!confirm('Ta bort alla icke-låsta rader och rubriker?')) return;
      Array.from(tbody.querySelectorAll('tr:not(.locked)')).forEach(tr => tr.remove());
    });
  }

  /* ── Serialisera tabellen till hidden inputs vid PDF ────── */
  const form = document.getElementById('pdf-form');
  if (form) {
    form.addEventListener('submit', function () {
      // Commit eventuella pågående redigeringar
      tbody.querySelectorAll('.editable input').forEach(function (input) {
        const span = input.parentElement;
        span.textContent = input.value;
      });

      let container = document.getElementById('hidden-rows');
      if (!container) {
        container = document.createElement('div');
        container.id = 'hidden-rows';
        form.insertBefore(container, form.firstChild);
      }
      container.innerHTML = '';

      const addHidden = (name, value) => {
        const inp = document.createElement('input');
        inp.type = 'hidden';
        inp.name = name;
        inp.value = value;
        container.appendChild(inp);
      };

      tbody.querySelectorAll('tr').forEach(function (tr) {
        const tds = tr.querySelectorAll('td');
        const isCat = tr.classList.contains('category-row') ? '1' : '0';
        addHidden('is_category[]', isCat);
        if (isCat === '1') {
          addHidden('kategori[]', tds[0].innerText.trim());
        } else {
          addHidden('kp[]',       tds[0].innerText.trim());
          addHidden('vem[]',      tds[1].innerText.trim());
          addHidden('hur[]',      tds[2].innerText.trim());
          addHidden('mot[]',      tds[3].innerText.trim());
          addHidden('nar[]',      tds[4].innerText.trim());
          addHidden('signatur[]', '');
        }
      });
    });
  }
})();
