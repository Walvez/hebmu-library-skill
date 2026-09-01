# hebmu-library-skill（河北医科大学图书馆文献检索与下载）

更适配河北医科大学宝宝体质的文献获取 skill。从 [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills)（MIT）的自用改造起步,如今已经长成了独立项目:以学校 WebVPN 为底座,把「检索 → 下载 → 入 Zotero」整条链路固化成文档,Agent 照着走就行。

> 本项目仅用于已授权的机构访问（校园 WebVPN / 图书馆订阅 / 个人账号），请遵守各数据库的使用条款，文献仅供个人科研学习使用。

---

这个 skill 是我在跑 Meta 分析筛文献的过程中被逼出来的。学校进数据库要先登 WebVPN、再进图书馆、再进各个库,每家的下载按钮藏得都不一样,Agent 极易在中间迷路;中文文献经常 PubMed 上连 DOI 都没有,验证码还一篇一张。于是我把每一座踩通的桥都写进了路线书(`references/hebmu-webvpn-route.md`,§1–§11),所有步骤均在本机实测通过。目前只在 **macOS + ego 浏览器**环境下开发和测试;建议在学校统一身份认证处保存好学号密码,配合浏览器自动填充可以省去手动输入。

## 能力一览

| 模块 | 能力 | 说明 |
|---|---|---|
| **文献检索** | CNKI 工作流 | 关键词/高级检索、结果解析、翻页、文献详情、期刊收录/过刊目录、引文导出(沿用上游能力) |
| | 万方医学网 | 隧道内检索,按 id 匹配下载链接,标题归一化全等匹配 |
| | yiigle 定位 | DOI→LinkIn→cmaid 桥、期刊官网过刊目录(`CN441530<年><期>` 规律)、万方短特征词三路兜底 |
| **全文下载** | 万方三通道 | MedFulltext / CMAJump / DegreePaper(学位论文 PDF 直取) |
| | yiigle API 链 | `downloadPdfToken → resource/auth → downloadPdf`,验证码存图人读、批量协同 |
| | sci-hub 批量 | CDP `Fetch` 拦截二进制流,`%PDF` 校验,`serverFetch` 损毁二进制的教训也写在书里 |
| **文献传递** | FMRS 全文请求 | 140 字符规范化头部严格匹配提交,防错配 |
| | 邮箱收割 | 到货邮件单页 DOM 取附件直链,文件名自带 PMID,零成本映射回筛选清单 |
| **Zotero 导入** | 本地 API 写入 | 条目创建、附件 `If-None-Match → uploadKey → local/uploads` 注册,分页幂等去重(按 `筛选清单No`) |

## 前置要求

- 支持 SKILL.md 的 Agent(Codex / Claude Code 等)
- macOS + [ego lite](https://lite.ego.app/zh-cn) 浏览器(本项目的开发与实测环境)
- 学校 WebVPN 账号(下载走机构订阅,需自行登录授权)
- [Zotero](https://www.zotero.org/) 桌面端(可选,用于导入;本地 API 默认开启)
- Python 3(可选,用于 Zotero 导入脚本)

## 安装方法

把仓库地址丢给 Agent,说一句:

```text
帮我安装这个 skill:https://github.com/Walvez/hebmu-library-skill
```

Agent 会把它克隆到 `~/.codex/skills/hebmu-library` 并完成挂载,装完重启 Agent 即可加载。可以拿一篇学校有订阅的中文文献验证:「从万方下载《文献名》并导入 Zotero」。

浏览器依赖的 ego lite 也可以单独添加:

```bash
npx skills add citrolabs/ego-lite
```

---

## 🍎 环境与实测平台

- **实测环境**:macOS + ego lite([GitHub](https://github.com/citrolabs/ego-lite) · [官网](https://lite.ego.app/zh-cn))。路线书里的选择器、接口和流程均在该环境真机验证。
- **推荐(自用推荐,非广告)**:Mac 上的 Agent 用户可以试试 ego lite。它让 Agent 在独立的 Space 中复用你已登录的浏览器状态——WebVPN 登录一次即可;遇到验证码、滑块或 FMRS 邮箱验证时控制权交还给你手动处理,完成后 Agent 继续执行。与本项目无任何利益关联,纯粹是自己天天在用的体验分享。
- **平台支持**:ego lite 目前官方提供 macOS 版本(Apple Silicon / Intel);Windows 与 Linux 在其官方 roadmap 中,暂未发布。Windows 平台的用户请等待后续适配或自行测试。

## 文件结构

```
SKILL.md                            # 技能入口与工作流路由
agents/openai.yaml                  # agent 元信息
references/
├── hebmu-webvpn-route.md           # 河北医科大学 WebVPN 路线书(核心原创,§1–§11)
├── cnki-workflows.md               # CNKI 工作流摘要
├── original-cnki-skills.md         # 上游项目改编说明与致谢
└── upstream/                       # 上游任务参考(原样保留)
    ├── cnki-search.md              # 关键词检索
    ├── cnki-advanced-search.md     # 高级检索
    ├── cnki-parse-results.md       # 解析结果页
    ├── cnki-navigate-pages.md      # 翻页与排序
    ├── cnki-paper-detail.md        # 论文详情提取
    ├── cnki-journal-search.md      # 期刊查找
    ├── cnki-journal-index.md       # 收录情况与影响因子
    ├── cnki-journal-toc.md         # 期刊目录浏览
    ├── cnki-download.md            # PDF/CAJ 下载
    └── cnki-export.md              # 引文导出
scripts/
├── zotero_local_api.py             # Zotero 本地 API 导入器(分页幂等,原创)
└── push_to_zotero.py               # Zotero 推送脚本(上游保留)
```

## 致谢

- [cookjohn/cnki-skills](https://github.com/cookjohn/cnki-skills) — 上游 CNKI 技能集,`references/upstream/` 原样保留其任务参考文档。

## License

[MIT](LICENSE)
