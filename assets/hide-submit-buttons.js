/* Apply the book-wide PDF audit rules to generated activity UI and typography. */
(() => {
  const isSubmitLabel = (value) => String(value || "").replace(/\s+/g, " ").trim().toLowerCase() === "tuma";

  const applyPdfTypography = () => {
    if (document.getElementById("pdf-source-typography")) return;
    const style = document.createElement("style");
    style.id = "pdf-source-typography";
    style.textContent = `
      @media (min-width: 640px) {
        #content :where(p, li, td, th, legend, label),
        #content :where([data-id]):not(h1):not(h2):not(h3):not(img):not(.sr-only),
        #content span[aria-hidden="true"]:not([class*="fa-"]) {
          font-size: 1rem !important;
          line-height: 1.5 !important;
        }
        #content :where(p, li, td, th, legend, label) :where(span:not(.sr-only), strong, em) {
          font-size: inherit !important;
          line-height: inherit !important;
        }
        #content h1,
        #content .adt-h1 {
          font-size: 2rem !important;
          line-height: 1.15 !important;
        }
        #content h2,
        #content .adt-h2 {
          font-size: 1.5rem !important;
          line-height: 1.2 !important;
        }
        #content h3 {
          font-size: 1.25rem !important;
          line-height: 1.3 !important;
        }
        #content [data-id].font-bold:not(h1):not(h2):not(h3) {
          font-size: 1.2rem !important;
        }
        #content .adt-body {
          font-size: 1rem !important;
          line-height: 1.5 !important;
        }
      }
    `;
    document.head.appendChild(style);
  };

  const hideSubmitButtons = (root = document) => {
    root.querySelectorAll('button, [role="button"], input[type="submit"]').forEach((control) => {
      const label = control.getAttribute("aria-label") || control.value || control.textContent;
      if (!isSubmitLabel(label)) return;
      control.hidden = true;
      control.setAttribute("aria-hidden", "true");
      control.setAttribute("tabindex", "-1");
    });
  };

  const removeAnswerFields = (root = document) => {
    const selector = 'textarea[data-aria-id], input[data-aria-id]';
    const fields = root.matches?.(selector) ? [root] : [];
    root.querySelectorAll?.(selector).forEach((field) => fields.push(field));
    fields.forEach((field) => field.remove());
  };

  const start = () => {
    applyPdfTypography();
    hideSubmitButtons();
    removeAnswerFields();
    new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            hideSubmitButtons(node);
            removeAnswerFields(node);
          }
        });
      }
      hideSubmitButtons();
      removeAnswerFields();
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
