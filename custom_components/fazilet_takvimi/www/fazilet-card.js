/* Fazilet Takvimi card. Usage:
 *   type: custom:fazilet-card
 *   entity: sensor.<city>_next_prayer
 *   show_sabah: false   # optional
 */
const FZ_NAMES = {imsak: "İmsak", sabah: "Sabah", gunes: "Güneş", ogle: "Öğle", ikindi: "İkindi", aksam: "Akşam", yatsi: "Yatsı"};

class FaziletCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Set `entity` to the 'Next prayer' sensor of your city");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._render(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {entity: ""};
  }

  _esc(value) {
    const el = document.createElement("span");
    el.textContent = value == null ? "" : String(value);
    return el.innerHTML;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._root) {
      this._root = this.attachShadow({mode: "open"});
      this._root.innerHTML = `
        <style>
          .head {display:flex; justify-content:space-between; align-items:baseline; padding:16px 16px 4px;}
          .city {font-size:1.1em; font-weight:500;}
          .count {color: var(--secondary-text-color); font-size:0.9em;}
          .row {display:flex; gap:6px; padding:8px 12px 16px; flex-wrap:wrap;}
          .cell {flex:1 1 0; min-width:48px; text-align:center; padding:8px 2px; border-radius:10px;
                 background: var(--secondary-background-color);}
          .cell.next {background: var(--primary-color); color: var(--text-primary-color, #fff);}
          .name {font-size:0.75em; opacity:0.85;}
          .time {font-size:1.05em; font-weight:500; font-variant-numeric: tabular-nums;}
          .msg {padding:16px;}
        </style>
        <ha-card><div id="c"></div></ha-card>`;
    }
    const box = this._root.getElementById("c");
    const st = this._hass.states[this._config.entity];
    if (!st) {
      box.innerHTML = `<div class="msg">Entity not found: ${this._esc(this._config.entity)}</div>`;
      return;
    }
    const a = st.attributes || {};
    const today = a.today || {};
    const keys = ["imsak", "sabah", "gunes", "ogle", "ikindi", "aksam", "yatsi"]
      .filter((k) => today[k] && (k !== "sabah" || this._config.show_sabah));
    if (!keys.length) {
      box.innerHTML = `<div class="msg">No prayer times available</div>`;
      return;
    }
    let count = "";
    if (a.next_time) {
      const mins = Math.max(0, Math.ceil((new Date(a.next_time) - new Date()) / 60000));
      const h = Math.floor(mins / 60), m = mins % 60;
      count = `${this._esc(st.state)} · ${h ? h + " h " : ""}${m} min`;
    }
    const cells = keys.map((k) => `
      <div class="cell ${k === a.next_key ? "next" : ""}">
        <div class="name">${this._esc(FZ_NAMES[k])}</div>
        <div class="time">${this._esc(today[k])}</div>
      </div>`).join("");
    box.innerHTML = `
      <div class="head"><span class="city">${this._esc(this._config.title || a.city || "")}</span>
      <span class="count">${count}</span></div>
      <div class="row">${cells}</div>`;
  }
}

if (!customElements.get("fazilet-card")) {
  customElements.define("fazilet-card", FaziletCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "fazilet-card",
    name: "Fazilet Takvimi",
    description: "Today's prayer times with the next one highlighted",
  });
}
