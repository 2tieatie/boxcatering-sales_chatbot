
const chatHistory = []
const isTyping = false
let ws = null
let reconnectTimer = null
const RECONNECT_DELAY_MS = 1500

const scriptTag = Array.from(document.getElementsByTagName("script")).find((s) => s.src.includes("widget.js"))
const srcLink = scriptTag.getAttribute("src")
const homeLink = srcLink.includes("http") ? srcLink.split("//")[0] + "//" + srcLink.split("//")[1].split("/")[0] : ""

function isMobileDevice() {
  return (
    window.innerWidth <= 768 ||
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
  )
}

function getContainerMinHeight() {
  return isMobileDevice() ? "505px" : "600px"
}


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


        const scripts = [`https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js`]

        scripts.forEach((scriptHref) => {
          const link = document.createElement("script")
          link.src = scriptHref
          document.head.appendChild(link)
        })


        const widget = document.createElement("div")
        widget.id = "callback-widget"


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

                        <div class="chat-input-container">
                            <form class="chat-input-form" id="chat-form">
                                <div class="input-group">
                                    <input id="chat-input" class="chat-input" data-i18n="chatTest.input.label" placeholder="Enter a message:"/>
                                </div>
                                <button type="submit" class="send-btn" id="send-btn" data-i18n="chatTest.send">Send</button>
                            </form>

                            <div class="status-indicator" style="display: none; margin-top: 15px; justify-content: center;">
                                <div class="status-dot" id="status-dot"></div>
                                <span id="status-text" data-i18n="chatTest.status.connectedToAI">Connected to AI service</span>
                            </div>
                        </div>
                        
                        <div id="order-form-container" style="display: none; position: absolute; bottom: 16px; left: 16px; right: 16px; background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); z-index: 1000;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <h3 style="margin: 0; font-size: 16px; color: #333;">Place an Order</h3>
                                <button onclick="closeOrderForm()" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #999;">&times;</button>
                            </div>
                            
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                <div>
                                    <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Name</label>
                                    <input id="order-name" type="text" placeholder="Enter your name" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;" />
                                </div>
                                
                                <div>
                                    <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Phone</label>
                                    <input id="order-phone" type="tel" placeholder="+38 (09X) XXX-XXXX" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;" />
                                </div>
                                
                                <div>
                                    <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Date</label>
                                    <input id="order-date" type="date" onchange="updateTimeOptions()" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;" />
                                </div>
                                
                                <div style="display: flex; gap: 6px;">
                                    <div style="flex: 1;">
                                        <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Hour</label>
                                        <select id="order-hour" onchange="handleHourChange()" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;">
                                            <option value="">Select</option>
                                        </select>
                                    </div>
                                    <div style="flex: 1;">
                                        <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Minute</label>
                                        <select id="order-minute" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;">
                                            <option value="0">00</option>
                                            <option value="15">15</option>
                                            <option value="30">30</option>
                                            <option value="45">45</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <div>
                                    <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">City</label>
                                    <select id="order-city" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;">
                                        <option value="">Select city</option>
                                        <option value="Odesa">Odesa</option>
                                        <option value="Kyiv">Kyiv</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label style="display: block; font-size: 12px; margin-bottom: 3px; color: #333; font-weight: 500;">Delivery Address</label>
                                    <input id="order-address" type="text" placeholder="Street, building, apartment" style="width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; box-sizing: border-box;" />
                                </div>
                                
                                <div style="display: flex; gap: 8px; margin-top: 10px;">
                                    <button onclick="submitOrderForm()" style="flex: 1; padding: 8px; background: #ff5b55; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">Submit</button>
                                    <button onclick="closeOrderForm()" style="flex: 1; padding: 8px; background: #f0f0f0; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">Cancel</button>
                                </div>
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
                                                    fillRule="evenodd"
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
                                                    fillRule="evenodd"
                                                    d="M940.872414,978.904882 C939.924716,977.937215 938.741602,977.937215 937.79994,978.904882 C937.08162,979.641558 936.54439,979.878792 935.838143,980.627954 C935.644982,980.833973 935.482002,980.877674 935.246586,980.740328 C934.781791,980.478121 934.286815,980.265859 933.840129,979.97868 C931.757607,978.623946 930.013117,976.882145 928.467826,974.921839 C927.701216,973.947929 927.019115,972.905345 926.542247,971.731659 C926.445666,971.494424 926.463775,971.338349 926.6509,971.144815 C927.36922,970.426869 927.610672,970.164662 928.316918,969.427987 C929.300835,968.404132 929.300835,967.205474 928.310882,966.175376 C927.749506,965.588533 927.206723,964.77769 926.749111,964.14109 C926.29156,963.50449 925.932581,962.747962 925.347061,962.154875 C924.399362,961.199694 923.216248,961.199694 922.274586,962.161118 C921.55023,962.897794 920.856056,963.653199 920.119628,964.377388 C919.437527,965.045391 919.093458,965.863226 919.021022,966.818407 C918.906333,968.372917 919.274547,969.840026 919.793668,971.269676 C920.856056,974.228864 922.473784,976.857173 924.43558,979.266977 C927.085514,982.52583 930.248533,985.104195 933.948783,986.964613 C935.6148,987.801177 937.341181,988.444207 939.218469,988.550339 C940.510236,988.625255 941.632988,988.288132 942.532396,987.245549 C943.148098,986.533845 943.842272,985.884572 944.494192,985.204083 C945.459999,984.192715 945.466036,982.969084 944.506265,981.970202 C943.359368,980.777786 942.025347,980.091055 940.872414,978.904882 Z M940.382358,973.54478 L940.649524,973.497583 C941.23257,973.394635 941.603198,972.790811 941.439977,972.202844 C940.97488,970.527406 940.107887,969.010104 938.90256,967.758442 C937.61538,966.427182 936.045641,965.504215 934.314009,965.050223 C933.739293,964.899516 933.16512,965.298008 933.082785,965.905204 L933.044877,966.18514 C932.974072,966.707431 933.297859,967.194823 933.791507,967.32705 C935.117621,967.682278 936.321439,968.391422 937.308977,969.412841 C938.437799,970.575457 939.217896,971.984721 939.574162,973.520437 C939.65786,973.87819 939.939308,974.141003 940.382358,973.54478 Z"
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
                                                    fillRule="evenodd"
                                                ></path>
                                            </svg>
                                        </div>
                                    </div>
                                    <div class="callback-widget-button-inner-item callback-widget-button-close" onclick="displayWidget()">
                                        <svg class="callback-widget-button-icon callback-widget-button-close-item" xmlns="http://www.w3.org/2000/svg" width="29" height="29" viewBox="0 0 29 29">
                                            <path
                                                fill="#FFF"
                                                fillRule="evenodd"
                                                d="M18.866 14.45l9.58-9.582L24.03.448l-9.587 9.58L4.873.447.455 4.866l9.575 9.587-9.583 9.57 4.418 4.42 9.58-9.577 9.58 9.58 4.42-4.42"
                                            ></path>
                                        </svg>
                                    </div>
                                    <div class="callback-widget-button-inner-item callback-widget-button-close-chat" onclick="closeChat()">
                                        <svg class="callback-widget-button-icon callback-widget-button-close-item" xmlns="http://www.w3.org/2000/svg" width="29" height="29" viewBox="0 0 29 29">
                                            <path
                                                fill="#FFF"
                                                fillRule="evenodd"
                                                d="M18.866 14.45l9.58-9.582L24.03.448l-9.587 9.58L4.873.447.455 4.866l9.575 9.587-9.583 9.57 4.418 4.42 9.58-9.577 9.58 9.58 4.42-4.42"
                                            ></path>
                                        </svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="order-form-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; justify-content: center; align-items: center;">
                    <div style="background: white; border-radius: 8px; padding: 24px; max-width: 400px; width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2 style="margin: 0; font-size: 20px; color: #333;">Place an Order</h2>
                            <button onclick="closeOrderForm()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999;">&times;</button>
                        </div>
                        
                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            <div>
                                <label style="display: block; font-size: 14px; margin-bottom: 4px; color: #333; font-weight: 500;">Name</label>
                                <input id="order-name" type="text" placeholder="Enter your name" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;" />
                            </div>
                            
                            <div>
                                <label style="display: block; font-size: 14px; margin-bottom: 4px; color: #333; font-weight: 500;">Phone</label>
                                <input id="order-phone" type="tel" placeholder="+1 (555) 000-0000" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;" />
                            </div>
                            
                            <div>
                                <label style="display: block; font-size: 14px; margin-bottom: 4px; color: #333; font-weight: 500;">Date</label>
                                <input id="order-date" type="date" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;" />
                            </div>
                            
                            <div>
                                <label style="display: block; font-size: 14px; margin-bottom: 4px; color: #333; font-weight: 500;">City</label>
                                <select id="order-city" onchange="populateTimeSlots(document.getElementById('order-date').value)" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                                    <option value="">Select city</option>
                                    <option value="Odesa">Odesa</option>
                                    <option value="Kyiv">Kyiv</option>
                                </select>
                            </div>
                            
                            <div>
                                <label style="display: block; font-size: 14px; margin-bottom: 4px; color: #333; font-weight: 500;">Delivery Address</label>
                                <input id="order-address" type="text" placeholder="Street, building, apartment" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;" />
                            </div>
                            
                            <div style="display: flex; gap: 10px; margin-top: 16px;">
                                <button onclick="submitOrderForm()" style="flex: 1; padding: 10px; background: #ff5b55; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500;">Submit</button>
                                <button onclick="closeOrderForm()" style="flex: 1; padding: 10px; background: #f0f0f0; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">Cancel</button>
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
          })()
        }, 250)
      }
    } catch (error) {
      console.error("Error loading settings:", error)
    }
  })()
}


