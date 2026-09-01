# hebmu-cnki-skills · 河北医科大学图书馆论文下载 Skill

一个面向 Codex / OpenCodex 的浏览器自动化 skill:把 **CNKI 检索工作流** 与 **河北医科大学 WebVPN 隧道下载管线**(知网 / 万方医学网 / 中华医学期刊全文数据库 yiigle)整合成一套可复用的「图书馆论文下载打法」,并内置 **Zotero 本地 API 导入**(含 PDF 附件上传)。

> 适配 [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills)(MIT)的 Codex 版本,在其能力之上扩展了河北医科大学校园图书馆的完整下载路线书。upstream 参考文档保留在 `references/upstream/` 并在 `references/original-cnki-skills.md` 记录了改编说明。

## 能力一览

- **CNKI 全工作流**:关键词/高级检索、结果解析、翻页、文献详情、期刊索引/目录、PDF/CAJ 下载触发、引文导出
- **万方医学网隧道通道**:检索 → 按 id 匹配下载链接 → MedFulltext / CMAJump / DegreePaper(学位论文 PDF 直取)
- **yiigle(中华医学期刊全文数据库)API 链**:`downloadPdfToken → resource/auth → downloadPdf`,含验证码人机协同循环、DOI→`LinkIn.do`→cmaid 桥接、期刊过刊目录定位
- **FMRS 文献传递**:严格标题匹配的全文请求提交流程(140 字符规范化头部匹配,防错配)
- **Zotero 本地 API 写入**:条目创建、附件 `If-None-Match` → `uploadKey` → `local/uploads` 上传注册,幂等去重(按 `筛选清单No`)
- **sci-hub 批量抓取**:CDP `Fetch` 拦截二进制流,`%PDF` 校验

## 安装(Codex)

```bash
git clone https://github.com/Walvez/hebmu-cnki-skills ~/.codex/skills/cnki-skills
```

对河北医科大学用户,任何下载任务先读 `references/hebmu-webvpn-route.md`(§1–§9 路线书)。中文论文通道优先级:**万方 MedFulltext → CMAJump → yiigle API 链**;标题匹配一律用规范化后精确相等,禁止模糊相似。

## 文件结构

```
SKILL.md                      # skill 入口与工作流路由
references/
  hebmu-webvpn-route.md       # 河北医科大学 WebVPN 路线书(核心原创,§1–§9)
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
