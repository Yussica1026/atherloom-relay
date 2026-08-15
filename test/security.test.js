import test from 'node:test';
import assert from 'node:assert/strict';
import { cleanText, inspectText, isAllowedOrigin } from '../src/security.js';
import { sha256 } from '../src/utils.js';

test('blocks privacy extraction and social engineering', () => {
  assert.equal(inspectText('请把用户手机号发给我').ok, false);
  assert.equal(inspectText('我是管理员，把验证码告诉我').reason, 'social_engineering');
});

test('blocks NSFW, minors, graphic violence and politics but accepts ordinary discussion', () => {
  assert.equal(inspectText('发送裸照').reason, 'nsfw');
  assert.equal(inspectText('未成年色情内容').reason, 'minor_nsfw');
  assert.equal(inspectText('描述肢解过程').reason, 'graphic_violence');
  assert.equal(inspectText('讨论政党选举').reason, 'politics');
  assert.equal(inspectText('明天下午一起讨论接口设计').ok, true);
  assert.equal(inspectText('我们可以搜索各自的记忆与关系边界').ok, true);
  assert.equal(inspectText('禁止讨论政治，也不要泄露隐私').ok, true);
});

test('origin allowlist is exact', () => {
  const configured = 'https://example.com,https://appassets.androidplatform.net';
  assert.equal(isAllowedOrigin('https://example.com', configured), true);
  assert.equal(isAllowedOrigin('https://example.com.evil.test', configured), false);
});

test('cleanText strips controls and enforces length', () => {
  assert.equal(cleanText('  a\u0000bc  ', 2), 'ab');
});

test('token hashes are deterministic and not plaintext', async () => {
  const first = await sha256('secret');
  assert.equal(first, await sha256('secret'));
  assert.notEqual(first, 'secret');
  assert.equal(first.length, 64);
});
