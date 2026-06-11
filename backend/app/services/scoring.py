from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring_rules.json"


@dataclass(frozen=True)
class LocationSignals:
    category: str
    competitor_count_500m: int = 0
    competitor_count_1000m: int = 0
    residential_poi_count: int = 0
    office_poi_count: int = 0
    school_poi_count: int = 0
    transit_poi_count: int = 0
    commercial_poi_count: int = 0
    complementary_poi_count: int = 0
    rent_monthly: Optional[float] = None
    budget_monthly: Optional[float] = None


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


@lru_cache
def load_scoring_rules() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def score_location(signals: LocationSignals) -> dict:
    rules = load_scoring_rules()
    traffic_score = _score_traffic(signals, rules)
    competition_score = _score_competition(signals, rules)
    match_score = _score_match(signals, rules)
    cost_score = _score_cost(signals, rules)
    transit_score = _score_transit(signals, rules)
    risk_score = _score_risk(signals, rules, traffic_score=traffic_score)

    dimensions = [
        {
            "name": "客流潜力",
            "score": traffic_score,
            "reason": (
                f"周边住宅{signals.residential_poi_count}个、办公{signals.office_poi_count}个、"
                f"学校{signals.school_poi_count}个、交通节点{signals.transit_poi_count}个、"
                f"商业{signals.commercial_poi_count}个，按客流代理权重归一化估算。"
            ),
        },
        {
            "name": "竞争压力",
            "score": competition_score,
            "reason": _competition_reason(signals, competition_score),
        },
        {
            "name": "消费匹配",
            "score": match_score,
            "reason": _match_reason(signals, rules, match_score),
        },
        {
            "name": "成本压力",
            "score": cost_score,
            "reason": _cost_reason(signals, rules, cost_score),
        },
        {
            "name": "交通可达",
            "score": transit_score,
            "reason": (
                f"周边交通设施{signals.transit_poi_count}个，并参考商业配套{signals.commercial_poi_count}个，"
                "用于估算到店便利度。"
            ),
        },
        {
            "name": "经营风险",
            "score": risk_score,
            "reason": _risk_reason(signals, traffic_score=traffic_score, competition_score=competition_score, cost_score=cost_score),
        },
    ]

    weights = rules["weights"]
    weighted_score = clamp(sum(item["score"] * float(weights[item["name"]]) for item in dimensions))
    score_cap_notes = _score_cap_notes(signals, rules)
    total_score = _apply_score_caps(weighted_score, score_cap_notes)
    level = _level_for_score(total_score, rules)
    insights = _model_insights(
        signals,
        rules,
        traffic_score=traffic_score,
        cost_score=cost_score,
        weighted_score=weighted_score,
        total_score=total_score,
        score_cap_notes=score_cap_notes,
    )

    return {
        "total_score": total_score,
        "level": level,
        "dimensions": dimensions,
        "model_insights": insights,
        "next_actions": [
            "实地观察早晚高峰、午晚餐和周末客流。",
            "核实500米内同品类竞品的价格、评分、排队和外卖销量。",
            "确认租金、转让费、装修费、人力和平台费用，补齐真实成本假设。",
            "把IRS和哈夫结果视为基于公开数据和假设的模拟，不作为绝对预测。",
            *[note["reason"] for note in score_cap_notes],
        ],
    }


def _score_traffic(signals: LocationSignals, rules: dict[str, Any]) -> int:
    config = rules["traffic"]
    value = float(config["base"])
    for field in _poi_signal_fields():
        value += getattr(signals, field) * float(config.get(field, 0))
    return clamp(value)


def _score_competition(signals: LocationSignals, rules: dict[str, Any]) -> int:
    config = rules["competition"]
    far_competitors = max(signals.competitor_count_1000m - signals.competitor_count_500m, 0)
    penalty = (
        signals.competitor_count_500m * float(config["penalty_500m"])
        + far_competitors * float(config["penalty_1000m"])
    )
    return clamp(100 - penalty)


