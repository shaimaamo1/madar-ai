const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const ts = require("typescript");
const root = path.resolve(__dirname, "../src");
function loadSource(name) {
  const filename = path.join(root, name);
  const mod = new Module(filename, module);
  mod.filename = filename;
  mod.paths = Module._nodeModulePaths(root);
  mod._compile(
    ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    }).outputText,
    filename,
  );
  return mod.exports;
}
const i18n = loadSource("i18n.ts");
const ar = require("../src/locales/ar.json");
const en = require("../src/locales/en.json");

test("catalogs cover the same keys, contain Arabic, and preserve every interpolation", () => {
  assert.deepEqual(Object.keys(ar).sort(), Object.keys(en).sort());
  for (const [key, value] of Object.entries(ar)) {
    assert.ok(value.trim(), key);
    if (!["n8n", "{count} / {total}", "HTTP {count}"].includes(key))
      assert.match(value, /[\u0600-\u06ff]/, key);
    const tokens = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    assert.deepEqual(tokens(value), tokens(en[key]), key);
  }
});

test("rendered literals and translation calls cannot silently miss a catalog entry", () => {
  const missing = [];
  for (const filename of [
    "App.tsx",
    "Premium.tsx",
    "Enterprise.tsx",
    "TelegramSetup.tsx",
    "LanguageSelector.tsx",
    "i18n.ts",
  ]) {
    const source = ts.createSourceFile(
      filename,
      fs.readFileSync(path.join(root, filename), "utf8"),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    function visit(node) {
      if (
        ts.isCallExpression(node) &&
        ["tr", "localize"].includes(node.expression.getText(source)) &&
        node.arguments[0] &&
        ts.isStringLiteral(node.arguments[0]) &&
        !(node.arguments[0].text in ar)
      )
        missing.push(filename + ": " + node.arguments[0].text);
      if (
        ts.isJsxText(node) &&
        /[a-z]{2}/i.test(node.text) &&
        !/^(?:MADAR AI|MADAR|AI|English \(EN\)|العربية \(AR\))$/.test(
          node.text.trim(),
        )
      )
        missing.push(filename + ": raw JSX " + node.text.trim());
      const readOnly = node.parent?.properties?.some(
        (p) => p.name?.text === "readOnly",
      );
      if (
        !readOnly &&
        ts.isJsxAttribute(node) &&
        ["key", "value", "name", "checked"].includes(node.name.text) &&
        node.initializer?.expression &&
        /\b(?:tr|localize|number)\(/.test(
          node.initializer.expression.getText(source),
        )
      )
        missing.push(
          filename + ": translated identity/input " + node.getText(source),
        );
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
  assert.deepEqual(missing, []);
});

test("workflow labels translate without changing workflow identities or connections", () => {
  const { workflowCatalog } = loadSource("workflowCatalog.ts");
  for (const flow of workflowCatalog) {
    assert.ok(ar[flow.name.replace("MADAR ", "")], flow.name);
    for (const node of flow.nodes) {
      assert.ok(ar[node.name], node.name);
      if (node.type !== "stickyNote") assert.ok(ar[node.type], node.type);
    }
    for (const edge of flow.edges) {
      assert.ok(flow.nodes.some((n) => n.name === edge.source));
      assert.ok(flow.nodes.some((n) => n.name === edge.target));
    }
  }
});

test("numbers, dates, currencies, statuses and placeholders follow the current language", () => {
  i18n.setLanguage("en");
  assert.equal(i18n.tr("Save"), "Save");
  assert.equal(i18n.number(1234), "1,234");
  assert.equal(i18n.localize("Qualified"), "Qualified");
  assert.equal(i18n.localize("offer_viewing"), "Offer viewing");
  i18n.setTimezone("Africa/Cairo");
  const time = "2030-01-01T10:00:00Z";
  assert.equal(
    i18n.date(time),
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Africa/Cairo",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(time)),
  );
  i18n.setLanguage("ar");
  assert.equal(i18n.tr("Save"), ar.Save);
  assert.equal(i18n.number(1234), "١٬٢٣٤");
  assert.equal(i18n.localize("Qualified"), ar.Qualified);
  assert.equal(
    i18n.tr("Open {name}", { name: "Palm Residence" }),
    ar["Open {name}"].replace("{name}", "Palm Residence"),
  );
  for (const currency of ["EGP", "SAR", "AED", "USD"])
    assert.equal(
      i18n.money(5000000, currency),
      new Intl.NumberFormat("ar-EG", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(5000000),
    );
  assert.match(i18n.date(time), /٢٠٣٠|يناير/);
  assert.equal(i18n.localize("Palm Residence"), "Palm Residence");
  assert.equal(i18n.date("invalid"), "—");
  assert.equal(
    i18n.errorText("an unknown raw exception with credentials"),
    ar["The operation could not be completed. Please try again."],
  );
  i18n.setLanguage("en");
});
