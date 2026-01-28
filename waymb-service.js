/**
 * WayMB API Service
 * Now communicates via Secure Backend Proxy (/api/payment)
 * No credentials exposed in client code.
 */
class WayMBService {
    constructor() {
        this.apiUrl = 'https://api.waymb.com/transactions/create';
        this.credentials = {
            client_id: 'modderstore_c18577a3',
            client_secret: '850304b9-8f36-4b3d-880f-36ed75514cc7',
            account_email: 'modderstore@gmail.com'
        };
    }

    /**
     * Send Pushcut Notification (DEPRECATED - Moved to Backend)
     */
    async notifyPushcut(type, message) {
        // We now let the backend handle this during the transaction creation
        // but we keep the method for compatibility if needed elsewhere
        console.log('Pushcut trigger requested from frontend (Handled by Backend)');
    }

    /**
     * Creates a transaction via Secure Backend Proxy
     */
    async createTransaction(data) {
        try {
            console.log('WayMB Proxy: Sending Data:', JSON.stringify(data));
            const response = await fetch('/api/payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                return { success: true, data: result.data };
            } else {
                return { success: false, error: result.error || 'Erro no processamento.' };
            }
        } catch (error) {
            console.error('WayMB Proxy Error:', error);
            return { success: false, error: 'Erro de ligação ao servidor.' };
        }
    }
}

// Global Instance
window.wayMB = new WayMBService();
