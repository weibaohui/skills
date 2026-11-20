#!/usr/bin/env bash
# ============================================================================
# FDE 标准操作流程模板 (workflow.sh)
# 用途：演示「登录采集 → 校验 → 查空间 → 需求/缺陷操作」的完整调用顺序。
# 使用：复制本模板，按需修改 SPACE 与各操作段，然后 bash workflow.sh
# 说明：脚本本身不含业务逻辑，仅串联 scripts/ 下的正式工具脚本。
# ============================================================================
set -euo pipefail

# 定位到 skill 根目录（本模板位于 templates/ 下）
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$SKILL_DIR/scripts"
SPACE="${SPACE:-G2026000S}"   # 可用环境变量覆盖默认空间码

echo "================ FDE 工作流开始 ================"
echo "Skill 目录: $SKILL_DIR"
echo "目标空间  : $SPACE"

# --- 步骤 1：凭证采集（首次或过期时执行；登录页固定为 micrologin/#/login）---
# python3 "$SCRIPTS/fetch_browser_auth.py" interactive

# --- 步骤 2：校验凭证有效性 ---
python3 "$SCRIPTS/auth_login.py" --check

# --- 步骤 3：确认研发空间 ---
python3 "$SCRIPTS/manage_spaces.py" list
python3 "$SCRIPTS/manage_spaces.py" set --code "$SPACE"

# --- 步骤 4：需求清单 ---
python3 "$SCRIPTS/manage_demands.py" list --space "$SPACE"

# --- 步骤 5：（按需）字段编辑 —— 写后会自动读回核对 ---
# python3 "$SCRIPTS/manage_demands.py" update --space "$SPACE" --id <ID> \
#   --set "优先级=P1" --set "负责人=张三"

# --- 步骤 6：（按需）缺陷清单 ---
# python3 "$SCRIPTS/manage_bugs.py" list --space "$SPACE"

echo "================ FDE 工作流结束 ================"