async function initI18N() {
  try {
    const token = localStorage.getItem("access_token")
    const storedLang = localStorage.getItem("ui_language")
    const lang = storedLang || "uk"

    if (window.I18N && window.I18N.setLanguage) {
      await window.I18N.setLanguage(lang)
    }
    console.log(window.I18N)

    try {
      const input = document.getElementById("chat-input")

      if (input && window.I18N && window.I18N.t) {
        input.placeholder = window.I18N.t("chatTest.input.label")
      }
    } catch {}
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n")
      if (window.I18N && window.I18N.t) {
        el.textContent = window.I18N.t(k)
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
    placeholder.placeholder = window.I18N && window.I18N.t ? window.I18N.t("chatTest.input.label") : "Enter a message:"
  }
  fetchActiveChatbotConfig()
})


function displayChat() {
  document.querySelector(".callback-widget-button-wrapper").classList.add("callback-widget-button-chat")
  const widget = document.querySelector(".callback-widget-button-wrapper")
  widget.classList.toggle("callback-widget-button-bottom")
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


  document.getElementById("bot-welcome-time").textContent = new Date().toLocaleTimeString()


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
      session_id: sessionId,
      sender: "user",
      message: message,
      timestamp: timestamp,
    }


    showTypingIndicator()
    sendToWebSocket(payload)
  })






}


