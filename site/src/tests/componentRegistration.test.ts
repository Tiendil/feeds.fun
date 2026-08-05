import fs from "node:fs";
import path from "node:path";

import {describe, expect, it} from "vitest";
import ts from "typescript";

type Registration = {
  readonly name: string;
  readonly component: string;
};

const sourceRoot = path.join(process.cwd(), "src");
const mainSource = fs.readFileSync(path.join(sourceRoot, "main.ts"), "utf8");
const mainFile = ts.createSourceFile("main.ts", mainSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

function filesIn(directory: string): string[] {
  return fs.readdirSync(directory, {withFileTypes: true}).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      return filesIn(entryPath);
    }

    if (entry.isFile() && entry.name.endsWith(".vue")) {
      return [entryPath];
    }

    return [];
  });
}

const componentPaths = filesIn(sourceRoot)
  .map((componentPath) => path.relative(sourceRoot, componentPath).split(path.sep).join("/"))
  .filter((componentPath) => componentPath !== "App.vue" && !componentPath.startsWith("views/"))
  .sort();

const componentImports = new Map<string, string>();

for (const statement of mainFile.statements) {
  if (!ts.isImportDeclaration(statement) || !ts.isStringLiteral(statement.moduleSpecifier)) {
    continue;
  }

  const importName = statement.importClause?.name?.text;

  if (importName !== undefined) {
    componentImports.set(statement.moduleSpecifier.text, importName);
  }
}

const registrations: Registration[] = [];

function collectRegistrations(node: ts.Node): void {
  if (
    ts.isCallExpression(node) &&
    ts.isPropertyAccessExpression(node.expression) &&
    ts.isIdentifier(node.expression.expression) &&
    node.expression.expression.text === "app" &&
    node.expression.name.text === "component" &&
    ts.isStringLiteral(node.arguments[0]) &&
    ts.isIdentifier(node.arguments[1])
  ) {
    registrations.push({name: node.arguments[0].text, component: node.arguments[1].text});
  }

  ts.forEachChild(node, collectRegistrations);
}

collectRegistrations(mainFile);

describe("global component registration", () => {
  it.each(componentPaths)("registers %s exactly once in main.ts", (componentPath) => {
    const importName = componentImports.get(`./${componentPath}`);

    expect(importName, `${componentPath} must have a default import in main.ts`).toBeDefined();

    const componentRegistrations = registrations.filter((registration) => registration.component === importName);

    expect(componentRegistrations).toHaveLength(1);
    expect(componentRegistrations[0].name).toMatch(/^[A-Z][A-Za-z0-9]*$/);
  });

  it("uses unique PascalCase global component names", () => {
    const names = registrations.map((registration) => registration.name);

    expect(new Set(names).size).toBe(names.length);
    expect(names).toEqual(names.filter((name) => /^[A-Z][A-Za-z0-9]*$/.test(name)));
  });
});
