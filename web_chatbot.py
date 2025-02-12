from fastapi import FastAPI, UploadFile, File, Form
import subprocess
import os

app = FastAPI()

# 存储所有 Web API 的端口映射
services = {
    "load": 8000,       # 对应 GUI_load.py
    "work": 8004,       # 对应 GUI_work.py
    "training": 8003,   # 对应 GUI_training.py
    "testing": 8002     # 对应 GUI_testing.py
}

def start_service(script_name, port):
    """启动 Web API 服务"""
    try:
        subprocess.Popen(["python3", script_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"message": f"{script_name} started on port {port}"}
    except Exception as e:
        return {"error": f"Failed to start {script_name}: {str(e)}"}

@app.post("/start_all/")
def start_all_services():
    """启动所有 Web 服务"""
    responses = {}
    responses["load"] = start_service("web_load.py", services["load"])
    responses["work"] = start_service("web_work.py", services["work"])
    responses["training"] = start_service("web_training.py", services["training"])
    responses["testing"] = start_service("web_testing.py", services["testing"])
    return responses

@app.get("/status/")
def get_services_status():
    """检查所有 Web 服务的状态"""
    status = {}
    for service, port in services.items():
        status[service] = f"http://localhost:{port}/docs"
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
