"""Sayfalar arası geçişte ekranın ortasında gösterilen "traktörlü yükleme barı".

Kullanım (app.py içinde):

    from page_transition import begin_transition, end_transition
    ...
    _tx = begin_transition(st.session_state["step"])   # sayfa çizilmeden ÖNCE
    ... (sayfalar çizilir) ...
    end_transition(_tx)                                 # dosyanın EN SONUNDA

Özellikler:
- Geçiş süresi 1.0 saniyenin altındaysa animasyon ekrana HİÇ girmez (CSS
  `animation-delay: 1s` ile yönetilir; hızlı geçişlerde kullanıcıyı bekletmez).
- 1 saniyeyi aşan yüklemelerde tam opak boş arka plan üzerinde sadece ortadaki
  traktörlü ilerleme kartı görünür, arkadaki sayfa içeriği tamamen gizlenir.
- Sayfa hazır olduğunda 1 saniyeden uzun sürdüyse bar %100'e tamamlanıp söner;
  1 saniyeden kısa sürdüyse katman hiç görünmeden doğrudan kaldırılır.
"""

import time

import streamlit as st

SHOW_DELAY_SECONDS = 1.0  # geçiş 1 saniyeyi aşarsa animasyon görünür

# Bar / traktör ilerleme çizelgesi: (saniye, yüzde).
_POINTS = [
    (0.0, 0), (1.0, 15), (1.3, 35), (1.8, 55), (2.5, 70),
    (4.0, 82), (8.0, 90), (20.0, 95), (40.0, 98),
]
_TOTAL = _POINTS[-1][0]
_FAILSAFE_DELAY = 45  # sn; sayfa hata verip script erken durursa katman kendiliğinden kapanır

DEFAULT_LABELS = {
    "step1_city": "Loading your farm…",
    "step2_map": "Loading your map…",
    "step3_results": "Analyzing your field…",
}
_FALLBACK_LABEL = "Loading…"


def _compact(css: str) -> str:
  return " ".join(css.split())


_TRACTOR_SVG = _compact(
    """
<svg class="tr-tx-svg" viewBox="0 0 72 48" width="72" height="48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle class="tr-tx-puff" cx="54" cy="6" r="2.6" fill="#A1A1AA"/>
  <circle class="tr-tx-puff p2" cx="54" cy="6" r="2.2" fill="#A1A1AA"/>
  <g class="tr-tx-body">
    <rect x="52" y="9" width="4" height="14" rx="1.5" fill="#3F3F46"/>
    <rect x="51" y="7.5" width="6" height="3" rx="1.2" fill="#27272A"/>
    <rect x="34" y="22" width="30" height="14" rx="3" fill="#15803D"/>
    <rect x="61.5" y="25" width="2" height="8" rx="1" fill="#166534"/>
    <rect x="10" y="6" width="26" height="28" rx="3" fill="#16A34A"/>
    <rect x="14" y="10" width="18" height="13" rx="2" fill="#DCFCE7"/>
    <rect x="7" y="2.5" width="32" height="4.5" rx="2.2" fill="#166534"/>
    <rect x="18" y="31" width="42" height="6" rx="2" fill="#166534"/>
  </g>
  <g transform="translate(22 34)">
    <g class="tr-tx-wheel">
      <circle r="14" fill="#27272A"/>
      <circle r="13" fill="none" stroke="#52525B" stroke-width="2" stroke-dasharray="3.2 4.4"/>
      <circle r="7.6" fill="#FACC15"/>
      <path d="M-7.6 0H7.6M0 -7.6V7.6" stroke="#CA8A04" stroke-width="1.6"/>
      <circle r="2.4" fill="#3F3F46"/>
    </g>
  </g>
  <g transform="translate(58 40)">
    <g class="tr-tx-wheel">
      <circle r="8" fill="#27272A"/>
      <circle r="7.2" fill="none" stroke="#52525B" stroke-width="1.6" stroke-dasharray="2.6 3.2"/>
      <circle r="4.2" fill="#FACC15"/>
      <path d="M-4.2 0H4.2M0 -4.2V4.2" stroke="#CA8A04" stroke-width="1.2"/>
      <circle r="1.4" fill="#3F3F46"/>
    </g>
  </g>
</svg>
"""
)

