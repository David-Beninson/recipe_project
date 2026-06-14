document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id), $$ = sel => document.querySelectorAll(sel);

    // 1. Handle ingredient click for substitutes or selection mode
    $$('.clickable-ingredient').forEach(item => {
        item.addEventListener('click', async () => {
            const cb = item.querySelector('.ai-select-ingredient-checkbox');
            if (document.body.classList.contains('ai-selection-mode')) {
                if (cb) {
                    cb.checked = !cb.checked;
                    item.style.backgroundColor = cb.checked ? '#f3e5f5' : '';
                    item.style.border = cb.checked ? '1px solid #7c4dff' : '';
                }
                return;
            }

            const name = item.getAttribute('data-name'), subSec = $('substitutes-section'), subList = $('substitutes-list');
            if (!subSec || !subList) return;

            const recBox = $('ai-quick-recommendation');
            if (recBox) recBox.style.display = 'none';

            subList.innerHTML = '<li>Loading...</li>';
            subSec.style.display = 'block';
            if ($('sub-title')) $('sub-title').textContent = name;

            const btn = $('btn-ai-quick-sub');
            if (btn) btn.setAttribute('data-ingredient', name);

            try {
                const res = await fetch(`/substitutes?ingredient=${encodeURIComponent(name)}`);
                const data = await res.json();
                subList.innerHTML = data.substitutes?.length ? data.substitutes.map(s => `<li>${s}</li>`).join('') : '<li>No substitutes found.</li>';
            } catch {
                subList.innerHTML = '<li>Error loading substitutes.</li>';
            }
        });
    });

    // 2. Selection Mode Toggle Button
    const btnToggle = $('btn-toggle-select-mode');
    if (btnToggle) {
        btnToggle.addEventListener('click', () => {
            const active = document.body.classList.toggle('ai-selection-mode');
            btnToggle.textContent = active ? 'Cancel Selection' : 'Select & swap ingredients';
            btnToggle.style.backgroundColor = active ? '#f44336' : '';
            
            $$('.ai-select-ingredient-checkbox').forEach(cb => {
                cb.style.display = active ? 'inline-block' : 'none';
                if (!active) cb.checked = false;
            });
            if (!active) $$('.clickable-ingredient').forEach(i => i.style.backgroundColor = i.style.border = '');
            if ($('ai-multi-replace-card')) $('ai-multi-replace-card').style.display = active ? 'block' : 'none';
        });
    }

    // 3. Quick AI substitute suggestion
    const btnQuick = $('btn-ai-quick-sub');
    if (btnQuick) {
        btnQuick.addEventListener('click', async () => {
            const ing = btnQuick.getAttribute('data-ingredient'), id = btnQuick.getAttribute('data-recipe-id');
            const box = $('ai-quick-recommendation'), txt = $('ai-quick-recommendation-text');
            if (!ing || !id) return;
            if (txt) txt.textContent = 'Thinking...';
            if (box) box.style.display = 'block';

            try {
                const res = await fetch(`/ai/quick-substitute?recipe_id=${id}&ingredient=${encodeURIComponent(ing)}`);
                const data = await res.json();
                if (txt) txt.textContent = data.recommendation || 'Could not retrieve recommendation.';
            } catch {
                if (txt) txt.textContent = 'Error loading AI recommendation.';
            }
        });
    }

    // 4. Multi-ingredient recipe adaptation form submission
    const form = $('ai-multi-substitute-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            const checked = Array.from($$('.ai-select-ingredient-checkbox:checked')).map(cb => cb.value);
            if (!checked.length) {
                e.preventDefault();
                return alert('Please select at least one ingredient to replace.');
            }
            if ($('ai-multi-replace-val')) $('ai-multi-replace-val').value = checked.join(', ');
        });
    }
});
