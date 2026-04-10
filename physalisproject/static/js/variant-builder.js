function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return '';
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Не удалось выполнить действие.');
  }
  return data;
}

async function postForm(url, body) {
  return fetchJson(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      'X-CSRFToken': getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: new URLSearchParams(body),
  });
}

function updateWidget(summary) {
  const link = document.querySelector('[data-variant-nav]');
  const badge = document.querySelector('[data-variant-nav-badge]');
  if (!link) {
    return;
  }

  link.setAttribute('href', summary.current_url);
  if (summary.can_use === false) {
    link.classList.remove('active');
    link.classList.add('inactive');
    link.setAttribute('aria-disabled', 'true');
    link.setAttribute('title', 'Войдите, чтобы собирать варианты');
    if (badge) {
      badge.hidden = true;
    }
    return;
  }

  if (summary.count > 0) {
    link.classList.remove('inactive');
    link.classList.add('active');
    link.setAttribute('aria-disabled', 'false');
    link.setAttribute('title', `Открыть подборку (${summary.count} задач)`);
    if (badge) {
      badge.hidden = false;
      badge.textContent = String(summary.count);
    }
  } else if (summary.can_open_current) {
    link.classList.remove('active');
    link.classList.add('inactive');
    link.setAttribute('aria-disabled', 'false');
    link.setAttribute('title', 'Открыть подборку и недавно удалённые задачи');
    if (badge) {
      badge.hidden = true;
    }
  } else {
    link.classList.remove('active');
    link.classList.add('inactive');
    link.setAttribute('aria-disabled', 'true');
    link.setAttribute('title', 'Добавьте задачи в вариант, чтобы открыть подборку');
    if (badge) {
      badge.hidden = true;
    }
  }
}

function updateSelectionMoveButtons() {
  const content = document.getElementById('variant-current-content');
  const sortCheckbox = content?.querySelector('input[name="sort_by_complexity"]');
  const fullCheckbox = content?.querySelector('input[name="is_full"]');
  const isSortedByComplexity = Boolean(sortCheckbox?.checked) && !Boolean(fullCheckbox?.checked);
  const entries = Array.from(document.querySelectorAll('[data-selection-entry]'));

  entries.forEach((entry, index) => {
    const upButton = entry.querySelector('input[name="action"][value="move_up"]')?.closest('form')?.querySelector('button');
    const downButton = entry.querySelector('input[name="action"][value="move_down"]')?.closest('form')?.querySelector('button');
    const entryComplexity = Number(entry.dataset.complexity || 0);
    const previousComplexity = index > 0 ? Number(entries[index - 1].dataset.complexity || 0) : null;
    const nextComplexity = index < entries.length - 1 ? Number(entries[index + 1].dataset.complexity || 0) : null;

    if (upButton) {
      upButton.disabled = isSortedByComplexity
        ? index === 0 || previousComplexity !== entryComplexity
        : index === 0;
    }
    if (downButton) {
      downButton.disabled = isSortedByComplexity
        ? index === entries.length - 1 || nextComplexity !== entryComplexity
        : index === entries.length - 1;
    }
  });
}

function getSortedSwapTarget(form) {
  const action = form.querySelector('input[name="action"]')?.value;
  if (action !== 'move_up' && action !== 'move_down') {
    return null;
  }

  const content = document.getElementById('variant-current-content');
  const sortCheckbox = content?.querySelector('input[name="sort_by_complexity"]');
  const fullCheckbox = content?.querySelector('input[name="is_full"]');
  const isSortedByComplexity = Boolean(sortCheckbox?.checked) && !Boolean(fullCheckbox?.checked);
  if (!isSortedByComplexity) {
    return null;
  }

  const entry = form.closest('[data-selection-entry]');
  if (!entry) {
    return null;
  }

  const entries = Array.from(document.querySelectorAll('[data-selection-entry]'));
  const index = entries.indexOf(entry);
  if (index === -1) {
    return null;
  }

  const targetIndex = action === 'move_up' ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= entries.length) {
    return null;
  }

  const targetEntry = entries[targetIndex];
  const sourceComplexity = Number(entry.dataset.complexity || 0);
  const targetComplexity = Number(targetEntry.dataset.complexity || 0);
  if (sourceComplexity !== targetComplexity) {
    return null;
  }

  return {
    action: 'swap',
    targetProblemId: targetEntry.dataset.problemId,
  };
}

