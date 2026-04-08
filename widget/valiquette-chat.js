(function () {
  'use strict';

  var API_BASE = (function () {
    var scripts = document.getElementsByTagName('script');
    var src = scripts[scripts.length - 1].src;
    return src.replace('/widget/valiquette-chat.js', '');
  })();

  var conversationId = null;

  // Inject CSS
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = API_BASE + '/widget/valiquette-chat.css';
  document.head.appendChild(link);

  // Build HTML
  var wrapper = document.createElement('div');
  wrapper.id = 'vm-chat-widget';
  wrapper.innerHTML = [
    '<button id="vm-chat-bubble" aria-label="Open Valiquette Mechanical chat">',
      '<div id="vm-online-dot"></div>',
      '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">',
        '<path d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26A7.002 7.002 0 0 0 19 9c0-3.87-3.13-7-7-7zm1 14h-2v-1.08C8.48 14.41 7 11.86 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 2.86-1.48 5.41-4 5.92V16zm-1 4c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z"/>',
      '</svg>',
    '</button>',
    '<div id="vm-chat-window" role="dialog" aria-label="Valiquette Mechanical chat">',
      '<div id="vm-chat-header">',
        '<div class="vm-logo">',
          '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">',
            '<path d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26A7.002 7.002 0 0 0 19 9c0-3.87-3.13-7-7-7zm1 14h-2v-1.08C8.48 14.41 7 11.86 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 2.86-1.48 5.41-4 5.92V16zm-1 4c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z"/>',
          '</svg>',
        '</div>',
        '<div class="vm-header-text">',
          '<h3>Valiquette Mechanical</h3>',
          '<p>Answers in seconds, 24/7</p>',
        '</div>',
        '<button id="vm-close-btn" aria-label="Close chat">',
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
        '</button>',
      '</div>',
      '<div id="vm-messages"></div>',
      '<div id="vm-suggestions"></div>',
      '<div id="vm-input-area">',
        '<textarea id="vm-input" rows="1" placeholder="Ask about heating, cooling, or gas..."></textarea>',
        '<button id="vm-mic-btn" aria-label="Voice input" style="display:none">',
          '<svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1 1.93c-3.94-.49-7-3.86-7-7.93H2c0 4.97 3.58 9.08 8 9.8V21h4v-3.27c4.42-.73 8-4.84 8-9.73h-2c0 4.07-3.06 7.44-7 7.93V15.93z"/></svg>',
        '</button>',
        '<button id="vm-send-btn" aria-label="Send message">',
          '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
        '</button>',
      '</div>',
    '</div>',
  ].join('');

  document.body.appendChild(wrapper);

  var bubble = document.getElementById('vm-chat-bubble');
  var chatWindow = document.getElementById('vm-chat-window');
  var closeBtn = document.getElementById('vm-close-btn');
  var messages = document.getElementById('vm-messages');
  var suggestions = document.getElementById('vm-suggestions');
  var input = document.getElementById('vm-input');
  var sendBtn = document.getElementById('vm-send-btn');

  var micBtn = document.getElementById('vm-mic-btn');
  var isOpen = false;
  var isTyping = false;

  // Speech recognition setup
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognition = null;
  var isRecording = false;

  if (SpeechRecognition) {
    micBtn.style.display = 'flex';
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-CA';

    recognition.onstart = function() {
      isRecording = true;
      micBtn.classList.add('vm-recording');
      input.placeholder = 'Listening...';
    };

    recognition.onresult = function(e) {
      var transcript = Array.from(e.results)
        .map(function(r) { return r[0].transcript; })
        .join('');
      input.value = transcript;
    };

    recognition.onend = function() {
      isRecording = false;
      micBtn.classList.remove('vm-recording');
      input.placeholder = 'Ask about heating, cooling, or gas...';
      if (input.value.trim()) sendMessage();
    };

    recognition.onerror = function() {
      isRecording = false;
      micBtn.classList.remove('vm-recording');
      input.placeholder = 'Ask about heating, cooling, or gas...';
    };

    micBtn.addEventListener('click', function() {
      if (isRecording) {
        recognition.stop();
      } else {
        recognition.start();
      }
    });
  }

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
      chatWindow.classList.add('vm-open');
      if (isMobile) bubble.classList.add('vm-hidden');
      input.focus();
      if (messages.children.length === 0) {
        loadConfig();
      }
    } else {
      chatWindow.classList.remove('vm-open');
      bubble.classList.remove('vm-hidden');
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
        appendBotMessage("Hi! I'm the Valiquette Mechanical assistant. How can I help you today?", false);
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
      btn.className = 'vm-suggestion-btn';
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
    btn.className = 'vm-suggestion-btn';
    btn.style.cssText = 'background:#1557A0;color:white;border-color:#1557A0;width:100%';
    btn.textContent = '📅 Fill Out Booking Form';
    btn.addEventListener('click', function () {
      hideSuggestions();
      showBookingFormMessage();
    });
    suggestions.appendChild(btn);
  }

  function showBookingFormMessage() {
    var div = document.createElement('div');
    div.className = 'vm-msg vm-bot vm-form-msg';
    div.innerHTML = [
      '<div class="vm-form-title">📅 Book a Free Estimate</div>',
      '<div class="vm-form-row"><input type="text" class="gf-name" placeholder="Your name *"></div>',
      '<div class="vm-form-row"><input type="tel" class="gf-phone" placeholder="Phone number *"></div>',
      '<div class="vm-form-row"><input type="email" class="gf-email" placeholder="Email address"></div>',
      '<div class="vm-form-row"><input type="text" class="gf-service" placeholder="Service needed (e.g. New furnace)"></div>',
      '<div class="vm-form-row"><input type="text" class="gf-time" placeholder="Best time to reach you"></div>',
      '<div class="vm-form-row"><input type="text" class="gf-notes" placeholder="Any notes?"></div>',
      '<button class="vm-form-submit" onclick="window._vmSubmitBooking(this)">Send Request \u2192</button>',
    ].join('');
    messages.appendChild(div);
    scrollToBottom();
  }

  window._vmSubmitBooking = function (btn) {
    var form = btn.closest('.vm-form-msg');
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
        form.innerHTML = '<div style="text-align:center;padding:8px 0"><div style="font-size:24px;margin-bottom:8px">\u2705</div><strong>Request sent!</strong><p style="font-size:13px;color:#6b7280;margin-top:4px">We\'ll call you at ' + name.split(' ')[0] + '\'s number shortly — usually within the hour!</p></div>';
        scrollToBottom();
        sendMessage('I just submitted my booking request. My name is ' + name + ' and my phone is ' + phone + '.');
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Try Again';
        appendBotMessage('Sorry, something went wrong. Please call us directly at 613-620-1000.', false);
      });
  };

  function appendUserMessage(text) {
    var div = document.createElement('div');
    div.className = 'vm-msg vm-user';
    div.textContent = text;
    messages.appendChild(div);
    scrollToBottom();
  }

  function appendBotMessage(text, emergency) {
    var div = document.createElement('div');
    div.className = 'vm-msg vm-bot' + (emergency ? ' vm-emergency' : '');
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
    div.className = 'vm-typing';
    div.id = 'vm-typing-indicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    messages.appendChild(div);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var el = document.getElementById('vm-typing-indicator');
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
          'Sorry, I\'m having trouble connecting right now. Please call us at 613-620-1000 for immediate help.',
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
