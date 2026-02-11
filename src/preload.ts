// preload.ts
// Since we turned contextIsolation: false for the prototype, we can access node implementation directly in renderer for speed.
// But for cleaner architecture we can expose some things here if needed.
console.log('Preload script loaded');
