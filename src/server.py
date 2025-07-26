import socket
import json
import sqlite3
import numpy as np
import faiss
import struct
import threading
from table_define import FACT_EVENT_TABLE, SIMPLE_FACT_EVENT_TABLE

class VectorDBServer:
    def __init__(self, host='0.0.0.0', port=12345, db_file='events.db', index_file='faiss_index.index', dim=128):
        self.host = host
        self.port = port
        self.dim = dim
        self.lock = threading.Lock()  # 确保线程安全
        
        # 初始化Faiss索引
        try:
            self.index = faiss.read_index(index_file)
            print(f"Loaded existing Faiss index with {self.index.ntotal} vectors")
        except:
            self.index = faiss.IndexFlatL2(dim)
            faiss.write_index(self.index, index_file)
            print("Created new Faiss index")
        
        # 初始化SQLite数据库
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute(SIMPLE_FACT_EVENT_TABLE)
        self.conn.commit()
    
    def _receive_data(self, sock):
        # 接收数据长度头 (4字节)
        raw_len = sock.recv(4)
        if not raw_len:
            return None
        data_len = struct.unpack('>I', raw_len)[0]
        
        # 接收完整数据
        chunks = []
        bytes_received = 0
        while bytes_received < data_len:
            chunk = sock.recv(min(data_len - bytes_received, 4096))
            if not chunk:
                break
            chunks.append(chunk)
            bytes_received += len(chunk)
        
        return b''.join(chunks)
    
    def _store_data(self, vector, metadata):
        vector = np.array(vector, dtype=np.float32).reshape(1, -1)
        
        with self.lock:
            # 存储到Faiss
            self.index.add(vector)
            vector_id = self.index.ntotal - 1  # 获取最后插入的ID
            
            # 存储到SQLite
            try:
                self.cursor.execute("INSERT INTO events (vector_id, data) VALUES (?, ?)",
                                   (vector_id, json.dumps(metadata)))
                self.conn.commit()
            except sqlite3.IntegrityError:
                # 处理可能的ID冲突
                self.cursor.execute("REPLACE INTO events (vector_id, data) VALUES (?, ?)",
                                   (vector_id, json.dumps(metadata)))
                self.conn.commit()
        
        return vector_id
    
    def _query_data(self, query_vector, k=5):
        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        
        with self.lock:
            # Faiss搜索
            distances, indices = self.index.search(query_vector, k)
            
            # 获取元数据
            results = []
            for i in range(len(indices[0])):
                vector_id = int(indices[0][i])
                distance = float(distances[0][i])
                
                # 无效结果处理
                if vector_id < 0:
                    continue
                
                # 从SQLite获取元数据
                self.cursor.execute("SELECT data FROM event WHERE vector_id = ?", (vector_id,))
                row = self.cursor.fetchone()
                metadata = json.loads(row[0]) if row else {}
                
                results.append({
                    "vector_id": vector_id,
                    "distance": distance,
                    "metadata": metadata
                })
        
        return results
    
    def _handle_request(self, payload):
        action = payload.get("action", "insert")
        
        if action == "insert":
            vector = payload["vector"]
            metadata = payload["metadata"]
            vector_id = self._store_data(vector, metadata)
            return {"status": "success", "vector_id": vector_id}
        
        elif action == "query":
            query_vector = payload["vector"]
            k = min(payload.get("k", 5), 100)  # 限制最大返回数量
            results = self._query_data(query_vector, k)
            return {"status": "success", "results": results}
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"Server listening on {self.host}:{self.port}")
            
            while True:
                conn, addr = s.accept()
                print(f"Connection from {addr}")
                try:
                    # 接收并解析数据
                    data = self._receive_data(conn)
                    if not data:
                        continue
                    
                    payload = json.loads(data.decode('utf-8'))
                    
                    # 处理请求
                    response = self._handle_request(payload)
                    
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
                    import traceback
                    traceback.print_exc()
                
                # 发送响应
                conn.sendall(json.dumps(response).encode('utf-8'))
                conn.close()

if __name__ == "__main__":
    server = VectorDBServer()
    server.start()