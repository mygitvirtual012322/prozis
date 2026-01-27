/**
 * WayMB API Service
 * Now communicates via Secure Backend Proxy (/api/payment)
 * No credentials exposed in client code.
 */
class WayMBService {
    constructor() {
        this.backendUrl = '/api/payment'; // Local Proxy
    }

    /**
     * Send Pushcut Notification (Handled by Backend now)
     */
    async notifyPushcut(type, message) {
        // Deprecated: Backend handles this on payment success
        console.log('Pushcut handled by backend.');
    }

    /**
     * Creates a transaction via Backend Proxy
     */
    async createTransaction(data) {
        const payload = {
            amount: data.amount,
            method: data.method,
            payer: data.payer
        };

        try {
            console.log('WayMB Proxy: Creating Transaction...', payload);
            const response = await fetch(this.backendUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            console.log('WayMB Proxy Response:', result);

            if (response.ok && result.success) {
                return { success: true, data: result.data };
            } else {
                return { success: false, error: result.error || 'Erro desconhecido no servidor' };
            }
        } catch (error) {
            console.error('WayMB Proxy Error:', error);
            return { success: false, error: 'Erro de conexão com o servidor.' };
        }
    }
}

// Global Instance
window.wayMB = new WayMBService();
