/**
 * Connection Test Component
 * 
 * Use this to test if your mobile app can connect to the backend
 */

import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { api, API_URL } from '@/lib/api-client';

export default function ConnectionTest() {
  const [status, setStatus] = useState<'idle' | 'testing' | 'connected' | 'error'>('idle');
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const testConnection = async () => {
    setStatus('testing');
    setError(null);
    setResponse(null);

    try {
      const data = await api.healthCheck();
      setResponse(data);
      setStatus('connected');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStatus('error');
    }
  };

  useEffect(() => {
    // Auto-test on mount
    testConnection();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Backend Connection Test</Text>
      <Text style={styles.url}>API URL: {API_URL}</Text>
      
      <TouchableOpacity 
        style={[styles.button, status === 'testing' && styles.buttonDisabled]} 
        onPress={testConnection}
        disabled={status === 'testing'}
      >
        <Text style={styles.buttonText}>
          {status === 'testing' ? 'Testing...' : 'Test Connection'}
        </Text>
      </TouchableOpacity>

      {status === 'connected' && (
        <View style={styles.successContainer}>
          <Text style={styles.successText}>✓ Connected Successfully!</Text>
          {response && (
            <Text style={styles.responseText}>
              {JSON.stringify(response, null, 2)}
            </Text>
          )}
        </View>
      )}

      {status === 'error' && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>✗ Connection Failed</Text>
          {error && <Text style={styles.errorDetail}>{error}</Text>}
          <Text style={styles.helpText}>
            Make sure:{'\n'}
            • Backend is running{'\n'}
            • Devices are on same Wi-Fi{'\n'}
            • IP address is correct in app.json{'\n'}
            • CORS is configured in backend
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#f5f5f5',
    borderRadius: 10,
    margin: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  url: {
    fontSize: 12,
    color: '#666',
    marginBottom: 15,
    fontFamily: 'monospace',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15,
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: 'white',
    fontWeight: '600',
  },
  successContainer: {
    backgroundColor: '#d4edda',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#c3e6cb',
  },
  successText: {
    color: '#155724',
    fontWeight: '600',
    marginBottom: 10,
  },
  responseText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#155724',
  },
  errorContainer: {
    backgroundColor: '#f8d7da',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#f5c6cb',
  },
  errorText: {
    color: '#721c24',
    fontWeight: '600',
    marginBottom: 10,
  },
  errorDetail: {
    color: '#721c24',
    fontSize: 12,
    marginBottom: 10,
    fontFamily: 'monospace',
  },
  helpText: {
    color: '#721c24',
    fontSize: 11,
    marginTop: 10,
  },
});

