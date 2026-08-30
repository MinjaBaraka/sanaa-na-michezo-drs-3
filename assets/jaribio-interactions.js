/* Local, offline-safe interactions for the Jaribio on pg077–pg079. */
(() => {
  const section = document.querySelector('[data-section-id="pg077_sec001"], [data-section-id="pg078_sec001"], [data-section-id="pg079_sec001"]');
  if (!section) return;

  const sectionId = section.getAttribute('data-section-id') || 'jaribio';
  const storageKey = `adt-jaribio-${sectionId}`;
  const normalize = (value) => String(value || '')
    .trim()
    .toLocaleLowerCase('sw-TZ')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[.,;:!?]+$/g, '')
    .replace(/\s+/g, ' ');

  const readSaved = () => {
    try {
      return JSON.parse(sessionStorage.getItem(storageKey) || '{}');
    } catch {
      return {};
    }
  };

  const writeSaved = (state) => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
      // The activity remains usable when browser storage is unavailable.
    }
  };

  const saved = readSaved();
  const controls = Array.from(section.querySelectorAll('[data-jaribio-persist], [data-jaribio-question] input[type="radio"]'));
  const groupControls = new Map();

  controls.forEach((control) => {
    const key = control.getAttribute('data-jaribio-persist') || control.getAttribute('name') || control.id;
    if (!key) return;
    if (control.type === 'radio') {
      const controlsInGroup = groupControls.get(key) || [];
      controlsInGroup.push(control);
      groupControls.set(key, controlsInGroup);
      return;
    }
    if (saved[key] !== undefined) control.value = saved[key];
  });

  groupControls.forEach((radios, key) => {
    const value = saved[key];
    if (value === undefined) return;
    const selected = radios.find((radio) => radio.value === value);
    if (selected) selected.checked = true;
  });

  const updateSelection = (control) => {
    if (control.type !== 'radio') return;
    const key = control.getAttribute('data-jaribio-persist') || control.name;
    if (!key) return;
    const radios = groupControls.get(key) || [];
    radios.forEach((radio) => {
      radio.closest('.jaribio-choice-option, .jaribio-true-false-option')?.classList.toggle('is-selected', radio.checked);
    });
  };

  const clearQuestionState = (control) => {
    const question = control.closest('[data-jaribio-question]');
    if (!question) return;
    question.removeAttribute('data-jaribio-state');
    question.querySelectorAll('input, select').forEach((field) => field.setAttribute('aria-invalid', 'false'));
  };

  controls.forEach((control) => {
    updateSelection(control);
    const persist = () => {
      const key = control.getAttribute('data-jaribio-persist') || control.getAttribute('name') || control.id;
      if (!key) return;
      if (control.type === 'radio' && !control.checked) return;
      saved[key] = control.value;
      writeSaved(saved);
      updateSelection(control);
      clearQuestionState(control);
    };
    control.addEventListener(control.type === 'radio' || control.tagName === 'SELECT' ? 'change' : 'input', persist);
  });

  const answerFor = (question) => String(question.getAttribute('data-jaribio-answer') || '')
    .split('|')
    .map(normalize)
    .filter(Boolean);

  const evaluateQuestion = (question) => {
    const type = question.getAttribute('data-jaribio-kind');
    let value = '';
    let answered = false;
    let correct = false;

    if (type === 'activity-choice') {
      const checked = question.querySelector('input[type="radio"]:checked');
      answered = Boolean(checked);
      correct = Boolean(checked?.getAttribute('data-activity-item') && window.correctAnswers?.[checked.getAttribute('data-activity-item')]);
      value = checked?.value || '';
    } else if (type === 'radio') {
      const checked = question.querySelector('input[type="radio"]:checked');
      answered = Boolean(checked);
      value = checked?.value || '';
      correct = answered && answerFor(question).includes(normalize(value));
    } else {
      const input = question.querySelector('input, select, textarea');
      value = input?.value || '';
      answered = Boolean(normalize(value));
      correct = answered && answerFor(question).includes(normalize(value));
    }

    const state = !answered ? 'unanswered' : correct ? 'correct' : 'incorrect';
    question.setAttribute('data-jaribio-state', state);
    question.querySelectorAll('input, select').forEach((field) => field.setAttribute('aria-invalid', state === 'incorrect' ? 'true' : 'false'));
    return { answered, correct };
  };

  const checkButton = section.querySelector('[data-jaribio-check]');
  const resetButton = section.querySelector('[data-jaribio-reset]');
  const status = section.querySelector('[data-jaribio-status]');
  checkButton?.addEventListener('click', () => {
    const questions = Array.from(section.querySelectorAll('[data-jaribio-question]'));
    let answered = 0;
    let correct = 0;
    let firstIncomplete = null;

    questions.forEach((question) => {
      const result = evaluateQuestion(question);
      if (result.answered) answered += 1;
      if (result.correct) correct += 1;
      if (!result.answered && !firstIncomplete) firstIncomplete = question;
    });

    if (status) {
      const responseFields = Array.from(section.querySelectorAll('[data-jaribio-open-response]'));
      const responseNote = responseFields.length === 0
        ? ''
        : responseFields.every((field) => normalize(field.value))
          ? ' Majibu ya kujieleza yamehifadhiwa.'
          : ' Kamilisha pia majibu ya kujieleza.';
      status.textContent = (answered === questions.length
        ? `Sahihi ${correct} kati ya ${questions.length}.`
        : `Umejibu ${answered} kati ya ${questions.length}. Bado kuna ${questions.length - answered} ya kujibu.`) + responseNote;
    }
    if (firstIncomplete) firstIncomplete.querySelector('input, select, textarea')?.focus();
  });

  resetButton?.addEventListener('click', () => {
    controls.forEach((control) => {
      if (control.type === 'radio') {
        control.checked = false;
      } else if (control.tagName === 'SELECT') {
        control.selectedIndex = 0;
      } else {
        control.value = '';
      }
      updateSelection(control);
    });
    Object.keys(saved).forEach((key) => delete saved[key]);
    try {
      sessionStorage.removeItem(storageKey);
    } catch {
      // Clearing remains available even when browser storage is unavailable.
    }
    section.querySelectorAll('[data-jaribio-question]').forEach((question) => {
      question.removeAttribute('data-jaribio-state');
      question.querySelectorAll('input, select').forEach((field) => field.setAttribute('aria-invalid', 'false'));
    });
    if (status) status.textContent = 'Majibu yamefutwa.';
  });
})();
