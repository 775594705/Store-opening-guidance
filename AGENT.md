# AGENT.md

## 项目定位

这是一个“开店指导模拟预测软件”MVP。当前目标是帮助用户输入候选位置、开店品类、租金/预算等信息后，基于高德地图 POI 数据和可解释规则模型生成选址报告。

## 当前功能

- 后端：FastAPI，提供健康检查、地图搜索、静态地图代理、POI 采集、选址分析接口。
- 前端：单页 HTML 应用，支持详细地点搜索、真实 POI 候选、静态地图点选、品类自由输入、报告展示、周边 POI 明细点击查看。
- 评分：`stage3_rules_v2_conservative`，包含六项分项评分、IRS 零售饱和指数、哈夫模型雏形、保守校准和数据置信度。
- 入口：`open-app.html` 可双击进入完整功能页面，但生成报告仍需要本地后端 `http://127.0.0.1:8000` 正在运行。

## 目录说明

```text
backend/              FastAPI 后端
frontend/             前端页面和样式
docs/                 PRD、接口文档、数据字典、开发日志
docs/source/          原始项目书和详细实施计划 Word 文档
prototypes/           第2周低保真原型
experiments/mirofish/ 实验区
scripts/              环境检查和文档生成脚本
packages/             本地 zip 打包产物，已被 Git 忽略
open-app.html         可双击打开的完整功能入口
```

## 本地运行

后端：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

前端开发模式：

```powershell
cd frontend
npm run dev
```

无需前端开发服务时：

```text
双击 open-app.html
```

## 验证命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

```powershell
cd frontend
npm run build
```

## 敏感信息

- `.env` 是本地私密配置，不允许提交。
- 高德 API Key 只放在 `.env`，不要写入前端、文档、测试或压缩包。
- `.env.example` 只能保留占位符。

## 打包方式

从 Git 当前提交生成源码包：

```powershell
git archive --format=zip --output packages\Store-opening-guidance-project-snapshot.zip HEAD
```

打包后检查：

```powershell
tar -tf packages\Store-opening-guidance-project-snapshot.zip
```

确认不包含 `.env`、`.venv`、`node_modules`、`dist`、日志和真实 API Key。

## 线上部署

- 目标域名：`guidance.csgozbt.com`
- 生产前端通过同源 `/api` 调用后端。
- 本地双击 `open-app.html` 时仍调用 `http://127.0.0.1:8000`。
- 部署脚本和模板位于 `deploy/`。
- `deploy/deploy_server.sh` 需要服务器环境变量 `AMAP_API_KEY`，不要把真实 Key 写入仓库。

## 开发注意

- 改前端后运行 `npm run build`。
- 改后端后运行 `python -m unittest discover -s tests`。
- 评分权重和阈值集中在 `backend/app/config/scoring_rules.json`，不要把权重写死在代码里。
- 地图和 POI 能力经后端代理调用，高德 Key 不进入浏览器代码。
- `frontend/index.html` 的 CSS 路径必须保持相对路径 `./src/styles.css`，这样 `open-app.html` 跳转后可以直接打开使用。
- 后端 CORS 允许 `null` origin，用于支持本地双击 HTML 页面访问 API。

## 下一步建议

- 增加历史记录保存。
- 扩充不同品类的竞品关键词。
- 增加报告导出图片或 PDF。
- 让哈夫模型使用竞品距离分布，而不是仅用竞品数量近似。
