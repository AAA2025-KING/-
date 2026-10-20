# Windows 桌面演示打包与分发说明

面向：**把 Gradio 演示发给同事试用**（一键启动），而不是打成内含完整 8B 基座的超大安装包。

## 你发给别人什么 / 对方自己下什么

| 内容 | 是否打进 zip | 大约体积 | 说明 |
|------|--------------|----------|------|
| 代码（`src/` `apps/` `scripts/` …） | ✅ 是 | 很小 | MIT 项目代码 |
| 表格域 LoRA（`models/lora_tables/`） | ✅ 是 | ~80–90 MB | 实验适配器；可随代码分享 |
| 启动脚本（`Start-BrailleDemo.bat` 等） | ✅ 是 | 很小 | 双击启动 |
| 基座 **Vision-Braille-Qwen3-8B** | ❌ **不要**默认打进包 | 数 GB～约 16 GB | 见下方许可；对方用脚本或 HF 自下 |
| `.venv-qwen` | ❌ 一般不带 | 数 GB | 对方本机跑 `setup_demo_env.ps1` |

### 许可提醒（必读）

- 项目代码：见仓库根目录 `LICENSE`（MIT）。
- 基座模型 [Violet-yo/Vision-Braille-Qwen3-8B](https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B)：**CC BY-NC-SA 4.0**（偏**非商业**；再分发需署名且保持相同许可）。
- **不要**声称可以商业再分发该基座权重。分享 zip 时请写明：基座需接收方自行下载并遵守模型卡许可。
- LoRA 为在基座上微调的实验适配器，使用时仍依赖上述基座及其许可约束。

## 接收方需要什么硬件 / 软件

| 项目 | 建议 |
|------|------|
| 系统 | Windows 10/11，64 位 |
| GPU | NVIDIA，显存 **≥ 8 GB**（4-bit 推理；RTX 3060/4060/5060 等） |
| 磁盘 | 代码+LoRA ~0.2 GB；基座另需约 **10 GB+**；venv 另约数 GB |
| 软件 | Python **3.10+**；最新 NVIDIA 驱动；可访问 Hugging Face（或你提供的内网镜像） |

无 GPU 时界面仍可打开，但 `qwen8b` 会走脚手架字符串，不能当真机翻译。

## 你（发送方）怎么打包

在已训好 / 已放好 LoRA 的机器上（例如本机桌面项目）：

```powershell
cd C:\Users\LENOVO\Desktop\chinese-braille-toolkit
powershell -ExecutionPolicy Bypass -File scripts\windows\Pack-DemoZip.ps1 -MakeZip
```

产物：

- 文件夹：`dist\chinese-braille-demo\`
- 压缩包：`dist\chinese-braille-demo.zip`（**不含**基座权重）

把 zip 或文件夹通过网盘 / U 盘发给对方即可。包根目录另有 `Start-BrailleDemo.bat`（与 `scripts\windows\Start-BrailleDemo.bat` 相同入口，便于双击）。

可选：若内网同事完全不想装依赖，可加 `-IncludeVenv`（体积很大，且绑死 CUDA/Python 版本，一般不推荐）。

## 接收方一步步操作

1. **解压**到任意路径，例如 `D:\chinese-braille-demo\`（路径尽量短、避免中文空格问题更稳）。
2. **安装 Python 3.10+**（官网安装时勾选 *Add python.exe to PATH*）。
3. **装依赖（只需一次）**，在解压目录打开 PowerShell：

   ```powershell
   cd D:\chinese-braille-demo
   powershell -ExecutionPolicy Bypass -File scripts\windows\setup_demo_env.ps1
   ```

   若自检显示 `cuda False`，按脚本提示到 [pytorch.org](https://pytorch.org) 安装对应 GPU 版 PyTorch 后再跑一次本脚本。

4. **下载基座（只需一次，体积大）**：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\windows\Download-BaseModel.ps1
   ```

   或手动把模型放到 `models\Vision-Braille-Qwen3-8B\`。遵守 **CC BY-NC-SA**。

5. **启动演示**：双击包根目录或 `scripts\windows\Start-BrailleDemo.bat`。  
   浏览器打开 [http://127.0.0.1:7860/](http://127.0.0.1:7860/)（脚本会尝试自动打开）。  
   **关掉黑色命令行窗口即停止服务。** 首次加载模型可能要 1–3 分钟。

6. 在页面里选样例或粘贴盲文 → 点「翻译」。

### 常见问题

| 现象 | 处理 |
|------|------|
| 提示没有 `.venv-qwen` | 先跑 `setup_demo_env.ps1` |
| 翻译结果像脚手架 / 乱码说明 | 基座未下或 CUDA 不可用；检查 `models\Vision-Braille-Qwen3-8B` 与 `torch.cuda.is_available()` |
| 端口占用 | 设环境变量 `CBT_WEBUI_PORT=7861` 再启动 |
| 仅测界面、不加载 8B | 启动前设 `set CBT_QWEN_STUB=1` |

## 脚本一览

| 路径 | 作用 |
|------|------|
| `scripts/windows/Start-BrailleDemo.bat` | 一键启动 Gradio + 打开浏览器 |
| `scripts/windows/setup_demo_env.ps1` | 创建 `.venv-qwen` 并 `pip install -e ".[demo,qwen]"` |
| `scripts/windows/Download-BaseModel.ps1` | 从 HF 拉取基座到 `models/Vision-Braille-Qwen3-8B` |
| `scripts/windows/Pack-DemoZip.ps1` | 生成可分享目录/zip（排除基座） |
| `scripts/windows/inno_setup_outline.iss` | （可选）Inno Setup 安装包大纲，需本机安装 Inno |

## 可选：Inno Setup / NSIS

若需要「安装向导」体验，可用 `scripts/windows/inno_setup_outline.iss` 作模板：安装时只释放**代码+LoRA+脚本**，首次运行再提示下载基座。不要把数 GB 基座写进安装程序，除非你已确认许可且接受超大安装包。

## 与「完整单文件 exe」的差别

把 8B + CUDA 打进单文件 exe（如 PyInstaller）体积巨大、签名与驱动兼容麻烦，且易误导为可随意商用分发基座。本仓库推荐路径是：**启动器 + 安装脚本 + 接收方自备 GPU/基座**。
