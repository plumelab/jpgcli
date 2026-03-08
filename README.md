# jpgcli

`jpgcli` 是一个面向组会、周报和阶段汇报的科研风格图表 CLI。给它一份 `CSV / Excel` 数据和一句自然语言提示词，它会自动生成适合放进 PPT 的图表图片。


## 环境与依赖

- Python `3.10+`
- 需要可用的模型接口（`OPENAI_API_KEY`，可选 `OPENAI_BASE_URL`）
- 运行依赖：`matplotlib`、`openai`、`openpyxl`、`pandas`、`pydantic`、`python-dotenv`、`seaborn`、`typer`
- 测试依赖：`pytest`

推荐安装方式：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

如需测试：

```bash
python3 -m pip install -e '.[dev]'
```

## 使用方法

首次使用先初始化：

```bash
jpgcli init
```

日常最推荐直接交互式生成：

```bash
jpgcli chart
```

程序会让你选择数据文件并输入提示词，然后自动生成图片到输出目录。

也可以直接命令行传参：

```bash
jpgcli chart data.csv --prompt "自选角度生成一张组会使用的图片"
```

如果是 Excel：

```bash
jpgcli chart experiment.xlsx --sheet Sheet1 --prompt "比较不同实验组结果，生成适合组会展示的科研风格图"
```

# 示例

提示词：

自选角度生成一张组会使用的图片，注意标题尽可能简洁

生成结果：

output/examples_20260308_204701.png
