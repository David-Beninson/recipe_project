document.addEventListener('DOMContentLoaded', () => {
    let ingredientsList = [];

    const ingNameInput = document.getElementById('ing-name');
    const ingAmountInput = document.getElementById('ing-amount');
    const btnAddIngredient = document.getElementById('btn-add-ingredient');
    const inventoryZone = document.getElementById('inventory-zone');
    const instructionsZone = document.getElementById('instructions-zone');
    const submitBtn = document.getElementById('btn-submit-recipe');

    if (!btnAddIngredient || !inventoryZone || !instructionsZone || !submitBtn) return;

    // Add new ingredient
    btnAddIngredient.addEventListener('click', () => {
        if (!ingNameInput.value || !ingAmountInput.value) return;

        const rawAmount = ingAmountInput.value;
        ingredientsList.push({
            id: 'ing-' + Date.now(),
            name: ingNameInput.value,
            originalAmount: rawAmount,
            qty: parseFloat(rawAmount) || 1,
            unitString: rawAmount.replace(/[0-9.]/g, '').trim(),
            usedQty: 0
        });

        ingNameInput.value = ingAmountInput.value = '';
        renderInventory();
    });

    // Remove ingredient entirely
    window.deleteIngredient = function (id) {
        ingredientsList = ingredientsList.filter(ing => ing.id !== id);
        document.querySelectorAll(`.inline-ing[data-id="${id}"]`).forEach(el => el.remove());
        updateTotals();
    };

    // Calculate total usage from instructions text input elements
    window.updateTotals = function () {
        ingredientsList.forEach(ing => ing.usedQty = 0);
        document.querySelectorAll('.ing-qty-input').forEach(input => {
            const ing = ingredientsList.find(i => i.id === input.getAttribute('data-id'));
            if (ing) ing.usedQty += parseFloat(input.value) || 0;
        });
        renderInventory();
    };

    instructionsZone.addEventListener('input', updateTotals);

    function setupDragAndDrop() {
        document.querySelectorAll('.draggable-ing').forEach(item => {
            item.addEventListener('dragstart', e => e.dataTransfer.setData('text/custom-id', item.id));
        });
    }

    // Handle dropping ingredients into instructions text editor
    instructionsZone.addEventListener('dragover', e => e.preventDefault());
    instructionsZone.addEventListener('drop', e => {
        e.preventDefault();
        const id = e.dataTransfer.getData('text/custom-id');
        const ing = ingredientsList.find(i => i.id === id);
        if (!ing) return;

        const htmlToInsert = `
            <span class="inline-ing" contenteditable="false" data-id="${ing.id}">
                ${ing.name} 
                <input type="number" class="ing-qty-input" data-id="${ing.id}" value="0" min="0" max="${ing.qty}" step="any" oninput="updateTotals()"> 
                ${ing.unitString}
            </span>&nbsp;`;

        let range = document.caretRangeFromPoint ? document.caretRangeFromPoint(e.clientX, e.clientY) : null;
        if (!range && document.caretPositionFromPoint) {
            const pos = document.caretPositionFromPoint(e.clientX, e.clientY);
            range = document.createRange();
            range.setStart(pos.offsetNode, pos.offset);
            range.collapse(true);
        }

        if (range) {
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }
        document.execCommand('insertHTML', false, htmlToInsert);
        instructionsZone.focus();
    });

    // Render the Inventory UI and handle validation state
    function renderInventory() {
        document.querySelectorAll('.draggable-ing').forEach(el => el.remove());
        let allGreen = ingredientsList.length > 0;

        ingredientsList.forEach(ing => {
            const el = document.createElement('div');
            el.id = ing.id;
            el.draggable = true;

            const isExact = ing.usedQty === ing.qty;
            const isPartial = ing.usedQty > 0 && ing.usedQty < ing.qty;
            const color = isExact ? 'green' : (isPartial ? 'orange' : 'red');
            if (!isExact) allGreen = false;

            el.className = `draggable-ing ${color}`;
            el.innerHTML = `
                ${ing.name} - ${ing.originalAmount} <small>(Used: ${ing.usedQty})</small>
                <button type="button" onclick="deleteIngredient('${ing.id}')" class="btn-delete-ing">X</button>
            `;
            inventoryZone.appendChild(el);
        });

        submitBtn.disabled = !allGreen;
        setupDragAndDrop();
    }

    document.getElementById('add-recipe-form').addEventListener('submit', () => {
        document.getElementById('hidden-ingredients').value = JSON.stringify(ingredientsList);
        document.getElementById('hidden-instructions').value = instructionsZone.innerHTML;
    });
});
