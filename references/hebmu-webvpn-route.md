# 河北医科大学图书馆论文下载路线册（hebmu-webvpn-route）

> 2026-08-26 起固化、2026-08-31 大版本扩充。覆盖:知网、万方医学网、中华医学期刊全文
> 数据库(yiigle)、Zotero 本地 API 全链路。全部条目经 ego-browser 实测。
> 本机用户:河北医科大学;ego 浏览器继承其 WebVPN 登录态。

## 0. 通道总览与固定 URL

| 通道 | WebVPN 内 URL(哈希) | 用途 |
|---|---|---|
| 图书馆入口 | `webvpn.hebmu.edu.cn/https/77…fcfe43d22f356a5d6b468ca88d1b203b/` | 资源导航 |
| 中国知网 | `…77…e7e056d2243e635930068cb8/` | 中文期刊(有按钮才有全文) |
| 万方医学网 | `…77…fdf245d2303166567f068ea89941227b23fa41b38259/` | 中文主力通道 |
| yiigle(中华医学期刊全文库) | `…77…e2e40f852e396f5c7b468aa395/` | 中华系列(CMAJump 落点) |
| 万方全文服务器 f.med | `…77…ffe452d2303166567f068ea89941227b8b47969ef4a4/` | 学位论文 PDF 直取 |
| ScienceDirect | `…77…e7e056d234336155700b8ca891472636a6d29e640e/` | 机构认证 OK,**但 SPA 搜索页在代理下渲染失败** |

哈希规律:前缀 `77726476706e69737468656265737421` 固定,后段是目标主机名的加密,
同站不同子域哈希不同。未知主机哈希的获取法:**在图书馆资源导航里真实点击对应条目**
(见 §2),或从用户处要直链。

登录判定:任何库页面顶部显示 **"河北医科大学"** = 机构通道可用。WebVPN 登录页
`https://webvpn.hebmu.edu.cn/` → CAS 统一身份认证(浏览器已存密码,点
「CAS统一身份认证登录」→「登 录」即成,密码框 JS 读值为空是受保护假象,直接点登录)。

## 1. ego-browser 硬规则(全部踩过坑)

- **每个 heredoc 开头必须 `await useOrCreateTaskSpace(<id或name>)`**;接管用
  `takeOverTaskSpace('任务空间名')`(数字 id 会返回 undefined),用户确认后才能接管。
- ESM 环境:`const fs = await import('node:fs')`;`require` + 顶层 await 会炸。
- `js()` 返回的 JSON **已是对象**,不要再 `JSON.parse`(会抛 "[object Object]")。
- CDP 点击与网络监听(drainEvents)必须在**同一个 heredoc 会话**里做,跨会话捕获为空。
- 往生成的 JS 字符串里注值一律 `JSON.stringify()`;正则判等用
  `text.replace(/[\s\p{P}\p{S}]+/gu,'')` 归一化后比较。
- 下载落盘 `~/Downloads`;**文件没出现前不得报成功**。触发下载的按钮一律用
  真实鼠标 `await click([x,y])`,坐标来自 `getBoundingClientRect()` 中心。
- WebVPN 隧道只改写**页面上下文里的导航/请求**;`location.href = 外部直链` 会脱离
  隧道(落到家庭 IP/未登录)。同源 fetch(任意 webvpn 代理页 → 任意 webvpn 代理 URL,
  带 `credentials:'include'`)永远安全,跨目标主机也行 —— 隧道按路径哈希分流并注入
  各自 cookie 罐。
- 二进制落盘:页面内 fetch → ArrayBuffer → base64 → Node `Buffer` → `fs.writeFileSync`,
  校验头部 `%PDF`。

## 2. 图书馆资源导航(拿任意库的隧道入口)

图书馆页 `资源导航` 里的锚点,DOM href 是直链 `lib.hebmu.edu.cn/link/<N>/3`,
但站点 JS 会拦截点击并改走 WebVPN 隧道(**direct gotoAndWait 那个直链是错的**,
会 302 出隧道报「IP地址不在有效范围」)。流程:

```js
// 真实点击资源导航条目(如 FMRS/万方/ScienceDirect),等跳转后读 location.href
const a = [...document.querySelectorAll('a')].find(x => /万方医学网/.test(x.textContent))
const r = a.getBoundingClientRect()
await click([Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)])
// 之后 location.href 即该库的 webvpn 哈希 URL,记下来复用
```