function getOrCreateSessionId() {
  const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return id
}
const sessionId = getOrCreateSessionId()


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
  const messagesContainer = document.getElementById("chat-messages")
  const messageDiv = document.createElement("div")
  messageDiv.className = `message ${isUser ? "user" : "bot"}`

  const time = timestamp || new Date().toLocaleTimeString()

  messageDiv.innerHTML = `
                <div class="message-content">
                    <div>${window.marked.parse(content)}</div>
                    <div class="message-time">${time}</div>
                </div>
            `

  messagesContainer.appendChild(messageDiv)
  messagesContainer.scrollTop = messagesContainer.scrollTop + 300


  chatHistory.push({
    content,
    isUser,
    timestamp: time,
  })
}


function showTypingIndicator() {
  const indicator = document.getElementById("typing-indicator")
  indicator.style.display = "block"
  document.getElementById("chat-messages").scrollTop = document.getElementById("chat-messages").scrollHeight
}


function hideTypingIndicator() {
  document.getElementById("typing-indicator").style.display = "none"
}


function setStatus(status, cssClass) {
  const dot = document.getElementById("status-dot")
  const text = document.getElementById("status-text")
  dot.classList.remove("offline", "connecting")
  if (cssClass) dot.classList.add(cssClass)
  try {
    if (window.I18N && window.I18N.t) {
      text.textContent = window.I18N.t(status) || status
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
  const url = `${protocol}://${location.host}/chat/ws${location.search || ""}`
  setStatus("chatTest.status.connectingToAI", "connecting")

  ws = new WebSocket(url)

  ws.onopen = () => {
    setStatus("chatTest.status.connectedToAI", "")
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      hideTypingIndicator()

      if (data.show_form) {
        showOrderForm()
      }

      const text = data && typeof data.response === "string" ? data.response.trim() : ""
      if (text) {
        addMessage(text)
      } else if (!data.show_form) {
        addMessage(
          window.I18N && window.I18N.t
            ? window.I18N.t("chatTest.error.generic")
            : "Sorry, something went wrong. Please try again later.",
        )
      }

      if (data.handover_to_manager) {
        showHandoverNotice(data)
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
        addMessage(
          window.I18N && window.I18N.t
            ? window.I18N.t("chatTest.error.connectFail")
            : "Connection failed. Please try again later.",
        )
      }
    }, 500)
    return
  }
  ws.send(JSON.stringify(payload))
}

