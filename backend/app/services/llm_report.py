def build_rule_based_summary(category: str, scoring_result: dict) -> str:
    total_score = scoring_result["total_score"]
    level = scoring_result["level"]
    dimensions = scoring_result["dimensions"]
    weakest = min(dimensions, key=lambda item: item["score"])
    strongest = max(dimensions, key=lambda item: item["score"])
    return (
        f"{category}当前评估为“{level}”，总分为 {total_score} 分。"
        f"优势主要来自“{strongest['name']}”，主要风险集中在“{weakest['name']}”。"
        "该结果基于当前输入、公开POI数据和规则模型生成，仅供选址参考。"
    )
