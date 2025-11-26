// Initialize chat
const chatHistory = []
let ws = null
let reconnectTimer = null
const RECONNECT_DELAY_MS = 1500

const scriptTag = Array.from(document.getElementsByTagName("script")).find((s) => s.src.includes("widget.js"))
const srcLink = scriptTag.getAttribute("src")
const homeLink = srcLink.includes("http") ? srcLink.split("//")[0] + "//" + srcLink.split("//")[1].split("/")[0] : ""

// Declare I18N and marked variables
let I18N = null
let marked = null

function loadWidget() {
  ;(async () => {
    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch(homeLink + "/system-config/settings/widget", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })

      if (response.ok) {
        const settings = await response.json()

        const styles = [`./call_style.min.css`, `./live_chat.css`]
        styles.forEach((styleHref) => {
          const link = document.createElement("link")
          link.rel = "stylesheet"
          link.href = homeLink ? homeLink + "/static/" + styleHref : "static/" + styleHref
          document.head.appendChild(link)
        })

        const scripts = [
          `https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js`,
          `https://example.com/path/to/i18n.js`,
        ]

        scripts.forEach((scriptHref) => {
          const link = document.createElement("script")
          link.src = scriptHref
          link.onload = () => {
            if (scriptHref.includes("i18n.js")) {
              I18N = window.I18N
            } else if (scriptHref.includes("marked.umd.js")) {
              marked = window.marked?.marked || window.marked
              if (marked?.use) {
                marked.use({ breaks: true, gfm: true })
              }
            }
          }
          document.head.appendChild(link)
        })

        const widget = document.createElement("div")
        widget.id = "callback-widget"
        await initI18N()
        widget.innerHTML = `
                
                <div class="callback-widget-block">
                    <div style="display: none">
                        <a class="callback-widget-button-social-item" title="">
                            <i></i>
                            <span class="callback-widget-button-social-tooltip"></span>
                        </a>
                    </div>

                    <div class="chat-container callback-widget-button-hide hide-container">
                        <div class="chat-header">
                            <div class="avatar">👩</div>
                            <h2 data-i18n="chatTest.headerTitleName">Marichka</h2>
                            <button class="close-btn" onclick="closeChat()">&times;</svg>
                            </button>
                        </div>

                        <div class="chat-messages" id="chat-messages">
                          <div id="messages-container">
                              <div class="message bot">
                                <div class="message-content">
                                    <div id="bot-welcome-content" data-i18n="chatTest.welcome.loading">Loading welcome message…</div>
                                    <div class="message-time" id="bot-welcome-time"></div>
                                </div>
                            </div>
                          </div>
                            
                          <div class="typing-indicator" id="typing-indicator">
                            <div class="typing-dots">
                              <div class="typing-dot"></div>
                              <div class="typing-dot"></div>
                              <div class="typing-dot"></div>
                            </div>
                          </div>
                        </div>

                        <div class="chat-input-container">
                            <form class="chat-input-form" id="chat-form">
                                <div class="input-group">
                                    <input 
                                        id="chat-input"
                                        autocomplete="off"
                                        autocorrect="off"
                                        autocapitalize="off"
                                        spellcheck="false" 
                                        class="chat-input" data-i18n="chatTest.input.label" placeholder="Введіть повідомлення..."/>
                                </div>
                                <button type="submit" class="send-btn clear-btn" id="send-btn">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-send-horizontal-icon lucide-send-horizontal"><path d="M3.714 3.048a.498.498 0 0 0-.683.627l2.843 7.627a2 2 0 0 1 0 1.396l-2.842 7.627a.498.498 0 0 0 .682.627l18-8.5a.5.5 0 0 0 0-.904z"/><path d="M6 12h16"/></svg>  
                                </button>
                                <button class="send-btn clear-btn" id="clear-btn">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-brush-cleaning-icon lucide-brush-cleaning"><path d="m16 22-1-4"/><path d="M19 13.99a1 1 0 0 0 1-1V12a2 2 0 0 0-2-2h-3a1 1 0 0 1-1-1V4a2 2 0 0 0-4 0v.99a1 1 0 0 0 1 1"/><path d="M5 14h14l1.973 6.767A1 1 0 0 1 20 22H4a1 1 0 0 1-.973-1.233z"/><path d="m8 22 1-4"/></svg>
                            </button>
                            </form>

                            <div class="status-indicator" style="display: none; margin-top: 15px; justify-content: center;">
                                <div class="status-dot" id="status-dot"></div>
                                <span id="status-text" data-i18n="chatTest.status.connectedToAI">Connected to AI service</span>
                            </div>
                        </div>
                    </div>


                    <div dir="ltr" class="callback-widget-button-wrapper callback-widget-button-position-bottom-right callback-widget-button-visible display-chat">
                        <div class="callback-widget-button-social callback-widget-button-hide">
                            <a
                                class="callback-widget-button-social-item callback-widget-button-openline_livechat"
                                title=""
                                style="
                                    background-color: rgb(255, 91, 85);
                                    background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2231%22%20height%3D%2228%22%20viewBox%3D%220%200%2031%2028%22%3E%3Cpath%20fill%3D%22%23ffffff%22%20fill-rule%3D%22evenodd%22%20d%3D%22M23.29%2013.25V2.84c0-1.378-1.386-2.84-2.795-2.84h-17.7C1.385%200%200%201.462%200%202.84v10.41c0%201.674%201.385%203.136%202.795%202.84H5.59v5.68h.93c.04%200%20.29-1.05.933-.947l3.726-4.732h9.315c1.41.296%202.795-1.166%202.795-2.84zm2.795-3.785v4.733c.348%202.407-1.756%204.558-4.658%204.732h-8.385l-1.863%201.893c.22%201.123%201.342%202.127%202.794%201.893h7.453l2.795%203.786c.623-.102.93.947.93.947h.933v-4.734h1.863c1.57.234%202.795-1.02%202.795-2.84v-7.57c0-1.588-1.225-2.84-2.795-2.84h-1.863z%22/%3E%3C/svg%3E');
                                "
                                onclick="displayChat()"
                            >
                                <i></i>
                                <span class="callback-widget-button-social-tooltip">Live Chat</span> </a
                            >
                            ${
                              settings.widget?.facebook
                                ? `
                            <a
                                class="callback-widget-button-social-item ui-icon ui-icon-service-fb connector-icon-45"
                                title=""
                                href="https://m.me/${settings.widget?.facebook}"
                                target="_blank"
                                rel="nofollow"
                                id="messenger-btn"
                            >
                                <i></i>
                                <span class="callback-widget-button-social-tooltip">Facebook</span> </a
                            >
                            `
                                : ""
                            }
                            ${
                              settings.widget?.viber
                                ? `
                            <a class="callback-widget-button-social-item ui-icon ui-icon-service-viber connector-icon-45" title="" href="viber://pa?chatURI=${settings.widget?.viber}" target="_blank" id="viber-btn">
                                <i></i>
                                <span class="callback-widget-button-social-tooltip">Viber</span> </a
                            >
                            `
                                : ""
                            }
                            ${
                              settings.widget?.telegram
                                ? `
                            <a
                                class="callback-widget-button-social-item ui-icon ui-icon-service-telegram connector-icon-45"
                                title=""
                                href="https://t.me/${settings.widget?.telegram}"
                                target="_blank"
                                rel="nofollow"
                                id="telegram-btn"
                            >
                                <i></i>
                                <span class="callback-widget-button-social-tooltip">Telegram</span>
                            </a>
                            `
                                : ""
                            }
                        </div>
                        <div class="callback-widget-button-inner-container">
                            <div class="callback-widget-button-inner-mask" style="background: #ff5b55"></div>
                            <div class="callback-widget-button-block">
                                <div class="callback-widget-button-pulse callback-widget-button-pulse-animate" style="border-color: #ff5b55"></div>
                                <div class="callback-widget-button-inner-block" style="background: #ff5b55">
                                    <div class="callback-widget-button-icon-container" onclick="displayWidget()">
                                        <div class="callback-widget-button-inner-item" style="display: none">
                                            <svg class="callback-crm-button-icon" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 28">
                                                <path
                                                    class="callback-crm-button-webform-icon"
                                                    fill=" #ffffff"
                                                    fill-rule="evenodd"
                                                    d="M815.406703,961 L794.305503,961 C793.586144,961 793,961.586144 793,962.305503 L793,983.406703 C793,984.126062 793.586144,984.712206 794.305503,984.712206 L815.406703,984.712206 C816.126062,984.712206 816.712206,984.126062 816.712206,983.406703 L816.712206,962.296623 C816.703325,961.586144 816.117181,961 815.406703,961 L815.406703,961 Z M806.312583,979.046143 C806.312583,979.454668 805.975106,979.783264 805.575462,979.783264 L796.898748,979.783264 C796.490224,979.783264 796.161627,979.445787 796.161627,979.046143 L796.161627,977.412044 C796.161627,977.003519 796.499105,976.674923 796.898748,976.674923 L805.575462,976.674923 C805.983987,976.674923 806.312583,977.0124 806.312583,977.412044 L806.312583,979.046143 L806.312583,979.046143 Z M813.55946,973.255747 C813.55946,973.664272 813.221982,973.992868 812.822339,973.992868 L796.889868,973.992868 C796.481343,973.992868 796.152746,973.655391 796.152746,973.255747 L796.152746,971.621647 C796.152746,971.213122 796.490224,970.884526 796.889868,970.884526 L812.813458,970.884526 C813.221982,970.884526 813.550579,971.222003 813.550579,971.621647 L813.550579,973.255747 L813.55946,973.255747 Z M813.55946,967.45647 C813.55946,967.864994 813.221982,968.193591 812.822339,968.193591 L796.889868,968.193591 C796.481343,968.193591 796.152746,967.856114 796.152746,967.45647 L796.152746,965.82237 C796.152746,965.413845 796.490224,965.085249 796.889868,965.085249 L812.813458,965.085249 C813.221982,965.085249 813.550579,965.422726 813.550579,965.82237 L813.550579,967.45647 L813.55946,967.45647 Z"
                                                    transform="translate(-793 -961)"
                                                ></path>
                                            </svg>
                                        </div>

                                        <div class="callback-widget-button-inner-item" style="display: none">
                                            <svg class="callback-crm-button-icon" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 30">
                                                <path
                                                    class="callback-crm-button-call-icon"
                                                    fill="#ffffff"
                                                    fill-rule="evenodd"
                                                    d="M940.872414,978.904882 C939.924716,977.937215 938.741602,977.937215 937.79994,978.904882 C937.08162,979.641558 936.54439,979.878792 935.838143,980.627954 C935.644982,980.833973 935.482002,980.877674 935.246586,980.740328 C934.781791,980.478121 934.286815,980.265859 933.840129,979.97868 C931.757607,978.623946 930.013117,976.882145 928.467826,974.921839 C927.701216,973.947929 927.019115,972.905345 926.542247,971.731659 C926.445666,971.494424 926.463775,971.338349 926.6509,971.144815 C927.36922,970.426869 927.610672,970.164662 928.316918,969.427987 C929.300835,968.404132 929.300835,967.205474 928.310882,966.175376 C927.749506,965.588533 927.206723,964.77769 926.749111,964.14109 C926.29156,963.50449 925.932581,962.747962 925.347061,962.154875 C924.399362,961.199694 923.216248,961.199694 922.274586,962.161118 C921.55023,962.897794 920.856056,963.653199 920.119628,964.377388 C919.437527,965.045391 919.093458,965.863226 919.021022,966.818407 C918.906333,968.372917 919.274547,969.840026 919.793668,971.269676 C920.856056,974.228864 922.473784,976.857173 924.43558,979.266977 C927.085514,982.52583 930.248533,985.104195 933.948783,986.964613 C935.6148,987.801177 937.341181,988.444207 939.218469,988.550339 C940.510236,988.625255 941.632988,988.288132 942.532396,987.245549 C943.148098,986.533845 943.842272,985.884572 944.494192,985.204083 C945.459999,984.192715 945.466036,982.969084 944.506265,981.970202 C943.359368,980.777786 942.025347,980.091055 940.872414,978.904882 Z M940.382358,973.54478 L940.649524,973.497583 C941.23257,973.394635 941.603198,972.790811 941.439977,972.202844 C940.97488,970.527406 940.107887,969.010104 938.90256,967.758442 C937.61538,966.427182 936.045641,965.504215 934.314009,965.050223 C933.739293,964.899516 933.16512,965.298008 933.082785,965.905204 L933.044877,966.18514 C932.974072,966.707431 933.297859,967.194823 933.791507,967.32705 C935.117621,967.682278 936.321439,968.391422 937.308977,969.412841... <truncated>
                                                    transform="translate(-919 -959)"
                                                ></path>
                                            </svg>
                                        </div>

                                        <div class="callback-widget-button-inner-item callback-widget-button-icon-animation">
                                            <svg class="callback-crm-button-icon callback-crm-button-icon-active" width="28" height="29" xmlns="http://www.w3.org/2000/svg">
                                                <path
                                                    class="callback-crm-button-chat-icon"
                                                    d="M25.99 7.744a2 2 0 012 2v11.49a2 2 0 01-2 2h-1.044v5.162l-4.752-5.163h-7.503a2 2 0 01-2-2v-1.872h10.073a3 3 0 003-3V7.744zM19.381 0a2 2 0 012 2v12.78a2 2 0 01-2 2h-8.69l-5.94 6.453V16.78H2a2 2 0 01-2-2V2a2 2 0 012-2h17.382z"
                                                    fill=" #ffffff"
                                                    fill-rule="evenodd"
                                                ></path>
                                            </svg>
                                        </div>
                                    </div>
                                    <div class="callback-widget-button-inner-item callback-widget-button-close" onclick="displayWidget()">
                                        <svg class="callback-widget-button-icon callback-widget-button-close-item" xmlns="http://www.w3.org/2000/svg" width="29" height="29" viewBox="0 0 29 29">
                                            <path
                                                fill="#FFF"
                                                fill-rule="evenodd"
                                                d="M18.866 14.45l9.58-9.582L24.03.448l-9.587 9.58L4.873.447.455 4.866l9.575 9.587-9.583 9.57 4.418 4.42 9.58-9.577 9.58 9.58 4.42-4.42"
                                            ></path>
                                        </svg>
                                    </div>
                                    <div class="callback-widget-button-inner-item callback-widget-button-close-chat" onclick="closeChat()">
                                        <svg class="callback-widget-button-icon callback-widget-button-close-item" xmlns="http://www.w3.org/2000/svg" width="29" height="29" viewBox="0 0 29 29">
                                            <path
                                                fill="#FFF"
                                                fill-rule="evenodd"
                                                d="M18.866 14.45l9.58-9.582L24.03.448l-9.587 9.58L4.873.447.455 4.866l9.575 9.587-9.583 9.57 4.418 4.42 9.58-9.577 9.58 9.58 4.42-4.42"
                                            ></path>
                                        </svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                `
        setTimeout(() => {
          ;(async () => {
            document.body.appendChild(widget)
            await fetchActiveChatbotConfig()
            setTimeout(() => {
              document.querySelector(".chat-container").classList.remove("hide-container")
            }, 500)
            initChat()
            initI18N()
            setTimeout(() => {
              fetchActiveChatbotConfig()
            }, 500)
            loadChatHistory()
            await initI18N()
          })()
        }, 250)
      }
    } catch (error) {
      console.error("Error loading settings:", error)
    }
  })()
}

