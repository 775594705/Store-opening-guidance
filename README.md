# 开店指导模拟预测软件

这是“开店选址可行性评估 + 经营策略模拟 + 多智能体市场推演”的项目工作区。当前已经跑通 MVP 主闭环：输入候选位置和品类，后端调用高德采集周边 POI，计算基础评分，并在前端展示报告。

## 当前已完成

- 后端 FastAPI 项目结构。
- Python 3.12 虚拟环境：`backend/.venv`。
- 高德地理编码和周边 POI 搜索。
- POI 分类、去重、汇总和 QPS 限速重试。
- `/api/health` 健康检查接口。
- `/api/pois/search` POI 预览接口。
- `/api/analysis` 自动采集 POI 并生成评分报告。
- `/api/map/geocode` 地址定位接口和 `/api/map/static` 静态地图代理接口。
- 前端 Vite 单页应用，已接入后端真实分析接口、真实 POI 候选搜索、可拖拽缩放的地图精确选点和自定义品类输入。
- 报告页周边摘要卡片可点击，能查看对应分类 POI 明细作为参考。
- 前端已完成黏土拟态视觉升级：输入面板、地图选点、报告卡片和 POI 明细表使用柔和圆角、低对比配色、内外阴影和卡通化立体按钮。
- 阶段3基础评估模型：评分权重和等级阈值已配置化，报告新增 IRS 零售饱和指数、哈夫模型雏形、保守校准和数据置信度；竞品密集区域会触发总分封顶，避免评分虚高。
- 第2周低保真交付物：简短 PRD、页面流程图、可点击静态 HTML 原型。

## 目录结构

```text
.
├── backend/              # FastAPI 后端：数据采集、评分、报告生成
├── frontend/             # Web 前端：地址输入、品类选择、报告展示
├── docs/                 # PRD、接口文档、数据字典、开发日志
├── prototypes/           # 低保真和交互原型
├── experiments/mirofish/ # MiroFish 独立实验区
├── scripts/              # 环境检查和辅助脚本
├── .env.example          # 环境变量示例
└── README.md
```

## 启动后端

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

## 启动前端

```powershell
cd frontend
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests

cd ..\frontend
npm run build
```

## 直接打开完整功能页面

```text
open-app.html
```

双击该文件会进入真实前端页面，不需要启动 Vite 前端服务；生成报告、地图搜索和 POI 分析仍需要先启动本地后端 `http://127.0.0.1:8000`。

## 第2周低保真原型

```text
http://127.0.0.1:5812/week2_low_fidelity.html
```

对应文档：

- `docs/05_week2_low_fidelity_prd.md`
- `docs/06_week2_page_flow.md`
- `prototypes/week2_low_fidelity.html`

## 下一步

1. 增加地址解析结果确认。
2. 把 POI 分类字段从英文值改成中文展示。
3. 扩充不同品类的竞品关键词和评分权重。
4. 增加报告保存和历史记录。
