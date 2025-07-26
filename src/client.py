import socket
import json
import struct
import numpy as np

class VectorDBClient:
    def __init__(self, host, port=12345):
        self.host = host
        self.port = port
    
    def _send_request(self, payload):
        data = json.dumps(payload).encode('utf-8')
        data_len = struct.pack('>I', len(data))
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(data_len + data)
            response = s.recv(65536)  # 增大缓冲区以容纳查询结果
            return json.loads(response.decode('utf-8'))
    
    def insert_data(self, vector, metadata):
        """插入向量数据和元数据"""
        payload = {
            "action": "insert",
            "vector": vector,
            "metadata": metadata
        }
        return self._send_request(payload)
    
    def query_data(self, query_vector, k=5):
        """查询相似向量"""
        payload = {
            "action": "query",
            "vector": query_vector,
            "k": k
        }
        return self._send_request(payload)

# 示例用法
if __name__ == "__main__":
    # 替换为目标设备的局域网IP
    SERVER_IP = "10.42.0.1"  
    
    client = VectorDBClient(SERVER_IP)
    
    # 示例1: 插入数据
    print("Inserting sample data...")
    sample_vector = np.random.rand(128).astype(np.float32).tolist()
    sample_metadata = {
        "item_id": "product_001",
        "name": "Wireless Headphones",
        "category": "Electronics",
        "price": 99.99,
        "tags": ["audio", "wireless", "bluetooth"]
    }
    
    insert_response = client.insert_data(sample_vector, sample_metadata)
    print("Insert response:", insert_response)
    
    # 示例2: 查询相似向量
    print("\nQuerying similar vectors...")
    # 创建与样本相似的查询向量（添加少量噪声）
    query_vec = [x + np.random.normal(0, 0.01) for x in sample_vector]
    
    query_response = client.query_data(query_vec, k=3)
    if query_response["status"] == "success":
        print("Top results:")
        for i, result in enumerate(query_response["results"]):
            print(f"Result {i+1}:")
            print(f"  Vector ID: {result['vector_id']}")
            print(f"  Distance: {result['distance']:.6f}")
            print(f"  Metadata: {json.dumps(result['metadata'], indent=2)}")
    else:
        print("Query failed:", query_response["message"])