_BASE_CSS = _compact(
    """
/* Katman ekran akışının dışında kalsın (sayfa düzenini kaydırmasın) */
[data-testid="stElementContainer"]:has(.tr-tx),
.element-container:has(.tr-tx) { position: fixed; width: 0; height: 0; margin: 0; padding: 0; }

/* Tam opak arka plan: geçiş sırasında arkadaki hiçbir içerik gözükmez */
.tr-tx { position: fixed; inset: 0; z-index: 2147483000; display: flex; align-items: center;
  justify-content: center; cursor: progress; opacity: 0; visibility: hidden; pointer-events: none;
  background: var(--background-color, #ffffff); }
.tr-tx-card { width: 280px; padding: 30px 44px 24px 44px; border-radius: 18px; box-sizing: content-box;
  background: var(--secondary-background-color, #F4F4F5); border: 1px solid rgba(128,128,128,0.28);
  box-shadow: 0 10px 36px rgba(0,0,0,0.12); text-align: center; overflow: visible; }

/* Bar: traktör barın üst kenarına basar, bar ile aynı genişlik/zaman çizelgesini kullanır */
.tr-tx-bar { position: relative; width: 100%; height: 12px; margin-top: 50px; }
.tr-tx-rail { width: 100%; height: 100%; border-radius: 999px; overflow: hidden;
  background: rgba(128,128,128,0.25); }
.tr-tx-fill { width: 0; height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #15803D, #22C55E);
  animation-timing-function: linear; animation-fill-mode: forwards; }
.tr-tx-tractor { position: absolute; left: 0; bottom: calc(100% - 1px); width: 72px; height: 48px;
  transform: translateX(-50%); animation-timing-function: linear; animation-fill-mode: forwards; }
.tr-tx-svg { display: block; overflow: visible; }

.tr-tx-wheel { animation: trtxSpin 0.55s linear infinite; }
.tr-tx-body { animation: trtxBob 0.28s ease-in-out infinite alternate; }
.tr-tx-puff { transform-box: fill-box; transform-origin: center; opacity: 0;
  animation: trtxPuff 1s ease-out infinite; }
.tr-tx-puff.p2 { animation-delay: 0.5s; }

.tr-tx-label { margin-top: 16px; font-size: 13.5px; font-weight: 500; color: var(--text-color, #18181B);
  opacity: 0.75; letter-spacing: 0.01em; }

@keyframes trtxSpin { to { transform: rotate(360deg); } }
@keyframes trtxBob { from { transform: translateY(0); } to { transform: translateY(-1.2px); } }
@keyframes trtxPuff { 0% { opacity: 0; transform: translate(0,0) scale(0.6); }
  20% { opacity: 0.55; } 100% { opacity: 0; transform: translate(-9px,-12px) scale(1.7); } }
@keyframes trtxIn { from { opacity: 0; visibility: visible; pointer-events: auto; }
  to { opacity: 1; visibility: visible; pointer-events: auto; } }
@keyframes trtxOut { from { opacity: 1; visibility: visible; }
  to { opacity: 0; visibility: hidden; pointer-events: none; } }

@media (prefers-reduced-motion: reduce) {
  .tr-tx-wheel, .tr-tx-body, .tr-tx-puff { animation: none; }
}
"""
)


def _progress_at(t: float) -> float:
  """Python tarafında çizelgenin t. saniyedeki yüzdesi (CSS ile aynı tablo)."""
  if t <= 0:
    return 0.0
  for (t0, p0), (t1, p1) in zip(_POINTS, _POINTS[1:]):
    if t <= t1:
      return p0 + (p1 - p0) * (t - t0) / (t1 - t0)
  return float(_POINTS[-1][1])


def _running_keyframes(n: int) -> str:
  fill, tractor = "", ""
  for t, p in _POINTS:
    pct = t / _TOTAL * 100
    fill += f"{pct:.3f}%{{width:{p}%}}"
    tractor += f"{pct:.3f}%{{left:{p}%}}"
  return f"@keyframes trtxF{n}{{{fill}}} @keyframes trtxT{n}{{{tractor}}}"


def _finish_keyframes(n: int, p0: float) -> str:
  return (
      f"@keyframes trtxF{n}f{{from{{width:{p0:.2f}%}}to{{width:100%}}}} "
      f"@keyframes trtxT{n}f{{from{{left:{p0:.2f}%}}to{{left:100%}}}}"
  )


def _card(label: str, fill_anim: str, tractor_anim: str) -> str:
  from html import escape

  return (
      '<div class="tr-tx-card"><div class="tr-tx-bar">'
      f'<div class="tr-tx-tractor" style="{tractor_anim}">{_TRACTOR_SVG}</div>'
      f'<div class="tr-tx-rail"><div class="tr-tx-fill" style="{fill_anim}"></div></div></div>'
      f'<div class="tr-tx-label">{escape(label)}</div></div>'
  )


