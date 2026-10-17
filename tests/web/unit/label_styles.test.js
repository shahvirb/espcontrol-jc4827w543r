"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const ROOT = path.resolve(__dirname, "../../..");
const styles = fs.readFileSync(path.join(ROOT, "src/webserver/application/styles.ts"), "utf8");
const core = fs.readFileSync(path.join(ROOT, "src/webserver/application/core.ts"), "utf8");
const grid = fs.readFileSync(path.join(ROOT, "src/webserver/model/grid.ts"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "devices/manifest.json"), "utf8"));

function styleRule(selector, predicate = () => true) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = [...styles.matchAll(new RegExp(`"${escaped}\\{[^\"]*\\}" \\+`, "g"))]
    .map((entry) => entry[0])
    .find(predicate);
  assert(match, `style rule is present: ${selector}`);
  return match;
}

test("label CSS consumes profile line settings without broadening max-size behavior", () => {
  assert.match(core, /r\.setProperty\("--btn-label-white-space", labelLines === 1 \? "nowrap" : "normal"\);/);
  assert.match(core, /r\.setProperty\("--btn-label-text-overflow", labelLines === 1 \? "ellipsis" : "clip"\);/);

  const profiles = manifest.devices;
  const jc4827 = profiles["guition-jc4827w543r"];
  assert.equal(jc4827.web.btn.labelLines, 1);
  assert.equal(jc4827.web.btn.labelLinesDouble, 3);
  assert.equal(jc4827.layout.cols, 2);
  assert.equal(jc4827.layout.rows, 3);

  const otherProfiles = Object.entries(profiles).filter(([slug]) => slug !== "guition-jc4827w543r");
  assert(otherProfiles.length > 0);
  function expectedBaseLabelStyle(profile) {
    return profile.web.btn.labelLines === 1
      ? { whiteSpace: "nowrap", textOverflow: "ellipsis" }
      : { whiteSpace: "normal", textOverflow: "clip" };
  }

  assert.deepEqual(expectedBaseLabelStyle(jc4827), { whiteSpace: "nowrap", textOverflow: "ellipsis" });
  for (const [slug, profile] of otherProfiles) {
    assert.equal(profile.web.btn.labelLines, 2, `${slug} keeps the upstream two-line base profile`);
    assert.equal(profile.web.btn.labelLinesDouble, 3, `${slug} keeps the upstream three-line tall profile`);
    assert.deepEqual(expectedBaseLabelStyle(profile), { whiteSpace: "normal", textOverflow: "clip" },
      `${slug} keeps upstream base wrapping and clipping`);
  }

  const base = styleRule(".sp-btn-label", (rule) => rule.includes("display:block"));
  assert.match(base, /white-space:var\(--btn-label-white-space,normal\)/);
  assert.match(base, /text-overflow:var\(--btn-label-text-overflow,clip\)/);

  for (const selector of [
    ".sp-btn-double .sp-btn-label,.sp-btn-double .sp-btn-label-row .sp-btn-label",
    ".sp-btn-extra-tall .sp-btn-label,.sp-btn-extra-tall .sp-btn-label-row .sp-btn-label",
    ".sp-btn-big .sp-btn-label,.sp-btn-big .sp-btn-label-row .sp-btn-label",
  ]) {
    const rule = styleRule(selector);
    assert.match(rule, /max-height:var\(--btn-label-max-height-dbl\)/);
    assert.match(rule, /white-space:normal;text-overflow:clip/);
  }

  assert.match(
    styleRule(".sp-btn-extra-large .sp-btn-label,.sp-btn-extra-large .sp-btn-label-row .sp-btn-label"),
    /max-height:var\(--btn-label-max-height-dbl\)\}/,
  );
  assert.doesNotMatch(
    styleRule(".sp-btn-extra-large .sp-btn-label,.sp-btn-extra-large .sp-btn-label-row .sp-btn-label"),
    /white-space:normal|text-overflow:clip/,
  );

  for (const size of ["max-wide", "max-tall", "portrait-large", "landscape-large"]) {
    assert.doesNotMatch(styles, new RegExp(`\\.sp-btn-${size}[^\"]*\\.sp-btn-label`),
      `${size} does not receive a new label-height rule`);
  }

  assert.match(grid, /token: "d", rowSpan: 2, colSpan: 1/);
  assert.match(grid, /token: "b", rowSpan: 2, colSpan: 2/);
  assert.match(grid, /token: "t", rowSpan: 3, colSpan: 1/);
  assert.match(grid, /token: "v", rowSpan: 3, colSpan: 2/);
});
