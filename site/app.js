'use strict';
const search = document.querySelector('#search');
const area = document.querySelector('#area');
const list = document.querySelector('#tasks');
const count = document.querySelector('#result-count');
let catalogue;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function render() {
  if (!catalogue) return;
  const query = search.value.toLocaleLowerCase('sv');
  const tasks = catalogue.tasks.filter(task => (!area.value || task.area === area.value) &&
    `${task.title} ${task.workflow} ${task.instructions} ${task.inputs || ''} ${task.verifier || ''} ${(task.edge_cases || []).join(' ')}`.toLocaleLowerCase('sv').includes(query));
  count.textContent = `${tasks.length} av ${catalogue.tasks.length} startuppgifter. Aktuella anspråk visas i respektive GitHub-issue.`;
  list.replaceChildren();
  tasks.forEach((task, i) => {
    const row = element('article', undefined, 'task');
    row.append(element('span', String(i + 1).padStart(2, '0'), 'task-number'));
    const body = element('div');
    body.append(element('h3', task.title));
    body.append(element('p', catalogue.areas.find(a => a.id === task.area).name + ' / ' + task.workflow));
    const link = element('a', '↗');
    // Only known GitHub issue URLs may enter a link from catalogue content.
    link.href = /^https:\/\/github\.com\/BirgerMoell\/svenska-rl\/issues\/\d+$/.test(task.issue_url || '')
      ? task.issue_url : 'https://github.com/BirgerMoell/svenska-rl/issues';
    link.setAttribute('aria-label', `Öppna uppgiften: ${task.title}`);
    row.append(body, link);
    const details = element('details');
    details.append(element('summary', 'Uppdrag och krav'));
    details.append(element('p', task.instructions));
    for (const [key, label] of [['inputs', 'Indata'], ['objective', 'Uppgift'],
                               ['verifier', 'Verifiering'], ['evaluation', 'Eval']]) {
      if (task[key]) {
        details.append(element('h4', label));
        details.append(element('p', task[key]));
      }
    }
    const checks = element('ul');
    task.acceptance_checks.forEach(check => checks.append(element('li', check)));
    details.append(checks);
    row.append(details);
    list.append(row);
  });
}

fetch('catalogue.json').then(response => {
  if (!response.ok) throw new Error('catalogue unavailable');
  return response.json();
}).then(data => {
  catalogue = data;
  document.querySelector('#env-count').textContent = String(data.environments.length);
  document.querySelector('#task-count').textContent = String(data.tasks.length);
  data.areas.forEach(item => { const option = element('option', item.name); option.value = item.id; area.append(option); });
  render();
}).catch(() => {count.textContent = 'Katalogen kunde inte laddas. Öppna GitHub för att välja en uppgift.';});

search.addEventListener('input', render);
area.addEventListener('change', render);
document.querySelector('#copy').addEventListener('click', async () => {
  const status = document.querySelector('#copy-status');
  try {
    await navigator.clipboard.writeText(document.querySelector('#agent-prompt').textContent);
    status.textContent = 'Kopierat. Klistra in instruktionen i din kodagent.';
  } catch {
    status.textContent = 'Markera och kopiera texten ovan; webbläsaren tillät inte automatisk kopiering.';
  }
});
