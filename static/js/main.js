document.addEventListener('click', async (event) => {
    const likeBtn = event.target.closest('.btn-like-ajax');
    if (!likeBtn) return;

    event.preventDefault();
    const recipeId = likeBtn.getAttribute('data-recipe-id');
    const wasLiked = likeBtn.classList.contains('liked');

    // Helper to toggle active class and increment/decrement count optimistically
    const updateUI = (liked) => {
        document.querySelectorAll(`.btn-like-ajax[data-recipe-id="${recipeId}"]`).forEach(btn => btn.classList.toggle('liked', liked));
        document.querySelectorAll(`.recipe-likes-count[data-recipe-id="${recipeId}"]`).forEach(span => {
            const count = parseInt(span.textContent) || 0;
            span.textContent = Math.max(0, count + (liked ? 1 : -1));
        });
    };

    // 1. Optimistic Update
    updateUI(!wasLiked);

    try {
        const response = await fetch(`/recipe/${recipeId}/like`, { method: 'POST' });
        if (response.ok) {
            const data = await response.json();
            // 2. Sync with exact database values from server
            document.querySelectorAll(`.btn-like-ajax[data-recipe-id="${recipeId}"]`).forEach(btn => btn.classList.toggle('liked', data.status === 'liked'));
            document.querySelectorAll(`.recipe-likes-count[data-recipe-id="${recipeId}"]`).forEach(span => span.textContent = data.likes);
        } else {
            throw new Error();
        }
    } catch {
        // 3. Revert to original state on failure
        updateUI(wasLiked);
    }
});

// Toggle recipe card active state (open/close dropdown) on click
document.addEventListener('click', (event) => {
    const recipeItem = event.target.closest('.recipe-item');
    const clickedInsideDropdown = event.target.closest('.recipe-dropdown-overlay');
    
    // If the click was not inside a recipe item, or if it was inside the dropdown's interactive actions,
    // we should close any active recipe items that are currently open.
    if (!recipeItem || clickedInsideDropdown) {
        if (!clickedInsideDropdown) {
            document.querySelectorAll('.recipe-item.active').forEach(activeItem => {
                activeItem.classList.remove('active');
            });
        }
        return;
    }

    // Toggle the clicked recipe item
    const wasActive = recipeItem.classList.contains('active');
    
    // Close all open cards first
    document.querySelectorAll('.recipe-item.active').forEach(activeItem => {
        activeItem.classList.remove('active');
    });

    // Toggle active state on the clicked item
    if (!wasActive) {
        recipeItem.classList.add('active');
    }
});

// Handle AI filter generator submit button on the search page with loading feedback
document.addEventListener('click', (event) => {
    const btnSubmit = event.target.closest('#btn-ai-filter-submit');
    if (!btnSubmit) return;

    const input = document.getElementById('ai-ingredients-input');
    const form = document.getElementById('ai-filter-form');
    const field = document.getElementById('ai-form-ingredients-field');

    if (input && form && field) {
        const value = input.value.trim();
        if (!value) {
            alert('Please enter ingredients for the AI to use.');
            return;
        }
        field.value = value;
        
        // Disable button and show loading text
        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Looking for recipe...';
        
        form.submit();
    }
});

// Handle AI generator fallback submit button on the search results page with loading feedback
document.addEventListener('click', (event) => {
    const btnAiGenerate = event.target.closest('#btn-ai-generate');
    if (!btnAiGenerate) return;

    btnAiGenerate.disabled = true;
    btnAiGenerate.textContent = 'Looking for recipe...';
    
    const form = document.getElementById('ai-generate-form');
    if (form) {
        form.submit();
    }
});

// Handle "New Search" button click to show the search card again, clear inputs, and hide results
document.addEventListener('click', (event) => {
    const btnNewSearch = event.target.closest('#btn-new-search');
    if (!btnNewSearch) return;

    const searchCard = document.querySelector('.search-card');
    const recipesContainer = document.querySelector('.recipes');

    // Show the search inputs card again
    if (searchCard) {
        searchCard.classList.remove('hidden');
    }
    
    // Hide all search results and the AI custom generator card
    if (recipesContainer) {
        recipesContainer.classList.add('hidden');
    }

    // Clear the search query inputs so the user starts fresh
    const ingredientsInput = document.getElementById('ingredients');
    if (ingredientsInput) {
        ingredientsInput.value = '';
    }
    const aiIngredientsInput = document.getElementById('ai-ingredients-input');
    if (aiIngredientsInput) {
        aiIngredientsInput.value = '';
    }
});