function scrollChatToBottom() {
  const chat = document.getElementById("chat-messages")
  if (!chat) return
  chat.scrollTop = chat.scrollHeight
}

async function initI18N() {
  try {
    const lang = localStorage.getItem("ui_language") || "uk"

    if (I18N && I18N.setLanguage) {
      await I18N.setLanguage(lang)
    }
    console.log(I18N)

    try {
      const input = document.getElementById("chat-input")
      if (input && I18N && I18N.t) {
        input.placeholder = I18N.t("chatTest.input.label")
      }
    } catch {}

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n")
      if (I18N && I18N.t) {
        el.textContent = I18N.t(k)
      }
    })
  } catch (e) {
    console.log(e)
  }
}

loadWidget()

document.addEventListener("i18n:languageChanged", () => {
  const placeholder = document.getElementById("chat-input")
  if (placeholder) {
    placeholder.placeholder = I18N && I18N.t ? I18N.t("chatTest.input.label") : "Enter a message:"
  }
  fetchActiveChatbotConfig()
})

function displayChat() {
  const wrapper = document.querySelector(".callback-widget-button-wrapper")
  wrapper.classList.add("callback-widget-button-chat")
  wrapper.classList.toggle("callback-widget-button-bottom")
  document.querySelector(".chat-container").classList.remove("callback-widget-button-hide")
}