def _running_html(n: int, label: str, elapsed_offset: float = 0.0) -> str:
  dur = f"{_TOTAL:g}s"
  rem_delay = max(0.0, SHOW_DELAY_SECONDS - elapsed_offset)
  delay = f"{rem_delay:.3f}s"
  neg_offset = f"-{elapsed_offset:.3f}s" if elapsed_offset > 0 else "0s"
  return (
      f"<style>{_BASE_CSS} {_running_keyframes(n)}</style>"
      f'<div class="tr-tx" role="status" aria-live="polite" '
      f'style="animation: trtxIn .18s ease-out {delay} forwards, trtxOut .4s ease {_FAILSAFE_DELAY}s forwards">'
      + _card(
          label,
          f"animation-name:trtxF{n};animation-duration:{dur};animation-delay:{neg_offset}",
          f"animation-name:trtxT{n};animation-duration:{dur};animation-delay:{neg_offset}",
      )
      + "</div>"
  )


def _finish_html(n: int, label: str, p0: float) -> str:
  return (
      f"<style>{_BASE_CSS} {_finish_keyframes(n, p0)}</style>"
      '<div class="tr-tx" role="status" aria-live="polite" '
      'style="opacity:1;visibility:visible;animation: trtxOut .3s ease .35s forwards">'
      + _card(
          label,
          f"animation-name:trtxF{n}f;animation-duration:.3s;animation-timing-function:ease-out",
          f"animation-name:trtxT{n}f;animation-duration:.3s;animation-timing-function:ease-out",
      )
      + "</div>"
  )


def start_pending_transition(target_step: str, labels: dict | None = None):
  """Butona basıldığı anda (ör. Analyze field) geçiş sayacını başlatır.
  st.rerun() sonrasında begin_transition() bu süreyi kaldığı yerden devralır.
  """
  t0 = time.monotonic()
  st.session_state["_tx_pending"] = {"target": target_step, "t0": t0}
  n = st.session_state.get("_tx_count", 0) + 1
  st.session_state["_tx_count"] = n
  label = (labels or DEFAULT_LABELS).get(target_step, _FALLBACK_LABEL)
  slot = st.empty()
  slot.markdown(_running_html(n, label, elapsed_offset=0.0), unsafe_allow_html=True)
  return {"slot": slot, "n": n, "label": label, "t0": t0}


def cancel_pending_transition(handle=None) -> None:
  """Geçiş iptal edilirse (ör. tarla tarıma uygun değilse) katmanı temizler."""
  st.session_state.pop("_tx_pending", None)
  if handle and handle.get("slot"):
    handle["slot"].empty()


def begin_transition(step_value, labels: dict | None = None):
  """Sayfa değiştiyse katmanı çizer; <1 sn sürerse ekrana hiç girmez."""
  pending = st.session_state.pop("_tx_pending", None)
  prev = st.session_state.get("_tx_prev_step")
  st.session_state["_tx_prev_step"] = step_value

  if pending and pending.get("target") == step_value:
    t0 = pending["t0"]
    elapsed_offset = max(0.0, time.monotonic() - t0)
  elif prev is not None and prev != step_value:
    t0 = time.monotonic()
    elapsed_offset = 0.0
  else:
    return None

  n = st.session_state.get("_tx_count", 0) + 1
  st.session_state["_tx_count"] = n
  label = (labels or DEFAULT_LABELS).get(step_value, _FALLBACK_LABEL)
  slot = st.empty()
  slot.markdown(_running_html(n, label, elapsed_offset=elapsed_offset), unsafe_allow_html=True)
  return {"slot": slot, "n": n, "label": label, "t0": t0}


def end_transition(handle) -> None:
  """Sayfa çizimi bittiğinde çağrılır.
  - Geçiş 1 saniyenin altındaysa katmanı hiç göstermeden temizler.
  - 1 saniyeyi aştıysa barı %100'e tamamlayıp sönerek kapatır.
  """
  if not handle:
    return
  elapsed = time.monotonic() - handle["t0"]
  if elapsed < SHOW_DELAY_SECONDS:
    handle["slot"].empty()
    return
  handle["slot"].markdown(
      _finish_html(handle["n"], handle["label"], _progress_at(elapsed)),
      unsafe_allow_html=True,
  )
