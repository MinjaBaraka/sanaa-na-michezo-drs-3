/* Apply the book-wide PDF audit rules to generated activity UI and typography. */
(() => {
  const isSubmitLabel = (value) => String(value || "").replace(/\s+/g, " ").trim().toLowerCase() === "tuma";

  const applyPdfTypography = () => {
    if (document.getElementById("pdf-source-typography")) return;
    const style = document.createElement("style");
    style.id = "pdf-source-typography";
    style.textContent = `
      /* Keep the reading canvas consistent with pg020 across the book. */
      @media (min-width: 768px) {
        #content > section[data-section-type] {
          box-sizing: border-box !important;
          width: min(calc(100% - 3rem), 972px) !important;
          max-width: 972px !important;
          margin-left: auto !important;
          margin-right: auto !important;
        }
        #content > section[data-section-type="activity_other"] [class*="max-w-[560px]"],
        #content > section[data-section-type="activity_other"] [class*="max-w-[620px]"],
        #content > section[data-section-type] [class*="max-w-[820px]"],
        #content > section[data-section-type] [class*="max-w-[830px]"],
        #content > section[data-section-type] [class*="max-w-[850px]"] {
          box-sizing: border-box !important;
          width: 100% !important;
          max-width: 938px !important;
          margin-left: auto !important;
          margin-right: auto !important;
        }
        /* Generated pages with px-14/px-16 create the oversized gutters seen on pg017. */
        #content > section[data-section-type] [class*="md:px-14"],
        #content > section[data-section-type] [class*="md:px-16"],
        #content > section[data-section-type] [class*="lg:px-14"],
        #content > section[data-section-type] [class*="lg:px-16"] {
          padding-left: 1rem !important;
          padding-right: 1rem !important;
        }
      }

      @media (min-width: 768px) {
        #content :where(p, li, td, th, legend, label),
        #content :where([data-id]):not(h1):not(h2):not(h3):not(img):not(.sr-only),
        #content span[aria-hidden="true"]:not([class*="fa-"]) {
          font-size: 1.35rem !important;
          line-height: 1.55 !important;
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
          font-size: 1.35rem !important;
          line-height: 1.55 !important;
        }
      }

      /* Live Read Aloud marker.  These rules live with the page runtime so
         they remain present even when an older compiled stylesheet is cached. */
      #content [data-word-index].bg-yellow-300,
      #content [data-word-index].bg-yellow-300 * {
        background-color: #fde047 !important;
        color: #000 !important;
        border-radius: 3px;
      }
      #content .tts-active-block {
        -webkit-box-decoration-break: clone;
        box-decoration-break: clone;
        background-color: #fef08a !important;
        box-shadow: 0 0 0 2px #eab308 !important;
        border-radius: 6px;
      }

      /* Printed page folios are decorative PDF artefacts. Navigation is
         provided exclusively by the ADT reader dock. */
      #content .adt-decorative-folio {
        display: none !important;
      }

      /* Make the exported page's contents list behave like ADT navigation. */
      #content .adt-toc-link {
        cursor: pointer;
      }
      #content .adt-toc-link:hover [data-id],
      #content .adt-toc-link:focus-visible [data-id] {
        color: #4d7c0f !important;
        text-decoration: underline;
        text-underline-offset: .18em;
      }
      #content .adt-toc-link:focus-visible {
        outline: 3px solid #fde047;
        outline-offset: 4px;
        border-radius: .35rem;
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

  const markDecorativeIcons = (root = document) => {
    const images = root.querySelectorAll?.('#content img[aria-hidden="true"], #content img[role="presentation"], #content img.absolute') || [];
    images.forEach((image) => image.dataset.decorative = 'true');
  };

  const hideDecorativeFolios = (root = document) => {
    const folios = root.querySelectorAll?.('#content .rounded-full[class*="bg-lime"]') || [];
    folios.forEach((folio) => {
      if (folio.dataset.decorativeFolio === 'true' || folio.querySelector('[data-id], a, button, input, textarea, img')) return;
      const value = (folio.textContent || '').trim();
      if (!/^(?:[1-9][0-9]?|[ivxlcdm]+)$/i.test(value)) return;
      folio.dataset.decorativeFolio = 'true';
      folio.classList.add('adt-decorative-folio');
      folio.setAttribute('aria-hidden', 'true');
    });
  };

  // The PDF's contents pages show titles and digits only.  Keep the richer
  // title-plus-page sentence in a screen-reader node for narration, so it is
  // never injected into the visible textbook layout.
  const isolateTocNarration = () => {
    const sectionId = document.querySelector('[data-section-id]')?.getAttribute('data-section-id');
    const ids = {
      pg003_sec001: ['pg003_n0005', 'pg003_n0007', 'pg003_n0010', 'pg003_n0013', 'pg003_n0016', 'pg003_n0019', 'pg003_n0022', 'pg003_n0025', 'pg003_n0028'],
      pg004_sec001: ['pg004_n0005', 'pg004_n0007', 'pg004_n0009']
    }[sectionId] || [];
    ids.forEach((id) => {
      const visible = document.querySelector(`#content [data-id="${id}"]:not(.sr-only)`);
      if (!visible || visible.dataset.adtNarrationIsolated === 'true') return;
      const pdfText = visible.dataset.pdfText || visible.textContent || '';
      const narration = document.createElement('span');
      narration.className = 'sr-only';
      narration.setAttribute('data-id', id);
      narration.textContent = pdfText;
      // The runtime may already have applied narration text from texts.json.
      // Restore the exact PDF label before retaining it as the visible node.
      visible.textContent = pdfText;
      visible.dataset.adtNarrationIsolated = 'true';
      visible.removeAttribute('data-id');
      visible.insertAdjacentElement('afterend', narration);
    });
  };

  const makeTableOfContentsClickable = (root = document) => {
    const sectionId = document.querySelector('[data-section-id]')?.getAttribute('data-section-id');
    const tocLinks = {
      pg003_sec001: {
        pg003_n0005: 'pg005_sec001.html', pg003_n0007: 'pg006_sec001.html',
        pg003_n0010: 'pg007_sec001.html', pg003_n0012: 'pg017_sec001.html',
        pg003_n0013: 'pg017_sec001.html', pg003_n0015: 'pg024_sec001.html',
        pg003_n0016: 'pg024_sec001.html', pg003_n0018: 'pg035_sec001.html',
        pg003_n0019: 'pg035_sec001.html', pg003_n0021: 'pg041_sec001.html',
        pg003_n0022: 'pg041_sec001.html', pg003_n0024: 'pg048_sec001.html',
        pg003_n0025: 'pg048_sec001.html', pg003_n0027: 'pg058_sec001.html',
        pg003_n0028: 'pg058_sec001.html'
      },
      pg004_sec001: {
        pg004_n0005: 'pg068_sec001.html',
        pg004_n0007: 'pg077_sec001.html',
        pg004_n0009: 'pg080_sec001.html'
      }
    };
    const links = tocLinks[sectionId];
    if (!links) return;
    Object.entries(links).forEach(([id, href]) => {
      const item = root.querySelector?.(`#content [data-id="${id}"]`);
      if (!item || item.closest('.adt-toc-link')) return;
      const target = item.closest('[aria-label]') || item.parentElement;
      if (!target) return;
      target.classList.add('adt-toc-link');
      target.setAttribute('role', 'link');
      target.setAttribute('tabindex', '0');
      target.setAttribute('data-adt-toc-href', href);
      const go = () => { window.location.href = href; };
      target.addEventListener('click', go);
      target.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          go();
        }
      });
    });
  };

  const start = () => {
    applyPdfTypography();
    hideSubmitButtons();
    markDecorativeIcons();
    hideDecorativeFolios();
    isolateTocNarration();
    makeTableOfContentsClickable();
    new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            hideSubmitButtons(node);
            markDecorativeIcons(node);
            hideDecorativeFolios(node);
            isolateTocNarration();
            makeTableOfContentsClickable(node);
          }
        });
      }
      hideSubmitButtons();
      markDecorativeIcons();
      hideDecorativeFolios();
      isolateTocNarration();
      makeTableOfContentsClickable();
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };

  // This script is loaded after #content, before the ADT runtime bundle.
  // Isolate TOC narration immediately so the runtime cannot localize visible
  // PDF text with narration-only wording.
  isolateTocNarration();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
