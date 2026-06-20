(function() {
  // Extract agent ID from script tag
  const scriptTag = document.currentScript;
  const agentId = scriptTag.getAttribute('data-agent-id');
  const host = new URL(scriptTag.src).origin;

  if (!agentId) {
    console.error('CallForce Widget: data-agent-id attribute is missing.');
    return;
  }

  // Inject styles
  const style = document.createElement('style');
  style.innerHTML = `
    #callforce-widget-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #callforce-widget-iframe {
      width: 380px;
      height: 600px;
      border: none;
      border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.15);
      opacity: 0;
      transform: translateY(20px) scale(0.95);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: none;
      background: transparent;
      margin-bottom: 16px;
      transform-origin: bottom right;
    }
    #callforce-widget-iframe.cf-open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }
    #callforce-widget-button {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background-color: #fff;
      color: #000;
      border: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s ease;
    }
    #callforce-widget-button:hover {
      transform: scale(1.05);
    }
    #callforce-widget-button svg {
      width: 24px;
      height: 24px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    @media (max-width: 480px) {
      #callforce-widget-iframe {
        width: calc(100vw - 32px);
        height: calc(100vh - 100px);
        bottom: 80px;
        right: 16px;
      }
      #callforce-widget-container {
        bottom: 16px;
        right: 16px;
      }
    }
  `;
  document.head.appendChild(style);

  // Container
  const container = document.createElement('div');
  container.id = 'callforce-widget-container';

  // Iframe
  const iframe = document.createElement('iframe');
  iframe.id = 'callforce-widget-iframe';
  iframe.src = `${host}/widget/${agentId}`;

  // Button
  const button = document.createElement('button');
  button.id = 'callforce-widget-button';

  const iconChat = '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
  const iconClose = '<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';

  button.innerHTML = iconChat;

  let isOpen = false;
  button.addEventListener('click', () => {
    isOpen = !isOpen;
    if (isOpen) {
      iframe.classList.add('cf-open');
      button.innerHTML = iconClose;
    } else {
      iframe.classList.remove('cf-open');
      button.innerHTML = iconChat;
    }
  });

  container.appendChild(iframe);
  container.appendChild(button);
  document.body.appendChild(container);
})();
