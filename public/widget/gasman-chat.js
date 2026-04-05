(function () {
  'use strict';

  var API_BASE = (function () {
    var scripts = document.getElementsByTagName('script');
    var src = scripts[scripts.length - 1].src;
    return src.replace('/widget/gasman-chat.js', '');
  })();

  var conversationId = null;

  // Inject CSS
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = API_BASE + '/widget/gasman-chat.css';
  document.head.appendChild(link);

  // Build HTML
  var wrapper = document.createElement('div');
  wrapper.id = 'gasman-chat-widget';
  wrapper.innerHTML = [
    '<button id="gasman-chat-bubble" aria-label="Open Gas Man Ottawa chat">',
      '<div id="gasman-online-dot"></div>',
      '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">',
        '<path d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26A7.002 7.002 0 0 0 19 9c0-3.87-3.13-7-7-7zm1 14h-2v-1.08C8.48 14.41 7 11.86 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 2.86-1.48 5.41-4 5.92V16zm-1 4c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z"/>',
      '</svg>',
    '</button>',
    '<div id="gasman-chat-window" role="dialog" aria-label="Gas Man Ottawa chat">',
      '<div id="gasman-chat-header">',
        '<div class="gasman-logo">',
          '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">',
            '<path d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26A7.002 7.002 0 0 0 19 9c0-3.87-3.13-7-7-7zm1 14h-2v-1.08C8.48 14.41 7 11.86 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 2.86-1.48 5.41-4 5.92V16zm-1 4c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z"/>',
          '</svg>',
        '</div>',
        '<div class="gasman-header-text">',
          '<h3>Gas Man Assistant</h3>',
          '<p>Answers in seconds, 24/7</p>',
        '</div>',
        '<button id="gasman-close-btn" aria-label="Close chat">',
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
        '</button>',
      '</div>',
      '<div id="gasman-messages"></div>',
      '<div id="gasman-suggestions"></div>',
      '<div id="gasman-input-area">',
        '<textarea id="gasman-input" rows="1" placeholder="Ask about heating, cooling, or gas..."></textarea>',
        '<button id="gasman-send-btn" aria-label="Send message">',
          '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
        '</button>',
      '</div>',
    '</div>',
  ].join('');

  document.body.appendChild(wrapper);

  var bubble = document.getElementById('gasman-chat-bubble');
  var chatWindow = document.getElementById('gasman-chat-window');
  var closeBtn = document.getElementById('gasman-close-btn');
  var messages = document.getElementById('gasman-messages');
  var suggestions = document.getElementById('gasman-suggestions');
  var input = document.getElementById('gasman-input');
  var sendBtn = document.getElementById('gasman-send-btn');

  var isOpen = false;
  var isTyping = false;

  var EMERGENCY_KEYWORDS = [
    'gas smell', 'smell gas', 'carbon monoxide', 'co detector', 'no heat',
    'furnace not working', 'emergency', 'odeur de gaz', 'monoxyde de carbone',
    'pas de chauffage', 'urgence'
  ];

  var BOOKING_TRIGGERS = [
    'pass your info', 'collect your', 'set one up', 'book a free estimate',
    'reach out shortly', 'contact you shortly', 'book an estimate', 'schedule'
  ];

  function isEmergency(text) {
    var lower = text.toLowerCase();
    return EMERGENCY_KEYWORDS.some(function (kw) { return lower.indexOf(kw) !== -1; });
  }

  function shouldShowBooking(botText) {
    var lower = botText.toLowerCase();
    return BOOKING_TRIGGERS.some(function (kw) { return lower.indexOf(kw) !== -1; });
  }

  function toggleChat() {
    isOpen = !isOpen;
    var isMobile = window.innerWidth <= 440;
    if (isOpen) {
      chatWindow.classList.add('gasman-open');
      if (isMobile) bubble.classList.add('gasman-hidden');
      input.focus();
      if (messages.children.length === 0) {
        loadConfig();
      }
    } else {
      chatWindow.classList.remove('gasman-open');
      bubble.classList.remove('gasman-hidden');
    }
  }

  function loadConfig() {
    fetch(API_BASE + '/api/widget/config')
      .then(function (r) { return r.json(); })
      .then(function (cfg) {
        appendBotMessage(cfg.greeting, false);
        if (cfg.suggestions && cfg.suggestions.length) {
          showSuggestions(cfg.suggestions);
        }
      })
      .catch(function () {
        appendBotMessage("Hi! I'm the Gas Man Ottawa assistant. How can I help you today?", false);
        showSuggestions([
          'I need a new furnace',
          'Emergency — no heat!',
          'Book a free estimate',
          'Do you service my area?'
        ]);
      });
  }

  function showSuggestions(items) {
    suggestions.innerHTML = '';
    items.forEach(function (text) {
      var btn = document.createElement('button');
      btn.className = 'gasman-suggestion-btn';
      btn.textContent = text;
      btn.addEventListener('click', function () {
        hideSuggestions();
        sendMessage(text);
      });
      suggestions.appendChild(btn);
    });
  }

  function hideSuggestions() {
    suggestions.innerHTML = '';
  }

  function showBookingButton() {
    suggestions.innerHTML = '';
    var btn = document.createElement('button');
    btn.className = 'gasman-suggestion-btn';
    btn.style.cssText = 'background:#E8531E;color:white;border-color:#E8531E;width:100%';
    btn.textContent = '📅 Fill Out Booking Form';
    btn.addEventListener('click', function () {
      hideSuggestions();
      showBookingFormMessage();
    });
    suggestions.appendChild(btn);
  }

  function showBookingFormMessage() {
    var div = document.createElement('div');
    div.className = 'gasman-msg gasman-bot gasman-form-msg';
    div.innerHTML = [
      '<div class="gasman-form-title">📅 Book a Free Estimate</div>',
      '<div class="gasman-form-row"><input type="text" class="gf-name" placeholder="Your name *"></div>',
      '<div class="gasman-form-row"><input type="tel" class="gf-phone" placeholder="Phone number *"></div>',
      '<div class="gasman-form-row"><input type="email" class="gf-email" placeholder="Email address"></div>',
      '<div class="gasman-form-row"><input type="text" class="gf-service" placeholder="Service needed (e.g. New furnace)"></div>',
      '<div class="gasman-form-row"><input type="text" class="gf-time" placeholder="Best time to reach you"></div>',
      '<div class="gasman-form-row"><input type="text" class="gf-notes" placeholder="Any notes?"></div>',
      '<button class="gasman-form-submit" onclick="window._gasmanSubmitBooking(this)">Send Request →</button>',
    ].join('');
    messages.appendChild(div);
    scrollToBottom();
  }

  window._gasmanSubmitBooking = function (btn) {
    var form = btn.closest('.gasman-form-msg');
    var name = form.querySelector('.gf-name').value.trim();
    var phone = form.querySelector('.gf-phone').value.trim();
    if (!name || !phone) {
      form.querySelector('.gf-name').style.borderColor = name ? '' : '#ef4444';
      form.querySelector('.gf-phone').style.borderColor = phone ? '' : '#ef4444';
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Sending...';

    var payload = {
      name: name,
      phone: phone,
      email: form.querySelector('.gf-email').value.trim() || null,
      service_needed: form.querySelector('.gf-service').value.trim() || null,
      preferred_time: form.querySelector('.gf-time').value.trim() || null,
      notes: form.querySelector('.gf-notes').value.trim() || null,
      conversation_id: conversationId,
    };

    fetch(API_BASE + '/api/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        // Replace form with confirmation
        form.innerHTML = '<div style="text-align:center;padding:8px 0"><div style="font-size:24px;margin-bottom:8px">✅</div><strong>Request sent!</strong><p style="font-size:13px;color:#6b7280;margin-top:4px">We\'ll call you at ' + name.split(' ')[0] + '\'s number shortly — usually within the hour!</p></div>';
        scrollToBottom();
        // Also send a chat message so the bot knows
        sendMessage('I just submitted my booking request. My name is ' + name + ' and my phone is ' + phone + '.');
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Try Again';
        appendBotMessage('Sorry, something went wrong. Please call us directly at (613) 880-3888.', false);
      });
  };

  function appendUserMessage(text) {
    var div = document.createElement('div');
    div.className = 'gasman-msg gasman-user';
    div.textContent = text;
    messages.appendChild(div);
    scrollToBottom();
  }

  function appendBotMessage(text, emergency) {
    var div = document.createElement('div');
    div.className = 'gasman-msg gasman-bot' + (emergency ? ' gasman-emergency' : '');
    div.innerHTML = formatMessage(text);
    messages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function formatMessage(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  function showTypingIndicator() {
    var div = document.createElement('div');
    div.className = 'gasman-typing';
    div.id = 'gasman-typing-indicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    messages.appendChild(div);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var el = document.getElementById('gasman-typing-indicator');
    if (el) el.remove();
  }

  function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function sendMessage(text) {
    text = (text || '').trim();
    if (!text || isTyping) return;

    hideSuggestions();
    appendUserMessage(text);
    input.value = '';
    autoResizeInput();

    isTyping = true;
    sendBtn.disabled = true;
    showTypingIndicator();

    var emergency = isEmergency(text);

    fetch(API_BASE + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, conversation_id: conversationId }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTypingIndicator();
        conversationId = data.conversation_id;
        appendBotMessage(data.response, emergency);
        if (shouldShowBooking(data.response)) {
          setTimeout(showBookingButton, 400);
        }
      })
      .catch(function () {
        removeTypingIndicator();
        appendBotMessage(
          'Sorry, I\'m having trouble connecting right now. Please call us at (613) 880-3888 for immediate help.',
          false
        );
      })
      .finally(function () {
        isTyping = false;
        sendBtn.disabled = false;
        input.focus();
      });
  }

  function autoResizeInput() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 100) + 'px';
  }

  bubble.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);
  sendBtn.addEventListener('click', function () { sendMessage(input.value); });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  input.addEventListener('input', autoResizeInput);
})();