注意资源导航模块可能要滚动后才渲染;模块里出现的 `link/N/3` 锚点是**点击后**
由 JS 改道的,不要抄 href 直接 goto。

## 3. 万方医学网通道(中文主力,实测 +20 篇/轮)

搜索框 `input[placeholder="请输入检索关键词"]`,检索按钮文本「检索」(回车无效必须点击)。
结果匹配:**归一化后全等**比较标题;中文标题才能命中,PubMed 行的英文标题命中率低。

进详情(`target='_self'` + click)后,按**当前论文 id** 找自己的下载链接 ——
页面侧栏的相关论文也带下载按钮,按"第一个找到的"选会拿错:

```js
const m = location.search.match(/id=([A-Za-z_0-9-]+)/i)   // PeriodicalPaper_xxx / DegreePaper_xxx
const myId = m[1].toLowerCase(); const shortId = myId.replace(/^periodicalpaper_/, '')
const mine = [...document.querySelectorAll('a[href*="MedFulltext"],a[href*="CMAJump"]')]
  .filter(a => { const h = a.href.toLowerCase(); return h.includes(myId) || h.includes(shortId) })
```

三种落点:

| 链接形态 | 含义 | 处理 |
|---|---|---|
| `f.med.wanfangdata.com.cn/MedFulltext?Id=…` | 期刊论文,可直下 | 真实点击,等文件落盘(慢下可重试一轮) |
| `…/MedFulltext?inline=True&Id=DegreePaper_…` | 学位论文,inline 阅读器 | 见 §3.1 |
| `med.wanfangdata.com.cn/Paper/CMAJump?id=…&url=…rs.yiigle.com/cmaid/<ID>` | 中华系列,跳 yiigle | 取出 cmaid,走 §4 API 链 |

检索无结果或无下载按钮 → 记失败,不硬重试。

### 3.1 学位论文 PDF 直取(绕过 inline 阅读器)

1. 详情页点 inline 链接(`target='_self'`),等 SPA 跳到
   `…ffe452d2…/URLFile/<编码文件名>`(浏览器 PDF 查看器,标签元数据可读全 URL)。
2. **先记下完整 URL**,再切回任意 webvpn 代理页,同源 fetch 该 URL:

```js
const b64 = await js(`(() => fetch(${JSON.stringify(pdfUrl)}, { credentials: 'include' })
  .then(r => r.arrayBuffer()).then(b => { const u = new Uint8Array(b); let s = ''
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000))
  return btoa(s) }))()`)
```

3. Node 侧 base64 解码,`%PDF-` 头校验后写盘。

### 3.2 英文标题桥接失败的模式

PubMed 收录的中文刊行,CSV 里只有英文标题,万方检索常 0 命中(如中华胃肠外科杂志
多数文章)。先试"英文标题直接搜",失败则要换桥:PubMed 页取 DOI / 中文标题,或
yiigle 站内按刊浏览。**未命中就记录,别硬凑相似度**(相似度匹配出过错卷)。

## 4. yiigle(中华医学期刊全文数据库)API 直下链(实测核心)

前提:**机构 IP(隧道)+ 个人账号登录**(登录必须发生在隧道内的 yiigle 页面上,
WebVPN 各目标主机独立 cookie 罐;用户在浏览器外部登录无效)。页面右上机构名旁
用户菜单可查登录态;未登录时点 PDF 会弹「阅读权限 请先登录」抽屉,点「个人账户登录」。

SPA 的按钮用合成/真实点击都不触发下载处理器 → **直接打 API**,在任意 webvpn 代理页
同源 fetch( yiigle 隧道 base + 接口):

```js
// 三步链:token → auth → pdf,resourceId = cmaid(万方 CMAJump href 的 url= 参数里抓)
const post = (u, d) => fetch(base + u, { method: 'POST', credentials: 'include',
  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }).then(r => r.json())
const tk = await post('/api/file/downloadPdfToken', { resourceId: pid })
//   tk.data.downloadToken;若 needCaptcha=true 见下方验证码
const au = await get(`/api/resource/auth?resourceId=${pid}&resPermType=d&reduceTimes=true`)
//   au.data.hasPerm === true → au.data.token
const pdf = await fetch(`${base}/api/file/downloadPdf?resourceId=${pid}&token=${au.data.token}&downloadToken=${tk.data.downloadToken}`,
  { credentials: 'include' }).then(r => r.arrayBuffer())
```