function ensureProblemToggle(problemId, container, isDetail = false) {
  let button = container.querySelector(`[data-variant-toggle][data-problem-id="${problemId}"]`);
  if (button) {
    return button;
  }

  button = document.createElement('button');
  button.type = 'button';
  button.className = `variant-inline-toggle no-print${isDetail ? ' variant-inline-toggle-detail' : ''}`;
  button.dataset.variantToggle = '';
  button.dataset.problemId = String(problemId);
  button.setAttribute('aria-label', 'Добавить в вариант');
  button.textContent = '+';

  if (container.classList.contains('id-in-list')) {
    container.appendChild(button);
  } else {
    container.appendChild(button);
  }

  return button;
}

function buildMissingToggles() {
  document.querySelectorAll('.id-in-list').forEach((container) => {
    if (container.closest('#variant-current-content')) {
      return;
    }
    const idNumber = container.querySelector('.id-number');
    if (!idNumber) {
      return;
    }
    const match = idNumber.textContent.match(/\d+/);
    if (!match) {
      return;
    }
    ensureProblemToggle(Number(match[0]), container, false);
  });
}

function updateToggleButtons(summary) {
  if (summary.can_use === false) {
    document.querySelectorAll('[data-variant-toggle]').forEach((button) => button.remove());
    return;
  }

  const selectedIds = summary.problem_ids || [];
  const selectedIndexById = new Map();
  selectedIds.forEach((problemId, index) => {
    selectedIndexById.set(Number(problemId), index + 1);
  });

  document.querySelectorAll('[data-variant-toggle]').forEach((button) => {
    const problemId = Number(button.dataset.problemId);
    const index = selectedIndexById.get(problemId);
    const isSelected = Boolean(index);
    button.dataset.selected = isSelected ? 'true' : 'false';
    button.classList.toggle('active', isSelected);
    button.textContent = isSelected ? '−' : '+';
    button.title = isSelected
      ? `№ ${index} в подборке; нажмите, чтобы удалить`
      : 'Добавить в вариант';
  });
}

async function refreshSelection() {
  const summary = await fetchJson('/variants/current/data/');
  updateWidget(summary);
  if (summary.can_use === false) {
    document.querySelectorAll('[data-variant-toggle]').forEach((button) => button.remove());
    return summary;
  }
  buildMissingToggles();
  updateToggleButtons(summary);
  return summary;
}

function applyCurrentSelectionSort() {
  const list = document.getElementById('selection-problem-list');
  if (!list) {
    return;
  }

  const content = document.getElementById('variant-current-content');
  const checkbox = content?.querySelector('input[name="sort_by_complexity"]');
  const fullCheckbox = content?.querySelector('input[name="is_full"]');
  const entries = Array.from(list.querySelectorAll('[data-selection-entry]'));

  if (!checkbox || entries.length === 0) {
    return;
  }

  const wrappers = entries.map((entry) => ({
    entry,
    complexity: Number(entry.dataset.complexity || 0),
    originalIndex: Number(entry.dataset.originalIndex || 0),
  }));

  const shouldSort = checkbox.checked && !(fullCheckbox && fullCheckbox.checked);
  const sorted = wrappers.slice().sort((a, b) => {
    if (!shouldSort) {
      return a.originalIndex - b.originalIndex;
    }
    if (a.complexity === b.complexity) {
      return a.originalIndex - b.originalIndex;
    }
    return a.complexity - b.complexity;
  });

  sorted.forEach((wrapper) => {
    list.appendChild(wrapper.entry);
  });
  updateSelectionMoveButtons();
}

