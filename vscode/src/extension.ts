/*---------------------------------------------------------
 * Copyright (c) 2026 Konstantin Sokolov
 * Portions Copyright (c) Microsoft Corporation
 *--------------------------------------------------------*/
/*
 * extension.ts (and activateMLIRDebug.ts) forms the "plugin" that plugs into VS Code and contains the code that
 * connects VS Code with the debug adapter.
 * 
 * extension.ts contains code for launching the debug adapter in three different ways:
 * - as an external program communicating with VS Code via stdin/stdout,
 * - as a server process communicating with VS Code via sockets or named pipes, or
 * - as inlined code running in the extension itself (default).
 * 
 * Since the code in extension.ts uses node.js APIs it cannot run in the browser.
 */

'use strict';

import * as Net from 'net';
import * as vscode from 'vscode';
import { existsSync } from 'fs';
import { randomBytes } from 'crypto';
import { tmpdir } from 'os';
import { join } from 'path';
import { platform } from 'process';
import { ProviderResult } from 'vscode';
import { MLIRDebugSession } from './mlirDebug';
import { activateMLIRDebug, workspaceFileAccessor } from './activateMLIRDebug';
import { resolveDapServerPath } from './pathResolver';

/*
 * The compile time flag 'runMode' controls how the debug adapter is run.
 * Please note: the test suite only supports 'external' mode.
 */
const runMode: 'external' | 'server' | 'namedPipeServer' | 'inline' = 'external';

export function activate(context: vscode.ExtensionContext) {

	// debug adapters can be run in different ways by using a vscode.DebugAdapterDescriptorFactory:
	switch (runMode) {
		case 'server':
			// run the debug adapter as a server inside the extension and communicate via a socket
			activateMLIRDebug(context, new MLIRDebugAdapterServerDescriptorFactory());
			break;

		case 'namedPipeServer':
			// run the debug adapter as a server inside the extension and communicate via a named pipe (Windows) or UNIX domain socket (non-Windows)
			activateMLIRDebug(context, new MLIRDebugAdapterNamedPipeServerDescriptorFactory());
			break;

		case 'external': default:
			// run the debug adapter as a separate process
			activateMLIRDebug(context, new DebugAdapterExecutableFactory());
			break;

		case 'inline':
			// run the debug adapter inside the extension and directly talk to it
			activateMLIRDebug(context);
			break;
	}
}

export function deactivate() {
	// nothing to do
}

class DebugAdapterExecutableFactory implements vscode.DebugAdapterDescriptorFactory {

	// The following use of a DebugAdapter factory shows how to control what debug adapter executable is used.
	// Since the code implements the default behavior, it is absolutely not neccessary and we show it here only for educational purpose.

