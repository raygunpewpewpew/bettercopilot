// Minimal VS Code extension scaffold (not a complete packaged extension)
// This file demonstrates how a real extension could call the local Python
// bridge via HTTP. For testing, the bridge is implemented in Python.

const vscode = require('vscode');
const fetch = require('node-fetch');

function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand('bettercopilot.ask', async () => {
        const q = await vscode.window.showInputBox({prompt: 'Ask BetterCopilot'});
        if (!q) return;
        const resp = await fetch('http://localhost:8767/ask', {method: 'POST', body: JSON.stringify({question: q}), headers: {'Content-Type': 'application/json'}});
        const data = await resp.json();
        vscode.window.showInformationMessage('BetterCopilot response received');
    }));
}

function deactivate() {}

module.exports = { activate, deactivate };