function bindCurrentSelectionInteractions() {
  const content = document.getElementById('variant-current-content');
  if (!content) {
    return;
  }

  function captureGenerateFormState() {
    const generateForm = content.querySelector('#variant-generate-form');
    if (!generateForm) {
      return {};
    }

    const state = {};
    generateForm.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      state[input.name] = input.checked;
    });
    return state;
  }

  function restoreGenerateFormState(state) {
    const generateForm = content.querySelector('#variant-generate-form');
    if (!generateForm) {
      return;
    }

    generateForm.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      if (Object.prototype.hasOwnProperty.call(state, input.name)) {
        input.checked = state[input.name];
      }
    });
  }

  function updateLastGeneratedLinkVisibility() {
    const generateForm = content.querySelector('#variant-generate-form');
    const existingLink = content.querySelector('[data-last-generated-link]');
    const regenerateButton = content.querySelector('[data-force-regenerate-button]');
    if (!generateForm || !existingLink) {
      return;
    }

    const expectedSignature = existingLink.dataset.lastGeneratedSignature || '';
    const formData = new FormData(generateForm);
    const has = (name) => formData.get(name) !== null;
    const signature = [
      has('is_full'),
      has('show_answers'),
      has('sort_by_complexity') && !has('is_full'),
      has('show_complexity'),
      has('show_source'),
      has('show_type'),
      has('show_max_score'),
      has('show_original_number'),
      has('show_solution_link'),
      has('is_published'),
    ].map((value) => (value ? '1' : '0')).join('|');

    const matches = signature === expectedSignature;
    existingLink.style.display = matches ? '' : 'none';
    if (regenerateButton) {
      regenerateButton.textContent = matches ? 'Сгенерировать заново' : 'Сгенерировать вариант';
      regenerateButton.classList.toggle('text-action-link', matches);
      regenerateButton.classList.toggle('button-primary', !matches);
    }
  }

  function bindLastGeneratedLinkVisibility() {
    const generateForm = content.querySelector('#variant-generate-form');
    const existingLink = content.querySelector('[data-last-generated-link]');
    if (!generateForm || !existingLink) {
      return;
    }

    generateForm.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.addEventListener('change', updateLastGeneratedLinkVisibility);
    });
    updateLastGeneratedLinkVisibility();
  }

  content.querySelectorAll('[data-selection-action-form]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton && submitButton.disabled) {
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
      }
      const generateFormState = captureGenerateFormState();

      try {
        const payload = {};
        new FormData(form).forEach((value, key) => {
          payload[key] = value;
        });
        const swapTarget = getSortedSwapTarget(form);
        if (swapTarget) {
          payload.action = swapTarget.action;
          payload.target_problem_id = swapTarget.targetProblemId;
        }
        const data = await postForm('/variants/current/', payload);
        content.innerHTML = data.html;
        restoreGenerateFormState(generateFormState);
        updateWidget(data.summary);
        updateToggleButtons(data.summary);
        bindCurrentSelectionInteractions();
      } catch (error) {
        window.alert(error.message);
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  const sortCheckbox = content.querySelector('input[name="sort_by_complexity"]');
  const fullCheckbox = content.querySelector('input[name="is_full"]');

  if (sortCheckbox) {
    sortCheckbox.addEventListener('change', () => {
      applyCurrentSelectionSort();
    });
  }

  if (fullCheckbox) {
    fullCheckbox.addEventListener('change', () => {
      applyCurrentSelectionSort();
    });
  }

  applyCurrentSelectionSort();
  updateSelectionMoveButtons();
  bindLastGeneratedLinkVisibility();
}

document.addEventListener('DOMContentLoaded', () => {
  refreshSelection().catch(() => {});
  bindCurrentSelectionInteractions();

  document.body.addEventListener('click', async (event) => {
    const navLink = event.target.closest('[data-variant-nav][aria-disabled="true"]');
    if (navLink) {
      event.preventDefault();
      return;
    }

    const button = event.target.closest('[data-variant-toggle]');
    if (!button) {
      return;
    }

    const problemId = button.dataset.problemId;
    const action = button.dataset.selected === 'true' ? 'remove' : 'add';
    button.disabled = true;

    try {
      const summary = await postForm('/variants/current/problem/', {
        action,
        problem_id: problemId,
      });
      updateWidget(summary);
      updateToggleButtons(summary);
    } catch (error) {
      window.alert(error.message);
    } finally {
      button.disabled = false;
    }
  });
});
