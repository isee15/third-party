import http.server
import socketserver
import socket
import base64
import urllib.request
import urllib.error
import select

# 配置代理端口和认证信息
PROXY_PORT = 3128
USERNAME = "proxyuser"
PASSWORD = "123456"

# 代理请求处理类
class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_CONNECT(self):
        """处理 HTTPS 请求（建立隧道 CONNECT）"""
        if not self.authenticate():
            return

        try:
            host, port = self.path.split(":")
            port = int(port)
            # 连接目标服务器
            with socket.create_connection((host, port)) as remote:
                # 告诉客户端连接已建立
                self.send_response(200, "Connection Established")
                self.end_headers()

                # 建立 socket 隧道转发
                self._tunnel(self.connection, remote)
        except Exception as e:
            self.send_error(502, f"Tunnel error: {e}")

    def _tunnel(self, client_sock, remote_sock):
        """转发客户端和远程服务器之间的加密数据"""
        sockets = [client_sock, remote_sock]
        while True:
            r, _, _ = select.select(sockets, [], [])
            for s in r:
                other = remote_sock if s is client_sock else client_sock
                data = s.recv(8192)
                if not data:
                    return
                other.sendall(data)

    def do_GET(self): self.forward_request()
    def do_POST(self): self.forward_request()
    def do_PUT(self): self.forward_request()
    def do_DELETE(self): self.forward_request()
    def do_HEAD(self): self.forward_request()
    def do_OPTIONS(self): self.forward_request()

    def forward_request(self):
        """处理 HTTP 请求，转发到目标服务器"""
        if not self.authenticate():
            return

        try:
            url = self.path
            # 如果是相对路径，拼接成完整 URL
            if not url.startswith("http"):
                url = f"http://{self.headers['Host']}{self.path}"

            # 读取请求体
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else None

            # 转发的请求头，去掉代理认证
            headers = dict(self.headers)
            headers.pop("Proxy-Authorization", None)
            headers.pop("Host", None)

            # 创建并发送请求
            req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
            with urllib.request.urlopen(req) as resp:
                # 返回响应给客户端
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.read())

        except urllib.error.HTTPError as e:
            self.send_error(e.code, e.reason)
        except Exception as e:
            self.send_error(500, f"Proxy error: {e}")

    def authenticate(self):
        """检查客户端的 Proxy-Authorization 头部"""
        auth = self.headers.get("Proxy-Authorization")
        if not auth or not self._check_auth(auth):
            self.send_response(407)  # 407 Proxy Authentication Required
            self.send_header('Proxy-Authenticate', 'Basic realm="SimplePythonProxy"')
            self.end_headers()
            return False
        return True

    def _check_auth(self, header):
        """验证用户名和密码"""
        try:
            method, encoded = header.split()
            decoded = base64.b64decode(encoded).decode()
            user, pwd = decoded.split(":", 1)
            return user == USERNAME and pwd == PASSWORD
        except:
            return False

# 启动代理服务器
if __name__ == "__main__":
    print(f"🚀 启动代理服务器，端口 {PROXY_PORT}，用户名 {USERNAME}")
    with socketserver.ThreadingTCPServer(("", PROXY_PORT), ProxyHTTPRequestHandler) as httpd:
        httpd.serve_forever()
