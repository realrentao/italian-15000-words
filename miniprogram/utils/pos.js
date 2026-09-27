// utils/pos.js — 词性短码 → 中文（与网页版 POS_ZH 一致）
const POS_ZH = {
  "n": "名词", "s": "名词", "m": "阳性名词", "f": "阴性名词",
  "n.m": "阳性名词", "n.f": "阴性名词", "s.m": "阳性名词", "s.f": "阴性名词",
  "adj": "形容词", "agg": "形容词",
  "v": "动词", "v.t": "及物动词", "v.i": "不及物动词",
  "v.tr": "及物动词", "v.intr": "不及物动词", "v.rifl": "反身动词", "v.pr": "反身动词", "i": "不及物动词",
  "avv": "副词", "adv": "副词", "prep": "介词", "cong": "连词",
  "art": "冠词", "pron": "代词", "inter": "叹词", "escl": "感叹词", "loc": "短语", "pl": "复数", "inv": "不变",
  "形": "形容词", "名": "名词", "介": "介词", "副": "副词", "固": "固定搭配", "短": "短语",
  "nm": "阳性名词", "nf": "阴性名词", "agg": "形容词",
  "va": "助动词avere", "ve": "助动词essere", "va/ve": "双助动词",
  "avv": "副词", "prep": "介词", "cong": "连词", "art": "冠词", "pron": "代词", "inter": "叹词", "loc": "短语", "pl": "复数", "inv": "不变",
  "n": "名词",
  "Nm": "阳性名词", "Nf": "阴性名词", "Agg": "形容词",
  "Va": "助动词avere", "Ve": "助动词essere", "Va/Ve": "双助动词",
  "Avv": "副词", "Prep": "介词", "Cong": "连词", "Art": "冠词", "Pron": "代词", "Inter": "叹词", "Loc": "短语", "Pl": "复数", "Inv": "不变",
  "N": "名词", "Nm/Nf": "阳性/阴性名词"
};

function posZh(p) {
  if (!p) return "";
  function look(s) {
    if (POS_ZH[s] != null) return POS_ZH[s];
    const lc = s.toLowerCase();
    if (POS_ZH[lc] != null) return POS_ZH[lc];
    const t = s.replace(/\.+$/, "");
    if (POS_ZH[t] != null) return POS_ZH[t];
    const k = t.replace(/\./g, "").toLowerCase();
    if (POS_ZH[k] != null) return POS_ZH[k];
    return null;
  }
  function one(tok) {
    tok = tok.trim();
    const a = look(tok);
    if (a) return a;
    if (tok.indexOf(".") >= 0) {
      const mp = tok.split(".").filter(Boolean).map(look);
      if (mp.length && mp.every(m => m != null)) return mp.join("·");
    }
    return tok;
  }
  return p.trim().split(/\s+/).map(one).join("·");
}

module.exports = { POS_ZH, posZh };
