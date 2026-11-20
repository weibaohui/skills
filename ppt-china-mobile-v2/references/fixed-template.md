# 固定模板使用

模板ID：`cm-internal-report-20261105`。默认复制 `assets/internal-report-template.pptx` 的实际源页；两个Skill共享相同固定版式，区别在正文信息密度和图形使用要求。原件及独立资产的SHA-256记录在manifest/provenance中。

## 单页种子

在本Skill目录执行，路径按当前任务替换：

```sh
python3 scripts/template_page.py --type body --fields /path/to/body-fields.json --output /path/to/body-seed.pptx
```

字段文件为UTF-8 JSON：

| `--type` | 源页 | 字段文件内容 |
|---|---:|---|
| `cover` | 1 | `{"title":"安全能力建设方案","organization":"编制部门","date":"2026年11月"}` |
| `contents` | 2 | `{"items":["建设背景","总体方案","建设内容","实施安排"]}` |
| `chapter` | 2派生 | `{"items":["建设背景","总体方案","建设内容","实施安排"],"activeIndex":1}` |
| `body` | 3 | `{"title":"大模型应用安全防护建设方案"}` |
| `closing` | 4 | `{"text":"汇报完毕"}` |

示例部门和日期须换为当前任务信息，缺失的organization/date省略即可。`activeIndex`从0计数。目录脚本仅支持恰4个条目；其他数量需用编辑工具适配原成套图形，保留真实章节和约定页数。

脚本使用标准库直接复制OOXML源页并替换指定字段，保留原始母版、布局和图片字节，不重绘背景，不依赖python-pptx。原件和已存在的输出不会被覆盖。输出只含所选一页，是后续编辑的模板种子；正文种子仅有模板Logo和已填标题，不能作为完整内容页交付。

## 填充正文

使用当前Presentations能力和`@oai/artifact-tool`导入种子，例如：

```js
const deck = await PresentationFile.importPptx(await FileBlob.load(seedPath));
const slide = deck.slides.getItem(0);
// 在x=24,y=90,w=1232,h=606px范围内添加本次原生图文内容。
// 此处继承了模板Logo并已有标题，不再次调用header或添加背景/Logo。
```

组件接口和导入行为以当前工具文档为准。所有新增内容先按本Skill完成文案和布局规划；模板壳固定，正文分区、图文比例和嵌套层次可随内容变化。复用 `cm-components.mjs` 的panel/cell/nativeTable等内容组件时，坐标必须落在新安全区内。

需要多页时逐页生成与填写，按SKILL.md逐页交付。不得用模板四页数量限制整套报告的实际页数，也不得先批量生成整套再拆分冒充逐页制作。

## 保真检查

保留源页引用的layout1/layout4及slideMaster1。Logo框含透明留白并且负y，必须原样保留映射；源母版里的日期、页码和编辑提示不是当前可见内容，不能自动显示。

导入导出后将首尾背景、目录阴影/渐变/组合、标题位置和Logo与模板渲染比较。若导入工具丢失固定对象，不以整页截图替代可编辑目录或正文；修复相应对象，或对原始PPTX采用局部OOXML编辑以保留模板。最终交付仍须渲染检查。
