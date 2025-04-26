// Minimal confetti burst
function startConfetti() {
    const confettiContainer = document.getElementById('confetti');
    for (let i = 0; i < 100; i++) {
      const el = document.createElement('div');
      el.className = 'confetti';
      el.style.left = Math.random() * 100 + '%';
      el.style.animationDelay = Math.random() * 2 + 's';
      confettiContainer.appendChild(el);
    }
  }
  
  // CSS injected via JS for simplicity
  const style = document.createElement('style');
  style.innerHTML = `
    .confetti {
      position: absolute;
      width: 8px; height: 8px;
      background: rgba(255,255,255,0.8);
      animation: confetti-fall 3s linear infinite;
    }
    @keyframes confetti-fall {
      0% { transform: translateY(0) rotate(0); opacity:1 }
      100% { transform: translateY(100vh) rotate(360deg); opacity:0 }
    }
  `;
  document.head.appendChild(style);
  