def _score_match(signals: LocationSignals, rules: dict[str, Any]) -> int:
    config = rules["category_match"]
    profile = _category_profile(signals.category, config)
    value = float(config["base"])
    for field in _poi_signal_fields():
        value += getattr(signals, field) * float(profile.get(field, 0))
    return clamp(value)


def _score_cost(signals: LocationSignals, rules: dict[str, Any]) -> int:
    config = rules["cost"]
    if not signals.rent_monthly or not signals.budget_monthly:
        return clamp(float(config["default_score"]))
    rent_ratio = signals.rent_monthly / max(signals.budget_monthly, 1)
    return clamp(100 - rent_ratio * float(config["rent_budget_multiplier"]))


def _score_transit(signals: LocationSignals, rules: dict[str, Any]) -> int:
    config = rules["transit"]
    value = (
        float(config["base"])
        + signals.transit_poi_count * float(config["transit_poi_count"])
        + signals.commercial_poi_count * float(config["commercial_bonus"])
    )
    return clamp(value)


def _score_risk(signals: LocationSignals, rules: dict[str, Any], *, traffic_score: int) -> int:
    config = rules["risk"]
    value = float(config["base"])
    value -= signals.competitor_count_500m * float(config["competitor_500m_penalty"])
    value -= signals.competitor_count_1000m * float(config["competitor_1000m_penalty"])

    if signals.rent_monthly and signals.budget_monthly:
        rent_ratio = signals.rent_monthly / max(signals.budget_monthly, 1)
        if rent_ratio > float(config["rent_ratio_warning"]):
            value -= (rent_ratio - float(config["rent_ratio_warning"])) * float(config["rent_ratio_penalty_multiplier"])

    if traffic_score < int(config["low_traffic_threshold"]):
        value -= float(config["low_traffic_penalty"])
    if _single_customer_group_risk(signals):
        value -= float(config["single_customer_group_penalty"])

    return clamp(value)


def _competition_reason(signals: LocationSignals, score: int) -> str:
    if signals.competitor_count_500m:
        prefix = f"500米内有{signals.competitor_count_500m}家同品类商家"
    else:
        prefix = "500米内未发现明显同品类商家"
    if score < 60:
        return f"{prefix}，1000米内共{signals.competitor_count_1000m}家，竞争压力偏高。"
    if score < 80:
        return f"{prefix}，1000米内共{signals.competitor_count_1000m}家，存在一定竞争。"
    return f"{prefix}，1000米内共{signals.competitor_count_1000m}家，竞争压力相对可控。"


def _match_reason(signals: LocationSignals, rules: dict[str, Any], score: int) -> str:
    profile_name = _matched_profile_name(signals.category, rules["category_match"])
    if score >= 80:
        tone = "匹配度较高"
    elif score >= 60:
        tone = "匹配度中等"
    else:
        tone = "匹配度偏弱"
    return (
        f"按“{profile_name or '通用品类'}”规则评估，周边办公、住宅、学校、商业和互补业态共同形成需求代理，"
        f"当前与{signals.category}的消费场景{tone}。"
    )


def _cost_reason(signals: LocationSignals, rules: dict[str, Any], score: int) -> str:
    if not signals.rent_monthly or not signals.budget_monthly:
        return f"未填写完整租金和预算，暂用默认成本分{score}分；后续应补充租金、人力、原料和平台费用。"
    rent_ratio = signals.rent_monthly / max(signals.budget_monthly, 1)
    percent = round(rent_ratio * 100, 1)
    warning_ratio = float(rules["cost"]["warning_ratio"])
    if rent_ratio >= float(rules["cost"]["high_ratio"]):
        tone = "成本压力较高"
    elif rent_ratio >= warning_ratio:
        tone = "成本压力需要关注"
    else:
        tone = "成本压力相对可控"
    return f"月租金约占月预算{percent}%，{tone}；MVP暂未纳入转让费、装修摊销和人力成本。"


