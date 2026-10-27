const {test} = require('node:test');
const assert = require('node:assert/strict');
const {replay} = require('../scripts/claims.cjs');
const start = Date.parse('2026-10-27T10:00:00Z');
const c = (id, who, body, hours = 0) => ({id, user:{login:who,type:'User'}, body,
  created_at:new Date(start + hours * 3600000).toISOString()});

test('earliest claim wins even with simultaneous competing requests', () => {
  assert.equal(replay([c(2,'b','/claim'),c(1,'a','/claim')],start+1000).owner,'a');
});
test('only owner can release and renew', () => {
  assert.equal(replay([c(1,'a','/claim'),c(2,'b','/release'),c(3,'b','/renew')],start+1000).owner,'a');
  assert.equal(replay([c(1,'a','/claim'),c(2,'a','/release')],start+1000),null);
});
test('expiry and renewal free abandoned work', () => {
  assert.equal(replay([c(1,'a','/claim')],start+25*3600000),null);
  assert.equal(replay([c(1,'a','/claim'),c(2,'b','/claim',25)],start+26*3600000).owner,'b');
  assert.equal(replay([c(1,'a','/claim'),c(2,'a','/renew',23)],start+25*3600000).owner,'a');
});
test('embedded commands and bot replies cannot claim work', () => {
  assert.equal(replay([c(1,'a','please /claim')],start+1000),null);
  const bot = c(1,'a','/claim'); bot.user.type='Bot';
  assert.equal(replay([bot],start+1000),null);
});
