# Backend

后端负责地图数据采集、评分计算、报告生成。建议使用 FastAPI。

## 当前环境

- 本机已确认 Python 3.12.0 可用：`C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`
- 已创建独立虚拟环境：`backend/.venv`
- 已安装 `requirements.txt` 中的依赖

## 启动方式

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

当前电脑的全局 `python` 仍指向 Python 3.13 alpha。开发后端时请使用 `.venv`，不要直接使用全局 Python。

## 验证命令

```powershell
cd backend
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 真实 POI 冒烟测试

确保工作区根目录存在本地 `.env`，且已配置 `AMAP_API_KEY`。然后运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.post('/api/pois/search', json={'city':'广州','address':'天河区体育西路','category':'奶茶店','radius_meters':1000,'pages':1}); print(r.status_code); print(r.json().get('summary'))"
```

注意：高德接口有 QPS 限制。当前代码已加入轻量限速和 `10021` 重试。
