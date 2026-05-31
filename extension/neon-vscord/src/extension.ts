import * as vscode from 'vscode';
import WebSocket = require('ws');
import * as path from 'path';

interface EditorState {
  file: string; filePath: string; workspace: string; language: string;
  line: number; totalLines: number; errors: number; warnings: number;
  message: string; gitBranch: string; isDirty: boolean; focused: boolean;
}

let ws: WebSocket | null = null;
let reconnTimer: NodeJS.Timeout | null = null;
let updateTimer: NodeJS.Timeout | null = null;
let enabled = true;
let statusItem: vscode.StatusBarItem;

export function activate(ctx: vscode.ExtensionContext) {
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusItem.command = 'neonVscord.toggle';
  ctx.subscriptions.push(statusItem);
  setStatus('connecting');
  ctx.subscriptions.push(
    vscode.commands.registerCommand('neonVscord.reconnect', () => { disconnect(); connect(); }),
    vscode.commands.registerCommand('neonVscord.toggle', () => {
      enabled = !enabled;
      if (!enabled) { setStatus('disabled'); } else { setStatus('connecting'); connect(); }
    }),
    vscode.window.onDidChangeActiveTextEditor(scheduleUpdate),
    vscode.window.onDidChangeTextEditorSelection(scheduleUpdate),
    vscode.workspace.onDidSaveTextDocument(scheduleUpdate),
    vscode.workspace.onDidChangeTextDocument(scheduleUpdate),
    vscode.window.onDidChangeWindowState(_ => scheduleUpdate()),
    vscode.languages.onDidChangeDiagnostics(scheduleUpdate)
  );
  const interval = getConfig<number>('updateInterval', 2000);
  updateTimer = setInterval(scheduleUpdate, interval);
  ctx.subscriptions.push({ dispose: () => { if (updateTimer) { clearInterval(updateTimer); } } });
  connect();
}

export function deactivate() { disconnect(); }

function connect() {
  if (!enabled) { return; }
  const port = getConfig<number>('port', 7878);
  try {
    ws = new WebSocket(`ws://localhost:${port}`);
    const sock = ws;
    sock.on('open', () => { setStatus('connected'); if (reconnTimer) { clearTimeout(reconnTimer); reconnTimer = null; } scheduleUpdate(); });
    sock.on('close', () => { setStatus('disconnected'); scheduleReconnect(); });
    sock.on('error', (_e: Error) => { setStatus('disconnected'); scheduleReconnect(); });
  } catch (_e) { setStatus('disconnected'); scheduleReconnect(); }
}

function disconnect() {
  if (ws) { ws.removeAllListeners(); ws.close(); ws = null; }
  if (reconnTimer) { clearTimeout(reconnTimer); reconnTimer = null; }
}

function scheduleReconnect() {
  if (reconnTimer) { return; }
  reconnTimer = setTimeout(() => { reconnTimer = null; connect(); }, 10000);
}

function buildState(): EditorState {
  const editor = vscode.window.activeTextEditor;
  const workspace = vscode.workspace.name ?? vscode.workspace.workspaceFolders?.[0]?.name ?? 'Workspace';
  const focused = vscode.window.state.focused;
  if (!editor) {
    return { file: '', filePath: '', workspace, language: '', line: 0, totalLines: 0, errors: 0, warnings: 0, message: '', gitBranch: getGitBranch(), isDirty: false, focused };
  }
  const doc = editor.document;
  const fileName = path.basename(doc.fileName);
  const wsFolder = vscode.workspace.getWorkspaceFolder(doc.uri);
  const safePath = wsFolder ? `${wsFolder.name}/${fileName}` : fileName;
  const diags = vscode.languages.getDiagnostics(doc.uri);
  const errors = diags.filter(d => d.severity === vscode.DiagnosticSeverity.Error).length;
  const warnings = diags.filter(d => d.severity === vscode.DiagnosticSeverity.Warning).length;
  const first = diags.filter(d => d.severity <= vscode.DiagnosticSeverity.Warning).sort((a, b) => a.severity - b.severity)[0];
  const message = first ? `L${first.range.start.line + 1}: ${first.message.split('\n')[0].slice(0, 80)}` : '';
  return { file: fileName, filePath: safePath, workspace, language: doc.languageId, line: editor.selection.active.line + 1, totalLines: doc.lineCount, errors, warnings, message, gitBranch: getGitBranch(), isDirty: doc.isDirty, focused };
}

let _pending = false;
function scheduleUpdate() {
  if (_pending) { return; }
  _pending = true;
  setImmediate(() => { _pending = false; sendState(buildState()); });
}

function sendState(state: EditorState) {
  if (!ws || ws.readyState !== WebSocket.OPEN) { return; }
  try { ws.send(JSON.stringify(state)); } catch (_e) { /* ignore */ }
}

function getGitBranch(): string {
  try {
    const gitExt = vscode.extensions.getExtension('vscode.git');
    if (!gitExt?.isActive) { return ''; }
    const repo = gitExt.exports.getAPI(1).repositories[0];
    return repo?.state?.HEAD?.name ?? '';
  } catch { return ''; }
}

function getConfig<T>(key: string, fallback: T): T {
  return vscode.workspace.getConfiguration('neonVscord').get<T>(key, fallback);
}

function setStatus(state: 'connected' | 'disconnected' | 'connecting' | 'disabled') {
  const icons = { connected: '$(pulse) NEON', disconnected: '$(circle-slash) NEON', connecting: '$(sync~spin) NEON', disabled: '$(eye-closed) NEON' };
  const tips = { connected: 'NEON RPC: Connected', disconnected: 'NEON RPC: Disconnected', connecting: 'NEON RPC: Connecting...', disabled: 'NEON RPC: Disabled' };
  statusItem.text = icons[state]; statusItem.tooltip = tips[state]; statusItem.show();
}
