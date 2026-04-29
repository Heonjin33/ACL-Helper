# ACL-helper

ACL-helper 是一个康复辅助评估 Web 应用。前端使用 Vue 3、Vite、TypeScript 和 MediaPipe Pose 在浏览器端分析“深蹲”和“走路”动作；后端 FastAPI 只接收结构化评估指标，使用 DeepSeek Chat 生成康复辅助报告并导出 PDF。

> 本项目仅用于康复训练辅助评估，不作为正式医学诊断结果。

## 隐私边界

- 原始视频、摄像头画面、图片帧不上传服务器。
- MediaPipe Pose 运行在浏览器端。
- 后端只接收动作类型、关节角度统计、左右对称性、稳定性、次数和初步评分等结构化数据。
- 训练历史优先保存在浏览器 localStorage。
- SQLite 只保存必要摘要和报告内容。

## 启动

```bash
cd frontend
npm install
npm run dev
```

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

在 `backend/.env` 中配置 `DEEPSEEK_API_KEY` 后会调用 DeepSeek；未配置时后端会用本地规则生成可测试报告。
