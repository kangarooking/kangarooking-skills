#!/usr/bin/env python3
"""
Internal design compiler for multi-agent-image.

This module extracts the prompt-compilation logic that was previously delegated
to an external runtime. It keeps the prompt-only path lightweight and reusable
from both CLI wrappers and Python call sites.
"""

from __future__ import annotations

from typing import Any


TASK_KEYWORDS = {
    "poster": ["海报", "poster", "封面", "主视觉", "campaign", "kv"],
    "product": ["商品", "产品", "电商", "product", "hero shot", "广告图", "首图"],
    "ppt": ["ppt", "幻灯片", "演示", "deck", "slide", "配图", "章节页"],
    "infographic": ["信息图", "infographic", "流程图", "结构图", "总结图", "overview"],
    "teaching": ["教学", "演示图", "讲解", "培训", "课件", "步骤图", "demo"],
}

DEFAULT_ASPECT = {
    "poster": "3:4",
    "product": "1:1",
    "ppt": "16:9",
    "infographic": "4:3",
    "teaching": "16:9",
}

QUALITY_MODEL = {
    "draft": "gpt-image-2",
    "final": "gpt-image-2",
    "premium": "gpt-image-2",
}

ASPECT_SIZES = {
    "1:1": {"2K": "2048x2048", "3K": "3072x3072"},
    "3:4": {"2K": "1728x2304", "3K": "2592x3456"},
    "4:3": {"2K": "2304x1728", "3K": "3456x2592"},
    "16:9": {"2K": "2848x1600", "3K": "4096x2304"},
    "9:16": {"2K": "1600x2848", "3K": "2304x4096"},
    "3:2": {"2K": "2496x1664", "3K": "3744x2496"},
    "2:3": {"2K": "1664x2496", "3K": "2496x3744"},
    "4:5": {"2K": "1840x2304", "3K": "2760x3456"},
    "5:4": {"2K": "2304x1840", "3K": "3456x2760"},
    "2:1": {"2K": "3072x1536", "3K": "4096x2048"},
    "1:2": {"2K": "1536x3072", "3K": "2048x4096"},
    "21:9": {"2K": "3360x1440", "3K": "5120x2160"},
    "9:21": {"2K": "1440x3360", "3K": "2160x5120"},
}

CORE_SOURCE_SECTIONS = [
    "## Your workflow",
    "## Output creation guidelines",
    "### How to do design work",
    "## Content Guidelines",
    "**Do not add filler content.**",
    "**Create a system up front:**",
    "**Avoid AI slop tropes:**",
]

TASK_SOURCE_SECTIONS = {
    "poster": [
        "### How to do design work",
        "## Content Guidelines",
        "**Do not add filler content.**",
    ],
    "product": [
        "## Output creation guidelines",
        "## Content Guidelines",
        "**Avoid AI slop tropes:**",
    ],
    "ppt": [
        "## Content Guidelines",
        "**Create a system up front:**",
        "**Use appropriate scales:**",
    ],
    "infographic": [
        "## Content Guidelines",
        "**Do not add filler content.**",
        "**Avoid AI slop tropes:**",
    ],
    "teaching": [
        "## Content Guidelines",
        "**Do not add filler content.**",
        "**Use appropriate scales:**",
    ],
}

DIRECTION_PROFILES = {
    "conservative": {
        "style_bias": "restrained, cleaner, corporate, polished, lower-risk",
        "energy_bias": "controlled, composed, authoritative",
        "composition_bias": "cleaner geometry, more negative space, lower background complexity",
        "palette_bias": "restricted palette with restrained accents",
        "detail_bias": "cleaner surfaces, less decorative detail",
    },
    "balanced": {
        "style_bias": "premium editorial, contemporary, polished, commercially strong",
        "energy_bias": "energetic but disciplined, confident, professional",
        "composition_bias": "clear hierarchy, dynamic but stable layout, deliberate focal contrast",
        "palette_bias": "premium neutrals with one strong accent family",
        "detail_bias": "hero-detail emphasis with a restrained background",
    },
    "bold": {
        "style_bias": "larger scale, more dramatic, more surprising, high-contrast",
        "energy_bias": "ambitious, high-energy, assertive, vivid",
        "composition_bias": "bolder crop, stronger scale contrast, more motion cues, still disciplined",
        "palette_bias": "higher-contrast palette with strong accent energy",
        "detail_bias": "high-impact hero detail, expressive texture, controlled spectacle",
    },
}

