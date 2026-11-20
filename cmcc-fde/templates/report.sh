#!/usr/bin/env bash
# ============================================================================
# FDE 报告生成模板 (report.sh)
# 用途：把需求/缺陷/仓库等查询结果汇总为一份 Markdown 报告。
# 使用：复制本模板，修改 SPACE 与 OUT 变量后运行 bash report.sh
# 依赖：各查询结果由 scripts/ 下脚本输出，本模板负责重定向汇总。
# ============================================================================
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$SKILL_DIR/scripts"
SPACE="${SPACE:-G2026000S}"
OUT="${OUT:-$SKILL_DIR/fde_report_$(date +%Y%m%d_%H%M%S).md}"

{
  echo "# FDE 平台数据报告"
  echo
  echo "- 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- 空间编码: $SPACE"
  echo

  echo "## 研发空间清单"
  echo '```'
  python3 "$SCRIPTS/manage_spaces.py" list 2>&1
  echo '```'
  echo

  echo "## 需求清单"
  echo '```'
  python3 "$SCRIPTS/manage_demands.py" list --space "$SPACE" 2>&1
  echo '```'
  echo

  echo "## 缺陷清单"
  echo '```'
  python3 "$SCRIPTS/manage_bugs.py" list --space "$SPACE" 2>&1
  echo '```'
  echo

  echo "## 资产统计"
  echo '```'
  python3 "$SCRIPTS/manage_assets.py" stats 2>&1
  echo '```'
} > "$OUT"

echo "[✓] 报告已生成: $OUT"
