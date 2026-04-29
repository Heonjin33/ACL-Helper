# ACL-helper

ACL-helper 是一个康复辅助评估 Web 应用。前端使用 Vue 3、Vite、TypeScript 和 MediaPipe Pose 在浏览器端分析“深蹲”和“走路”动作；后端 FastAPI 只接收结构化评估指标，使用 DeepSeek Chat 生成康复辅助报告并导出 PDF。

> 本项目仅用于康复训练辅助评估，不作为正式医学诊断结果。

## 项目演示
上传录制好的深蹲或走路的一段视频，或者选择开启摄像头实时检测。
![alt text](https://ai-code-generator33-1407333245.cos.ap-beijing.myqcloud.com/screenshots/2026/03/01/Snipaste_2026-04-29_15-39-32.png)

检测完毕后，能够生成一份检测报告。对目前康复状况进行打分并规划接下来的康复计划。
![alt text](https://ai-code-generator33-1407333245.cos.ap-beijing.myqcloud.com/screenshots/2026/03/01/Snipaste_2026-04-29_15-41-20.png)

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