function showHandoverNotice(data) {
  const reason = data.handover_reason || "HANDOVER"
  const desc = data.handover_reason_description || ""
  try {
    const notice =
      window.I18N && window.I18N.t
        ? window.I18N.t("chatTest.handover.notice", { reason: reason, desc: desc }).trim()
        : `Handing over to manager (${reason}). ${desc}`.trim()
    addMessage(notice)
  } catch {
    addMessage(`Handing over to manager (${reason}). ${desc}`.trim())
  }
}



function validateUkrainianPhone(phone) {
  return /^\+380\d{9}$/.test(phone.replace(/\D/g, "").replace(/^38/, "+38"))
}

function getMinDateTime() {
  const now = new Date()
  const hour = now.getHours()
  const isLate = hour >= 17

  const minDate = new Date(now)
  if (isLate) {
    minDate.setDate(minDate.getDate() + 1)
    minDate.setHours(9, 0, 0, 0)
  } else {
    minDate.setHours(hour + 2, 0, 0, 0)
    if (minDate.getHours() < 9) {
      minDate.setDate(minDate.getDate() + 1)
      minDate.setHours(9, 0, 0, 0)
    }
  }
  return minDate
}

function handleHourChange() {
  document.getElementById("order-minute").value = "0"
  updateTimeOptions()
}

function getAvailableHours(selectedDate) {
  const now = new Date()
  const minDateTime = getMinDateTime()
  const selected = new Date(selectedDate + "T00:00:00")
  const hours = []

  for (let h = 9; h <= 19; h++) {
    const slotTime = new Date(selected)
    slotTime.setHours(h, 0, 0, 0)

    if (slotTime >= minDateTime) {
      hours.push(h)
    }
  }
  return hours
}

function updateTimeOptions() {
  const dateInput = document.getElementById("order-date")
  const hourSelect = document.getElementById("order-hour")
  const chatContainer = document.querySelector(".chat-container")

  if (!dateInput.value) {
    hourSelect.innerHTML = '<option value="">Select</option>'
    return
  }

  const hours = getAvailableHours(dateInput.value)
  hourSelect.innerHTML = '<option value="">Select</option>'

  hours.forEach((hour) => {
    const option = document.createElement("option")
    option.value = String(hour)
    option.textContent = String(hour).padStart(2, "0") + ":00"
    hourSelect.appendChild(option)
  })

  if (chatContainer && dateInput.value) {
    chatContainer.style.minHeight = getContainerMinHeight()
  }
}

function showOrderForm() {
  const container = document.getElementById("order-form-container")
  const chatContainer = document.querySelector(".chat-container")
  const chatInput = document.querySelector(".chat-input-container")

  if (!container) return

  container.style.display = "block"

  if (chatContainer) {
    chatContainer.style.minHeight = getContainerMinHeight()
    chatContainer.style.backdropFilter = "blur(4px)"
    chatContainer.style.background = "rgba(255, 255, 255, 0.9)"
  }

  const dateInput = document.getElementById("order-date")
  const minDate = getMinDateTime()

  dateInput.min = minDate.toISOString().split("T")[0]
  dateInput.value = minDate.toISOString().split("T")[0]

  updateTimeOptions()
}

function closeOrderForm() {
  const container = document.getElementById("order-form-container")
  const chatContainer = document.querySelector(".chat-container")

  if (container) container.style.display = "none"

  if (chatContainer) {
    chatContainer.style.minHeight = "auto"
    chatContainer.style.backdropFilter = "none"
    chatContainer.style.background = "white"
  }
}

function submitOrderForm() {
  const name = document.getElementById("order-name").value.trim()
  const phone = document.getElementById("order-phone").value.trim()
  const date = document.getElementById("order-date").value
  const hour = document.getElementById("order-hour").value
  const minute = document.getElementById("order-minute").value
  const city = document.getElementById("order-city").value
  const address = document.getElementById("order-address").value.trim()

  const time = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`
  const formData = { name, phone, date, time, city, address }
  const payload = {
    session_id: sessionId,
    sender: "user",
    message: `Form submission: ${JSON.stringify(formData)}`,
    timestamp: new Date().toISOString().replace("Z", "+00:00"),
    form_data: formData,
  }

  sendToWebSocket(payload)
  closeOrderForm()
  addMessage(`Order accepted: ${name}, ${phone}`)
}


window.I18N = window.I18N || {}
window.marked = window.marked || { parse: (text) => text }
