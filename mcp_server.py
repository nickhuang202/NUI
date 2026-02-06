# MCP Server Implementation for NUI Testing and Report Analysis

class MCPServer:
    def __init__(self):
        """Initializes the MCP server"""
        self.data = []

    def receive_data(self, data):
        """Receives data for processing"""
        self.data.append(data)

    def analyze_data(self):
        """Analyze received data and generate report"""
        # Dummy analysis; replace with actual logic
        report = {
            'total_received': len(self.data),
            'data_samples': self.data,
        }
        return report

    def clear_data(self):
        """Clears the received data"""
        self.data = []

if __name__ == '__main__':
    server = MCPServer()
    # Example usage
    server.receive_data({'sample_1': 'data'})
    report = server.analyze_data()
    print(report)