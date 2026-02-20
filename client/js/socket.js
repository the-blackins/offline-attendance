/**
 * WebSocket connection manager using Socket.IO.
 */
const SocketManager = (() => {
    let socket = null;
    let isConnected = false;
    const listeners = {};

    function connect(serverUrl) {
        if (socket && isConnected) return;

        socket = io(serverUrl || window.location.origin, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: Infinity,
        });

        socket.on('connect', () => {
            isConnected = true;
            console.log('[WS] Connected:', socket.id);
            trigger('connectionChange', true);
        });

        socket.on('disconnect', () => {
            isConnected = false;
            console.log('[WS] Disconnected');
            trigger('connectionChange', false);
        });

        socket.on('connect_error', (err) => {
            console.warn('[WS] Connection error:', err.message);
            trigger('connectionChange', false);
        });

        return socket;
    }

    function emit(event, data) {
        if (socket) {
            socket.emit(event, data);
        }
    }

    function on(event, callback) {
        if (socket) {
            socket.on(event, callback);
        }
        // Also store in listeners for late binding
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
    }

    function trigger(event, data) {
        if (listeners[event]) {
            listeners[event].forEach(cb => cb(data));
        }
    }

    function getSocket() { return socket; }
    function connected() { return isConnected; }

    return { connect, emit, on, getSocket, connected };
})();