function closeChat() {
  document.querySelector(".chat-container").classList.add("callback-widget-button-hide")
  document.querySelector(".callback-widget-button-wrapper").classList.remove("callback-widget-button-chat")
}

function displayWidget() {
  const widget = document.querySelector(".callback-widget-button-wrapper")
  widget.classList.toggle("callback-widget-button-bottom")

  const social = document.querySelector(".callback-widget-button-social")
  social.classList.toggle("callback-widget-button-hide")
  social.classList.toggle("callback-widget-button-show")
}

function initChat() {
  connectWebSocket()

  document.getElementById("clear-btn").addEventListener("click", () => {
    if (!confirm("Очистити чат?")) return

    setTimeout(() => {
      clearChatMessages()
      chatHistory.length = 0
      getOrCreateSessionId(true)
      hideTypingIndicator()
      ws.close()
      connectWebSocket()
      enableSend()
    }, 0)

  })

  document.getElementById("chat-form").addEventListener("submit", (e) => {
    e.preventDefault()

    const input = document.getElementById("chat-input")
    const message = input.value.trim()
    if (!message) return

    addMessage(message, true)

    input.value = ""
    input.style.height = "auto"

    const timestamp = new Date().toISOString().replace("Z", "+00:00")
    const payload = {
      session_id: getOrCreateSessionId(),
      sender: "user",
      message,
      timestamp,
    }

    updateTypingIndicator()
    sendToWebSocket(payload)
  })
}

