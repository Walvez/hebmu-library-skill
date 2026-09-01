# hebmu-library-skill · 河北医科大学图书馆文献检索与下载 Skill

一个面向 Codex / OpenCodex 的浏览器自动化 skill:以河北医科大学 WebVPN 隧道为底座,覆盖**文献检索**(CNKI / 万方医学网 / 中华医学期刊全文数据库 yiigle / FMRS)→ **全文下载**(MedFulltext / CMAJump / yiigle API 链 / 验证码协同 / sci-hub 批量)→ **Zotero 导入**(本地 API + PDF 附件幂等上传)的完整「图书馆文献获取打法」。

> 改编自 [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills)(MIT)并大幅扩展:upstream CNKI 参考文档保留在 `references/upstream/`,改编说明见 `references/original-cnki-skills.md`。核心原创内容为 `references/hebmu-webvpn-route.md` 路线书与 `scripts/zotero_local_api.py`。

## 能力一览

- **文献检索**:CNKI 关键词/高级检索、结果解析、翻页、文献详情、期刊索引/过刊目录;万方医学网检索;yiigle DOI→`LinkIn.do`→cmaid 桥接与期刊官网过刊定位
- **全文下载**:万方 MedFulltext / CMAJump / DegreePaper(学位论文 PDF 直取);yiigle `downloadPdfToken → resource/auth → downloadPdf` API 链 + 验证码人机协同循环;sci-hub CDP `Fetch` 拦截二进制批量抓取
- **FMRS 文献传递**:严格标题匹配(140 字符规范化头部)提交全文请求 + 邮箱到货收割(附件文件名自带 PMID,零成本映射)
- **Zotero 本地 API 写入**:条目创建、附件 `If-None-Match` → `uploadKey` → `local/uploads` 上传注册,分页幂等去重(按 `筛选清单No`)

## 安装(Codex)

```bash
git clone https://github.com/Walvez/hebmu-library-skill ~/.codex/skills/hebmu-library
```

对河北医科大学用户,任何检索/下载任务先读 `references/hebmu-webvpn-route.md`(§1–§11 路线书)。中文论文通道优先级:**万方 MedFulltext → CMAJump → yiigle API 链**;标题匹配一律用规范化后精确相等,禁止模糊相似。

## 文件结构

```
SKILL.md                      # skill 入口与工作流路由(id: hebmu-library)
references/
  hebmu-webvpn-route.md       # 河北医科大学 WebVPN 路线书(核心原创,§1–§11)
  cnki-workflows.md           # CNKI 工作流摘要
  original-cnki-skills.md     # 上游改编说明与致谢
  upstream/                   # 上游 Claude Code 版参考文档(MIT)
scripts/
  zotero_local_api.py         # Zotero 本地 API v2 导入器(分页幂等)
  push_to_zotero.py           # 上游 Zotero 推送脚本
agents/openai.yaml
```

## 免责声明

本 skill 仅用于**已合法获得数据库访问权限**的用户(校园网 / 机构订阅 / 个人账号),自动化操作请遵守各数据库服务条款与下载频率限制,勿用于批量牟利或转售。验证码、滑块等风控环节请由账号本人手动完成。

## License

MIT(见 [LICENSE](LICENSE))。`references/upstream/` 内文档沿用上游 [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills) 的 MIT 许可与署名。