### 验证码(IP 风控,连下 3~4 篇后必触发)

downloadPdfToken 返回 `{needCaptcha:true, captchaId, message:"IP存在风险,需要验证码"}`:

1. `GET /api/file/captchaImage?captchaId=<id>&t=<ms>` → JPEG(120×40,4 位码)。
2. base64 存盘 → `read_image` 人读(4 位大小写字母数字;读错会换新 captchaId 重来)。
3. 带码重发:`post('/api/file/downloadPdfToken', { resourceId: pid, captchaCode: code, captchaId })`。

每篇都要码,流程照跑即可。yiigle 深链注意:`/cmaid/<id>` 可直达;`/login`、
`/Journal?q=`、`/body/pdf` 等 SPA 路由深链全 404,别试。

## 5. Zotero 本地 API v2(写链路,实测 107 篇)

Zotero Desktop 开着,端口 23119。**写操作要 API key**:

```bash
# 1) 授权(等用户在 Zotero 弹窗点 Allow;返回里有 key)
curl -X POST http://127.0.0.1:23119/api/local/authorize -H "Zotero-Server-ID: <serverId>" -d '{"appName":"dsh"}'
# 2) 之后所有请求带头:Zotero-Server-ID + Authorization: Bearer <key>
```

建条目(批量,`collections:[key]` 指定分类;`extra` 里写 `筛选清单No: <N>` 便于幂等):

```
POST /api/users/0/items   [{itemType:"journalArticle", title, creators:[{creatorType:"author", firstName, lastName}|{name}], ...}]
```

**附件挂载四步**(坑都在头和路径上):

```text
1. 建附件条目: itemType:imported_file, linkMode:imported_file, parentItem:<条目key>, filename
2. 认证:   POST /api/users/0/items/<附件key>/file
          头: If-None-Match: *   (新文件;已有文件用 If-Match: <version>)
          体: md5=<md5>&filename=<urlencode>&filesize=<n>&mtime=<ms>   (form-urlencoded)
          → { uploadKey }
3. 上传:   POST http://127.0.0.1:23119/api/local/uploads/<uploadKey>   ← 顶级路径!
          头: Content-Type: application/pdf;  体: 原始字节;  期望 201
          (拼成 /api/users/0/local/uploads/... 会 404 —— 踩过)
4. 注册:   再 POST /items/<附件key>/file,体: upload=<uploadKey>&md5=…&filename=…  期望 204
```

其他坑:

- DELETE 条目用 `If-Unmodified-Since-Version: <version>`(不是 If-Match),204 即成。
- 本地 API **忽略 `collection=` 查询参数**(过滤后计数仍返回全库总数);校验分类归属要
  读每条的 `data.collections`。
- 文件名中文无需特殊处理,但 file 认证体里的 filename 要 `urlencode`。
- 校验:逐条 `GET /items/<key>/children` 数 `contentType == "application/pdf"`。

## 6. 知网通道(保留,原路线实测)

原固化的知网路线继续有效:入口直达 → 检索(首页 `textarea[name="txt_SearchText"]`,
结果页 `input[placeholder="中文文献、外文文献"]`,点 `.search-btn`)→ 结果行
`a.fz14` 设 `target='_self'` 后 `.click()` → 详情页 `li.btn-dlpdf`/`li.btn-dlcaj`
真实鼠标点击 → `history.back()` 复用结果页。

- 滑块可见性按 `getBoundingClientRect().y > -500` 判,**别用 offsetParent**。
- 无按钮/无结果 = 知网无全文(中华系列独家在 yiigle),转 §3/§4。
- 标题破折号陷阱:`c—fos`(U+2014)逐字保留,否则零命中。

## 7. 状态管理约定(批量任务)

- 每通道一个 `_<通道>_state.json`:`{No: {title, status, file?}}`;状态机
  `pending → downloaded → done`,失败细分原因(wf_not_found / wf_no_download /
  wf_cma_jump / wf_click_no_file / yg_err…)。
- 落盘即改名 `<No>_<标题前20字>.pdf` 移入工作目录,再更新状态。
- 失败汇总 `download_failures.csv`(utf-8-sig),列:No/Title/Journal/Source/PMID/
  PubMedURL/FailStage;**不硬重试**,click_no_file 允许一轮重试。
- Zotero 幂等:导入前按 `extra` 里的 `筛选清单No` 枚举已有条目,只增量建。