function clearChatMessages() {
  const container = document.getElementById("messages-container")
  if (!container) return

  Array.from(container.children)
    .filter((el, index) => index !== 0 ? el.classList.contains("message") : null)
    .forEach((el) => el.remove())
}


async function loadChatHistory() {
  const prevMessages = await fetchChatHistoryRaw()

  clearChatMessages()
  chatHistory.length = 0

  for (const message of prevMessages) {
    const tsLocal = new Date(message.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })

    addMessage(message.text, message.sender === "user", tsLocal)
  }

  updateTypingIndicator()
  return prevMessages
}

function getOrCreateSessionId(create = false) {
  const key = "chat_session_id"
  let id = localStorage.getItem(key)
  if (!id || create) {
    id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
    localStorage.setItem(key, id)
  }

  return id
}

async function fetchActiveChatbotConfig() {
  try {
    const token = localStorage.getItem("access_token")
    const resp = await fetch(homeLink + "/chatbot-config/active", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const cfg = await resp.json()
    const welcome = cfg.welcome_message || ""
    const node = document.getElementById("bot-welcome-content")
    if (node) node.textContent = welcome
  } catch (e) {
    console.warn("Failed to load active chatbot config:", e)
    const node = document.getElementById("bot-welcome-content")
    if (node) node.textContent = ""
  }
}

function addMessage(content, isUser = false, timestamp = null) {
  const messagesContainer = document.getElementById("messages-container")
  const messageDiv = document.createElement("div")
  messageDiv.className = `message ${isUser ? "user" : "bot"}`

  const time =
    timestamp ||
    new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })

  let html
  if (marked?.parse) {
    const mdWithBreaks = content.replace(/\n/g, "  \n")
    html = marked.parse(mdWithBreaks)
  } else {
    html = content.replace(/\n/g, "<br/>")
  }

  messageDiv.innerHTML = `
    <div class="message-content">
      <div>${html}</div>
      <div class="message-time">${time}</div>
    </div>
  `

  messagesContainer.appendChild(messageDiv)

  chatHistory.push({ content, isUser, timestamp: time })
  scrollChatToBottom()
}


