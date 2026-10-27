/* Runs only from the default branch. Never checks out or executes contributor code. */
const LEASE_MS = 24 * 60 * 60 * 1000;

function replay(comments, now) {
  let lease = null;
  for (const c of [...comments].sort((a, b) => a.id - b.id)) {
    const time = Date.parse(c.created_at);
    if (lease && lease.expires <= time) lease = null;
    if (c.user.type === 'Bot') continue;
    const command = c.body.trim();
    if (command === '/claim' && (!lease || lease.owner === c.user.login)) {
      lease = {owner: c.user.login, expires: time + LEASE_MS, comment: c.id};
    } else if (command === '/renew' && lease?.owner === c.user.login) {
      lease = {...lease, expires: time + LEASE_MS, comment: c.id};
    } else if (command === '/release' && lease?.owner === c.user.login) {
      lease = null;
    }
  }
  return lease && lease.expires > now ? lease : null;
}

async function handle({github, context}) {
  const {issue, comment} = context.payload;
  if (issue.pull_request || comment.user.type === 'Bot') return;
  if (!['/claim', '/renew', '/release'].includes(comment.body.trim())) return;
  // Only repository-owner-authored task tickets participate in this first version.
  if (issue.user.login.toLowerCase() !== context.repo.owner.toLowerCase() ||
      !/<!-- svrl-task: [a-z0-9_-]+ -->/.test(issue.body || '')) return;
  if (issue.state !== 'open') return;
  const params = {...context.repo, issue_number: issue.number};
  const comments = await github.paginate(github.rest.issues.listComments, {...params, per_page: 100});
  const lease = replay(comments, Date.now());
  const body = lease
    ? `Claim status: @${lease.owner} holds this task until ${new Date(lease.expires).toISOString()}. ` +
      'The earliest active claim wins. Renew with `/renew`; release with `/release`. ' +
      `Source command: ${lease.comment}.`
    : 'Claim status: available. Comment `/claim` to take a 24-hour lease.';
  // Replies are snapshots; the command log is authoritative. No assignee permission needed.
  await github.rest.issues.createComment({...params, body});
}

module.exports = {replay, handle};