## 8. 实测战绩(2026-08-31)

- 知网 +52(检索-按钮-滑块全流程),万方 +11(含 3 篇学位论文直取),
  yiigle +17(中华胃肠外科/中华医史/中华肿瘤,验证码逐篇人读),
  PubMed 免登录 +28(前轮),sci-hub +19。共 126/181 篇 PDF,全部带附件入 Zotero
  (NMA/英文/中文三分类)。

## 9. FMRS 文献传递(www.metstr.com,个人账号,实测 2026-08-31)

用户个人账号(江万里)订阅外文医学信息资源检索平台,入口 `newfmrs.metstr.com`。
sci-hub 收不进的近年外文论文走这里申请全文投递(邮件/FMRS 站内信「我的邮箱」,
人工处理,数小时~数天,不是即时下载)。到货看 metstr.com 顶栏「我的邮箱」。

单篇提交流程:

1. `newfmrs.metstr.com/search?query=<标题前6-7个词>`(全标题会过度约束反而空结果)。
2. 点结果行 `span.el-popover__reference-wrapper`(文本"全文请求")。
3. 弹层:接收邮箱已填(平台内邮箱),承诺 checkbox 默认已勾,点 `.right`(确认提交)。
4. toast「提交成功!」;服务端核对:metstr.com/request「我的请求」列表(状态=正在处理)。

坑:

- **标题匹配只看弹层前 140 字符(标题区)并做归一化比对** —— 整个弹层 innerText
  含相关推荐,会出现包含式误配(实测错配 3 篇:Improved quality of life→Ibandronic、
  Robotic spleen-preserving→Cranial Approach、Clinical outcome→Double Shouldering)。
- 错配请求在 metstr.com/request 逐行点「删除」;该删除链接对合成 click 与 CDP
  真实点击均无响应(el-popconfirm 不弹出),需用户手点。
- checkbox 要点 `.el-checkbox__inner`(原生 input 隐藏,点它无效)。
- FMRS 检索空结果(noresult)= 未收录或索引标题变体,记失败,别拿相近题凑数。
- FMRS 每条结果自带 DOI + sci-hub.vg 链接 —— sci-hub 批量的入口:CDP
  `Fetch.enable`(urlPattern '*.pdf', requestStage Response)→ gotoAndWait PDF →
  drainEvents → getResponseBody → base64 落盘;`serverFetch` 损毁二进制不能用;
  Page.setDownloadBehavior 在该 Chromium 无效;2023 后新文献大多 sci_miss。

## 选择器/接口速查

| 目标 | 值 |
|---|---|
| 万方搜索框 | `input[placeholder="请输入检索关键词"]`,按钮文本「检索」 |
| 万方结果链接 | `a[href*="Paper/Detail"]`,归一化标题全等 |
| 万方自己的下载链接 | 按 `location.search` 的 id 匹配 `MedFulltext` |
| 学位论文阅读器 | `…ffe452d2…/URLFile/…`(标签 URL) |
| yiigle token | `POST /api/file/downloadPdfToken {resourceId[,captchaCode,captchaId]}` |
| yiigle 验证码图 | `GET /api/file/captchaImage?captchaId=<id>&t=<ms>` |
| yiigle 权限 | `GET /api/resource/auth?resourceId=<id>&resPermType=d&reduceTimes=true` |
| yiigle PDF | `GET /api/file/downloadPdf?resourceId=<id>&token=<t>&downloadToken=<d>` |
| Zotero 文件认证 | `POST /api/users/0/items/<key>/file` + `If-None-Match: *` |
| Zotero 上传 | `POST /api/local/uploads/<uploadKey>`(顶级路径) |
| Zotero 删除头 | `If-Unmodified-Since-Version: <version>` |
| 万方题录直取 | `GET med.wanfangdata.com.cn/Search/ExportTo?artilceIds=<csv>&exportType=Endnote`(注意拼写 artilceIds) |
| 万方记录 ID | 结果行 `input.item-checkbox[data-itemid]` |
| SinoMed 题录 | 结果行 `input[name="ids"]` 的 `mydata` 属性(逗号=分隔全字段)+`title` |
| SinoMed WBM | 快检框不支持 OR,必须走高级检索表达式框 |
| CENTRAL 行组合 | 空行直接键入 `#2 OR ((#4 OR #5) AND #6)`,MeSH 行必须走 picker |
| CENTRAL 导出 | `sessionStorage.exportOptions` 按类型存 `{exportAll, articleIds}`;RIS 对应 `downloadType=endnote` |

