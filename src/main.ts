import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { spawn, ChildProcess } from 'child_process';

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;

const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 400,
        height: 600,
        frame: false, // Frameless
        alwaysOnTop: false, // Default false, toggleable
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: true,
            contextIsolation: false, // Simplify for this prototype, or use contextBridge in preload
        },
        titleBarStyle: 'hidden',
    });

    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist-react/index.html'));
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonServer() {
    const scriptPath = path.join(__dirname, '../backend/server.py');
    // In dev, use 'python'. In prod, might need bundled executable.
    // Assuming python is in PATH for now.
    const pythonExecutable = 'python';

    pythonProcess = spawn(pythonExecutable, [scriptPath]);

    pythonProcess.stdout?.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });

    pythonProcess.stderr?.on('data', (data) => {
        console.error(`[Python API Error]: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });
}

app.whenReady().then(() => {
    startPythonServer();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        if (pythonProcess) {
            pythonProcess.kill();
        }
        app.quit();
    }
});

app.on('will-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

// IPC Handlers
ipcMain.on('toggle-always-on-top', (event, flag) => {
    if (mainWindow) {
        mainWindow.setAlwaysOnTop(flag);
    }
});

ipcMain.on('minimize-window', () => {
    mainWindow?.minimize();
});

ipcMain.on('close-window', () => {
    mainWindow?.close();
});
