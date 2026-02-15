/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2026 Konstantin Sokolov
 *  Portions Copyright (c) Microsoft Corporation
 *  Licensed under the MIT License. See LICENSE file for license information.
 *--------------------------------------------------------------------------------------------*/

import { existsSync } from 'fs';
import * as Path from 'path';

export const defaultPaths = [
	'debugger/dap_server.py',
	'../debugger/dap_server.py',
	'../../debugger/dap_server.py',
	'./debugger/dap_server.py',
	'symbolic_mlir_debugger/dap_server.py',
	'../symbolic_mlir_debugger/dap_server.py',
	'../../symbolic_mlir_debugger/dap_server.py',
	'./symbolic_mlir_debugger/dap_server.py'
];

/**
 * Resolves the DAP server path by trying multiple common locations
 * @param workspaceFolder The workspace folder path
 * @param configuredPath The path configured by the user
 * @returns The resolved path or null if not found
 */
export function resolveDapServerPath(workspaceFolder: string | undefined, configuredPath: string): string | null {
	if (!workspaceFolder) {
		console.log('MLIR Debug: No workspace folder found, using configured path');
		return existsSync(configuredPath) ? configuredPath : null;
	}

	if (!configuredPath) {
		console.log('MLIR Debug: No configured path, trying default locations');
	}

	console.log(`MLIR Debug: Resolving DAP server path for workspace: ${workspaceFolder}`);

	if (configuredPath && existsSync(configuredPath)) {
		console.log(`MLIR Debug: Using absolute path: ${configuredPath}`);
		return configuredPath;
	}

	if (configuredPath) {
		const workspaceRelativePath = Path.join(workspaceFolder, configuredPath);
		if (existsSync(workspaceRelativePath)) {
			console.log(`MLIR Debug: Using workspace-relative path: ${workspaceRelativePath}`);
			return workspaceRelativePath;
		}
	}

	for (const path of defaultPaths) {
		const resolvedPath = Path.join(workspaceFolder, path);
		if (existsSync(resolvedPath)) {
			console.log(`MLIR Debug: Found DAP server at: ${resolvedPath}`);
			return resolvedPath;
		}
	}

	let currentPath = workspaceFolder;
	const depth = 10;
	for (let i = 0; i < depth; i++) {
		for (const path of defaultPaths) {
			const candidatePath = Path.join(currentPath, path);
			if (existsSync(candidatePath)) {
				console.log(`MLIR Debug: Found DAP server at (parent): ${candidatePath}`);
				return candidatePath;
			}
		}
		currentPath = Path.dirname(currentPath);
		if (currentPath === workspaceFolder || currentPath.length < 2) {
			break;
		}
	}

	return null;
}
