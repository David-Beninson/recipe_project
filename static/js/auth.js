// Toggle between showing and hiding password
function togglePasswordVisibility(inputId, button) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.type = input.type === 'password' ? 'text' : 'password';
    const isHidden = input.type === 'password';
    button.textContent = isHidden ? '𓁹' : '‿';
    button.setAttribute('aria-label', isHidden ? 'Show password' : 'Hide password');
}
