/* Mobile bottom-sheet interaction, following the reference ADT:
 * https://adolfalfred.github.io/Writing-Pupil-s-Book-Standard-1-adt/
 * Enhance the existing dialogs without modifying the compiled reader or media.
 */
(function () {
  "use strict";

  var mobile = window.matchMedia("(max-width: 639.98px)");
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var selector = '[role="dialog"][data-slot="sheet-content"][data-side="bottom"]';
  var enhanced = new WeakSet();
  var lastTrigger = null;
  var scheduled = false;

  // The runtime's sheet and its toolbar button are rendered separately.
  document.addEventListener("click", function (event) {
    var trigger = event.target.closest && event.target.closest("[data-dock-trigger]");
    if (trigger) lastTrigger = trigger;
  }, true);

  function enhance(sheet) {
    if (enhanced.has(sheet)) return;
    var handle = sheet.firstElementChild;
    if (!handle || handle.getAttribute("aria-hidden") !== "true") return;
    enhanced.add(sheet);

    var opener = lastTrigger;
    var drag = null;
    var timer = null;
    var suppressClick = false;
    var swahili = document.documentElement.lang.toLowerCase().startsWith("sw");
    sheet.setAttribute("data-mobile-sheet-draggable", "");
    handle.removeAttribute("aria-hidden");
    handle.setAttribute("role", "button");
    handle.setAttribute("tabindex", "0");
    handle.setAttribute("aria-label", swahili ? "Funga menyu" : "Close menu");
    handle.setAttribute("title", swahili ? "Buruta chini au bonyeza kufunga" : "Drag down or press to close");
    handle.setAttribute("data-mobile-sheet-drag-handle", "");

    function clearStyles() {
      sheet.style.removeProperty("transition");
      sheet.style.removeProperty("transform");
    }

    function reset(animate) {
      window.clearTimeout(timer);
      drag = null;
      sheet.removeAttribute("data-mobile-sheet-dragging");
      if (!animate || reducedMotion.matches) {
        clearStyles();
        return;
      }
      sheet.style.transition = "transform 180ms ease-out";
      sheet.style.transform = "translateY(0)";
      timer = window.setTimeout(clearStyles, 180);
    }

    function close() {
      reset(false);
      // Let the existing dialog own its open state, overlay and focus trap.
      sheet.dispatchEvent(new KeyboardEvent("keydown", {
        key: "Escape", code: "Escape", bubbles: true, cancelable: true
      }));
      window.setTimeout(function () {
        if ((!sheet.isConnected || !sheet.hasAttribute("data-open")) &&
            opener && opener.isConnected && !document.querySelector(selector + "[data-open]")) {
          opener.focus({ preventScroll: true });
        }
      }, 220);
    }

    handle.addEventListener("pointerdown", function (event) {
      if (!mobile.matches || !event.isPrimary || event.button !== 0) return;
      window.clearTimeout(timer);
      suppressClick = false;
      drag = { id: event.pointerId, y: event.clientY, time: performance.now() };
      sheet.style.transition = "none";
      sheet.setAttribute("data-mobile-sheet-dragging", "");
      handle.setPointerCapture(event.pointerId);
    });

    handle.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.id) return;
      var distance = Math.max(0, event.clientY - drag.y);
      if (Math.abs(event.clientY - drag.y) > 5) suppressClick = true;
      sheet.style.transform = "translateY(" + distance + "px)";
    });

    handle.addEventListener("pointerup", function (event) {
      if (!drag || event.pointerId !== drag.id) return;
      var distance = Math.max(0, event.clientY - drag.y);
      var velocity = distance / Math.max(1, performance.now() - drag.time);
      var threshold = Math.min(120, sheet.offsetHeight * 0.25);
      if (distance >= threshold || (distance >= 40 && velocity >= 0.55)) {
        suppressClick = true;
        close();
      } else {
        reset(true);
      }
    });

    handle.addEventListener("pointercancel", function () {
      suppressClick = true;
      reset(true);
    });
    handle.addEventListener("lostpointercapture", function () {
      if (drag) reset(true);
    });
    handle.addEventListener("click", function () {
      if (mobile.matches && !suppressClick) close();
      suppressClick = false;
    });
    handle.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      close();
    });
    sheet.addEventListener("keydown", function (event) {
      if (event.key === "Escape") reset(false);
    });
  }

  function install() {
    scheduled = false;
    if (!mobile.matches) return;
    document.querySelectorAll(selector).forEach(enhance);
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(install);
  }

  function start() {
    var chrome = document.getElementById("interface-container");
    if (!chrome) return;
    new MutationObserver(schedule).observe(chrome, { childList: true, subtree: true });
    mobile.addEventListener("change", schedule);
    schedule();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
