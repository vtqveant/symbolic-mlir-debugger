/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2026 Konstantin Sokolov
 *  Portions Copyright (c) Microsoft Corporation
 *  Licensed under the MIT License. See LICENSE file for license information.
 *--------------------------------------------------------------------------------------------*/

import assert = require('assert');
import * as Path from 'path';
import * as fs from 'fs';
import { existsSync } from 'fs';
import { resolveDapServerPath, defaultPaths } from '../pathResolver';

suite('DAP Server Path Resolution', () => {

	const TEST_FIXTURE_ROOT = Path.join(__dirname, '../../tests/fixtures/dap_server_resolution/');

	setup(() => {
		if (!fs.existsSync(TEST_FIXTURE_ROOT)) {
			fs.mkdirSync(TEST_FIXTURE_ROOT, { recursive: true });
		}
	});

	suite('Success Cases', () => {

		test('should resolve absolute path when configured', () => {
			const absolutePath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');
			fs.writeFileSync(absolutePath, '# dummy file');

			const workspaceFolder = TEST_FIXTURE_ROOT;
			const resolved = resolveDapServerPath(workspaceFolder, absolutePath);

			assert.strictEqual(resolved, absolutePath, `Expected ${absolutePath}, got ${resolved}`);
		});

		test('should resolve workspace-relative path when configured', () => {
			const relativePath = 'debugger/dap_server.py';
			const workspaceRelativePath = Path.join(TEST_FIXTURE_ROOT, relativePath);
			fs.writeFileSync(workspaceRelativePath, '# dummy file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, relativePath);

			assert.strictEqual(resolved, workspaceRelativePath, `Expected ${workspaceRelativePath}, got ${resolved}`);
		});

		test('should find DAP server at debugger/dap_server.py relative to workspace', () => {
			const debuggerPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');
			fs.writeFileSync(debuggerPath, '# dummy file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, debuggerPath, `Expected ${debuggerPath}, got ${resolved}`);
		});

		test('should find DAP server at symbolic_mlir_debugger/dap_server.py relative to workspace', () => {
			const symbolicPath = Path.join(TEST_FIXTURE_ROOT, 'symbolic_mlir_debugger', 'dap_server.py');
			fs.writeFileSync(symbolicPath, '# dummy file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, symbolicPath, `Expected ${symbolicPath}, got ${resolved}`);
		});

		test('should find DAP server at ../../debugger/dap_server.py from nested workspace', () => {
			const nestedWorkspace = Path.join(TEST_FIXTURE_ROOT, 'project1', 'subproject');
			if (!fs.existsSync(nestedWorkspace)) {
				fs.mkdirSync(nestedWorkspace, { recursive: true });
			}

			const debuggerPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');
			fs.writeFileSync(debuggerPath, '# dummy file');

			const resolved = resolveDapServerPath(nestedWorkspace, '');

			assert.strictEqual(resolved, debuggerPath, `Expected ${debuggerPath}, got ${resolved}`);
		});

		test('should find DAP server at symbolic_mlir_debugger/dap_server.py from nested workspace', () => {
			const nestedWorkspace = Path.join(TEST_FIXTURE_ROOT, 'project1', 'subproject');
			if (!fs.existsSync(nestedWorkspace)) {
				fs.mkdirSync(nestedWorkspace, { recursive: true });
			}

			const symbolicPath = Path.join(TEST_FIXTURE_ROOT, 'symbolic_mlir_debugger', 'dap_server.py');
			fs.writeFileSync(symbolicPath, '# dummy file');

			const resolved = resolveDapServerPath(nestedWorkspace, '');

			assert.strictEqual(resolved, symbolicPath, `Expected ${symbolicPath}, got ${resolved}`);
		});

		test('should prefer debugger/dap_server.py over symbolic_mlir_debugger/dap_server.py when both exist', () => {
			const debuggerPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');
			const symbolicPath = Path.join(TEST_FIXTURE_ROOT, 'symbolic_mlir_debugger', 'dap_server.py');

			fs.writeFileSync(debuggerPath, '# debugger file');
			fs.writeFileSync(symbolicPath, '# symbolic file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, debuggerPath, `Expected ${debuggerPath} (first in list), got ${resolved}`);
		});

		test('should find DAP server after traversing up to 10 parent directories', () => {
			const deepPath = Path.join(TEST_FIXTURE_ROOT, 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'debugger', 'dap_server.py');

			fs.mkdirSync(Path.dirname(deepPath), { recursive: true });
			fs.writeFileSync(deepPath, '# dummy file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, deepPath, `Expected ${deepPath}, got ${resolved}`);
		});

		test('should return null when no workspace folder is provided', () => {
			const resolved = resolveDapServerPath(undefined, 'debugger/dap_server.py');

			assert.strictEqual(resolved, null, `Expected null when no workspace folder, got ${resolved}`);
		});
	});

	suite('Error Cases', () => {

		test('should return null when absolute path does not exist', () => {
			const fakePath = '/nonexistent/path/to/dap_server.py';
			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, fakePath);

			assert.strictEqual(resolved, null, `Expected null for non-existent path ${fakePath}, got ${resolved}`);
		});

		test('should return null when workspace-relative path does not exist', () => {
			const fakePath = 'nonexistent/dap_server.py';
			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, fakePath);

			assert.strictEqual(resolved, null, `Expected null for non-existent relative path ${fakePath}, got ${resolved}`);
		});

		test('should return null when configured path is empty and file not found', () => {
			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, null, `Expected null for empty configured path, got ${resolved}`);
		});

		test('should return null when no default paths are found', () => {
			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, null, `Expected null when no paths found, got ${resolved}`);
		});

		test('should return null when workspace folder does not exist (should not happen in practice)', () => {
			const fakePath = '/this/path/does/not/exist/debugger/dap_server.py';
			const resolved = resolveDapServerPath(fakePath, '');

			assert.strictEqual(resolved, null, `Expected null for non-existent workspace folder, got ${resolved}`);
		});
	});

	suite('Configuration Override Scenarios', () => {

		test('should use configured path even when file exists at default location', () => {
			const defaultPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');
			const configuredPath = Path.join(TEST_FIXTURE_ROOT, 'symbolic_mlir_debugger', 'dap_server.py');

			fs.writeFileSync(defaultPath, '# default file');
			fs.writeFileSync(configuredPath, '# configured file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, configuredPath);

			assert.strictEqual(resolved, configuredPath, `Should use configured path ${configuredPath}, got ${resolved}`);
		});

		test('should prefer workspace-relative path when configured', () => {
			const configuredPath = 'debugger/custom_dap_server.py';
			const workspacePath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'custom_dap_server.py');

			fs.writeFileSync(workspacePath, '# custom file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, configuredPath);

			assert.strictEqual(resolved, workspacePath, `Expected ${workspacePath}, got ${resolved}`);
		});
	});

	suite('Path Resolution Order', () => {

		test('should check absolute path before workspace-relative path', () => {
			const absolutePath = Path.join(TEST_FIXTURE_ROOT, 'absolute_dap_server.py');
			const relativePath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');

			fs.writeFileSync(absolutePath, '# absolute file');
			fs.writeFileSync(relativePath, '# relative file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, relativePath);

			assert.strictEqual(resolved, absolutePath, `Should check absolute path first, got ${resolved}`);
		});

		test('should check all default paths in order until file is found', () => {
			const customPath = Path.join(TEST_FIXTURE_ROOT, 'custom_debugger', 'dap_server.py');
			const debuggerPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');

			fs.writeFileSync(customPath, '# custom file');
			fs.writeFileSync(debuggerPath, '# debugger file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, customPath, `Should find first matching path in list, got ${resolved}`);
		});

		test('should not find file in parent directories before checking all default paths', () => {
			const nestedPath = Path.join(TEST_FIXTURE_ROOT, 'a', 'debugger', 'dap_server.py');
			const defaultPath = Path.join(TEST_FIXTURE_ROOT, 'debugger', 'dap_server.py');

			fs.mkdirSync(Path.dirname(nestedPath), { recursive: true });
			fs.writeFileSync(nestedPath, '# nested file');
			fs.writeFileSync(defaultPath, '# default file');

			const resolved = resolveDapServerPath(TEST_FIXTURE_ROOT, '');

			assert.strictEqual(resolved, defaultPath, `Should find default path before nested, got ${resolved}`);
		});
	});
});
