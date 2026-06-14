document.addEventListener('DOMContentLoaded', () => {
    const btnAiFilterSubmit = document.getElementById('btn-ai-filter-submit');
    if (!btnAiFilterSubmit) return;

    btnAiFilterSubmit.addEventListener('click', () => {
        const ingredientsInput = document.getElementById('ai-ingredients-input').value.trim();
        if (!ingredientsInput) {
            alert('Please enter some ingredients first.');
            return;
        }

        // Retrieve current filter values
        const dishType = document.getElementById('filter-dish-type').value;
        const prepTime = document.getElementById('filter-prep-time').value;
        const vegetarian = document.getElementById('filter-vegetarian').checked;
        const vegan = document.getElementById('filter-vegan').checked;
        const glutenFree = document.getElementById('filter-gluten-free').checked;
        const kosher = document.getElementById('filter-kosher').checked;

        // Construct a prompt query describing both the ingredients and active filters
        let prompt = `Ingredients: ${ingredientsInput}.`;
        let filterRequirements = [];

        if (dishType) filterRequirements.push(`Dish Type: ${dishType}`);
        if (prepTime && prepTime !== '9999') filterRequirements.push(`Max Cooking Time: ${prepTime} minutes`);
        if (vegetarian) filterRequirements.push('Vegetarian');
        if (vegan) filterRequirements.push('Vegan');
        if (glutenFree) filterRequirements.push('Gluten Free');
        if (kosher) filterRequirements.push('Kosher');

        if (filterRequirements.length > 0) {
            prompt += ` Dietary/Filter requirements: ${filterRequirements.join(', ')}.`;
        }

        // Set the prompt in the hidden form field and submit
        document.getElementById('ai-form-ingredients-field').value = prompt;
        document.getElementById('ai-filter-form').submit();
    });
});
