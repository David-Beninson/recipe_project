document.addEventListener('DOMContentLoaded', () => {
    // Fetch hidden DOM elements that contain pre-populated data (e.g., when editing an existing recipe)
    const prepopulatedIngredientsEl = document.getElementById('prepopulated-ingredients');
    const prepopulatedInstructionsEl = document.getElementById('prepopulated-instructions');

    // Fetch input fields used for adding a new ingredient: name and amount
    const ingNameInput = document.getElementById('ing-name');
    const ingAmountInput = document.getElementById('ing-amount');

    // Fetch critical UI components: the add button, display zones, and final submission button
    const btnAddIngredient = document.getElementById('btn-add-ingredient');
    const inventoryZone = document.getElementById('inventory-zone');
    const instructionsZone = document.getElementById('instructions-zone');
    const submitBtn = document.getElementById('btn-submit-recipe');

    // Guard clause: If any required element is missing from the DOM, abort execution to prevent runtime errors
    if (!btnAddIngredient || !inventoryZone || !instructionsZone || !submitBtn) return;

    let ingredientsList = [];
    // Check if the pre-populated ingredients element exists and actually contains text
    if (prepopulatedIngredientsEl && prepopulatedIngredientsEl.textContent.trim()) {
        try {
            const rawIngs = JSON.parse(prepopulatedIngredientsEl.textContent);
            ingredientsList = rawIngs.map((ing, index) => {
                const name = ing.name;
                const amt = ing.original ? ing.original.replace(`${name} - `, '').trim() : `${ing.amount} ${ing.unit}`;
                return {
                    id: ing.id ? String(ing.id) : ('ing-' + index + '-' + Date.now()),
                    name: name,
                    originalAmount: amt,
                    qty: parseFloat(ing.amount) || parseFloat(ing.qty) || 1,
                    unitString: ing.unit || ing.unitString || '',
                    usedQty: parseFloat(ing.amount) || parseFloat(ing.qty) || 1
                };
            });
        } catch(e) {
            console.error("Error parsing ingredientsList:", e);
        }
    }

    if (prepopulatedInstructionsEl && instructionsZone) {
        instructionsZone.innerHTML = prepopulatedInstructionsEl.innerHTML;
        instructionsZone.querySelectorAll('.ing-qty-input').forEach(input => {
            const ingId = input.getAttribute('data-id');
            let ing = ingredientsList.find(i => i.id === ingId);
            if (!ing && input.parentElement) {
                const text = input.parentElement.textContent.replace(input.value, '').trim().toLowerCase();
                ing = ingredientsList.find(i => text.includes(i.name.toLowerCase()));
                if (ing) {
                    input.setAttribute('data-id', ing.id);
                    input.parentElement.setAttribute('data-id', ing.id);
                }
            }
            if (ing && (input.value === "0" || input.value === "")) {
                input.value = ing.qty;
                input.setAttribute('value', ing.qty);
            }
        });
    }

    // Handle file input name display change and image preview
    const recipeImageInput = document.getElementById('recipe-image');
    const fileNameDisplay = document.getElementById('file-name-display');
    const previewContainer = document.getElementById('image-preview-container');
    const previewImage = document.getElementById('recipe-image-preview');
    const recipeImageLabel = document.getElementById('recipe-image-label');
    const hiddenImageInput = document.getElementById('hidden-image');

    // Prepopulate preview if image is already saved in hidden-image
    if (hiddenImageInput && hiddenImageInput.value && previewImage) {
        previewImage.src = hiddenImageInput.value;
        if (previewContainer) previewContainer.style.display = 'block';
        if (recipeImageLabel) recipeImageLabel.style.display = 'none';
        if (fileNameDisplay) fileNameDisplay.style.display = 'none';
    }

    if (recipeImageInput && fileNameDisplay) {
        recipeImageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                fileNameDisplay.textContent = file.name;
                
                // Hide input button and name text, show preview
                if (recipeImageLabel) recipeImageLabel.style.display = 'none';
                fileNameDisplay.style.display = 'none';
                
                const reader = new FileReader();
                reader.onload = function (event) {
                    if (previewImage) previewImage.src = event.target.result;
                    if (previewContainer) previewContainer.style.display = 'block';
                    if (hiddenImageInput) hiddenImageInput.value = event.target.result;
                };
                reader.readAsDataURL(file);
            } else {
                fileNameDisplay.textContent = 'No file chosen';
                if (recipeImageLabel) recipeImageLabel.style.display = 'inline-flex';
                fileNameDisplay.style.display = 'block';
                if (previewContainer) previewContainer.style.display = 'none';
                if (previewImage) previewImage.src = '';
            }
        });
    }

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
        instructionsZone.querySelectorAll('.ing-qty-input').forEach(input => {
            const ingId = input.getAttribute('data-id');
            let ing = ingredientsList.find(i => i.id === ingId);
            if (!ing && input.parentElement) {
                const text = input.parentElement.textContent.replace(input.value, '').trim().toLowerCase();
                ing = ingredientsList.find(i => text.includes(i.name.toLowerCase()));
                if (ing) {
                    input.setAttribute('data-id', ing.id);
                    input.parentElement.setAttribute('data-id', ing.id);
                }
            }
            if (ing) ing.usedQty += parseFloat(input.value) || 0;
        });
        ingredientsList.forEach(ing => {
            const isExact = ing.usedQty === ing.qty;
            const isPartial = ing.usedQty > 0 && ing.usedQty < ing.qty;
            const statusClass = isExact ? 'green' : (isPartial ? 'orange' : 'red');

            instructionsZone.querySelectorAll(`.inline-ing[data-id="${ing.id}"]`).forEach(el => {
                el.classList.remove('red', 'orange', 'green');
                el.classList.add(statusClass);
            });
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
                <span class="ing-name">${ing.name}</span>
                <input type="number" class="ing-qty-input" data-id="${ing.id}" value="0" min="0" max="${ing.qty}" step="any" oninput="updateTotals()"> 
                <span class="ing-unit">${ing.unitString}</span>
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
        instructionsZone.querySelectorAll('.ing-qty-input').forEach(input => {
            input.setAttribute('value', input.value);
        });
        document.getElementById('hidden-ingredients').value = JSON.stringify(ingredientsList);
        document.getElementById('hidden-instructions').value = instructionsZone.innerHTML;
    });

    if (ingredientsList.length > 0) {
        updateTotals();
    }
});
