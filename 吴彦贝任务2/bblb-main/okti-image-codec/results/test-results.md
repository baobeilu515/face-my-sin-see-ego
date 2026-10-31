# 测试与压缩结果

运行日期：2026-10-29（Asia/Shanghai）  
运行时：Python 3.14.10 Windows 64-bit embeddable runtime，解压在临时 `work/` 目录，未安装到系统。

## 测试结果

- `py_compile`：`main.py`、`okti_codec.py`、`test_okti_codec.py` 均编译通过。
- 自动化测试：7 项通过，0 项失败。覆盖 OKTI 四类编码及大小写变体、首像素黑色基准、错误头/尺寸/像素类型与行号、跨行及超过 255 长度的运行、样例编码解码回环、P6 PPM 二进制空白字节、无换行 token 输入。
- 七个 PPM 样例均通过实际 Python CLI 编码。生成 token 类型与样例设计一致；体积数据见下表。
- 上传用的 7 个 ASCII P3 测试夹具逐个与 ZIP 原始 P6 文件比较，宽、高和全部 RGB 像素均完全相同。
- 端到端 CLI 回环：`runs_and_short_indices_small.ppm` 编码为 OKTI 后再解码为 PPM，源文件与解码文件 SHA-256 相同：`B8E2F1D39751C7B722100454331EF2D565AFE597B077246C0F782E35AA1688E5`。
- CLI 异常检查：多余参数、缺失输入文件、未知 token 均以退出码 1 结束；未知 token 报告 `line 3: '?'`。
- GUI 预览未能验证：便携测试运行时没有 Tkinter 模块，程序如实打印 `Image display unavailable: No module named 'tkinter'`，但编码/解码及文件写入成功。

## 样例体积记录

字节数包含完整 PPM/OKTI 文件（含文件头和换行），输入数值为 ZIP 原始 P6 样例；上传的 `tests/data/` 保存相同像素的 P3 文本副本。`缩减量 = PPM 字节数 - OKTI 字节数`；负数表示编码后文件变大。百分比以输入 PPM 文件为分母。

| 输入 | PPM | OKTI | 缩减量 | token 类型 |
|---|---:|---:|---:|---|
| `tiny.ppm` | 23 B | 41 B | -18 B (-78.26%) | `p` |
| `pixels_small.ppm` | 754 B | 1,987 B | -1,233 B (-163.53%) | `p` |
| `differences_small.ppm` | 373 B | 641 B | -268 B (-71.85%) | `p`, `d` |
| `runs_short_small.ppm` | 396 B | 323 B | 73 B (18.43%) | `p`, `r` |
| `runs_long_small.ppm` | 3,085 B | 363 B | 2,722 B (88.23%) | `p`, `R` |
| `smallindices_small.ppm` | 781 B | 859 B | -78 B (-9.99%) | `p`, `r`, `i` |
| `runs_and_short_indices_small.ppm` | 396 B | 201 B | 195 B (49.24%) | `p`, `r`, `i` |

这些结果来自实际 Python 命令运行。压缩包只提供 PPM/PNG 输入，没有对应的 `.okti` 参考文件；因此没有声称与官方压缩文件逐字节比较。`tiny.ppm` 的 OKTI 输出另按说明中的四像素示例精确断言，并通过测试。