function updateTypingIndicator() {
  const indicator = document.getElementById("typing-indicator")
  const lastMessage = chatHistory[chatHistory.length - 1]
  const isUserLast = !!lastMessage?.isUser

  indicator.style.display = isUserLast ? "block" : "none"
  if (isUserLast) {
    disableSend()
    scrollChatToBottom()
  } else {
    enableSend()
  }
}

function showTypingIndicator() {
  const indicator = document.getElementById("typing-indicator")
  indicator.style.display = "block"
  disableSend()
}

function hideTypingIndicator() {
  document.getElementById("typing-indicator").style.display = "none"
  enableSend()
}

function setStatus(status, cssClass) {
  const dot = document.getElementById("status-dot")
  const text = document.getElementById("status-text")
  dot.classList.remove("offline", "connecting")
  if (cssClass) dot.classList.add(cssClass)
  try {
    if (I18N && I18N.t) {
      text.textContent = I18N.t(status) || status
    } else {
      text.textContent = status
    }
  } catch {
    text.textContent = status
  }
}

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  const protocol = location.protocol === "https:" ? "wss" : "ws"
  let url = "https://boxcatering-chatbot.todo.ltd/chat/ws"

  if (["0.0.0.0:8000", "localhost:8000"].includes(location.host)) {
    url = `${protocol}://${location.host}/chat/ws${location.search || ""}`
  }
  setStatus("chatTest.status.connectingToAI", "connecting")

  ws = new WebSocket(url)

  ws.onopen = async () => {
    setStatus("chatTest.status.connectedToAI", "")
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    const msgs = await loadChatHistory()
    const last = msgs[msgs.length - 1]

    if (last && last.sender === "user") {
      updateTypingIndicator()
      waitForBotReply(last.timestamp)
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      const text = data && typeof data.response === "string" ? data.response.trim() : ""
      if (text) {
        addMessage(text)
        updateTypingIndicator()
      } else {
        addMessage(
          I18N && I18N.t ? I18N.t("chatTest.error.generic") : "Sorry, something went wrong. Please try again later.",
        )
        updateTypingIndicator()
      }

      if (data.handover_to_manager) {
        // showHandoverNotice(data)
      }

      if (data.debug) {
        console.log("AI Debug:", data.debug)
      }
    } catch (err) {
      console.error("Failed to parse message:", err)
    }
  }

  ws.onerror = () => {
    setStatus("chatTest.status.connectionError", "connecting")
  }

  ws.onclose = () => {
    setStatus("chatTest.status.disconnected", "offline")
    reconnectTimer = setTimeout(connectWebSocket, RECONNECT_DELAY_MS)
  }
}