## 10. 无 DOI 中文论文 → cmaid 定位三路桥(实测 2026-08-31)

PubMed 无 DOI 的中华系列中文论文(摘要页 ArticleId 为空),按顺序试:

1. **DOI→LinkIn 桥**(有 DOI 时首选,公开站不占隧道):`https://doi.org/<doi>` 302 →
   `www.yiigle.com/LinkIn.do?linkin_type=DOI&DOI=<doi>`(小 Vue SPA)→
   ego 打开等 ~10s 读 `location.href` 得 `rs.yiigle.com/cmaid/<id>`。
2. **期刊官网过刊目录**(无 DOI):中华胃肠外科杂志官网 `zhwcwkzz.yiigle.com`
   (yiigle 子域!),过刊页 `gkmc/index.htm` 只列 2020+;期目录 URL 规律
   `/CN441530<YYYY><2位期号>/index.jhtml?tplReset=qikan`,页内文章标题直接挂
   `rs.yiigle.com/cmaid/<id>` 链接。⚠️ 别与中华消化外科 `zhxhwkzz.xml-journal.net`
   (`/cn/article/<年>/<期>` 结构)搞混。PubMed 英译标题常与期刊官方中文标题差异巨大
   (double tracks anastomosis ↔ 改良空肠间置术),**用卷期页码定位最稳**。
3. **万方短特征词**:官方中文标题的全等匹配失败时,取标题中段 4-8 字重搜。
   f.med.wanfangdata 全文接口在 WebVPN 重登后可能要求个人登录(会话握手失效),
   此时改走 yiigle。

拿到 cmaid 后走 §8 yiigle API 链下载;批量时先全部试探 token,needCaptcha 的
集中存图人读(`read_image`)后一次提交,验证码约 60% 一次通过。

## 11. FMRS 邮箱收割(mail.metstr.net,实测 2026-08-31)

文献传递到货在 FMRS 专用邮箱(Winmail)。入口:`www.metstr.com` 顶栏「我的邮箱」
点击 → 自动发新 token 跳 `mail.metstr.net/main.php?token=<t>#msglist`(旧 token
过期就用这招重进;邮件保留 20 天,别囤)。

- 读视图是**单页渲染全部消息**:所有附件 `act=download` 链接同页可取,
  按 `msgid=N&attach=K` 去重;同 origin `fetch` 直取 base64,`%PDF` 校验。
- **附件文件名自带 PMID**:`P<PMID>_<num>.pdf`(少数 `DOIE…`)→ 直接映射筛选清单 No,
  零标题匹配成本。
- 提交请求后 1-3 天内分批到货,一次 7-9 篇/封;「温馨提示:高难文献正在查找」
  = 还在处理,等下一轮即可。

## 12. 万方医学网题录直取管线(实测 2026-09-05,5701 条)

批量导出按钮走表单+弹窗,合成点击经常静默失败。直接打接口:

1. 检索照常用(§3),分库用 facet 复选框+「筛选」(直接点 facet 文字无效);
   分库切换最稳的是改 URL:`资源类型_f=<中文期刊|学位论文|会议论文|外文期刊>`。
2. 分页是直链 `&p=N`(共 N 页);跳页框会误伤年份框,认准跟在 `/N` 旁边的那个。
   单页 10 条锁死,无 20/50 选项。
3. 每页采 `input.item-checkbox[data-itemid]`(免点选!checkbox 的 value恒为 on 没用),
   200 个一组调 `GET med.wanfangdata.com.cn/Search/ExportTo?artilceIds=<csv>&exportType=Endnote`
   (注意官方拼写就是 artilceIds,带隧道 cookies),回包即 EndNote 文本流,按字节存 `.enw`。
4. 转码坑:回包 bytes → base64 必须走 `String.fromCharCode` 裸拼 + `btoa`,
   任何 unescape/encodeURIComponent 中转都会把中文烧成 Latin-1 乱码。
5. 反爬:约 100 页连翻后出滑块(且 IP 会浮动丢机构上下文);降速(页间隔 ≥6s)+
   见滑块就停手,等用户拖完再续。购物车 200/批是展示上限,直取链不受此限
   (但单次 URL 过长会 414,200 一组最稳)。
6. 不可选行约 0.5–4%(无 checkbox,多为未购记录),终稿如实披露;页码用
   `b.current` 校验,跑偏立即停。