def _risk_reason(signals: LocationSignals, *, traffic_score: int, competition_score: int, cost_score: int) -> str:
    risk_items: list[str] = []
    if competition_score < 70:
        risk_items.append("同品类竞争")
    if cost_score < 70:
        risk_items.append("租金/预算比例")
    if traffic_score < 60:
        risk_items.append("客流代理不足")
    if _single_customer_group_risk(signals):
        risk_items.append("客群结构偏单一")
    if not risk_items:
        return "当前规则未发现明显高风险项；后续会加入施工、政策、淡旺季和外卖平台变化。"
    return f"主要风险来自{'、'.join(risk_items)}；后续会加入施工、政策、淡旺季和外卖平台变化。"


def _model_insights(
    signals: LocationSignals,
    rules: dict[str, Any],
    *,
    traffic_score: int,
    cost_score: int,
    weighted_score: int,
    total_score: int,
    score_cap_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    irs = _irs_insight(signals, rules)
    huff = _huff_insight(signals, rules, traffic_score=traffic_score, cost_score=cost_score)
    return {
        "version": rules["version"],
        "disclaimer": "以下IRS与哈夫模型为基于公开POI数据和规则假设的模拟，不代表绝对预测结果。",
        "irs": irs,
        "huff": huff,
        "calibration": _calibration_insight(
            signals,
            rules,
            weighted_score=weighted_score,
            total_score=total_score,
            score_cap_notes=score_cap_notes,
        ),
    }


def _calibration_insight(
    signals: LocationSignals,
    rules: dict[str, Any],
    *,
    weighted_score: int,
    total_score: int,
    score_cap_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    confidence = _data_confidence(signals, rules)
    if score_cap_notes:
        explanation = f"原始加权分为{weighted_score}分，因触发强竞争规则，最终分数调整为{total_score}分。"
    else:
        explanation = f"原始加权分为{weighted_score}分，未触发竞品密集封顶规则。"
    return {
        "name": "保守校准",
        "weighted_score": weighted_score,
        "final_score": total_score,
        "applied_caps": score_cap_notes,
        "data_confidence": confidence,
        "explanation": explanation,
    }


def _irs_insight(signals: LocationSignals, rules: dict[str, Any]) -> dict[str, Any]:
    config = rules["irs"]
    demand = sum(getattr(signals, field) * float(weight) for field, weight in config["demand_weights"].items())
    supply = sum(getattr(signals, field) * float(weight) for field, weight in config["supply_weights"].items())
    saturation_index = round(supply / max(demand, 1), 2)
    if saturation_index >= float(config["saturated_threshold"]):
        status = "偏饱和"
    elif saturation_index >= float(config["balanced_threshold"]):
        status = "接近平衡"
    else:
        status = "仍有空间"
    return {
        "name": "IRS零售饱和指数",
        "demand_estimate": round(demand, 2),
        "supply_estimate": round(supply, 2),
        "saturation_index": saturation_index,
        "status": status,
        "explanation": (
            f"用住宅、办公、学校、交通、商业和互补POI估算需求，用1000米竞品和部分商业/互补POI估算供给，"
            f"当前饱和指数约{saturation_index}，判断为“{status}”。"
        ),
    }


def _huff_insight(
    signals: LocationSignals,
    rules: dict[str, Any],
    *,
    traffic_score: int,
    cost_score: int,
) -> dict[str, Any]:
    config = rules["huff"]
    target_attractiveness = max(
        0.1,
        float(config["target_base_attractiveness"])
        + traffic_score * float(config["traffic_attractiveness_multiplier"])
        - (100 - cost_score) * float(config["cost_penalty_multiplier"]),
    )
    far_competitors = max(signals.competitor_count_1000m - signals.competitor_count_500m, 0)
    competitor_attractiveness = (
        signals.competitor_count_500m * float(config["near_competitor_attractiveness"])
        + far_competitors * float(config["far_competitor_attractiveness"])
    )
    probability = round(target_attractiveness / max(target_attractiveness + competitor_attractiveness, 0.1), 2)
    return {
        "name": "哈夫模型雏形",
        "capture_probability": probability,
        "target_attractiveness": round(target_attractiveness, 2),
        "competitor_attractiveness": round(competitor_attractiveness, 2),
        "explanation": (
            "MVP先用客流代理、成本压力和竞品数量近似吸引力；"
            f"当前目标店选择概率模拟值约{round(probability * 100)}%，仅用于相对比较。"
        ),
    }


def _score_cap_notes(signals: LocationSignals, rules: dict[str, Any]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for cap in rules.get("competition", {}).get("total_score_caps", []):
        min_500m = cap.get("competitor_count_500m_min")
        min_1000m = cap.get("competitor_count_1000m_min")
        triggered_by_500m = min_500m is not None and signals.competitor_count_500m >= int(min_500m)
        triggered_by_1000m = min_1000m is not None and signals.competitor_count_1000m >= int(min_1000m)
        if triggered_by_500m or triggered_by_1000m:
            notes.append(
                {
                    "max_total_score": int(cap["max_total_score"]),
                    "reason": str(cap["reason"]),
                }
            )
    return sorted(notes, key=lambda item: item["max_total_score"])[:1]


def _apply_score_caps(weighted_score: int, score_cap_notes: list[dict[str, Any]]) -> int:
    if not score_cap_notes:
        return weighted_score
    cap_score = min(int(note["max_total_score"]) for note in score_cap_notes)
    return min(weighted_score, cap_score)


def _data_confidence(signals: LocationSignals, rules: dict[str, Any]) -> dict[str, Any]:
    config = rules.get("data_confidence", {})
    signal_count = (
        sum(getattr(signals, field) for field in _poi_signal_fields())
        + signals.competitor_count_1000m
    )
    has_cost_input = bool(signals.rent_monthly and signals.budget_monthly)
    if signal_count >= int(config.get("high_signal_count", 60)) and has_cost_input:
        level = "高"
    elif signal_count >= int(config.get("medium_signal_count", 20)):
        level = "中"
    else:
        level = "低"

    notes: list[str] = []
    if signal_count < int(config.get("medium_signal_count", 20)):
        notes.append("周边POI样本偏少，分数需要人工复核。")
    if not has_cost_input:
        notes.append("未填写租金和预算，成本项采用保守默认分。")
    if signals.competitor_count_1000m == 0:
        notes.append("未识别到1000米内竞品，可能是竞品关键词或POI页数不足。")
    if not notes:
        notes.append("POI样本和成本输入较完整，当前分数可信度相对更高。")

    return {
        "level": level,
        "observed_signal_count": signal_count,
        "has_cost_input": has_cost_input,
        "explanation": " ".join(notes),
    }


def _category_profile(category: str, config: dict[str, Any]) -> dict[str, float]:
    profile_name = _matched_profile_name(category, config)
    if not profile_name:
        return config["default"]
    return config["profiles"][profile_name]


def _matched_profile_name(category: str, config: dict[str, Any]) -> Optional[str]:
    for key in config["profiles"]:
        if key in category:
            return key
    return None


def _level_for_score(total_score: int, rules: dict[str, Any]) -> str:
    for item in rules["levels"]:
        if total_score >= int(item["min_score"]):
            return str(item["level"])
    return "不建议"


def _single_customer_group_risk(signals: LocationSignals) -> bool:
    demand_counts = [
        signals.residential_poi_count,
        signals.office_poi_count,
        signals.school_poi_count,
        signals.commercial_poi_count,
    ]
    total = sum(demand_counts)
    return total >= 8 and max(demand_counts) / total >= 0.75


def _poi_signal_fields() -> tuple[str, ...]:
    return (
        "residential_poi_count",
        "office_poi_count",
        "school_poi_count",
        "transit_poi_count",
        "commercial_poi_count",
        "complementary_poi_count",
    )
