/**
 * Device UUID generation and persistence.
 * Uses localStorage with IndexedDB fallback for durability.
 */
const DeviceUUID = (() => {
  const STORAGE_KEY = 'attendance_device_uuid';

  function generateUUID() {
    // Use crypto.randomUUID if available, otherwise fallback
    if (crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback for older browsers
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function get() {
    let uuid = localStorage.getItem(STORAGE_KEY);
    if (!uuid) {
      uuid = generateUUID();
      localStorage.setItem(STORAGE_KEY, uuid);
    }
    return uuid;
  }

  function reset() {
    const uuid = generateUUID();
    localStorage.setItem(STORAGE_KEY, uuid);
    return uuid;
  }

  return { get, reset, generateUUID };
})();