GLOBAL_DIRECTIVES = [
    "Start from purpose, audience, and channel rather than surface-level adjectives.",
    "Create a coherent visual system before detailing the image.",
    "Use one clear hero idea and preserve obvious hierarchy.",
    "Treat negative space and safe zones as design decisions, not leftover space.",
    "Avoid filler content, decorative noise, and meaningless visual data.",
    "Respect existing brand or context when available; if not, still commit to a clear direction.",
    "Avoid AI-slop tropes such as random HUD overlays, generic fog, empty gradients, and scattered floating debris.",
]

TASK_PROFILES = {
    "poster": {
        "communication_goal": "attract and persuade quickly in a campaign or recruitment context",
        "hero_strategy": "one dominant hero visual or symbolic concept, never a collage of equal-weight objects",
        "safe_zone": "reserve a clean, obvious text-safe zone in the upper third or one side for headline and CTA copy",
        "lighting": "crisp premium lighting with controlled contrast and energetic highlights",
        "palette": "restricted premium palette with disciplined neutrals and one energetic accent family",
        "detail_density": "hero-rich detail with restrained background complexity",
        "base_style": "editorial campaign key visual",
        "task_constraints": [
            "make the result feel campaign-ready rather than generic AI art",
            "prioritize focal hierarchy and typography-safe composition",
        ],
        "task_avoid": [
            "poster text rendered directly into the image unless explicitly requested",
            "random marketing icons and decorative interface fragments",
        ],
    },
    "product": {
        "communication_goal": "make the product feel desirable, premium, and commercially credible",
        "hero_strategy": "the product is the undisputed focal point with clear silhouette and edge readability",
        "safe_zone": "keep surrounding space supportive and uncluttered so the product remains dominant",
        "lighting": "commercial lighting that reveals material, finish, and shape without cheap reflections",
        "palette": "palette chosen to support product positioning rather than compete with the product",
        "detail_density": "high fidelity on the hero object, restrained props and background",
        "base_style": "high-end commercial product advertising",
        "task_constraints": [
            "preserve product proportions and perceived material integrity",
            "use props only when they reinforce product positioning",
        ],
        "task_avoid": [
            "oversized props stealing attention",
            "luxury claims paired with cheap lighting or noisy backgrounds",
        ],
    },
    "ppt": {
        "communication_goal": "support presentation storytelling with a clear, memorable visual metaphor",
        "hero_strategy": "a single strong metaphor or scene readable at presentation distance",
        "safe_zone": "reserve a large clean area for slide title and subtitle overlay",
        "lighting": "clean, legible lighting that supports shape readability over moodiness",
        "palette": "presentation-friendly palette with strong contrast and limited visual noise",
        "detail_density": "mid-detail image readable at a glance, not overloaded with tiny elements",
        "base_style": "presentation cover art",
        "task_constraints": [
            "favor readability from distance over excess detail",
            "keep enough room for future title placement",
        ],
        "task_avoid": [
            "ad-poster density",
            "tiny embedded text or fragile detail that disappears on slides",
        ],
    },
    "infographic": {
        "communication_goal": "communicate structure, grouping, and flow rather than literal dense data",
        "hero_strategy": "clear modular hierarchy with one dominant organizing principle",
        "safe_zone": "leave room for headings or labels without relying on the model to render tiny text",
        "lighting": "flat-to-controlled lighting that supports structure and clarity",
        "palette": "structured palette with clear grouping and low noise",
        "detail_density": "low-to-mid detail, with emphasis on grouping and directional logic",
        "base_style": "structured infographic-like visual system",
        "task_constraints": [
            "prioritize visual structure over fake data richness",
            "use symbolic clarity and modular composition",
        ],
        "task_avoid": [
            "tiny chart labels",
            "data slop, fake dashboards, and dense unreadable micro-details",
        ],
    },
    "teaching": {
        "communication_goal": "explain a process, comparison, or sequence with maximum clarity",
        "hero_strategy": "show the logic of the teaching point first, then add supporting visuals",
        "safe_zone": "keep panel or label areas simple and legible for later annotation",
        "lighting": "clear explanatory lighting, not overly cinematic",
        "palette": "clarity-first palette with simple grouping and controlled contrast",
        "detail_density": "mid-to-low detail with emphasis on readable sequence and large forms",
        "base_style": "instructional visual storytelling",
        "task_constraints": [
            "make sequence and cause-effect legible at first glance",
            "use big forms and obvious directional logic",
        ],
        "task_avoid": [
            "cinematic clutter that weakens explanation",
            "too many simultaneous steps in one frame",
        ],
    },
}