 	createDebugAdapterDescriptor(session: vscode.DebugSession, executable: vscode.DebugAdapterExecutable | undefined): ProviderResult<vscode.DebugAdapterDescriptor> {
		// param "executable" contains the executable optionally specified in the package.json (if any)
		
		console.log(`MLIR Debug: Debug session workspace folder: ${session.workspaceFolder?.uri.fsPath}`);
		console.log(`MLIR Debug: Original executable: command="${executable?.command}", args=${JSON.stringify(executable?.args)}`);
		console.log(`MLIR Debug: Original executable options: ${JSON.stringify(executable?.options)}`);

		// Get extension configuration for MLIR Debug
		const extensionConfig = vscode.workspace.getConfiguration('mlir-debug');
		const extensionPythonPath = extensionConfig.get<string>('pythonPath');
		const extensionDapServerPath = extensionConfig.get<string>('dapServerPath');
		
		console.log(`MLIR Debug: Extension configuration: pythonPath="${extensionPythonPath}", dapServerPath="${extensionDapServerPath}"`);
		
		// Always use extension configuration to create executable
		const pythonPath = extensionPythonPath || 'python3';
		let dapServerPath = extensionDapServerPath || 'debugger/dap_server.py';
		
		// Create executable with extension configuration
		executable = new vscode.DebugAdapterExecutable(
			pythonPath,
			[dapServerPath],
			executable?.options
		);

		// If executable is provided (from package.json), we need to fix the path resolution
		if (executable) {
			const workspaceFolder = session.workspaceFolder?.uri.fsPath;
			if (workspaceFolder) {
				// Process each argument to resolve paths
				const originalArgs = executable.args || [];
				const resolvedArgs = originalArgs.map(arg => {
					if (typeof arg === 'string') {
						let resolved = arg;
						
						// Handle case where ${workspaceFolder} wasn't expanded
						if (arg.includes('${workspaceFolder}')) {
							resolved = arg.replace('${workspaceFolder}', workspaceFolder);
							console.log(`MLIR Debug: Resolved ${workspaceFolder} in arg: ${arg} -> ${resolved}`);
						}
						// Handle case where extension directory is prepended
						else if (arg.includes('.vscode/extensions/')) {
							// Try to extract the relative path after extension directory
							const extensionDirPattern = /.*\/\.vscode\/extensions\/[^/]+\/(.+)/;
							const match = arg.match(extensionDirPattern);
							if (match) {
								const relativePath = match[1];
								const workspacePath = join(workspaceFolder, relativePath);
								// Check if the workspace path exists
								if (existsSync(workspacePath)) {
									resolved = workspacePath;
									console.log(`MLIR Debug: Fixed extension directory path: ${arg} -> ${resolved}`);
								}
							}
						}
						// Check if it's a relative path that doesn't exist
						else if (!existsSync(arg) && !arg.startsWith('/') && !arg.startsWith('~')) {
							// Try to resolve relative to workspace folder
							const workspacePath = join(workspaceFolder, arg);
							if (existsSync(workspacePath)) {
								resolved = workspacePath;
								console.log(`MLIR Debug: Resolved relative path: ${arg} -> ${resolved}`);
							}
						}
						
						return resolved;
					}
					return arg;
				});
				
				// Also ensure cwd is set to workspace folder
				const options = executable.options || {};
				if (!options.cwd && workspaceFolder) {
					options.cwd = workspaceFolder;
					console.log(`MLIR Debug: Set cwd to workspace folder: ${workspaceFolder}`);
				}
				
				if (JSON.stringify(resolvedArgs) !== JSON.stringify(originalArgs) || options !== executable.options) {
					// Create new executable with resolved paths and updated options
					const resolvedExecutable = new vscode.DebugAdapterExecutable(
						executable.command,
						resolvedArgs,
						options
					);
					console.log(`MLIR Debug: Using resolved executable: command="${resolvedExecutable.command}", args=${JSON.stringify(resolvedExecutable.args)}, cwd=${resolvedExecutable.options?.cwd}`);
					return resolvedExecutable;
				}
			}
		} else {
			// Fallback: should not happen because package.json defines program and runtime
			const extensionConfig = vscode.workspace.getConfiguration('mlir-debug');
			const extensionPythonPath = extensionConfig.get<string>('pythonPath');
			const extensionDapServerPath = extensionConfig.get<string>('dapServerPath');

			let pythonPath = extensionPythonPath || 'python3';
			let dapServerPath = extensionDapServerPath || 'debugger/dap_server.py';
			const workspaceFolder = session.workspaceFolder?.uri.fsPath;

			console.log(`MLIR Debug: Creating executable from extension configuration (fallback): pythonPath="${pythonPath}", dapServerPath="${dapServerPath}"`);

			// Try to automatically detect the DAP server path if not found
			dapServerPath = resolveDapServerPath(workspaceFolder, dapServerPath) ?? '';

			if (!dapServerPath) {
				const errorMessage = `MLIR Debug: Could not locate DAP server (dap_server.py). Please ensure it exists in one of the following locations:
  - Relative to workspace folder: debugger/dap_server.py
  - Relative to workspace folder: symbolic_mlir_debugger/dap_server.py
  - Absolute path (configure in settings: mlir-debug.dapServerPath)`;
				console.error(errorMessage);
				throw new Error(errorMessage);
			}

			const options = workspaceFolder ? { cwd: workspaceFolder } : undefined;
			executable = new vscode.DebugAdapterExecutable(pythonPath, [dapServerPath], options);
		}

		// make VS Code launch the DA executable
		console.log(`MLIR Debug: Launching external debug adapter: command="${executable?.command}", args=${JSON.stringify(executable?.args)}`);
		return executable;
	}
}

class MLIRDebugAdapterServerDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {

	private server?: Net.Server;

	createDebugAdapterDescriptor(session: vscode.DebugSession, executable: vscode.DebugAdapterExecutable | undefined): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {

		if (!this.server) {
			// start listening on a random port
			this.server = Net.createServer(socket => {
				const session = new MLIRDebugSession(workspaceFileAccessor);
				session.setRunAsServer(true);
				session.start(socket as NodeJS.ReadableStream, socket);
			}).listen(0);
		}

		// make VS Code connect to debug server
		return new vscode.DebugAdapterServer((this.server.address() as Net.AddressInfo).port);
	}

	dispose() {
		if (this.server) {
			this.server.close();
		}
	}
}

class MLIRDebugAdapterNamedPipeServerDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {

	private server?: Net.Server;

	createDebugAdapterDescriptor(session: vscode.DebugSession, executable: vscode.DebugAdapterExecutable | undefined): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {

		if (!this.server) {
			// start listening on a random named pipe path
			const pipeName = randomBytes(10).toString('utf8');
			const pipePath = platform === "win32" ? join('\\\\.\\pipe\\', pipeName) : join(tmpdir(), pipeName);

			this.server = Net.createServer(socket => {
				const session = new MLIRDebugSession(workspaceFileAccessor);
				session.setRunAsServer(true);
				session.start(<NodeJS.ReadableStream>socket, socket);
			}).listen(pipePath);
		}

		// make VS Code connect to debug server
		return new vscode.DebugAdapterNamedPipeServer(this.server.address() as string);
	}

	dispose() {
		if (this.server) {
			this.server.close();
		}
	}
}