## 13. SinoMed 隧道与 mydata 直采(实测 2026-09-05,CBM 1960+WBM 1939)

1. 资源导航点击经常回弹图书馆首页;**直接 goto 解析器 URL**
   `…/link/309/3`(隧道内)即落 SinoMed 隧道页,认准「欢迎 河北医科大学」。
2. 隧道会话约 30 分钟失效(症状:列表清空+「登录失效,请重新登录」),
   重进解析器 URL 即恢复,别在失效态上硬磨。
3. 记录行 `input[name="ids"]` 的 `mydata` 属性自带全题录
   (ui/作者/单位/刊年月卷期页,`title` 属性即题名),100 条/页(jQuery-change 触发),
   下一页链采 20 页即全收,按 ui 去重(本轮零重复)。
4. **快检框不支持 OR**(带 OR 直接 0 条);WBM 英文式必须走高级检索表达式框
   (textarea#searchword),完整布尔一次通过。
5. CBM 中文式与 WBM 英文式分开跑分开存(指南要求),不要混。

## 14. yiigle 跨刊题录清单(实测 2026-09-05,372 条)

平台无批量 RIS 导出时走结构化清单:9 词组逐个 `Paper/Search` + `.el-pager li`
翻页,按 `.s_searchResult_li` 采。**标题锚点=首个长文本链接**
(首个 cmaid 链接经常是「全文HTML」按钮,误抓则全坏);刊名《》/年份卷期正则另取;
cmaid 取卡片内任一 `cmaid/(\d+)` 链接。9 词组后 6 个多为首词子集(零新增属正常,
用 cmaid 去重验证,别当漏抓)。存 `cmaid/title/authors/journal/yearvol/groups` CSV。

## 15. CENTRAL Cochrane 实战(实测 2026-09-05,447 条 PARTIAL)

1. Manager 行内手打 MeSH(`[...]`)必被校验器拒;MeSH 必须走 MeSH browser 页
   (lookup→Exact match→Explode→Select→Add to search manager)。
2. 行间组合直接在空行键入 `#2 OR ((#4 OR #5) AND #6)`,Continue 可用。
3. 幽灵 facet 排查:结果被压到个位数且年份面全 0 → 检查 `Retracted Publication`
   等筛选面是否被误勾,点 pill ✕ 去掉。
4. Trials 内嵌面板可能**只渲染条目不渲染选择/导出控件**
   (25 条 label 对 0 个 checkbox 输入),而 Reviews 分区正常——此时不要反复点登录,
   直接改收结构化清单:18 页逐页采 CN 号+标题+来源标签(CN 号零重复即闭合)。
5. 清单后做三级匹配:标准化标题 exact/contain → PubMed API distinctive-token
   反查(accept 条件 inter≥8 且 j≥0.4)→ 注册库标题匹配;剩下 `central_only` 走详情页
   补作者/刊/年/DOI(墙外可见,摘要墙内),`review` 对留人工裁决。
6. RIS 不是必须的;方法学要的是可复现+全捕获+每条有去向+限制透明披露。

## 16. 注册库横扫(实测 2026-09-05,CT.gov 286/ChiCTR 36/CRIS 1/ICTRP 139)

- **CT.gov**:API v2(`query.term`+`pageSize=100`+`nextPageToken`),4 宽术语按 NCT 去重,
  全字段 JSON + 摘要 CSV 双存档;旧库 NCT 全保留即连续性通过。
- **ChiCTR**:搜索 DIV `#handle-search` 是 jQuery 绑定,原生 click/回车无效,
  必须 `jQuery(...).trigger('click')`;10 条/页数字翻页;旧号段(TRC/IPC/IOR/IIR)合法。
- **CRIS**:先调英文,搜 `input[name="searchWord"]`,提交调 **`fn_search(1,true)`**
  (顶部框 goSearch 在该页无 subForm 会报错);韩文 0 条有页面证据即有效结论。
- **ICTRP**:`Trial2.aspx?TrialID=` 正则采号(前缀即来源库),10 条/页数字+`>>`末页;
  与 CT.gov/ChiCTR 重叠高,合并阶段按注册号+secondary ID 去重。
- **jRCT**:curl 与 Chromium 双通道 SSL 握手失败即记 deviation(附证据),日本试验由
  ICTRP-JPRN 替代覆盖,写进局限性,不反复重试。