def detect_task(brief: str) -> str:
    text = brief.lower()
    scores: dict[str, int] = {}
    for task, keywords in TASK_KEYWORDS.items():
        scores[task] = sum(1 for keyword in keywords if keyword.lower() in text)
    best_task = max(scores, key=scores.get)
    return best_task if scores[best_task] > 0 else "poster"


def normalize_task(task: str, brief: str) -> str:
    return detect_task(brief) if task == "auto" else task


def choose_model(quality: str) -> str:
    return QUALITY_MODEL[quality]


def choose_size(task: str, aspect: str, quality: str) -> str:
    tier = "2K" if quality == "draft" or task in {"ppt", "infographic", "teaching"} else "3K"
    aspect_sizes = ASPECT_SIZES.get(aspect)
    if aspect_sizes:
        return aspect_sizes[tier]
    return ASPECT_SIZES[DEFAULT_ASPECT[task]][tier]


def join_phrases(items: list[str]) -> str:
    return "; ".join(item for item in items if item)


def unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def make_design_reasoning(
    *,
    brief: str,
    task: str,
    direction: str,
    audience: str | None = None,
    usage: str | None = None,
    brand: str | None = None,
    style: str | None = None,
    mood: str | None = None,
    goal: str | None = None,
    composition: str | None = None,
    constraints: str | None = None,
    avoid: str | None = None,
    safe_zone: str | None = None,
    lighting: str | None = None,
    palette: str | None = None,
    image: list[str] | None = None,
) -> dict[str, Any]:
    profile = TASK_PROFILES[task]
    direction_profile = DIRECTION_PROFILES[direction]

    brand_strategy = (
        f"use the provided brand/context: {brand}"
        if brand
        else "no explicit brand provided; commit to one coherent visual system instead of averaging styles"
    )

    reference_strategy = (
        "use provided reference images to preserve consistency and context"
        if image
        else "no reference images provided; rely on the compiled visual system and brief"
    )

    source_sections = unique_preserving_order(CORE_SOURCE_SECTIONS + TASK_SOURCE_SECTIONS[task])

    visual_system = [
        f"base mode: {profile['base_style']}",
        f"direction bias: {direction_profile['style_bias']}",
        f"energy bias: {direction_profile['energy_bias']}",
        f"composition bias: {direction_profile['composition_bias']}",
        f"palette bias: {direction_profile['palette_bias']}",
    ]

    hierarchy_strategy = [
        "one clear hero idea",
        profile["hero_strategy"],
        "secondary elements must support the hero rather than compete with it",
        "background should create rhythm, not narrative confusion",
    ]

    anti_filler_rules = [
        "every element must earn its place",
        "do not add objects, labels, icons, or stats that do not strengthen the core message",
        "if the frame feels empty, solve with scale, crop, rhythm, or texture rather than random extra elements",
    ]

    anti_slop_rules = [
        "avoid generic AI clutter",
        "avoid random floating UI fragments or HUD overlays",
        "avoid generic gradient fog with no composition logic",
        "avoid cheap neon cyberpunk treatment unless explicitly requested",
        "avoid noisy micro-detail that weakens the hierarchy",
    ]

    if avoid:
        anti_slop_rules.append(avoid)

    return {
        "task": task,
        "direction": direction,
        "communication_goal": goal or profile["communication_goal"],
        "audience": audience or "broad professional audience",
        "channel": usage or task,
        "brief": brief.strip(),
        "brand_strategy": brand_strategy,
        "reference_strategy": reference_strategy,
        "visual_system": visual_system,
        "hierarchy_strategy": hierarchy_strategy,
        "safe_zone_strategy": safe_zone or profile["safe_zone"],
        "lighting_strategy": lighting or profile["lighting"],
        "palette_strategy": palette or profile["palette"],
        "detail_density": direction_profile["detail_bias"] + "; " + profile["detail_density"],
        "style_direction": style or join_phrases(visual_system),
        "mood_direction": mood or direction_profile["energy_bias"],
        "composition_logic": composition or direction_profile["composition_bias"],
        "anti_filler_rules": anti_filler_rules,
        "anti_slop_rules": anti_slop_rules,
        "task_constraints": profile["task_constraints"] + ([constraints] if constraints else []),
        "task_avoid": profile["task_avoid"],
        "global_directives": GLOBAL_DIRECTIVES,
        "source_sections": source_sections,
        "primary_source_file": "internal:multi-agent-image/scripts/design_compiler.py",
    }


