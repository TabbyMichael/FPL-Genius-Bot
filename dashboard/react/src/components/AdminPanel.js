import React, { useState, useEffect } from 'react';
import { fetchSystemLogs, triggerBotRun } from '../services/api';

function AdminPanel() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [status, setStatus] = useState('');

    const loadLogs = async () => {
        try {
            setLoading(true);
            const response = await fetchSystemLogs(100);
            setLogs(response.data.logs || []);
        } catch (error) {
            console.error('Error fetching logs:', error);
            setStatus('Failed to fetch logs');
        } finally {
            setLoading(false);
        }
    };

    const handleRunBot = async () => {
        try {
            setRunning(true);
            setStatus('Starting bot process...');
            await triggerBotRun();
            setStatus('Bot process started successfully. Check logs for progress.');
            // Refresh logs after a short delay
            setTimeout(loadLogs, 2000);
        } catch (error) {
            console.error('Error starting bot:', error);
            setStatus('Failed to start bot process');
        } finally {
            setRunning(false);
        }
    };

    useEffect(() => {
        loadLogs();
        // Auto-refresh logs every 10 seconds
        const interval = setInterval(loadLogs, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="admin-panel">
            <h2>System Administration</h2>

            <div className="control-panel" style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <h3>Bot Control</h3>
                <p>Manually trigger the weekly analysis and transfer process.</p>
                <button
                    onClick={handleRunBot}
                    disabled={running}
                    style={{
                        padding: '10px 20px',
                        backgroundColor: running ? '#cccccc' : '#00ff87',
                        color: '#37003c',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: running ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold'
                    }}
                >
                    {running ? 'Starting...' : 'Run Bot Now'}
                </button>
                {status && <p style={{ marginTop: '10px', fontWeight: 'bold' }}>{status}</p>}
            </div>

            <div className="logs-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>System Logs</h3>
                    <button onClick={loadLogs} disabled={loading}>Refresh Logs</button>
                </div>
                <div
                    className="logs-container"
                    style={{
                        backgroundColor: '#1e1e1e',
                        color: '#00ff87',
                        padding: '15px',
                        borderRadius: '8px',
                        height: '400px',
                        overflowY: 'auto',
                        fontFamily: 'monospace',
                        textAlign: 'left',
                        whiteSpace: 'pre-wrap'
                    }}
                >
                    {loading && logs.length === 0 ? (
                        <p>Loading logs...</p>
                    ) : logs.length > 0 ? (
                        logs.map((line, index) => (
                            <div key={index}>{line}</div>
                        ))
                    ) : (
                        <p>No logs available</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AdminPanel;
