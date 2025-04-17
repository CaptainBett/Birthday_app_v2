// Live update of summary bar
const amountInput = document.querySelector('input[name="amount"]');
const phoneInput  = document.querySelector('input[name="phone"]');
const sumAmt      = document.getElementById('sum-amount');
const sumPhone    = document.getElementById('sum-phone');

function updateSummary() {
  sumAmt.textContent   = amountInput.value ? `KES ${amountInput.value}` : 'KES 0';
  sumPhone.textContent = phoneInput.value;
}

if (amountInput && phoneInput) {
  amountInput.addEventListener('input', updateSummary);
  phoneInput.addEventListener('input', updateSummary);
}