function sendToWebSocket(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    connectWebSocket()
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload))
      } else {
        hideTypingIndicator()
        addMessage(I18N && I18N.t ? I18N.t("chatTest.error.connectFail") : "Connection failed. Please try again later.")
      }
    }, 500)
    return
  }
  ws.send(JSON.stringify(payload))
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function fetchChatHistoryRaw() {
  try {
    const resp = await fetch(homeLink + `/conversations/widget/${getOrCreateSessionId()}/messages`)
    return resp.ok ? await resp.json() : []
  } catch {
    return []
  }
}

async function waitForBotReply(lastUserTs) {
  const start = Date.now()
  const lastUserTime = new Date(lastUserTs).getTime()

  while (Date.now() - start < 60000) {
    const msgs = await fetchChatHistoryRaw()
    const hasReply = msgs.some(
      (m) => m.sender === "bot" && new Date(m.timestamp).getTime() > lastUserTime,
    )

    if (hasReply) {
      await loadChatHistory()
      return
    }

    await sleep(1000)
  }

  updateTypingIndicator()
}

function disableSend() {
  const btn = document.getElementById("send-btn")
  btn.disabled = true
  btn.classList.add("disabled")
}

function enableSend() {
  const btn = document.getElementById("send-btn")
  btn.disabled = false
  btn.classList.remove("disabled")
}

function showHandoverNotice(data) {
  const reason = data.handover_reason || "HANDOVER"
  const desc = data.handover_reason_description || ""
  try {
    const notice =
      I18N && I18N.t
        ? I18N.t("chatTest.handover.notice", {
            reason,
            desc,
          }).trim()
        : `Handing over to manager (${reason}). ${desc}`.trim()
    addMessage(notice)
  } catch {
    addMessage(`Handing over to manager (${reason}). ${desc}`.trim())
  }
}
