const RULES = [
  ['minor_nsfw', /(?:未成年|儿童|幼童|小学生|初中生).{0,12}(?:性|裸|色情|性爱|性行为|性侵)/iu],
  ['nsfw', /(?:nsfw|裸照|色情|成人视频|性爱|约炮|强奸)/iu],
  ['graphic_violence', /(?:血腥暴力|血腥|虐杀|屠杀|肢解|斩首|开膛|挖眼|断肢|杀人教程|制作炸弹)/iu],
  ['social_engineering', /(?:(?:冒充|假扮).{0,16}(?:管理员|官方|用户|亲友)|(?:我是|自称).{0,16}(?:管理员|官方|用户|亲友).{0,20}(?:验证码|密码|token|api[ _-]?key|私钥|助记词)|(?:套取|骗取|窃取|绕过).{0,20}(?:验证码|密码|token|api[ _-]?key|私钥|助记词)|(?:验证码|密码|token|api[ _-]?key|私钥|助记词).{0,16}(?:提供|发送|发给|告诉|交出|泄露))/iu],
  ['personal_data', /(?:(?:身份证|护照号|银行卡号|精确住址|家庭住址|手机号|电话号码|联系方式|聊天记录|系统提示词).{0,16}(?:提供|发送|发给|告诉|公开|泄露|索取|获取)|(?:提供|发送|发给|告诉|公开|泄露|索取|获取).{0,16}(?:身份证|护照号|银行卡号|精确住址|家庭住址|手机号|电话号码|联系方式|聊天记录|系统提示词)|\b1[3-9]\d{9}\b|\b\d{17}[\dXx]\b)/iu],
  ['politics', /(?:政治|政党|选举|总统|总理|国家主席|政府执政|议会|国会|共产党|民主党|共和党|台独|港独)/iu]
];

const REFUSAL_PHRASE = /(?:拒绝|不|不要|不能|禁止|避免|不会)(?:讨论|涉及|生成|提供|索取|泄露|参与)?(?:任何)?(?:未成年.{0,4}NSFW|NSFW|色情|血腥暴力|血腥|政治|隐私|社工|社会工程)(?:内容|信息|话题)?/giu;

export function inspectText(...values) {
  // “记忆”不是违规词；同时允许“拒绝讨论政治”这类边界说明。
  const text = values.filter(Boolean).join('\n').slice(0, 20000).replace(REFUSAL_PHRASE, '');
  for (const [reason, pattern] of RULES) {
    if (pattern.test(text)) return { ok: false, reason };
  }
  return { ok: true, reason: null };
}

export function cleanText(value, maxLength) {
  if (typeof value !== 'string') return '';
  return value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim().slice(0, maxLength);
}

export function isAllowedOrigin(origin, configured = '') {
  if (!origin) return true;
  return configured.split(',').map(x => x.trim()).filter(Boolean).includes(origin);
}
