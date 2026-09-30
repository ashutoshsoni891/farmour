import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import en from "./en.json";
import hi from "./hi.json";

describe("i18n catalogues", () => {
  it("have the same keys in en and hi", () => {
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
  });

  it("have no empty values", () => {
    for (const cat of [en, hi]) {
      for (const [k, v] of Object.entries(cat)) expect(v.trim(), k).not.toBe("");
    }
  });

  it("cover every error code the backend can return", () => {
    const codes = [
      "unauthenticated",
      "forbidden_role",
      "not_found",
      "validation_error",
      "rate_limited",
      "link_invalid",
      "internal_error",
    ];
    for (const c of codes) expect(Object.keys(en)).toContain(`err.${c}`);
  });

  it("every t('key') used in source exists", () => {
    const keys = new Set(Object.keys(en));
    const used = new Set<string>();
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.tsx?$/.test(name) && !name.endsWith(".test.ts")) {
          for (const m of readFileSync(p, "utf8").matchAll(/\bt\("([\w.]+)"/g))
            used.add(m[1] ?? "");
        }
      }
    };
    walk(join(__dirname, ".."));
    for (const k of used) {
      const plural = keys.has(`${k}_one`) && keys.has(`${k}_other`);
      expect(keys.has(k) || plural, k).toBe(true);
    }
  });
});

describe("no hard-coded user-facing text in JSX", () => {
  it("TSX files contain no literal words between tags", () => {
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) walk(p);
        else if (name.endsWith(".tsx") && !name.endsWith(".test.tsx")) {
          const src = readFileSync(p, "utf8");
          for (const m of src.matchAll(
            /(?<![=-])>\s*([A-Za-z\p{Script=Devanagari}][^<>{}();=]*?)\s*</gu,
          )) {
            if (/[A-Za-z\p{Script=Devanagari}]{2,}/u.test(m[1] ?? ""))
              offenders.push(`${name}: ${m[1] ?? ""}`);
          }
        }
      }
    };
    walk(join(__dirname, ".."));
    expect(offenders).toEqual([]);
  });
});