def compile_design_brief(reasoning: dict[str, Any], aspect: str) -> dict[str, Any]:
    return {
        "task": reasoning["task"],
        "direction": reasoning["direction"],
        "brief": reasoning["brief"],
        "communication_goal": reasoning["communication_goal"],
        "audience": reasoning["audience"],
        "channel": reasoning["channel"],
        "brand_strategy": reasoning["brand_strategy"],
        "reference_strategy": reasoning["reference_strategy"],
        "visual_system": join_phrases(reasoning["visual_system"]),
        "hierarchy": join_phrases(reasoning["hierarchy_strategy"]),
        "composition": reasoning["composition_logic"],
        "safe_zone": reasoning["safe_zone_strategy"],
        "lighting": reasoning["lighting_strategy"],
        "palette": reasoning["palette_strategy"],
        "detail_density": reasoning["detail_density"],
        "style_direction": reasoning["style_direction"],
        "mood": reasoning["mood_direction"],
        "constraints": join_phrases(reasoning["task_constraints"]),
        "avoid": join_phrases(reasoning["anti_slop_rules"] + reasoning["task_avoid"]),
        "aspect": aspect,
        "source_sections": reasoning["source_sections"],
    }


def build_prompt(brief: dict[str, Any]) -> str:
    parts = [
        f"Create a {brief['task']} image for {brief['channel']} aimed at {brief['audience']}.",
        f"Treat this as a design-led visual solving this brief: {brief['brief']}.",
        f"Communication goal: {brief['communication_goal']}.",
        "Translate the brief into one strong hero concept rather than many equal-weight elements.",
        f"Brand and context strategy: {brief['brand_strategy']}.",
        f"Visual system: {brief['visual_system']}.",
        f"Hierarchy: {brief['hierarchy']}.",
        f"Composition: {brief['composition']}.",
        f"Safe zone: {brief['safe_zone']}.",
        f"Lighting: {brief['lighting']}.",
        f"Color strategy: {brief['palette']}.",
        f"Detail density: {brief['detail_density']}.",
        f"Style direction: {brief['style_direction']}.",
        f"Mood: {brief['mood']}.",
        f"Aspect ratio: {brief['aspect']}.",
        f"Important constraints: {brief['constraints']}.",
        f"Avoid: {brief['avoid']}.",
        "Emphasize strong hierarchy, intentional whitespace, disciplined background complexity, and polished professional finish.",
    ]
    return " ".join(parts)


def compile_prompt_package(
    *,
    brief: str,
    task: str = "auto",
    direction: str = "balanced",
    aspect: str | None = None,
    quality: str = "final",
    audience: str | None = None,
    usage: str | None = None,
    brand: str | None = None,
    style: str | None = None,
    mood: str | None = None,
    goal: str | None = None,
    composition: str | None = None,
    constraints: str | None = None,
    avoid: str | None = None,
    safe_zone: str | None = None,
    lighting: str | None = None,
    palette: str | None = None,
    image: list[str] | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    normalized_task = normalize_task(task, brief)
    resolved_aspect = aspect or DEFAULT_ASPECT[normalized_task]
    design_reasoning = make_design_reasoning(
        brief=brief,
        task=normalized_task,
        direction=direction,
        audience=audience,
        usage=usage,
        brand=brand,
        style=style,
        mood=mood,
        goal=goal,
        composition=composition,
        constraints=constraints,
        avoid=avoid,
        safe_zone=safe_zone,
        lighting=lighting,
        palette=palette,
        image=image,
    )
    compiled_brief = compile_design_brief(design_reasoning, resolved_aspect)
    prompt = build_prompt(compiled_brief)
    model = model_override or choose_model(quality)
    size = choose_size(normalized_task, resolved_aspect, quality)

    return {
        "design_reasoning": design_reasoning,
        "compiled_brief": compiled_brief,
        "prompt": prompt,
        "settings": {
            "model": model,
            "size": size,
            "aspect": resolved_aspect,
            "direction": direction,
            "quality": quality,
        },
    }
